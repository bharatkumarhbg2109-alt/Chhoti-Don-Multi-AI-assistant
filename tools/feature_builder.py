"""
Chhoti Don - Feature Builder (safe self-extension)

Lets the assistant grow NEW tools for itself from a natural-language request:

    "ek tool banao jo temperature Celsius <-> Fahrenheit convert kare"

Flow (deliberately gated — never blindly self-modifies):
    1. propose  -> deepseek generates a self-contained tool module, it is
                   STATICALLY SCANNED for dangerous code, then SMOKE-TESTED in
                   an isolated subprocess. Nothing is activated yet.
    2. apply    -> only on an explicit confirm=True does the vetted file move
                   into tools/generated/ and get recorded in the manifest
                   (a backup is kept so it is fully reversible).
    3. rollback -> remove an applied feature and restore the previous state.
    4. list     -> show applied features and pending proposals.

Safety model (defense in depth):
    - Core / brain / safety / cyber files are NEVER touched. Generated code only
      ever lands in tools/generated/.
    - Static blocklist rejects process-spawn, code-exec, destructive-fs, raw
      sockets/network and other dangerous calls BEFORE any execution.
    - The smoke test runs in a separate `python` process with a hard timeout.
    - Activation requires an explicit human confirm. Everything is reversible.

This is NOT a container/VM sandbox; it is process isolation + a static scan +
a human gate, which is appropriate for a single-user local assistant.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from typing import Dict, List, Tuple

# ── Paths ─────────────────────────────────────────────────────────────────────
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_THIS_DIR)
GENERATED_DIR = os.path.join(_THIS_DIR, "generated")
MANIFEST_PATH = os.path.join(GENERATED_DIR, "manifest.json")


def _runtime_dir() -> str:
    base = os.environ.get("CHHOTI_DON_RUNTIME_DIR") or os.path.join(PROJECT_ROOT, ".runtime")
    d = os.path.join(base, "feature_builder")
    os.makedirs(os.path.join(d, "proposals"), exist_ok=True)
    os.makedirs(os.path.join(d, "backups"), exist_ok=True)
    return d


# ── The contract every generated tool must satisfy ────────────────────────────
REQUIRED_MARKERS = ("def run(", "TOOL_NAME")

# ── Static safety blocklist (checked BEFORE any execution) ─────────────────────
# Generated tools are meant to be pure/computational by default. Anything that
# spawns processes, executes code, deletes files, or opens the network is
# rejected — the user can add such capabilities by hand, with review.
BLOCKED_PATTERNS: List[str] = [
    r"\bos\.system\b", r"\bsubprocess\b", r"\bos\.popen\b", r"\bpopen\s*\(",
    r"\beval\s*\(", r"\bexec\s*\(", r"\bcompile\s*\(", r"\b__import__\b",
    r"\bimportlib\b", r"\bctypes\b", r"\bwinreg\b",
    r"\bshutil\.rmtree\b", r"\bos\.remove\b", r"\bos\.unlink\b",
    r"\bos\.rmdir\b", r"\bos\.rename\b", r"\bos\.replace\b",
    r"\bpickle\.load", r"\bmarshal\.load", r"\byaml\.load\s*\(",
    r"\bsocket\b", r"\brequests\b", r"\burllib\b", r"\bhttp\.client\b",
    r"\bhttpx\b", r"\bftplib\b", r"\bsmtplib\b", r"\bparamiko\b",
    r"\bsys\.exit\b", r"\bquit\s*\(", r"\binput\s*\(",
    r"\bglobals\s*\(\s*\)\s*\[", r"\bsetattr\s*\(",
    r"\bopen\s*\([^)]*['\"][waxWAX]\+?['\"]",  # open(..., 'w'/'a'/'x')
]

MAX_CODE_CHARS = 20000


# ══════════════════════════════════════════════════════════════════════════════
# Public entry point (registry-compatible: one dict in, one dict out, never raises)
# ══════════════════════════════════════════════════════════════════════════════
def feature_builder(input_data: Dict) -> Dict:
    try:
        action = (input_data or {}).get("action", "propose")
        if action == "propose":
            return _propose(input_data.get("request", ""))
        if action == "apply":
            return _apply(input_data.get("proposal_id", ""), confirm=bool(input_data.get("confirm", False)))
        if action == "rollback":
            return _rollback(input_data.get("feature", ""))
        if action == "list":
            return _list()
        return _err(f"Unknown action '{action}'. Use: propose | apply | rollback | list.")
    except Exception as e:  # never bubble up into the app
        return _err(f"feature_builder crashed: {e}")


# ── 1. PROPOSE ────────────────────────────────────────────────────────────────
def _propose(request: str) -> Dict:
    request = (request or "").strip()
    if not request:
        return _err("Batao kya tool banana hai — e.g. \"ek tool jo BMI calculate kare\".")

    code = _generate_code(request)
    if not code or code.startswith("❌") or code.startswith("[GEN_ERROR]"):
        return _err(
            "Code generate nahi ho paya. Ollama + deepseek chaalu hai? "
            f"({code[:120] if code else 'empty response'})"
        )

    code = _strip_code_fences(code)
    if len(code) > MAX_CODE_CHARS:
        return _err(f"Generated code too large ({len(code)} chars > {MAX_CODE_CHARS}).")

    missing = [m for m in REQUIRED_MARKERS if m not in code]
    if missing:
        return _err(f"Generated code missing required parts: {missing}. Try rephrasing the request.")

    ok, reasons = _static_safety_scan(code)
    if not ok:
        return {
            "status": "rejected",
            "stage": "safety_scan",
            "message": "Generated code blocked ke it uses unsafe operations.",
            "reasons": reasons,
            "code": code,
        }

    test = _sandbox_test(code)
    if not test.get("passed"):
        return {
            "status": "test_failed",
            "stage": "sandbox",
            "message": "Generated code sandbox smoke-test mein fail hua.",
            "detail": test,
            "code": code,
        }

    tool_name = _extract_tool_name(code)
    proposal_id = uuid.uuid4().hex[:12]
    _save_proposal(proposal_id, {
        "proposal_id": proposal_id,
        "request": request,
        "tool_name": tool_name,
        "code": code,
        "test": test,
        "created_at": _now(),
        "passed": True,
    })

    return {
        "status": "confirmation_required",
        "message": (
            f"'{tool_name}' tool ready hai (safety-scan + sandbox test pass). "
            "Apply karne ke liye confirm karo."
        ),
        "proposal_id": proposal_id,
        "tool_name": tool_name,
        "code": code,
        "test_output": test.get("output"),
        "apply_hint": {"action": "apply", "proposal_id": proposal_id, "confirm": True},
    }


# ── 2. APPLY (requires explicit confirm) ──────────────────────────────────────
def _apply(proposal_id: str, confirm: bool = False) -> Dict:
    proposal_id = (proposal_id or "").strip()
    if not proposal_id:
        return _err("proposal_id required.")
    prop = _load_proposal(proposal_id)
    if not prop:
        return _err(f"Proposal '{proposal_id}' not found (ya expire ho gaya).")
    if not prop.get("passed"):
        return _err("Yeh proposal tests pass nahi kar paya tha — apply nahi kar sakte.")
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": "Apply confirm nahi hua. Dubara `confirm: true` ke saath bhejo.",
            "proposal_id": proposal_id,
            "tool_name": prop.get("tool_name"),
        }

    tool_name = prop["tool_name"]
    slug = _safe_slug(tool_name)
    os.makedirs(GENERATED_DIR, exist_ok=True)
    _ensure_pkg_init()
    target = os.path.join(GENERATED_DIR, f"{slug}.py")
    display = f"tools/generated/{slug}.py"

    # Backup any existing file we are about to overwrite (reversibility).
    backup_ref = None
    if os.path.exists(target):
        backup_ref = _backup_file(target)

    with open(target, "w", encoding="utf-8") as f:
        f.write(prop["code"])

    # Store the basename only (drive-independent; the file always lives under
    # GENERATED_DIR). Avoids os.path.relpath, which raises across Windows drives.
    _update_manifest(tool_name, {
        "tool_name": tool_name,
        "file": f"{slug}.py",
        "display": display,
        "request": prop.get("request"),
        "applied_at": _now(),
        "proposal_id": proposal_id,
        "backup": backup_ref,
    })
    _delete_proposal(proposal_id)

    return {
        "status": "success",
        "message": (
            f"Tool '{tool_name}' apply ho gaya. Agli baar assistant start hone par "
            "yeh live tool ban jayega (registry auto-loads tools/generated/). "
            "Hataana ho to: rollback."
        ),
        "tool_name": tool_name,
        "file": display,
    }


# ── 3. ROLLBACK ───────────────────────────────────────────────────────────────
def _rollback(feature: str) -> Dict:
    feature = (feature or "").strip()
    if not feature:
        return _err("feature (tool_name) required to rollback.")
    manifest = _read_manifest()
    entry = manifest.get(feature)
    if not entry:
        return _err(f"'{feature}' applied features mein nahi mila.")

    # File always lives under GENERATED_DIR as <slug>.py (drive-independent).
    target = os.path.join(GENERATED_DIR, f"{_safe_slug(feature)}.py")
    removed = False
    if os.path.exists(target):
        os.remove(target)
        removed = True

    # Restore a prior version if we had backed one up when overwriting.
    restored = False
    if entry.get("backup"):
        bpath = os.path.join(_runtime_dir(), "backups", entry["backup"])
        if os.path.exists(bpath):
            shutil.copyfile(bpath, target)
            restored = True

    del manifest[feature]
    _write_manifest(manifest)
    return {
        "status": "success",
        "message": f"'{feature}' rollback done (removed={removed}, restored_previous={restored}).",
        "tool_name": feature,
    }


# ── 4. LIST ───────────────────────────────────────────────────────────────────
def _list() -> Dict:
    manifest = _read_manifest()
    proposals = []
    pdir = os.path.join(_runtime_dir(), "proposals")
    for fn in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        if fn.endswith(".json"):
            try:
                p = json.load(open(os.path.join(pdir, fn), encoding="utf-8"))
                proposals.append({"proposal_id": p.get("proposal_id"), "tool_name": p.get("tool_name"), "request": p.get("request")})
            except Exception:
                continue
    return {
        "status": "success",
        "applied": [{"tool_name": k, **v} for k, v in manifest.items()],
        "pending_proposals": proposals,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Generation (deepseek) — isolated so tests can monkeypatch it (offline)
# ══════════════════════════════════════════════════════════════════════════════
_SYSTEM_PROMPT = (
    "You are a senior Python engineer generating a SINGLE self-contained tool "
    "module for a local assistant. Output ONLY Python code, no prose.\n"
    "Hard rules:\n"
    "- Define TOOL_NAME (snake_case str), TOOL_DESCRIPTION (str), and a function "
    "def run(input_data: dict) -> dict.\n"
    "- Also define SAMPLE_INPUT (a dict) that run() can be smoke-tested with.\n"
    "- Pure/standard-library only. NO subprocess, os.system, eval/exec, network "
    "(sockets/requests/urllib), file deletion, or input().\n"
    "- run() must never raise on bad input; return {\"status\": \"error\", ...} instead.\n"
)


def _generate_code(request: str) -> str:
    """Ask deepseek for the tool. Returns raw text (may contain fences)."""
    try:
        from core.local_model_engine import execute as run_model
        from core.config import Config
        model = getattr(Config, "CODING_MODEL", None) or getattr(Config, "MAIN_MODEL", "qwen3.5:latest")
    except Exception as e:  # pragma: no cover - import guard
        return f"[GEN_ERROR] engine import failed: {e}"

    prompt = (
        f"Build a tool for this request:\n\"{request}\"\n\n"
        "Return the complete Python module now."
    )
    try:
        out = run_model({"model": model, "temperature": 0.2, "system_prompt": _SYSTEM_PROMPT}, prompt)
        return out or ""
    except Exception as e:  # pragma: no cover - network guard
        return f"[GEN_ERROR] {e}"


# ══════════════════════════════════════════════════════════════════════════════
# Safety scan + sandbox
# ══════════════════════════════════════════════════════════════════════════════
def _static_safety_scan(code: str) -> Tuple[bool, List[str]]:
    reasons = []
    for pat in BLOCKED_PATTERNS:
        if re.search(pat, code):
            reasons.append(f"blocked pattern: {pat}")
    # Defense against writing outside the generated sandbox.
    if ".." in code and re.search(r"open\s*\(", code):
        reasons.append("suspicious path traversal near open()")
    return (len(reasons) == 0, reasons)


def _sandbox_test(code: str) -> Dict:
    """Run the generated module's run(SAMPLE_INPUT) in an isolated subprocess."""
    try:
        from tools.code_executor import execute_code
    except Exception as e:  # pragma: no cover
        return {"passed": False, "reason": f"sandbox import failed: {e}"}

    harness = code + (
        "\n\n"
        "if __name__ == '__main__':\n"
        "    import json as _json\n"
        "    try:\n"
        "        _inp = SAMPLE_INPUT\n"
        "    except NameError:\n"
        "        _inp = {}\n"
        "    _out = run(_inp)\n"
        "    assert isinstance(_out, dict), 'run() must return a dict'\n"
        "    print('SMOKE_OK::' + _json.dumps(_out, default=str)[:400])\n"
    )
    res = execute_code({"code": harness, "language": "python"})
    output = res.get("output") or ""
    passed = res.get("status") == "success" and "SMOKE_OK::" in output
    return {
        "passed": passed,
        "output": output[:600],
        "stderr": (res.get("stderr") or "")[:600],
        "return_code": res.get("return_code"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# Loader — lets ToolRegistry expose applied features as live tools
# ══════════════════════════════════════════════════════════════════════════════
def load_generated_tools() -> Dict[str, Dict]:
    """
    Import every applied module in tools/generated/ and return
    {tool_name: {"callable": run, "definition": {...}}}. A broken module is
    skipped (logged to the return under _errors), never crashing the registry.
    """
    import importlib
    out: Dict[str, Dict] = {}
    errors = {}
    if not os.path.isdir(GENERATED_DIR):
        return out
    manifest = _read_manifest()
    for tool_name, entry in manifest.items():
        slug = _safe_slug(tool_name)
        modname = f"tools.generated.{slug}"
        try:
            mod = importlib.import_module(modname)
            importlib.reload(mod)
            run = getattr(mod, "run")
            out[getattr(mod, "TOOL_NAME", tool_name)] = {
                "callable": run,
                "definition": {
                    "name": getattr(mod, "TOOL_NAME", tool_name),
                    "description": getattr(mod, "TOOL_DESCRIPTION", entry.get("request", "generated tool")),
                    "args": {"input_data": "dict"},
                },
            }
        except Exception as e:  # a bad generated tool must not break the app
            errors[tool_name] = str(e)
    if errors:
        out["_errors"] = errors
    return out


# ══════════════════════════════════════════════════════════════════════════════
# Small helpers
# ══════════════════════════════════════════════════════════════════════════════
def _strip_code_fences(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```[a-zA-Z0-9_]*\n(.*)\n```$", text, re.DOTALL)
    if fence:
        return fence.group(1).strip()
    # Also handle a leading ```python with no clean closing fence.
    text = re.sub(r"^```[a-zA-Z0-9_]*\n", "", text)
    text = re.sub(r"\n```$", "", text)
    return text.strip()


def _extract_tool_name(code: str) -> str:
    m = re.search(r"TOOL_NAME\s*=\s*['\"]([a-zA-Z0-9_]+)['\"]", code)
    return m.group(1) if m else "generated_tool"


def _safe_slug(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]", "_", (name or "").strip()).strip("_").lower()
    return slug or "generated_tool"


def _ensure_pkg_init() -> None:
    init = os.path.join(GENERATED_DIR, "__init__.py")
    if not os.path.exists(init):
        with open(init, "w", encoding="utf-8") as f:
            f.write('"""Assistant-generated tools (created via feature_builder). Reversible via rollback."""\n')


def _backup_file(path: str) -> str:
    ref = f"{os.path.basename(path)}.{int(time.time())}.bak"
    shutil.copyfile(path, os.path.join(_runtime_dir(), "backups", ref))
    return ref


def _proposal_path(pid: str) -> str:
    return os.path.join(_runtime_dir(), "proposals", f"{pid}.json")


def _save_proposal(pid: str, data: Dict) -> None:
    with open(_proposal_path(pid), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_proposal(pid: str) -> Dict:
    try:
        with open(_proposal_path(_safe_pid(pid)), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _delete_proposal(pid: str) -> None:
    try:
        os.remove(_proposal_path(_safe_pid(pid)))
    except Exception:
        pass


def _safe_pid(pid: str) -> str:
    return re.sub(r"[^a-f0-9]", "", (pid or "").lower())[:32]


def _read_manifest() -> Dict:
    try:
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_manifest(manifest: Dict) -> None:
    os.makedirs(GENERATED_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _update_manifest(tool_name: str, entry: Dict) -> None:
    manifest = _read_manifest()
    manifest[tool_name] = entry
    _write_manifest(manifest)


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _err(msg: str) -> Dict:
    return {"status": "error", "message": msg}


# LLM-facing metadata (registry merges this into tool_definitions).
TOOL_DEFINITION = {
    "name": "feature_builder",
    "description": (
        "Self-extend the assistant: generate a NEW tool from a natural-language "
        "request. It generates code with the local coding model, safety-scans and "
        "sandbox-tests it, then requires an explicit confirm to activate (reversible). "
        "Actions: propose (needs 'request'), apply (needs 'proposal_id' + confirm:true), "
        "rollback (needs 'feature'), list."
    ),
    "args": {
        "action": "propose | apply | rollback | list",
        "request": "string — what tool to build (for propose)",
        "proposal_id": "string (for apply)",
        "confirm": "boolean — must be true to apply",
        "feature": "string — tool_name to remove (for rollback)",
    },
}
