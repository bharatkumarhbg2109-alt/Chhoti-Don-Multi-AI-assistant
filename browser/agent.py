"""Phase 2: READ-ONLY browser research agent (bounded plan->act->observe loop).

Given a natural-language GOAL, a small/fast local model (the 'navigation' brain)
repeatedly chooses ONE read-only action; the agent executes it THROUGH the same
Guardian gate as Phase 1 (browser.guarded), then feeds a truncated observation
back, until the model emits `finish` or a HARD step cap is reached.

READ-ONLY INVARIANT (non-negotiable)
------------------------------------
The only actions the loop can take are search / navigate / read_page /
get_content / finish. There is NO click, type, fill, press, scroll-to-act,
upload, download, or any state-changing action here — and none may be added.
All web actions are the Phase-1 GUARDED wrappers, so the guardian stays in path.

TOKEN BUDGET PER STEP (protects 8GB VRAM + latency)
---------------------------------------------------
  navigation system prompt   ~200 tok
  goal                       ~40 tok
  history: last AGENT_MAX_OBS observations, each truncated to AGENT_OBS_CHARS
           chars (~AGENT_OBS_CHARS/4 tok) => ~<=6*300 = ~1800 tok worst case
  => context <= ~2.2k tokens, comfortably under num_ctx 4096
  output: AGENT_NUM_PREDICT (256) tokens -> exactly one small JSON action
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import guarded
from .config import (AGENT_MAX_STEPS, AGENT_OBS_CHARS, AGENT_MAX_OBS,
                     AGENT_MAX_PARSE_RETRIES)

logger = logging.getLogger("chhoti.browser.agent")

# The ONLY actions the loop may take. Every web action maps to a Phase-1 GUARDED
# wrapper (never the raw session), so browser.guarded._gate stays in the path.
READ_ONLY_ACTIONS = ("search", "navigate", "read_page", "get_content", "finish")

_GATE_DENY_MARKERS = {"BLOCKED_DOMAIN", "RATE_LIMITED", "GUARDIAN_DENIED", "INVALID_URL"}


def _dispatch(tool: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a read-only action via the guarded wrappers (guardian in path)."""
    if tool == "search":
        return guarded.web_search({"query": str(args.get("query", "")).strip(),
                                   "max_results": int(args.get("max_results", 5) or 5)})
    if tool == "navigate":
        return guarded.browser_navigate({"url": str(args.get("url", "")).strip()})
    if tool == "read_page":
        return guarded.browser_read({"url": str(args.get("url", "")).strip()})
    if tool == "get_content":
        return guarded.browser_get_content({"url": str(args.get("url", "")).strip()})
    return {"status": "error", "marker": "UNKNOWN_TOOL", "tool": tool}


def _parse_action(raw: str) -> Optional[Dict[str, Any]]:
    """Defensively parse a JSON action from possibly-messy model output.

    Tolerates code fences, leading/trailing prose, trailing commas and single
    quotes. Returns None (caller retries with a corrective nudge) on failure.
    """
    if not raw:
        return None
    text = raw.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    blob = text[start:end + 1]
    obj = None
    try:
        obj = json.loads(blob)
    except Exception:
        try:  # tolerate trailing commas / single quotes
            fixed = re.sub(r",\s*([}\]])", r"\1", blob).replace("'", '"')
            obj = json.loads(fixed)
        except Exception:
            return None
    if not isinstance(obj, dict):
        return None
    tool = str(obj.get("tool") or obj.get("action") or "").strip().lower()
    if tool not in READ_ONLY_ACTIONS:
        return None
    args = obj.get("args")
    if not isinstance(args, dict):
        # tolerate flat shapes: {"tool":"search","query":".."} / {"answer":".."}
        args = {k: v for k, v in obj.items() if k not in ("tool", "action", "thought")}
    return {"tool": tool, "args": args, "thought": str(obj.get("thought", ""))[:200]}


def _summarize(tool: str, result: Dict[str, Any], obs_chars: int) -> str:
    """Turn a tool result into a small, token-efficient observation string."""
    if not isinstance(result, dict):
        return str(result)[:obs_chars]
    if result.get("status") == "error":
        return f"ERROR {result.get('marker', '')}: {result.get('message', '')}".strip()[:obs_chars]
    if tool == "search":
        rows = result.get("results", []) or []
        if not rows:
            return "No results."
        lines = [f"{i + 1}. {r.get('title', '')} — {r.get('url', '')}\n   {r.get('snippet', '')}"
                 for i, r in enumerate(rows[:5])]
        return "\n".join(lines)[:obs_chars]
    if tool == "navigate":
        return f"title={result.get('title', '')} url={result.get('url', '')}"[:obs_chars]
    # read_page / get_content -> page content (already boilerplate-stripped)
    header = f"[{result.get('title', '')}] {result.get('url', '')}\n"
    return (header + (result.get("content", "") or ""))[:obs_chars]


class BrowserResearchAgent:
    """Bounded, read-only plan->act->observe loop over the guarded browser tools."""

    def __init__(self, think_fn: Callable[[str], str],
                 synth_fn: Optional[Callable[[str], str]] = None,
                 max_steps: int = AGENT_MAX_STEPS, obs_chars: int = AGENT_OBS_CHARS,
                 max_obs: int = AGENT_MAX_OBS,
                 max_parse_retries: int = AGENT_MAX_PARSE_RETRIES):
        self.think_fn = think_fn                 # nav brain -> JSON action (per step)
        self.synth_fn = synth_fn or think_fn     # plain-text final synthesis
        self.max_steps = max(1, int(max_steps))
        self.obs_chars = obs_chars
        self.max_obs = max_obs
        self.max_parse_retries = max_parse_retries

    def _build_prompt(self, goal: str, history: List[Tuple[Dict, str]],
                      corrective: Optional[str] = None) -> str:
        lines = [f"GOAL: {goal}", ""]
        if history:
            lines.append("OBSERVATIONS SO FAR:")
            for i, (act, obs) in enumerate(history[-self.max_obs:], 1):
                lines.append(f"[{i}] action={act['tool']} args={json.dumps(act['args'])[:160]}")
                lines.append(f"    observation: {obs}")
            lines.append("")
        if corrective:
            lines.append("NOTE: " + corrective)
        lines.append("Choose the next action. Reply with ONE JSON object only "
                     "(keys: thought, tool, args). Use finish when you can answer the GOAL.")
        return "\n".join(lines)

    def run(self, goal: str) -> Dict[str, Any]:
        history: List[Tuple[Dict, str]] = []
        trace: List[Dict[str, Any]] = []
        parse_retries = 0
        t0 = time.perf_counter()

        for step in range(1, self.max_steps + 1):
            # Up to 2 attempts per step: initial + one corrective nudge.
            action = None
            corrective = None
            for _attempt in range(2):
                step_llm_t = time.perf_counter()
                raw = self.think_fn(self._build_prompt(goal, history, corrective))
                llm_ms = round((time.perf_counter() - step_llm_t) * 1000, 1)
                action = _parse_action(raw)
                if action is not None:
                    break
                parse_retries += 1
                logger.info("[browser-agent] step=%d parse_retry (%d) raw=%r",
                            step, parse_retries, (raw or "")[:100])
                corrective = ("Your previous reply was not valid JSON. Reply with ONLY a JSON "
                              'object like {"thought":"..","tool":"search","args":{"query":".."}}.')
                if parse_retries > self.max_parse_retries:
                    break

            if action is None:
                if parse_retries > self.max_parse_retries:
                    trace.append({"step": step, "error": "parse_failed", "llm_ms": llm_ms})
                    return self._result(goal, "Could not parse a valid action from the model "
                                        "after repeated retries.", trace, step, history,
                                        "parse_error", t0)
                trace.append({"step": step, "error": "parse_failed_step", "llm_ms": llm_ms})
                history.append(({"tool": "search", "args": {}},
                                "(previous step produced no valid action)"))
                continue

            tool, args = action["tool"], action["args"]

            if tool == "finish":
                answer = str(args.get("answer", "")).strip() or "(no answer given)"
                logger.info("[browser-agent] step=%d FINISH", step)
                trace.append({"step": step, "action": "finish", "thought": action["thought"],
                              "llm_ms": llm_ms})
                return self._result(goal, answer, trace, step, history, "finish", t0)

            act_t = time.perf_counter()
            result = _dispatch(tool, args)
            tool_ms = round((time.perf_counter() - act_t) * 1000, 1)
            marker = result.get("marker") if isinstance(result, dict) else None
            gate = ("DENY:" + marker) if marker in _GATE_DENY_MARKERS else "ALLOW"
            logger.info("[browser-agent] step=%d tool=%s gate=%s args=%s llm_ms=%s tool_ms=%s",
                        step, tool, gate, json.dumps(args)[:120], llm_ms, tool_ms)
            obs = _summarize(tool, result, self.obs_chars)
            history.append((action, obs))
            trace.append({"step": step, "action": tool, "args": args,
                          "thought": action["thought"], "gate": gate,
                          "llm_ms": llm_ms, "tool_ms": tool_ms, "observation": obs[:400]})

        # Reached the HARD step cap without a finish -> synthesize + stop cleanly.
        logger.info("[browser-agent] max_steps=%d cap reached; stopping", self.max_steps)
        return self._result(goal, None, trace, self.max_steps, history, "max_steps", t0)

    def _result(self, goal, answer, trace, steps, history, stopped, t0) -> Dict[str, Any]:
        if answer is None:  # cap/fallback: one plain-text synthesis from observations
            answer = self._synthesize(goal, history)
        return {"answer": answer, "trace": trace, "steps": steps, "stopped": stopped,
                "total_ms": round((time.perf_counter() - t0) * 1000, 1)}

    def _synthesize(self, goal, history) -> str:
        if not history:
            return "Could not gather enough information within the step limit."
        obs_text = "\n\n".join(o for _, o in history[-self.max_obs:])[:3000]
        prompt = (f"GOAL: {goal}\n\nRead-only observations gathered:\n{obs_text}\n\n"
                  "Answer the GOAL from these observations in plain text. If they are "
                  "insufficient, say so briefly. No JSON.")
        try:
            ans = (self.synth_fn(prompt) or "").strip()
        except Exception:
            ans = ""
        return ans or "Could not determine the answer within the step limit."


def run_research(goal: str, think_fn: Callable[[str], str],
                 synth_fn: Optional[Callable[[str], str]] = None,
                 max_steps: int = AGENT_MAX_STEPS, **kw) -> Dict[str, Any]:
    """Convenience entry: build the agent and run one research goal."""
    return BrowserResearchAgent(think_fn, synth_fn=synth_fn, max_steps=max_steps, **kw).run(goal)
