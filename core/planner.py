"""
Chhoti Don - Structured Planner
Advanced task planning with telemetry bias,
tool preference routing, and plan mutation.
Phase 2.2 - Full Upgrade (Preserved)
"""

import json
from typing import Dict, Optional, Optional


class StructuredPlanner:
    """
    Advanced Structured Planner.
    Preserved + upgraded with better fallbacks.
    """

    def __init__(self, controller, telemetry=None):
        """
        controller: CyberController or Brain instance
        telemetry: TelemetryEngine instance (optional)
        """
        self.controller = controller
        self.telemetry = telemetry

    # ==================================================
    # 📊 TELEMETRY BIAS (PRESERVED)
    # ==================================================
    def _extract_bias(self):
        """Extract telemetry-based routing bias. Preserved."""
        preferred_tools = []
        avoid_tools = []
        unstable = False
        last_error_code = None

        if not self.telemetry:
            return preferred_tools, avoid_tools, unstable, last_error_code

        if hasattr(self.telemetry, "get_planner_bias_snapshot"):
            snapshot = self.telemetry.get_planner_bias_snapshot()
            preferred_tools = snapshot.get("preferred_tools", [])
            avoid_tools = snapshot.get("avoid_tools", [])
            unstable = snapshot.get("system_state", {}).get("unstable", False)
            last_error_code = snapshot.get("last_error_code")
            return preferred_tools, avoid_tools, unstable, last_error_code

        # Fallback legacy
        for tool, reliability in self.telemetry.tool_health_score.items():
            if reliability >= 0.7:
                preferred_tools.append(tool)
            elif reliability < 0.4:
                avoid_tools.append(tool)

        for tool, streak in self.telemetry.failure_streak.items():
            if streak >= 3 and tool not in avoid_tools:
                avoid_tools.append(tool)

        unstable = self.telemetry.detect_instability()
        return preferred_tools, avoid_tools, unstable, None

    # ==================================================
    # 🗺️ PLAN GENERATION (PRESERVED + UPGRADED)
    # ==================================================
    def generate_plan(self, user_goal: str) -> Dict:
        """Generate execution plan with telemetry bias. Preserved."""
        preferred_tools, avoid_tools, unstable, last_error_code = self._extract_bias()

        if self.telemetry and hasattr(self.telemetry, "tool_health_score"):
            preferred_tools = sorted(
                preferred_tools,
                key=lambda t: self.telemetry.tool_health_score.get(t, 0),
                reverse=True,
            )

        system_prompt = f"""You are a planning engine.
Return ONLY valid JSON. No explanation. No markdown.

Format:
{{"goal": "...", "steps": [{{"id": 1, "action": "tool_name", "input": {{}}}}]}}

System State:
- Unstable: {unstable}
- Preferred Tools: {preferred_tools}
- Avoid Tools: {avoid_tools}
- Last Error Code: {last_error_code}

Rules:
- Only JSON. No explanation.
- Prefer high reliability tools.
- Avoid listed tools unless absolutely necessary.
- If unstable, keep plan simple (max 3 steps).
"""

        try:
            # Generate plan
            if hasattr(self.controller, "generate"):
                response = self.controller.generate(system_prompt + "\nUser Goal:\n" + user_goal)
            elif hasattr(self.controller, "think"):
                response = self.controller.think(user_goal, brain_type="planner",
                                                  system_override=system_prompt)
            else:
                return {"status": "error", "reason": "Controller has no generate/think method"}

            # Parse JSON
            plan = self._parse_plan(response)
            if not plan:
                return {"status": "error", "reason": "Invalid JSON from LLM"}

            if "steps" not in plan:
                return {"status": "error", "reason": "Plan missing steps"}

            # Strategy mutation — replace avoided tools
            if avoid_tools:
                for step in plan.get("steps", []):
                    if step.get("action") in avoid_tools and preferred_tools:
                        step["action"] = preferred_tools[0]
                        step["mutated"] = True

            # Confidence hint
            confidence = 1.0
            if unstable:
                confidence *= 0.85
            if avoid_tools:
                confidence *= 0.9

            return {
                "status": "success",
                "plan": plan,
                "meta": {
                    "preferred_tools": preferred_tools,
                    "avoid_tools": avoid_tools,
                    "system_unstable": unstable,
                    "last_error_code": last_error_code,
                    "plan_confidence_hint": round(confidence, 4),
                },
            }

        except json.JSONDecodeError:
            return {"status": "error", "reason": "Invalid JSON from LLM"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}

    def _parse_plan(self, raw: str) -> Optional[Dict]:
        """Raw LLM output se JSON plan parse karo."""
        if not raw:
            return None
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        try:
            return json.loads(cleaned[start:end])
        except json.JSONDecodeError:
            return None

    def validate_plan(self, plan: Dict) -> Dict:
        """Plan structure validate karo."""
        if not isinstance(plan, dict):
            return {"valid": False, "reason": "Plan must be a dict"}
        if "steps" not in plan:
            return {"valid": False, "reason": "Missing 'steps' key"}
        if not isinstance(plan["steps"], list):
            return {"valid": False, "reason": "Steps must be a list"}
        if len(plan["steps"]) == 0:
            return {"valid": False, "reason": "Empty steps list"}
        return {"valid": True, "step_count": len(plan["steps"])}
