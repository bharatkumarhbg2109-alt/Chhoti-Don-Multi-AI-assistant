"""
Chhoti Don - Brain
Main AI brain with Ollama model routing + coding engine integration.
"""

import os
import re
import json
import requests
from dotenv import load_dotenv
from core.memory import Memory
from core.brain_registry import (
    get_brain,
    get_brain_model,
    get_system_prompt,
    get_temperature,
)
from core.config import Config

load_dotenv()

# Ollama config
OLLAMA_URL = Config.OLLAMA_URL
OLLAMA_TIMEOUT = Config.OLLAMA_TIMEOUT


class Brain:

    # ==================================================
    # INIT
    # ==================================================
    def __init__(self):
        self.memory = Memory()
        self.api_key = os.getenv("OPENAI_API_KEY")
        self._current_brain_type = "default"

        # Mode Priority:
        # 1. OpenAI API
        # 2. Local Ollama
        # 3. Simulation

        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                self.mode = "api"
            except ImportError:
                self.mode = "local"
        else:
            try:
                response = requests.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=3)
                response.raise_for_status()
                names = [item.get("name", "") for item in response.json().get("models", [])]
                required_base = Config.LOCAL_MODEL.split(":")[0]
                available = any(
                    name == Config.LOCAL_MODEL or name.split(":")[0] == required_base
                    for name in names
                )
                self.mode = "local" if available else "simulation"
            except Exception:
                self.mode = "simulation"

    # ==================================================
    # MAIN THINK FUNCTION
    # ==================================================
    def think(self, prompt, brain_type: str = None, system_override: str = None):
        """
        Main AI reasoning function.

        Args:
            prompt (str): User ka input
            brain_type (str): Kaunsa brain use karna hai — 'coding', 'debug', 'default', etc.
            system_override (str): Custom system prompt override

        Returns:
            str: AI response
        """
        self.memory.add("user", prompt)

        # Brain type set karo
        active_brain = brain_type or self._current_brain_type or "default"

        # System prompt decide karo
        if system_override:
            system_prompt = system_override
        else:
            system_prompt = get_system_prompt(active_brain)

        # Model decide karo
        model = get_brain_model(active_brain)
        temperature = get_temperature(active_brain)

        if self.mode == "simulation":
            reply = self.simulated_response(prompt)
            self.memory.add("assistant", reply)
            return reply

        if self.mode == "local":
            reply = self.local_think(
                prompt,
                model=model,
                system_prompt=system_prompt,
                temperature=temperature
            )
            self.memory.add("assistant", reply)
            return reply

        # API Mode (OpenAI)
        try:
            messages = self.memory.get_context()

            # System prompt inject karo
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + [
                    m for m in messages if m.get("role") != "system"
                ]

            from openai import OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=temperature
            )

            reply = response.choices[0].message.content
            self.memory.add("assistant", reply)
            return reply

        except Exception as e:
            return f"Brain Error: {str(e)}"

    # ==================================================
    # CODING-SPECIFIC THINK
    # ==================================================
    def think_code(self, prompt: str, language: str = "python") -> str:
        """
        Coding brain use karke code generate karo.

        Args:
            prompt (str): Kya banana hai
            language (str): Programming language

        Returns:
            str: Generated code response
        """
        system_prompt = (
            f"You are Chhoti Don's coding engine — an expert {language} programmer. "
            f"Write clean, working, well-commented {language} code. "
            f"Always wrap code in triple backticks with language name: ```{language} ... ```. "
            "Be concise. No extra explanation outside code block unless asked."
        )

        return self.think(prompt, brain_type="coding", system_override=system_prompt)

    # ==================================================
    # DEBUG-SPECIFIC THINK
    # ==================================================
    def think_debug(self, code: str, error: str, language: str = "python") -> str:
        """
        Debug brain use karke code fix karo.

        Args:
            code (str): Buggy code
            error (str): Error message
            language (str): Programming language

        Returns:
            str: Debug response with fix
        """
        prompt = f"""Ye {language} code mein bug hai. Fix karo.

ERROR:
{error}

BUGGY CODE:
```{language}
{code}
```

Response format:
EXPLANATION: [kya galat tha, 2-3 lines]
FIXED_CODE:
```{language}
[poora fixed code yahan]
```"""

        system_prompt = (
            "You are Chhoti Don's debugging specialist. "
            "Find bugs, explain what went wrong, and provide the complete fixed code. "
            "Always show: 1) EXPLANATION of the bug 2) FIXED_CODE in backticks."
        )

        return self.think(prompt, brain_type="debug", system_override=system_prompt)

    # ==================================================
    # EXPLAIN-SPECIFIC THINK
    # ==================================================
    def think_explain(self, code: str, language: str = "python", detail_level: str = "simple") -> str:
        """
        Code explanation generate karo.

        Args:
            code (str): Code to explain
            language (str): Programming language
            detail_level (str): 'simple' or 'detailed'

        Returns:
            str: Explanation
        """
        level_desc = "simple aur beginner-friendly" if detail_level == "simple" else "detailed aur technical"

        prompt = f"""Is {language} code ko {level_desc} tarike se explain karo:

```{language}
{code}
```

Explain karo:
1. Ye code kya karta hai (overview)
2. Har important part kya kar raha hai
3. Koi potential issues hain toh batao"""

        return self.think(prompt, brain_type="coding")

    # ==================================================
    # LOCAL OLLAMA MODE — Enhanced
    # ==================================================
    def local_think(
        self,
        prompt: str,
        model: str = None,
        system_prompt: str = "",
        temperature: float = 0.7
    ) -> str:
        """
        Ollama se local model call karo.
        """
        # Default model
        if not model:
            model = get_brain_model(self._current_brain_type or "default")

        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                # qwen3.x are "thinking" models: without this they spend the
                # token budget on hidden reasoning and can return an empty
                # visible answer. Disabling gives clean, fast replies.
                # Non-thinking models (e.g. deepseek-coder) ignore this flag.
                "think": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 2048,
                    # Cap the context window so qwen3.5 (whose default context is
                    # enormous -> ~16GB) fits an 8GB GPU instead of being
                    # CPU-offloaded and slow. Tunable via CHHOTI_DON_OLLAMA_NUM_CTX.
                    "num_ctx": int(os.getenv("CHHOTI_DON_OLLAMA_NUM_CTX", "8192")),
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=OLLAMA_TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                return f"Ollama HTTP Error {response.status_code}: {response.text[:200]}"

        except requests.exceptions.ConnectionError:
            return "❌ Ollama server nahi mila! Terminal mein 'ollama serve' run karo."
        except requests.exceptions.Timeout:
            return f"❌ Ollama timeout ({OLLAMA_TIMEOUT}s) — model slow hai ya GPU busy hai."
        except Exception as e:
            return f"Local Brain Error: {str(e)}"

    # ==================================================
    # SET ACTIVE BRAIN TYPE
    # ==================================================
    def set_brain(self, brain_type: str):
        """Active brain type set karo."""
        self._current_brain_type = brain_type

    def get_active_brain(self) -> str:
        """Current active brain type return karo."""
        return self._current_brain_type

    # ==================================================
    # LEVEL 4 — MEMORY-AWARE STRICT JSON PLANNER
    # ==================================================
    def plan_task(self, task):

        context = self.memory.get_context()

        planning_prompt = f"""
You are an autonomous AI planner.

Return ONLY valid JSON.
Do NOT explain.
Do NOT add extra text.

Available agents:
coder, security, analyst

Available tools:
calculator, run_python, read_file, search,
web_search, open_page, generate_code, execute_code, debug_code, explain_code

Conversation Context:
{context}

Current Task:
{task}

JSON FORMAT:

{{
  "steps": [
    {{"type": "agent", "name": "coder"}},
    {{"type": "tool", "name": "search"}}
  ]
}}
"""

        try:
            if self.mode == "local":
                raw = self.local_think(planning_prompt, model=get_brain_model("default"))
            elif self.mode == "api":
                from openai import OpenAI
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": planning_prompt}]
                )
                raw = response.choices[0].message.content
            else:
                return None

            print("RAW PLANNER OUTPUT:\n", raw)

            cleaned = raw.strip()
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1

            if start == -1 or end == -1:
                return None

            cleaned = cleaned[start:end]
            parsed = json.loads(cleaned)

            if "steps" not in parsed:
                return None

            return json.dumps(parsed)

        except Exception as e:
            print("PLANNER ERROR:", e)
            return None

    # ==================================================
    # RULE-BASED TOOL DETECTION (Fallback)
    # ==================================================
    def decide_tool(self, task):

        task_lower = task.lower()

        # Coding tools detection
        coding_generate = ["code banao", "code likho", "write code", "generate code",
                           "function banao", "script banao", "program banao"]
        coding_execute = ["code chalao", "run karo", "execute karo", "chalao", "run this"]
        coding_debug = ["debug karo", "fix karo", "error fix", "bug fix", "error hai"]
        coding_explain = ["samjhao", "explain karo", "kya karta hai ye code", "explain this code"]

        for kw in coding_execute:
            if kw in task_lower:
                return "execute_code"
        for kw in coding_debug:
            if kw in task_lower:
                return "debug_code"
        for kw in coding_explain:
            if kw in task_lower:
                return "explain_code"
        for kw in coding_generate:
            if kw in task_lower:
                return "generate_code"

        # Math patterns
        math_patterns = [
            r'\d+\s*[\+\-\*/]\s*\d+',
            r'add\s+\d+\s+and\s+\d+',
            r'subtract\s+\d+\s+from\s+\d+',
            r'multiply\s+\d+\s+by\s+\d+',
            r'divide\s+\d+\s+by\s+\d+',
            r'square\s+of\s+\d+',
            r'cube\s+of\s+\d+'
        ]

        for pattern in math_patterns:
            if re.search(pattern, task_lower):
                return "calculator"

        if "calculate" in task_lower:
            return "calculator"
        if "read file" in task_lower:
            return "read_file"
        if "run python" in task_lower:
            return "run_python"
        if re.search(r"https?://\S+", task_lower) and any(word in task_lower for word in ["open page", "read page", "open url", "read url"]):
            return "open_page"
        if any(word in task_lower for word in ["web search", "search web", "search online", "latest news"]):
            return "web_search"
        if "search" in task_lower:
            return "search"

        return None

    # ==================================================
    # NUMBER EXTRACTION
    # ==================================================
    def extract_numbers(self, text):
        return list(map(float, re.findall(r'\d+\.?\d*', text)))

    # ==================================================
    # SELF REVIEW & CORRECTION
    # ==================================================
    def review_and_fix(self, task, result):

        review_prompt = f"""
You are an AI quality reviewer.

Task:
{task}

Generated Result:
{result}

If correct return EXACTLY: APPROVED
If incorrect return corrected improved version only.
"""

        try:
            if self.mode == "local":
                review = self.local_think(review_prompt)
            elif self.mode == "api":
                from openai import OpenAI
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": review_prompt}]
                )
                review = response.choices[0].message.content
            else:
                return "APPROVED"

            return review.strip()

        except Exception:
            return "APPROVED"

    # ==================================================
    # OLLAMA STATUS CHECK
    # ==================================================
    def check_ollama(self) -> dict:
        """Ollama server status check karo."""
        try:
            response = requests.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                return {
                    "online": True,
                    "mode": self.mode,
                    "models": model_names,
                    "message": f"✅ Ollama online! {len(model_names)} models available."
                }
        except Exception:
            pass

        return {
            "online": False,
            "mode": self.mode,
            "models": [],
            "message": "❌ Ollama offline! 'ollama serve' run karo."
        }

    # ==================================================
    # SIMULATION MODE
    # ==================================================
    def simulated_response(self, prompt):
        return (
            "[Simulated Brain Response]\n"
            f"Processed task: {prompt}"
        )
