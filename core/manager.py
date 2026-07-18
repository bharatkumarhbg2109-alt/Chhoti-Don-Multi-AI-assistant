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
            elif tool_name == "run_python":
                payload = {"code": task}

            return self.safe_tool_execute(tool_name, payload, user_lang)

        response = self.brain.think(task)

        return {
            "agent": "Brain",
            "language": user_lang,
            "thinking": "LLM reasoning",
            "output": response,
        }

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

            if step_type == "agent":
                agent = self.create_agent(step_name)
                result = agent.act(current_output)

            elif step_type == "tool":
                tool_exec = self.tool_registry.execute(
                    step_name, {"input": current_output}
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
