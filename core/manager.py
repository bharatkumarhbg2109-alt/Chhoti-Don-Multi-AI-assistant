"""
Chhoti Don - Manager Agent
Central orchestrator — sab agents, tools, aur brain ko manage karta hai.
Coding engine fully integrated with brain routing.
"""

import json
import time
from tools.registry import ToolRegistry
from core.language import detect_language
from chhoti_agents.coder import CoderAgent
from chhoti_agents.security import SecurityAgent
from chhoti_agents.analyst import AnalystAgent
from core.brain import Brain
from core.memory import Memory
from cyber_engine.guardian.operator_guard import OperatorGuard
from core.task_classifier import detect_task
from core.brain_router import route_task, detect_intent, route_coding_tool
from core.local_model_engine import execute


def _should_run_rag(task: str) -> bool:
    """
    Decide whether a message is worth the RAG embed + Chroma query.

    The ai_knowledge corpus is arXiv AI/ML research, so RAG only ever helps
    knowledge/technical questions — never plain chit-chat. This cheap keyword
    check (detect_intent/detect_task, ~0ms) lets pure conversational messages
    (greetings, thanks, mood: "hi", "kaise ho", "good morning") SKIP the ~763ms
    embed entirely and go straight to generation.

    CONSERVATIVE BY DESIGN: RAG is skipped ONLY when the message is classified as
    conversational chit-chat by intent OR task. Everything else — research,
    analytics, and the catch-all "default" (any question that didn't match the
    chit-chat keywords) — still runs RAG. A missed factual context is worse than
    a wasted embed, so when in doubt we RUN RAG. This changes no answer content:
    a chit-chat message never had a chunk within the 0.45 distance gate, so it
    was never injected — we only avoid paying for the embed that returns nothing.
    """
    try:
        intent = detect_intent(task)
        task_type = detect_task(task)
    except Exception:
        return True  # any classifier hiccup -> fail safe, run RAG
    if intent == "conversation" or task_type == "conversation":
        return False
    return True


def _as_text(value) -> str:
    """Coerce an arbitrary pipeline value into a safe text task string."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        # Prefer common human-readable fields when chaining agent/tool output.
        for key in ("message", "output", "response", "explanation", "text", "result"):
            v = value.get(key)
            if isinstance(v, str) and v.strip():
                return v
        try:
            import json
            return json.dumps(value, ensure_ascii=False)[:4000]
        except Exception:
            return str(value)[:4000]
    return str(value)[:4000]


class ManagerAgent:

    def __init__(self):
        self.agents = {}
        self.brain = Brain()
        self.memory = Memory()
        self.tool_registry = ToolRegistry(brain=self.brain)  # Brain inject karo
        self.guardian = OperatorGuard()
        self.session_log = []

    # --------------------------------------------------
    # 🔥 LEVEL 7 — HYBRID BRAIN MODE
    # --------------------------------------------------
    def hybrid_llm_task(self, task):

        user_lang = detect_language(task)
        task_type = detect_task(task)
        model_config = route_task(task_type)

        start_time = time.time()

        try:
            response = execute(model_config, task)
        except Exception as e:
            response = f"Model execution failed: {str(e)}"

        execution_time = round(time.time() - start_time, 3)

        self.memory.add("user", task)
        self.memory.add("assistant", str(response)[:2000])

        return {
            "agent": f"HybridBrain({model_config.get('model')})",
            "language": user_lang,
            "task_type": task_type,
            "thinking": "Hybrid routing via Brain Router",
            "output": response,
            "execution_time_sec": execution_time,
            "confidence": 0.85,
        }

    # --------------------------------------------------
    # 🔁 Backward Compatibility
    # --------------------------------------------------
    def execute_tool(self, tool_name, payload):
        return self._process_tool_pipeline(tool_name, payload, "system")

    # --------------------------------------------------
    # 💻 CODING ENGINE — Natural Language Handler
    # --------------------------------------------------
    def coding_task(self, task: str) -> dict:
        """
        Natural language se coding task handle karo.
        Auto-detect karta hai — generate/execute/debug/explain

        Special: "banao aur chalao" type requests mein
        automatically generate → execute pipeline run hoti hai.
        """
        user_lang = detect_language(task)
        start_time = time.time()

        # Coding tool aur language detect karo
        routing = route_coding_tool(task)
        tool_name = routing["tool_name"]
        language = routing["extracted_language"]
        confidence = routing["confidence"]

        # Brain ko coding mode mein set karo
        self.brain.set_brain("coding")

        # --------------------------------------------------
        # 🔥 Generate + Execute Pipeline Detection
        # --------------------------------------------------
        run_keywords = [
            "aur chalao", "aur run karo", "aur execute karo",
            "and run", "and execute", "then run", "chalao bhi",
            "run bhi karo", "execute bhi", "aur chala do",
        ]
        needs_execute = any(kw in task.lower() for kw in run_keywords)

        # Agar execute detect hua but code nahi hai input mein
        # toh pehle generate karo
        extracted_code = self._extract_code_from_task(task)
        if tool_name == "execute_code" and not extracted_code:
            tool_name = "generate_code"
            needs_execute = True

        # Tool-specific payload build karo
        payload = self._build_coding_payload(task, tool_name, language)

        # Step 1 — Primary tool execute karo
        result = self._process_tool_pipeline(tool_name, payload, user_lang)

        # --------------------------------------------------
        # 🔄 Step 2 — Auto Execute agar generate+run request thi
        # --------------------------------------------------
        execution_result = None
        if needs_execute and tool_name == "generate_code":
            generated = result.get("output", {})
            generated_code = None

            if isinstance(generated, dict):
                generated_code = generated.get("code")

            if generated_code:
                print(f"\n⚙️  Auto-executing generated {language} code...")
                exec_payload = {
                    "code": generated_code,
                    "language": language,
                }
                execution_result = self._process_tool_pipeline(
                    "execute_code", exec_payload, user_lang
                )

        execution_time = round(time.time() - start_time, 3)

        # Memory mein save karo
        self.memory.add("user", task)
        self.memory.add("assistant", str(result.get("output", ""))[:2000])

        result["coding_meta"] = {
            "detected_tool": tool_name,
            "detected_language": language,
            "routing_confidence": confidence,
            "execution_time_sec": execution_time,
            "auto_executed": needs_execute,
        }

        # Execution result attach karo agar tha
        if execution_result:
            result["execution_result"] = execution_result.get("output")

        return result

    def _build_coding_payload(self, task: str, tool_name: str, language: str) -> dict:
        """Tool ke hisaab se payload build karo."""

        if tool_name == "generate_code":
            return {
                "prompt": task,
                "language": language,
            }

        elif tool_name == "execute_code":
            # Code extract karne ki koshish karo task se
            code = self._extract_code_from_task(task)
            return {
                "code": code or task,
                "language": language,
            }

        elif tool_name == "debug_code":
            code = self._extract_code_from_task(task)
            error = self._extract_error_from_task(task)
            return {
                "code": code or task,
                "error": error or "",
                "language": language,
            }

        elif tool_name == "explain_code":
            code = self._extract_code_from_task(task)
            return {
                "code": code or task,
                "language": language,
                "detail_level": "detailed" if "detail" in task.lower() else "simple",
            }

        return {"prompt": task, "language": language}

    def _extract_code_from_task(self, task: str) -> str:
        """Task se code block extract karo agar hai."""
        import re
        pattern = r"```(?:\w+)?\n([\s\S]*?)```"
        match = re.search(pattern, task)
        if match:
            return match.group(1).strip()
        return None

    def _extract_error_from_task(self, task: str) -> str:
        """Task se error message extract karo."""
        import re
        # Common error patterns
        error_patterns = [
            r"((?:Traceback|Error|Exception)[\s\S]*?)(?:\n\n|$)",
            r"error[:\s]+(.+?)(?:\n|$)",
        ]
        for pattern in error_patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(0).strip()
        return None

    # --------------------------------------------------
    # 🔥 CENTRALIZED TOOL PIPELINE
    # --------------------------------------------------
    def _process_tool_pipeline(self, tool_name, payload, user_lang):

        start_time = time.time()

        # Guardian check
        try:
            if self.guardian.requires_approval(tool_name):
                approved = self.guardian.request_permission(tool_name)
                if not approved:
                    return {
                        "agent": "Guardian",
                        "language": user_lang,
                        "thinking": "Execution blocked by Guardian",
                        "output": "Permission denied",
                        "confidence": 0.2,
                    }
        except Exception:
            pass

        tool_result = self.tool_registry.execute(tool_name, payload)

        if not tool_result or tool_result.get("status") != "success":
            return {
                "agent": "ToolError",
                "language": user_lang,
                "thinking": f"{tool_name} execution failed",
                "output": tool_result,
                "confidence": 0.2,
            }

        result_data = tool_result.get("result")
        confidence = tool_result.get("confidence", 0.7)
        risk_info = None

        # --------------------------------------------------
        # 🧠 Recon Intelligence Layer (Preserved)
        # --------------------------------------------------
        if tool_name in ["port_scan", "nmap_scan"] and isinstance(result_data, dict):

            open_ports = result_data.get("open_ports", [])
            count = len(open_ports)

            service_map = {
                80: "HTTP", 443: "HTTPS", 22: "SSH", 21: "FTP",
                25: "SMTP", 3306: "MySQL", 3389: "RDP", 8080: "HTTP-Alt",
            }

            threat_map = {
                22: "Brute-force / Remote Service Abuse (MITRE T1021)",
                3389: "RDP Remote Access Risk (MITRE T1021)",
                21: "FTP Credential Exposure (MITRE T1078)",
                80: "Web Attack Surface Exposure (MITRE T1190)",
                443: "Encrypted C2 Possibility (MITRE T1071)",
                3306: "Database Exposure Risk (MITRE T1046)",
            }

            guessed_services = []
            threat_tags = []

            for p in open_ports:
                if p in service_map:
                    guessed_services.append(service_map[p])
                if p in threat_map:
                    threat_tags.append(threat_map[p])

            if count == 0:
                severity = "low"
                score = 10
            elif count <= 3:
                severity = "medium"
                score = 40
            elif count <= 6:
                severity = "high"
                score = 70
            else:
                severity = "critical"
                score = 90

            risk_info = {
                "severity": severity,
                "risk_score": score,
                "open_port_count": count,
                "likely_services": guessed_services,
            }

            result_data["risk_assessment"] = risk_info
            self.memory.add("recon_event", str(result_data)[:2000])

            if severity in ["high", "critical"]:
                result_data["escalation"] = "Recommend deeper vulnerability analysis."

        # --------------------------------------------------
        # 📊 Confidence Adjustment (Preserved)
        # --------------------------------------------------
        if risk_info:
            if risk_info["severity"] == "critical":
                confidence = min(confidence + 0.15, 1.0)
            elif risk_info["severity"] == "high":
                confidence = min(confidence + 0.1, 1.0)
            elif risk_info["severity"] == "low":
                confidence = max(confidence - 0.1, 0.5)

        # --------------------------------------------------
        # 💻 Coding Result Intelligence
        # --------------------------------------------------
        if tool_name in ["generate_code", "execute_code", "debug_code", "explain_code"]:
            if isinstance(result_data, dict):
                result_data["coding_engine"] = "✅ Chhoti Don Coding Engine"
                # Confidence boost for successful coding
                if result_data.get("status") == "success":
                    confidence = min(confidence + 0.05, 1.0)

        # --------------------------------------------------
        # 🧠 Recon Pattern Awareness (Preserved)
        # --------------------------------------------------
        recent_recon = [
            entry for entry in self.session_log[-3:]
            if isinstance(entry, dict) and entry.get("risk")
        ]

        high_count = sum(
            1 for r in recent_recon
            if r.get("risk", {}).get("severity") in ["high", "critical"]
        )

        if high_count >= 2:
            result_data["pattern_warning"] = (
                "Multiple high-risk recon events detected."
            )

        # --------------------------------------------------
        # 📂 Session Logging (Preserved)
        # --------------------------------------------------
        self.session_log.append({
            "tool": tool_name,
            "risk": risk_info,
            "timestamp": time.time(),
        })

        result_data["execution_time_sec"] = round(time.time() - start_time, 3)

        return {
            "agent": "ToolExecutor",
            "language": user_lang,
            "thinking": f"{tool_name} executed through centralized intelligence pipeline",
            "output": result_data,
            "confidence": round(confidence, 2),
        }

    # --------------------------------------------------
    # 🔁 Safe Tool Execution (Preserved)
    # --------------------------------------------------
    def safe_tool_execute(self, tool_name, payload, user_lang):
        return self._process_tool_pipeline(tool_name, payload, user_lang)

    # --------------------------------------------------
    # Agent Factory (Preserved)
    # --------------------------------------------------
    def create_agent(self, agent_type):

        if agent_type == "coder":
            agent = CoderAgent()
        elif agent_type == "security":
            agent = SecurityAgent()
        elif agent_type == "analyst":
            agent = AnalystAgent()
        else:
            raise ValueError("Unknown agent type")

        self.agents[agent_type] = agent
        return agent

    # --------------------------------------------------
    # Single Agent Mode (Preserved)
    # --------------------------------------------------
    def assign_task(self, agent_type, task):

        user_lang = detect_language(task)

        if agent_type not in self.agents:
            self.create_agent(agent_type)

        agent = self.agents[agent_type]
        self.memory.add("user", task)

        thinking = agent.think(task)
        result = agent.act(task)
        formatted_output = agent.report(result)

        self.memory.add("assistant", str(formatted_output)[:2000])

        return {
            "agent": agent.name,
            "language": user_lang,
            "thinking": thinking,
            "output": formatted_output,
        }

    # --------------------------------------------------
    # Pipeline Mode (Preserved)
    # --------------------------------------------------
    def pipeline_task(self, task):

        user_lang = detect_language(task)
        self.memory.add("user", task)

        coder = self.create_agent("coder")
        code_output = coder.act(task)

        security = self.create_agent("security")
        security_review = security.act(
            f"Review this code carefully:\n\n{code_output}"
        )

        analyst = self.create_agent("analyst")
        summary = analyst.act(
            f"""Code:\n{code_output}\n\nSecurity Review:\n{security_review}\n\nProvide final technical summary."""
        )

        final_package = {
            "language": user_lang,
            "code": code_output,
            "security_review": security_review,
            "summary": summary,
        }

        self.memory.add("assistant", str(final_package)[:2000])
        return final_package

    # --------------------------------------------------
    # Brain Mode (Preserved + Coding Tools Added)
    # --------------------------------------------------
    def brain_task(self, task):

        user_lang = detect_language(task)

        # Phase-2 opt-in: an EXPLICIT "open the browser and research X" request runs
        # the read-only multi-step browser agent. The trigger is deliberately narrow
        # (see browser.routing.is_browser_research_request) so every ordinary chat /
        # coding / RAG message falls straight through to the unchanged logic below.
        try:
            from browser.routing import is_browser_research_request
            if is_browser_research_request(task):
                return self.research_task(task)
        except Exception:
            pass  # fail-open: never let the browser layer break ordinary chat

        try:
            tool_name = self.brain.decide_tool(task)
        except Exception:
            tool_name = None

        # Coding tools check
        if tool_name in ["generate_code", "execute_code", "debug_code", "explain_code"]:
            return self.coding_task(task)

        if tool_name == "calculator":
            numbers = self.brain.extract_numbers(task)
            operator = next((op for op in ["+", "-", "*", "/"] if op in task), None)

            if len(numbers) >= 2 and operator:
                return self.safe_tool_execute(
                    "calculator",
                    {"a": numbers[0], "b": numbers[1], "operator": operator},
                    user_lang,
                )

        if tool_name in self.tool_registry.list_tools():
            payload = {"input": task}
            if tool_name == "search":
                payload = {"query": task}
            elif tool_name == "web_search":
                payload = {"query": task}
            elif tool_name == "open_page":
                import re
                match = re.search(r"https?://\S+", task)
                payload = {"url": match.group(0).rstrip(".,)") if match else ""}
            elif tool_name == "run_python":
                payload = {"code": task}

            return self.safe_tool_execute(tool_name, payload, user_lang)

        # ── RAG grounding (merged ai_knowledge) ───────────────────
        # Pull fresh, relevant chunks from the shared ai_knowledge collection and
        # inject them as a SYSTEM prompt before generating. This runs AFTER the
        # guardian/safety gate (safety_policy.evaluate already ran in app.py
        # before brain_task) and ONLY on this free-form conversation path — not
        # coding, vision, or tool calls. Fail-open: no relevant context or any
        # error leaves the original behavior untouched.
        #
        # Intent gate: skip the embed + Chroma query for plain chit-chat, which
        # never clears the 0.45 distance gate anyway (see _should_run_rag). This
        # only avoids wasted work — it never changes an answer's content.
        rag_sources: list = []
        if _should_run_rag(task):
            try:
                from core.knowledge import retrieve_context, build_grounded_system
                _context, rag_sources = retrieve_context(task)
            except Exception:
                _context, rag_sources = "", []
        else:
            _context = ""

        if _context:
            from core.brain_registry import get_system_prompt
            grounded_system = build_grounded_system(get_system_prompt("default"), _context)
            response = self.brain.think(task, system_override=grounded_system)
        else:
            response = self.brain.think(task)

        result = {
            "agent": "Brain",
            "language": user_lang,
            "thinking": "LLM reasoning" + (" + ai_knowledge RAG" if rag_sources else ""),
            "output": response,
        }
        if rag_sources:
            result["sources"] = rag_sources
        return result

    # --------------------------------------------------
    # Browser research agent (Phase 2 — READ-ONLY multi-step loop)
    # --------------------------------------------------
    def research_task(self, goal: str, max_steps: int = None) -> dict:
        """Run the read-only browser research agent for ``goal`` and return a
        normal assistant result. The loop uses the dedicated 'navigation' brain
        (think_fast: think:false, small num_predict), and every browser action
        it takes is executed through the SAME guardian gate as Phase 1.
        """
        from browser.agent import run_research
        from browser.config import AGENT_MAX_STEPS

        # nav brain -> a single JSON action per step (token-cheap, fast).
        def _think(prompt: str) -> str:
            return self.brain.think_fast(prompt, brain_type="navigation")

        # plain-text synthesis for the cap/fallback path (no JSON directive).
        def _synth(prompt: str) -> str:
            return self.brain.think_fast(
                prompt, brain_type="navigation", num_predict=400,
                system_prompt="You are a concise research assistant. Answer in plain text.",
            )

        res = run_research(
            goal, think_fn=_think, synth_fn=_synth,
            max_steps=max_steps if max_steps is not None else AGENT_MAX_STEPS,
        )
        return {
            "agent": "BrowserResearchAgent",
            "language": detect_language(goal),
            "thinking": ("read-only browser research: %d step(s), stopped=%s"
                         % (res["steps"], res["stopped"])),
            "output": res["answer"],
            "steps": res["steps"],
            "stopped": res["stopped"],
            "total_ms": res["total_ms"],
            "trace": res["trace"],
        }

    # --------------------------------------------------
    # Brain Mode — STREAMING (token-by-token)
    # --------------------------------------------------
    def brain_task_stream(self, task):
        """
        Streaming counterpart of brain_task for the plain LLM-chat path.

        Yields response text chunks as the model generates them. The RAG grounding
        decision (intent-gated retrieval + 0.45 distance gate + top-3 injection)
        is resolved BEFORE the first token is yielded, so grounding is byte-for-
        byte identical to brain_task — only the final generation is streamed.

        Callers must only use this for the plain chat-generation path (i.e. when
        decide_tool would return None and the message isn't coding/vision/tool);
        app.py makes that determination and routes tool/coding messages through
        the non-streaming brain_task instead. Kept separate so brain_task stays
        untouched for every existing caller/test.
        """
        # RAG grounding (same logic + same intent gate as brain_task), resolved
        # up-front so no token is streamed before the grounding decision is made.
        grounded_system = None
        if _should_run_rag(task):
            try:
                from core.knowledge import retrieve_context, build_grounded_system
                _context, _sources = retrieve_context(task)
            except Exception:
                _context = ""
            if _context:
                from core.brain_registry import get_system_prompt
                grounded_system = build_grounded_system(get_system_prompt("default"), _context)

        if grounded_system:
            yield from self.brain.think_stream(task, system_override=grounded_system)
        else:
            yield from self.brain.think_stream(task)

    # --------------------------------------------------
    # Autonomous Mode (Preserved + Coding Tools Added)
    # --------------------------------------------------
    def autonomous_llm_task(self, task):

        user_lang = detect_language(task)

        # Coding intent check pehle
        intent = detect_intent(task)
        if intent in ["coding", "debug"]:
            return self.coding_task(task)

        simple_tool = self.brain.decide_tool(task)
        if simple_tool:
            return self.brain_task(task)

        plan_text = self.brain.plan_task(task)
        if not plan_text:
            return self.brain_task(task)

        try:
            plan_data = json.loads(plan_text)
        except Exception:
            return self.brain_task(task)

        steps = plan_data.get("steps", [])
        valid_agents = ["coder", "security", "analyst"]
        valid_tools = self.tool_registry.list_tools()

        clean_steps = []

        for step in steps:
            if not isinstance(step, dict):
                continue

            step_type = step.get("type")
            step_name = step.get("name")

            if step_type == "agent" and step_name in valid_agents:
                clean_steps.append(step)
            elif step_type == "tool" and step_name in valid_tools:
                clean_steps.append(step)

        if not clean_steps:
            return self.brain_task(task)

        current_output = task
        results = []

        for step in clean_steps:

            step_type = step.get("type")
            step_name = step.get("name")

            # Agents and tools expect a text task. Earlier steps may have produced
            # a dict/list/None, so always coerce the chained output to text before
            # feeding it into the next step (prevents e.g. dict.lower() crashes).
            step_input = current_output if isinstance(current_output, str) else _as_text(current_output)

            if step_type == "agent":
                agent = self.create_agent(step_name)
                result = agent.act(step_input)

            elif step_type == "tool":
                tool_exec = self.tool_registry.execute(
                    step_name, {"input": step_input}
                )
                result = tool_exec.get("result") if tool_exec else None

            results.append({f"{step_type}:{step_name}": result})
            current_output = result

        final_response = {
            "agent": "AutonomousLLM",
            "language": user_lang,
            "plan": clean_steps,
            "execution_results": results,
        }

        self.memory.add("assistant", str(final_response)[:2000])
        return final_response

    # --------------------------------------------------
    # Code Intelligence (Preserved)
    # --------------------------------------------------
    def code_intelligence(self, project_path):
        from cyber_engine.code_intelligence.code_controller import run_code_intelligence
        return run_code_intelligence(project_path)

    # --------------------------------------------------
    # Self Heal (Preserved)
    # --------------------------------------------------
    def full_self_heal(self, project_path):

        if self.guardian.requires_approval("self_heal"):
            approved = self.guardian.request_permission("self_heal")
            if not approved:
                print("[Guardian] Self-heal aborted.")
                return

        from cyber_engine.code_intelligence.auto_fix_engine import run_full_self_heal
        run_full_self_heal(project_path)

    # --------------------------------------------------
    # Memory (Preserved)
    # --------------------------------------------------
    def get_memory(self):
        return self.memory.get_context()
