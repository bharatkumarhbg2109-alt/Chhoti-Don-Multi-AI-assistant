#!/usr/bin/env python
"""Live smoke test for TASK 1 — exact stages L1-L4 against real deepseek model.

Uses SmokeAgent from smoke_coding_agent.py infrastructure with
custom stages matching the task specification exactly.
"""

from __future__ import annotations

import builtins
import functools
import json
import os
import shutil
import sys
import tempfile
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.brain import Brain
from core.brain_registry import get_brain_model, update_brain_model
from core.config import Config
from coding_agent import agent, guarded, hitl, server
from coding_agent.agent import CodingAgent, AGENT_SYSTEM_PROMPT

import io
import codecs

# Fix Windows console encoding for Unicode output
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print = functools.partial(builtins.print, flush=True)

# ── Custom stages (exact task specification) ───────────────────────────────────
STAGES = [
    {
        "name": "L1_file_write",
        "max_steps": 8,
        "instruction": "Write a file called hello.py containing: print('hello world')",
        "success_criteria": {
            "files_must_exist": ["hello.py"],
            "content_checks": [("hello.py", "print")],
        },
    },
    {
        "name": "L2_shell_shim",
        "max_steps": 14,
        "instruction": (
            "Write a Python file add.py with a function add(a,b) that returns a+b, "
            "then write a test file test_add.py that imports it and asserts add(2,3)==5, "
            "then run the tests"
        ),
        "success_criteria": {
            "files_must_exist": ["add.py", "test_add.py"],
            "shim_expected": True,
            "tests_must_pass": True,
            "termination": "implicit_verify",
        },
    },
    {
        "name": "L3_self_heal",
        "max_steps": 24,
        "instruction": (
            "Write fizzbuzz.py — a function fizzbuzz(n) that returns 'fizz' for "
            "multiples of 3, 'buzz' for multiples of 5, 'fizzbuzz' for both, "
            "else the number as string. Write test_fizzbuzz.py with 4 assertions. "
            "Run the tests. If they fail, read the error and fix the code."
        ),
        "success_criteria": {
            "files_must_exist": ["fizzbuzz.py", "test_fizzbuzz.py"],
            "tests_must_pass": True,
            "termination": "implicit_verify",
        },
    },
    {
        "name": "L4_fastapi_scaffold",
        "max_steps": 26,
        "instruction": (
            "Create a minimal FastAPI app in src/main.py with a single GET /health "
            "endpoint that returns {'status':'ok'}. Install fastapi and uvicorn if "
            "needed. Write test_main.py using TestClient that calls /health and asserts "
            "the response is 200 and body is {'status':'ok'}. Run the tests."
        ),
        "success_criteria": {
            "files_must_exist": ["src/main.py", "test_main.py"],
            "tests_must_pass": True,
            "termination": "implicit_verify",
        },
    },
]


class SmokeAgent(CodingAgent):
    """Auto-approve all write/shell proposals for observation run."""

    def _session_approver(self):
        return lambda proposal: True


def _enable_live_logs():
    import logging
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("      · %(message)s"))
    for name in ("chhoti.coding_agent.agent", "chhoti.coding_agent.guarded",
                 "chhoti.coding_agent.audit", "chhoti.coding_agent.shell"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        lg.handlers[:] = [h]
        lg.propagate = False


def _list_files(ws):
    out = []
    for root, _dirs, files in os.walk(ws):
        for f in files:
            out.append(os.path.relpath(os.path.join(root, f), ws).replace(os.sep, "/"))
    return sorted(out)


def _read_file(ws, relpath):
    full = os.path.join(ws, relpath)
    if not os.path.isfile(full):
        return None
    with open(full, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def make_think(brain, counters, plan_np=2048, step_np=512):
    """Real model call with timing and parse logging."""
    def think(prompt):
        is_plan = "Produce an ORDERED PLAN" in prompt
        num_predict = plan_np if is_plan else step_np
        t0 = time.perf_counter()
        try:
            out = brain.think_fast(prompt, brain_type="coding", num_predict=num_predict,
                                   system_prompt=AGENT_SYSTEM_PROMPT)
        except Exception as exc:
            out = ""
            print(f"    !! model call raised: {exc!r}")
        dt = time.perf_counter() - t0
        kind = "plan" if agent._parse_plan(out) else (
            "action" if agent._parse_action(out) else "UNPARSED"
        )
        counters["calls"] += 1
        counters[kind] = counters.get(kind, 0) + 1
        counters["model_s"] += dt
        tag = "PLAN" if is_plan else "step"
        print(f"    · [{tag}] model call #{counters['calls']}  {dt:5.1f}s  parse={kind}")
        print(f"        raw: {(out or '').strip()[:300]!r}")
        return out
    return think


def run_stage(brain, stage, workspace_root):
    """Run one stage, return structured result dict."""
    name = stage["name"]
    instruction = stage["instruction"]
    max_steps = stage["max_steps"]
    criteria = stage["success_criteria"]

    ws = os.path.join(workspace_root, name)
    shutil.rmtree(ws, ignore_errors=True)
    os.makedirs(ws, exist_ok=True)

    guarded.revoke_workspace()
    guarded.grant_workspace(ws)

    counters = {"calls": 0, "model_s": 0.0}
    think = make_think(brain, counters)

    print("\n" + "=" * 84)
    print(f"STAGE {name}   (max_steps={max_steps})")
    print(f"  instruction: {instruction[:120]}...")
    print("-" * 84)

    t0 = time.perf_counter()
    try:
        with hitl.use_approver(hitl.approve_all):
            ag = SmokeAgent(
                think,
                plan_approver=lambda p: True,
                shell_approver=hitl.approve_all,
                delete_approver=hitl.approve_all,
                max_steps=max_steps,
            )
            res = ag.run(instruction)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        res = {"stopped": "HARNESS_EXCEPTION", "steps": 0, "summary": repr(exc), "trace": []}

    wall = time.perf_counter() - t0

    # Print trace
    print("  --- trace ---")
    for tr in res.get("trace", []):
        if "action" in tr:
            print(f"    step {tr.get('step')}: {tr.get('action')} "
                  f"{json.dumps(tr.get('args', {}))[:90]}  gate={tr.get('gate')}")
            obs = str(tr.get("observation", "")).replace("\n", " NL ")
            print(f"        obs: {obs[:250]}")
        else:
            print(f"    {tr}")

    produced = _list_files(ws)
    print(f"  files: {produced}")
    if res.get("commands"):
        print(f"  commands: {[(c.get('command'), c.get('exit_code')) for c in res['commands']]}")
    print(f"  summary: stopped={res.get('stopped')} steps={res.get('steps')} "
          f"text={str(res.get('summary'))[:150]!r}")
    server.stop_all()

    # ── Evaluate success criteria ──────────────────────────────────────────
    termination = res.get("stopped", "")
    checks = {}

    # File existence
    for f in criteria.get("files_must_exist", []):
        exists = f in produced
        checks[f"file_{f}"] = "PASS" if exists else "FAIL"

    # Content checks
    for f, pattern in criteria.get("content_checks", []):
        content = _read_file(ws, f)
        has = content is not None and pattern in content
        checks[f"content_{f}_{pattern}"] = "PASS" if has else "FAIL"

    # Tests passed (exit_code=0 on any sh_run)
    if criteria.get("tests_must_pass"):
        any_pass = any(c.get("exit_code") == 0 for c in res.get("commands", []))
        checks["tests_pass"] = "PASS" if any_pass else "FAIL"

    # Shim fired (sh_run received python -m pytest)
    if criteria.get("shim_expected"):
        shim_fired = any(
            "python" in (c.get("command") or "") and "pytest" in (c.get("command") or "")
            for c in res.get("commands", [])
        )
        checks["shim_fired"] = "PASS" if shim_fired else "FAIL"

    # Termination path
    if criteria.get("termination"):
        expected = criteria["termination"]
        term_ok = termination == expected
        checks["termination"] = f"PASS (got {termination})" if term_ok else f"FAIL (expected {expected}, got {termination})"
    else:
        # For L1: any of implicit_verify, implicit_repeat, model_finish is acceptable
        good_terms = {"implicit_verify", "implicit_repeat", "finish"}
        term_ok = termination in good_terms
        checks["termination"] = f"PASS ({termination})" if term_ok else f"FAIL ({termination})"

    # Overall pass
    all_pass = all("PASS" in v for v in checks.values())
    overall = "PASS" if all_pass else "FAIL"

    print(f"  CHECKS: {json.dumps(checks, indent=2)}")
    print(f"  RESULT: {overall}")

    return {
        "stage": name,
        "result": overall,
        "termination": termination,
        "checks": checks,
        "steps": res.get("steps", 0),
        "calls": counters["calls"],
        "model_s": round(counters["model_s"], 1),
        "wall_s": round(wall, 1),
        "files": produced,
        "commands": res.get("commands", []),
        "trace": res.get("trace", []),
        "summary": str(res.get("summary", ""))[:300],
    }


def main():
    print("#" * 84)
    print("# CHHOTI DON — LIVE SMOKE TEST (TASK 1, real deepseek, no mocks)")
    print("#" * 84)

    _enable_live_logs()

    # Create throwaway workspace
    ws_root = tempfile.mkdtemp(prefix="chhoti_smoke_")
    print(f"Workspace: {ws_root}")

    brain = Brain()
    print(f"brain.mode = {brain.mode}   coding model = {get_brain_model('coding')}")

    if brain.mode != "local":
        print("ABORT: brain is not in 'local' mode. No real run.")
        return

    # Override coding model to deepseek
    tag = "deepseek-coder-v2:16b-lite-instruct-q4_K_M"
    orig = get_brain_model("coding")
    update_brain_model("coding", tag)

    results = []
    try:
        for stage in STAGES:
            r = run_stage(brain, stage, ws_root)
            results.append(r)
            print()
    finally:
        update_brain_model("coding", orig)
        server.stop_all()

    # ── Summary table ──────────────────────────────────────────────────────
    print("\n" + "#" * 84)
    print("# SMOKE RESULTS SUMMARY")
    print("#" * 84)
    hdr = f"{'Stage':20} {'Result':8} {'Termination':18} {'Steps':6} {'Calls':6} {'Wall':7}"
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        print(f"{r['stage']:20} {r['result']:8} {r['termination']:18} "
              f"{r['steps']:6} {r['calls']:6} {r['wall_s']:6.1f}s")

    # ── Safety checks (scan trace for any safety markers) ──────────────────
    print("\n--- SAFETY VERIFICATION ---")
    all_traces = []
    for r in results:
        all_traces.extend(r.get("trace", []))
    critical_blocked = any("CRITICAL_BLOCKED" in str(t) for t in all_traces)
    sandbox_violation = any("SANDBOX_VIOLATION" in str(t) for t in all_traces)
    deploy_attempt = any("deploy_run" in str(t) for t in all_traces)
    print(f"  CRITICAL_BLOCKED: {'fired' if critical_blocked else 'not triggered'}")
    print(f"  SANDBOX_VIOLATION: {'fired' if sandbox_violation else 'not triggered'}")
    print(f"  deploy_run DENY: {'confirmed' if deploy_attempt else 'not triggered (no deploy attempted)'}")

    # ── Write results to JSON for later use ────────────────────────────────
    import json as _json
    out_path = os.path.join(_REPO_ROOT, "_smoke_results.json")
    with open(out_path, "w") as f:
        _json.dump({
            "workspace": ws_root,
            "results": results,
            "safety": {
                "critical_blocked": critical_blocked,
                "sandbox_violation": sandbox_violation,
                "deploy_attempted": deploy_attempt,
            },
        }, f, indent=2, default=str)
    print(f"\nDetailed results saved to: {out_path}")
    print(f"Throwaway workspace: {ws_root}")


if __name__ == "__main__":
    main()
