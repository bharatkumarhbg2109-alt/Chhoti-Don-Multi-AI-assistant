#!/usr/bin/env python
"""LIVE smoke-test harness for the coding agent — OBSERVATION run (NOT a pytest).

Runs the REAL CodingAgent loop against the REAL local coding model
(deepseek-coder-v2:lite via Ollama) end-to-end, in a throwaway workspace, with
verbose per-step logging, so we can SEE whether deepseek actually emits clean JSON
actions, self-heals, and finishes.

Safety for a smoke run:
  * A FRESH throwaway workspace under ``_smoke_ws/<stage>`` is granted per stage —
    the real repo is NEVER the workspace.
  * Writes + shell auto-approve (we are testing the MODEL, not the HITL prompt).
  * The DEPLOY channel is left at its default (deny): this harness NEVER deploys.

Run from the repo root:  python tools/smoke_coding_agent.py
"""

from __future__ import annotations

import builtins
import functools
import json
import logging
import os
import shutil
import sys
import time

# Repo root on path so `coding_agent` / `core` import when run as a script.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from core.brain import Brain                       # noqa: E402
from core.model_router import resolve_model        # noqa: E402
from coding_agent import agent, guarded, hitl, server  # noqa: E402
from coding_agent.agent import CodingAgent, AGENT_SYSTEM_PROMPT  # noqa: E402

print = functools.partial(builtins.print, flush=True)  # live output for the bg log

WS_ROOT = os.path.join(os.getcwd(), "_smoke_ws")

# (name, goal, max_steps). L5 is seeded from L4's workspace if L4 produced main.py.
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
    MODEL behavior, not the approval logic. Deploy still rides its own channel,
    which stays at the default deny — this harness never deploys."""

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


def make_think(brain: Brain, counters: dict):
    """Wrap the real model call: log raw output (truncated), parse status, timing."""
    def think(prompt: str) -> str:
        t0 = time.perf_counter()
        try:
            out = brain.think_fast(prompt, brain_type="coding", num_predict=512,
                                   system_prompt=AGENT_SYSTEM_PROMPT)
        except Exception as exc:  # capture, don't crash the harness
            out = ""
            print(f"    !! model call raised: {exc!r}")
        dt = time.perf_counter() - t0
        parsed_action = agent._parse_action(out) is not None
        parsed_plan = agent._parse_plan(out) is not None
        kind = "action" if parsed_action else ("plan" if parsed_plan else "UNPARSED")
        counters["calls"] += 1
        counters[kind] = counters.get(kind, 0) + 1
        counters["model_s"] += dt
        print(f"    · model call #{counters['calls']}  {dt:5.1f}s  parse={kind}")
        print(f"        raw: {(out or '').strip()[:240]!r}")
        return out
    return think


def _list_files(ws: str):
    out = []
    for root, _dirs, files in os.walk(ws):
        for f in files:
            out.append(os.path.relpath(os.path.join(root, f), ws).replace(os.sep, "/"))
    return sorted(out)


def run_stage(brain: Brain, name: str, max_steps: int, goal: str, seed_from: str = None) -> dict:
    ws = os.path.join(WS_ROOT, name)
    shutil.rmtree(ws, ignore_errors=True)
    os.makedirs(ws, exist_ok=True)
    if seed_from and os.path.isdir(seed_from):
        shutil.copytree(seed_from, ws, dirs_exist_ok=True)

    guarded.revoke_workspace()
    guarded.grant_workspace(ws)
    counters = {"calls": 0, "model_s": 0.0}

    print("\n" + "=" * 84)
    print(f"STAGE {name}   (max_steps={max_steps})")
    print(f"  goal: {goal}")
    print(f"  ws:   {ws}")
    if seed_from:
        print(f"  seeded from: {seed_from}  -> {_list_files(ws)}")
    print("-" * 84)

    think = make_think(brain, counters)
    t0 = time.perf_counter()
    try:
        with hitl.use_approver(hitl.approve_all):  # literal per spec; SmokeAgent also approves
            ag = SmokeAgent(think, plan_approver=lambda p: True,
                            shell_approver=hitl.approve_all, delete_approver=hitl.approve_all,
                            max_steps=max_steps)
            res = ag.run(goal)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        res = {"stopped": "HARNESS_EXCEPTION", "steps": 0, "summary": repr(exc),
               "trace": [], "commands": [], "servers": [], "deploys": []}
    wall = time.perf_counter() - t0

    print("  --- trace ---")
    for tr in res.get("trace", []):
        if "action" in tr:
            print(f"    step {tr.get('step')}: {tr.get('action')} "
                  f"{json.dumps(tr.get('args', {}))[:90]}  gate={tr.get('gate')}")
            obs = str(tr.get("observation", "")).replace("\n", " ⏎ ")
            print(f"        obs: {obs[:220]}")
        else:
            print(f"    {tr}")

    produced = _list_files(ws)
    print(f"  files produced: {produced}")
    if res.get("commands"):
        print(f"  commands: {[(c.get('command'), c.get('exit_code')) for c in res['commands']]}")
    if res.get("servers"):
        print(f"  servers: {res['servers']}")
    print(f"  summary: stopped={res.get('stopped')}  steps={res.get('steps')}  "
          f"summary_text={str(res.get('summary'))[:120]!r}")

    server.stop_all()  # never leave a smoke server running between stages

    return {"stage": name, "stopped": res.get("stopped"), "steps": res.get("steps", 0),
            "finished": res.get("stopped") == "finish", "calls": counters["calls"],
            "action": counters.get("action", 0), "plan": counters.get("plan", 0),
            "unparsed": counters.get("UNPARSED", 0), "model_s": round(counters["model_s"], 1),
            "wall_s": round(wall, 1), "files": len(produced), "ws": ws}


def main():
    print("#" * 84)
    print("# CHHOTI DON — CODING AGENT LIVE SMOKE TEST (real deepseek-coder-v2:lite)")
    print("#" * 84)
    _enable_live_logs()
    shutil.rmtree(WS_ROOT, ignore_errors=True)
    os.makedirs(WS_ROOT, exist_ok=True)

    brain = Brain()
    print(f"brain.mode = {brain.mode}   coding model = {resolve_model('coding')}")
    if brain.mode != "local":
        print("ABORT: brain is not in 'local' mode (Ollama/coding model unavailable). "
              "No real run possible.")
        return

    results = []
    for name, max_steps, goal in STAGES:
        seed = None
        if name == "L5_local_host":
            l4_ws = os.path.join(WS_ROOT, "L4_scaffold")
            if not os.path.isfile(os.path.join(l4_ws, "main.py")):
                print("\n" + "=" * 84)
                print("STAGE L5_local_host  -> SKIPPED (L4 did not produce a runnable main.py)")
                results.append({"stage": "L5_local_host", "stopped": "SKIPPED", "steps": 0,
                                "finished": False, "calls": 0, "action": 0, "plan": 0,
                                "unparsed": 0, "model_s": 0.0, "wall_s": 0.0, "files": 0})
                continue
            seed = l4_ws
        results.append(run_stage(brain, name, max_steps, goal, seed_from=seed))

    print("\n" + "#" * 84)
    print("# FINAL SUMMARY")
    print("#" * 84)
    hdr = (f"{'stage':16} {'stopped':16} {'steps':>5} {'calls':>5} {'act':>4} "
           f"{'plan':>4} {'unpars':>6} {'model_s':>7} {'wall_s':>7} {'files':>5} {'done':>5}")
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        print(f"{r['stage']:16} {str(r['stopped']):16} {r['steps']:>5} {r['calls']:>5} "
              f"{r['action']:>4} {r['plan']:>4} {r['unparsed']:>6} {r['model_s']:>7} "
              f"{r['wall_s']:>7} {r['files']:>5} {str(r['finished']):>5}")
    print("\nDone. Throwaway workspaces are under:", WS_ROOT)


if __name__ == "__main__":
    main()
