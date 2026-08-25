#!/usr/bin/env python
"""LIVE smoke-test / model A-B harness for the coding agent — OBSERVATION run.

Runs the REAL CodingAgent loop against a REAL local coding model (Ollama) end-to-
end, in a throwaway workspace, with verbose per-step logging, so we can SEE which
model emits clean JSON, adheres to its plan, self-heals, and finishes.

Model override (NO edit to brain_registry): the coding brain's model is set at
RUNTIME via ``update_brain_model('coding', tag)`` for the duration of a run and
restored afterwards, so ANY installed Ollama model can drive the loop. The PLAN
phase gets a larger num_predict than per-step actions (content-heavy plans were
truncating mid-JSON at 512).

Safety for a smoke run:
  * A FRESH throwaway workspace under ``_smoke_ws/<model>/<stage>`` per stage.
  * Writes + shell auto-approve (we are testing the MODEL, not the HITL prompt).
  * The DEPLOY channel is left at its default (deny): this harness NEVER deploys.

Usage (from the repo root):
  python tools/smoke_coding_agent.py                      # deepseek (default)
  python tools/smoke_coding_agent.py --models deepseek
  python tools/smoke_coding_agent.py --models deepseek-coder-v2:16b-lite-instruct-q4_K_M --plan-num-predict 2048
"""

from __future__ import annotations

import argparse
import builtins
import functools
import json
import logging
import os
import shutil
import sys
import time

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import requests  # noqa: E402
from core.brain import Brain  # noqa: E402
from core.brain_registry import get_brain_model, update_brain_model  # noqa: E402
from core.config import Config  # noqa: E402
from coding_agent import agent, guarded, hitl, server  # noqa: E402
from coding_agent.agent import CodingAgent, AGENT_SYSTEM_PROMPT  # noqa: E402

print = functools.partial(builtins.print, flush=True)  # live output for the bg log

WS_ROOT = os.path.join(os.getcwd(), "_smoke_ws")

# Default per-phase token budgets. The PLAN phase needs more room so a content-
# heavy plan array does not truncate mid-JSON (the L3 plan_parse_error).
STEP_NUM_PREDICT = 512
PLAN_NUM_PREDICT = 2048

# Friendly alias -> explicit Ollama tag. Raw Ollama tags are also accepted as-is
# on the command line, so any installed model can still be A/B-tested at runtime.
_ALIASES = {"deepseek": "deepseek-coder-v2:16b-lite-instruct-q4_K_M"}

STAGES = [
    ("L1_plan_write", 8,
     "Create a file hello.txt containing exactly: Hello Chhoti Don"),
    ("L2_shell", 12,
     "Create a Python script add.py that prints the result of 2+2, then run it "
     "and show the output."),
    ("L3_self_heal", 22,
     "Create fizzbuzz.py with a fizzbuzz(n) function, write a pytest test in "
     "test_fizzbuzz.py, run pytest, and fix any failures until the tests pass."),
    ("L4_scaffold", 24,
     'Create a minimal FastAPI app in main.py with a GET /health endpoint '
     'returning {"status":"ok"}, plus a pytest test that asserts it, and run the test.'),
    ("L5_local_host", 12,
     "Start the FastAPI app from L4 as a local server and confirm it's serving."),
]


class SmokeAgent(CodingAgent):
    """Approve ALL write/shell proposals (bypass plan-scope) so we observe the raw
    MODEL behavior. Deploy still rides its own channel (default deny) — never runs."""

    def _session_approver(self):
        return lambda proposal: True


def _enable_live_logs():
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(logging.Formatter("      · %(message)s"))
    for name in ("chhoti.coding_agent.agent", "chhoti.coding_agent.guarded",
                 "chhoti.coding_agent.audit", "chhoti.coding_agent.server"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO)
        lg.handlers[:] = [h]
        lg.propagate = False


def make_think(brain: Brain, counters: dict, plan_np: int, step_np: int):
    """Real model call. PLAN prompts get plan_np tokens, step prompts step_np.
    Logs raw output (truncated), parse status, timing."""
    def think(prompt: str) -> str:
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
        kind = "plan" if agent._parse_plan(out) else ("action" if agent._parse_action(out)
                                                      else "UNPARSED")
        counters["calls"] += 1
        counters[kind] = counters.get(kind, 0) + 1
        counters["model_s"] += dt
        tag = "PLAN" if is_plan else "step"
        print(f"    · [{tag}] model call #{counters['calls']}  {dt:5.1f}s  parse={kind}")
        print(f"        raw: {(out or '').strip()[:240]!r}")
        return out
    return think


def _list_files(ws: str):
    out = []
    for root, _dirs, files in os.walk(ws):
        for f in files:
            out.append(os.path.relpath(os.path.join(root, f), ws).replace(os.sep, "/"))
    return sorted(out)


def run_stage(brain, model_label, name, max_steps, goal, plan_np, step_np, seed_from=None):
    ws = os.path.join(WS_ROOT, model_label, name)
    shutil.rmtree(ws, ignore_errors=True)
    os.makedirs(ws, exist_ok=True)
    if seed_from and os.path.isdir(seed_from):
        shutil.copytree(seed_from, ws, dirs_exist_ok=True)

    guarded.revoke_workspace()
    guarded.grant_workspace(ws)
    counters = {"calls": 0, "model_s": 0.0}

    print("\n" + "=" * 84)
    print(f"[{model_label}] STAGE {name}   (max_steps={max_steps})")
    print(f"  goal: {goal}")
    if seed_from:
        print(f"  seeded from: {seed_from} -> {_list_files(ws)}")
    print("-" * 84)

    think = make_think(brain, counters, plan_np, step_np)
    t0 = time.perf_counter()
    try:
        with hitl.use_approver(hitl.approve_all):
            ag = SmokeAgent(think, plan_approver=lambda p: True,
                            shell_approver=hitl.approve_all, delete_approver=hitl.approve_all,
                            max_steps=max_steps)
            res = ag.run(goal)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        res = {"stopped": "HARNESS_EXCEPTION", "steps": 0, "summary": repr(exc), "trace": []}
    wall = time.perf_counter() - t0

    print("  --- trace ---")
    for tr in res.get("trace", []):
        if "action" in tr:
            print(f"    step {tr.get('step')}: {tr.get('action')} "
                  f"{json.dumps(tr.get('args', {}))[:90]}  gate={tr.get('gate')}")
            obs = str(tr.get("observation", "")).replace("\n", " ⏎ ")
            print(f"        obs: {obs[:200]}")
        else:
            print(f"    {tr}")
    produced = _list_files(ws)
    print(f"  files: {produced}")
    if res.get("commands"):
        print(f"  commands: {[(c.get('command'), c.get('exit_code')) for c in res['commands']]}")
    print(f"  summary: stopped={res.get('stopped')} steps={res.get('steps')} "
          f"text={str(res.get('summary'))[:120]!r}")
    server.stop_all()

    return {"stage": name, "stopped": res.get("stopped"), "steps": res.get("steps", 0),
            "finished": res.get("stopped") == "finish", "calls": counters["calls"],
            "action": counters.get("action", 0), "plan": counters.get("plan", 0),
            "unparsed": counters.get("UNPARSED", 0), "model_s": round(counters["model_s"], 1),
            "wall_s": round(wall, 1), "files": len(produced)}


def _model_available(tag: str) -> bool:
    try:
        r = requests.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=5)
        names = [m.get("name", "") for m in r.json().get("models", [])]
        base = tag.split(":")[0]
        return any(n == tag or n.split(":")[0] == base for n in names)
    except Exception:
        return False


def _unload(tag: str):
    """Ask Ollama to drop the model from VRAM so the next model loads fresh."""
    try:
        requests.post(f"{Config.OLLAMA_HOST}/api/generate",
                      json={"model": tag, "prompt": "", "keep_alive": 0, "stream": False},
                      timeout=30)
    except Exception:
        pass


def run_model(brain, label, tag, plan_np, step_np):
    print("\n" + "#" * 84)
    print(f"# MODEL: {label}  ->  {tag}   (plan_np={plan_np}, step_np={step_np})")
    print("#" * 84)
    if not _model_available(tag):
        print(f"  !! MODEL NOT AVAILABLE in Ollama: {tag} — skipping this model.")
        return None

    orig = get_brain_model("coding")
    update_brain_model("coding", tag)  # runtime override (restored below)
    results = []
    try:
        for name, max_steps, goal in STAGES:
            seed = None
            if name == "L5_local_host":
                l4_ws = os.path.join(WS_ROOT, label, "L4_scaffold")
                if not os.path.isfile(os.path.join(l4_ws, "main.py")):
                    print(f"\n[{label}] STAGE L5_local_host -> SKIPPED (no runnable main.py from L4)")
                    results.append({"stage": "L5_local_host", "stopped": "SKIPPED", "steps": 0,
                                    "finished": False, "calls": 0, "action": 0, "plan": 0,
                                    "unparsed": 0, "model_s": 0.0, "wall_s": 0.0, "files": 0})
                    continue
                seed = l4_ws
            results.append(run_stage(brain, label, name, max_steps, goal, plan_np, step_np, seed))
    finally:
        update_brain_model("coding", orig)  # restore
        _unload(tag)
    return results


def _print_table(label, results):
    print(f"\n=== SUMMARY: {label} ===")
    hdr = (f"{'stage':16} {'stopped':16} {'steps':>5} {'calls':>5} {'act':>4} "
           f"{'plan':>4} {'unpars':>6} {'model_s':>7} {'wall_s':>7} {'files':>5} {'done':>5}")
    print(hdr)
    print("-" * len(hdr))
    for r in results or []:
        print(f"{r['stage']:16} {str(r['stopped']):16} {r['steps']:>5} {r['calls']:>5} "
              f"{r['action']:>4} {r['plan']:>4} {r['unparsed']:>6} {r['model_s']:>7} "
              f"{r['wall_s']:>7} {r['files']:>5} {str(r['finished']):>5}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="deepseek",
                    help="comma list of aliases (deepseek) or raw Ollama tags")
    ap.add_argument("--num-predict", type=int, default=STEP_NUM_PREDICT)
    ap.add_argument("--plan-num-predict", type=int, default=PLAN_NUM_PREDICT)
    args = ap.parse_args()

    print("#" * 84)
    print("# CHHOTI DON — CODING AGENT MODEL A/B (live, real Ollama models)")
    print("#" * 84)
    _enable_live_logs()
    shutil.rmtree(WS_ROOT, ignore_errors=True)
    os.makedirs(WS_ROOT, exist_ok=True)

    brain = Brain()
    print(f"brain.mode = {brain.mode}   configured coding model = {get_brain_model('coding')}")
    if brain.mode != "local":
        print("ABORT: brain is not in 'local' mode (Ollama unavailable). No real run.")
        return

    all_results = {}
    for token in [m.strip() for m in args.models.split(",") if m.strip()]:
        tag = _ALIASES.get(token, token)
        label = token if token in _ALIASES else token.split(":")[0]
        all_results[label] = run_model(brain, label, tag, args.plan_num_predict, args.num_predict)

    print("\n" + "#" * 84)
    print("# FINAL SUMMARY TABLES")
    print("#" * 84)
    for label, results in all_results.items():
        if results is None:
            print(f"\n=== SUMMARY: {label} === (model unavailable — not run)")
        else:
            _print_table(label, results)
    print("\nThrowaway workspaces under:", WS_ROOT)


if __name__ == "__main__":
    main()
