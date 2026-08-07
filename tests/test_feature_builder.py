"""Tests for the self-extension Feature Builder (tools/feature_builder.py).

The deepseek generation step is monkeypatched so the whole propose -> scan ->
sandbox -> apply -> rollback pipeline is exercised offline (no Ollama needed).
File-system side effects are redirected to a tmp dir and cleaned up.
"""
import json
import os

import pytest

import tools.feature_builder as fb


GOOD_TOOL = '''
TOOL_NAME = "temp_converter"
TOOL_DESCRIPTION = "Celsius to Fahrenheit converter"
SAMPLE_INPUT = {"celsius": 100}
def run(input_data: dict) -> dict:
    try:
        c = float(input_data.get("celsius", 0))
        return {"status": "success", "fahrenheit": c * 9 / 5 + 32}
    except Exception as e:
        return {"status": "error", "message": str(e)}
'''

UNSAFE_TOOL = '''
import os
TOOL_NAME = "danger"
TOOL_DESCRIPTION = "unsafe"
SAMPLE_INPUT = {}
def run(input_data: dict) -> dict:
    os.system("echo hacked")
    return {"status": "success"}
'''

BROKEN_TOOL = '''
TOOL_NAME = "broken"
TOOL_DESCRIPTION = "returns non-dict"
SAMPLE_INPUT = {}
def run(input_data: dict):
    return 123
'''


@pytest.fixture
def fb_env(tmp_path, monkeypatch):
    gen = tmp_path / "generated"
    gen.mkdir()
    monkeypatch.setattr(fb, "GENERATED_DIR", str(gen))
    monkeypatch.setattr(fb, "MANIFEST_PATH", str(gen / "manifest.json"))
    monkeypatch.setenv("CHHOTI_DON_RUNTIME_DIR", str(tmp_path / "rt"))
    return gen


def _stub_gen(monkeypatch, code):
    monkeypatch.setattr(fb, "_generate_code", lambda request: code)


# ── propose ───────────────────────────────────────────────────────────────────
def test_propose_good_tool_needs_confirmation(fb_env, monkeypatch):
    _stub_gen(monkeypatch, GOOD_TOOL)
    r = fb.feature_builder({"action": "propose", "request": "celsius to fahrenheit"})
    assert r["status"] == "confirmation_required"
    assert r["tool_name"] == "temp_converter"
    assert r["proposal_id"]
    assert "SMOKE_OK::" in (r.get("test_output") or "")


def test_empty_request_is_rejected(fb_env, monkeypatch):
    _stub_gen(monkeypatch, GOOD_TOOL)
    r = fb.feature_builder({"action": "propose", "request": "   "})
    assert r["status"] == "error"


def test_missing_contract_is_rejected(fb_env, monkeypatch):
    _stub_gen(monkeypatch, "x = 1\n")  # no def run / TOOL_NAME
    r = fb.feature_builder({"action": "propose", "request": "junk"})
    assert r["status"] == "error"
    assert "missing" in r["message"].lower()


# ── safety scan + sandbox ─────────────────────────────────────────────────────
def test_unsafe_code_blocked_before_execution(fb_env, monkeypatch):
    _stub_gen(monkeypatch, UNSAFE_TOOL)
    r = fb.feature_builder({"action": "propose", "request": "delete stuff"})
    assert r["status"] == "rejected"
    assert r["stage"] == "safety_scan"
    assert r["reasons"]


def test_broken_tool_fails_sandbox(fb_env, monkeypatch):
    _stub_gen(monkeypatch, BROKEN_TOOL)
    r = fb.feature_builder({"action": "propose", "request": "broken"})
    assert r["status"] == "test_failed"
    assert r["stage"] == "sandbox"


def test_static_scan_unit():
    ok, reasons = fb._static_safety_scan("import os\nos.system('x')\n")
    assert ok is False and reasons
    ok2, _ = fb._static_safety_scan("def run(d):\n    return {'x': 1}\n")
    assert ok2 is True


# ── apply gate + rollback ─────────────────────────────────────────────────────
def test_apply_requires_explicit_confirm(fb_env, monkeypatch):
    _stub_gen(monkeypatch, GOOD_TOOL)
    prop = fb.feature_builder({"action": "propose", "request": "temp"})
    pid = prop["proposal_id"]

    without = fb.feature_builder({"action": "apply", "proposal_id": pid})
    assert without["status"] == "confirmation_required"

    with_confirm = fb.feature_builder({"action": "apply", "proposal_id": pid, "confirm": True})
    assert with_confirm["status"] == "success"
    assert (fb_env / "temp_converter.py").exists()

    manifest = json.load(open(fb.MANIFEST_PATH, encoding="utf-8"))
    assert "temp_converter" in manifest


def test_apply_then_rollback(fb_env, monkeypatch):
    _stub_gen(monkeypatch, GOOD_TOOL)
    pid = fb.feature_builder({"action": "propose", "request": "temp"})["proposal_id"]
    fb.feature_builder({"action": "apply", "proposal_id": pid, "confirm": True})
    assert (fb_env / "temp_converter.py").exists()

    rb = fb.feature_builder({"action": "rollback", "feature": "temp_converter"})
    assert rb["status"] == "success"
    assert not (fb_env / "temp_converter.py").exists()
    assert "temp_converter" not in json.load(open(fb.MANIFEST_PATH, encoding="utf-8"))


def test_apply_unknown_proposal(fb_env):
    r = fb.feature_builder({"action": "apply", "proposal_id": "deadbeef", "confirm": True})
    assert r["status"] == "error"


# ── loader (uses the real tools/generated package path, with cleanup) ─────────
def test_loader_exposes_applied_tool_realpath():
    tool_name = "pytest_tmp_conv"
    slug = fb._safe_slug(tool_name)
    target = os.path.join(fb.GENERATED_DIR, f"{slug}.py")
    had_manifest = os.path.exists(fb.MANIFEST_PATH)
    manifest_backup = open(fb.MANIFEST_PATH, encoding="utf-8").read() if had_manifest else None
    try:
        os.makedirs(fb.GENERATED_DIR, exist_ok=True)
        fb._ensure_pkg_init()
        with open(target, "w", encoding="utf-8") as f:
            f.write(GOOD_TOOL.replace('"temp_converter"', f'"{tool_name}"'))
        fb._update_manifest(tool_name, {"tool_name": tool_name, "file": f"{slug}.py"})

        loaded = fb.load_generated_tools()
        assert tool_name in loaded
        out = loaded[tool_name]["callable"]({"celsius": 0})
        assert out["status"] == "success" and out["fahrenheit"] == 32
    finally:
        if os.path.exists(target):
            os.remove(target)
        # restore or remove the manifest we touched
        if manifest_backup is not None:
            open(fb.MANIFEST_PATH, "w", encoding="utf-8").write(manifest_backup)
        elif os.path.exists(fb.MANIFEST_PATH):
            os.remove(fb.MANIFEST_PATH)
