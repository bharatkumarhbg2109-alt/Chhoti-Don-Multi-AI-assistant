"""
Chhoti Don - Brain
Main AI brain with Ollama model routing + coding engine integration.
"""

import os
import re
import json
import logging
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

logger = logging.getLogger("chhoti.brain")

# How many EXTRA times to re-call the model when it returns an empty /
# whitespace-only generation (an Ollama hiccup, not a real answer). The coding-
# agent A/B saw qwen occasionally return '' and stall a whole stage.
_EMPTY_RETRIES = int(os.getenv("CHHOTI_DON_EMPTY_RETRIES", "2"))


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
    # STREAMING THINK (token-by-token)
    # ==================================================
    def think_stream(self, prompt, brain_type: str = None, system_override: str = None):
        """
        Streaming counterpart of think(): a generator that yields response text
        fragments as the model produces them. Behaviour, model, params, system
        prompt and MEMORY updates are identical to think() — only delivery is
        chunked. Only local (Ollama) mode truly token-streams; simulation and
        api modes yield the full reply once (local is the target of this path).
        """
        self.memory.add("user", prompt)

        active_brain = brain_type or self._current_brain_type or "default"
        if system_override:
            system_prompt = system_override
        else:
            system_prompt = get_system_prompt(active_brain)
        model = get_brain_model(active_brain)
        temperature = get_temperature(active_brain)

        if self.mode == "local":
            parts = []
            for chunk in self.local_think_stream(
                prompt, model=model, system_prompt=system_prompt, temperature=temperature
            ):
                parts.append(chunk)
                yield chunk
            self.memory.add("assistant", "".join(parts))
            return

        if self.mode == "simulation":
            reply = self.simulated_response(prompt)
            self.memory.add("assistant", reply)
            yield reply
            return

        # API Mode (OpenAI) — single yield; keeps memory consistent with think().
        try:
            messages = self.memory.get_context()
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + [
                    m for m in messages if m.get("role") != "system"
                ]
            from openai import OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=temperature,
            )
            reply = response.choices[0].message.content
        except Exception as e:
            reply = f"Brain Error: {str(e)}"
        self.memory.add("assistant", reply)
        yield reply

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
                # Keep the model resident in VRAM indefinitely so it doesn't
                # cold-reload (~15-18s) after Ollama's default 5-min idle unload.
                # qwen3.5 (~5.5GB) + nomic-embed (~0.3GB) coexist in 8GB.
                "keep_alive": -1,
                "options": {
                    "temperature": temperature,
                    "num_predict": 2048,
                    # Cap the context window so qwen3.5 (whose default context is
                    # enormous -> ~16GB) fits an 8GB GPU instead of being
                    # CPU-offloaded and slow. 4096 keeps the whole model on-GPU
                    # (no CPU spill) for faster eval. Tunable via CHHOTI_DON_OLLAMA_NUM_CTX.
                    "num_ctx": int(os.getenv("CHHOTI_DON_OLLAMA_NUM_CTX", "4096")),
                }
            }

            if system_prompt:
                payload["system"] = system_prompt

            # Retry-on-empty on the success path (transient empty generation),
            # keeping the existing user-facing error strings for HTTP/connection
            # failures.
            for attempt in range(_EMPTY_RETRIES + 1):
                response = requests.post(
                    OLLAMA_URL,
                    json=payload,
                    timeout=OLLAMA_TIMEOUT
                )
                if response.status_code != 200:
                    return f"Ollama HTTP Error {response.status_code}: {response.text[:200]}"
                text = (response.json().get("response", "") or "").strip()
                if text:
                    return text
                if attempt < _EMPTY_RETRIES:
                    logger.info("[brain] local_think empty generation; retry %d/%d",
                                attempt + 1, _EMPTY_RETRIES)
            return ""

        except requests.exceptions.ConnectionError:
            return "❌ Ollama server nahi mila! Terminal mein 'ollama serve' run karo."
        except requests.exceptions.Timeout:
            return f"❌ Ollama timeout ({OLLAMA_TIMEOUT}s) — model slow hai ya GPU busy hai."
        except Exception as e:
            return f"Local Brain Error: {str(e)}"

    # ==================================================
    # LOCAL OLLAMA MODE — Streaming (token-by-token)
    # ==================================================
    def local_think_stream(
        self,
        prompt: str,
        model: str = None,
        system_prompt: str = "",
        temperature: float = 0.7
    ):
        """
        Streaming variant of local_think(): identical Ollama payload but with
        "stream": True, yielding response text fragments as they arrive. Every
        generation parameter is the SAME as local_think() — keep_alive:-1,
        num_ctx:4096, num_predict:2048, think:False, temperature — so the answer
        content is unchanged; only delivery is chunked. Errors are yielded as a
        single text chunk (mirroring local_think's error-string returns).
        """
        if not model:
            model = get_brain_model(self._current_brain_type or "default")

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,          # <-- the only functional difference vs local_think
            "think": False,
            "keep_alive": -1,
            "options": {
                "temperature": temperature,
                "num_predict": 2048,
                "num_ctx": int(os.getenv("CHHOTI_DON_OLLAMA_NUM_CTX", "4096")),
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with requests.post(
                OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT, stream=True
            ) as response:
                if response.status_code != 200:
                    yield f"Ollama HTTP Error {response.status_code}: {response.text[:200]}"
                    return
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    chunk = data.get("response")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break
        except requests.exceptions.ConnectionError:
            yield "❌ Ollama server nahi mila! Terminal mein 'ollama serve' run karo."
        except requests.exceptions.Timeout:
            yield f"❌ Ollama timeout ({OLLAMA_TIMEOUT}s) — model slow hai ya GPU busy hai."
        except Exception as e:
            yield f"Local Brain Error: {str(e)}"

    # ==================================================
    # FAST STRUCTURED THINK (browser agent loop — Phase 2)
    # ==================================================
    # ==================================================
    # LOCAL GENERATE (single call) + RETRY-ON-EMPTY
    # ==================================================
    def _local_generate(self, payload: dict) -> str:
        """One Ollama /api/generate call. Returns the response text stripped, or
        '' on a non-200 status or any exception. This is the single-call primitive
        that the retry-on-empty loop drives (patched in tests to simulate empties)."""
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
            if r.status_code == 200:
                return (r.json().get("response", "") or "").strip()
            return ""
        except Exception:
            return ""

    def _local_generate_retry(self, payload: dict, retries: int = None) -> str:
        """Drive :meth:`_local_generate`, RE-CALLING on an empty/whitespace-only
        generation up to ``retries`` extra times before giving up (returns '')."""
        retries = _EMPTY_RETRIES if retries is None else retries
        for attempt in range(retries + 1):
            out = self._local_generate(payload)
            if out.strip():
                return out
            if attempt < retries:
                logger.info("[brain] empty generation; retry %d/%d (model=%s)",
                            attempt + 1, retries, payload.get("model"))
        logger.warning("[brain] gave up after %d empty generations (model=%s)",
                       retries + 1, payload.get("model"))
        return ""

    def think_fast(self, prompt: str, brain_type: str = "navigation",
                   num_predict: int = 256, temperature: float = None,
                   system_prompt: str = None) -> str:
        """Low-latency, token-cheap, structured call for the READ-ONLY browser
        agent loop. Uses the dedicated navigation brain, think:False, a SMALL
        num_predict, and does NOT write to conversation memory (the agent loop is
        stateless per step and must not pollute chat memory). Returns raw text.

        This is deliberately separate from think()/local_think so ordinary chat,
        streaming and memory behavior are completely untouched.
        """
        model = get_brain_model(brain_type)
        if temperature is None:
            temperature = get_temperature(brain_type)
        if system_prompt is None:
            system_prompt = get_system_prompt(brain_type)

        if self.mode == "simulation":
            return self.simulated_response(prompt)

        if self.mode == "local":
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,           # never the slow thinking path in the loop
                "keep_alive": -1,
                "options": {
                    "temperature": temperature,
                    "num_predict": num_predict,   # small: one JSON action per step
                    "num_ctx": int(os.getenv("CHHOTI_DON_OLLAMA_NUM_CTX", "4096")),
                },
            }
            if system_prompt:
                payload["system"] = system_prompt
            # Retry-on-empty: an empty generation is an Ollama hiccup, not an answer.
            return self._local_generate_retry(payload)

        # API (OpenAI) mode — single small completion, no memory writes.
        try:
            from openai import OpenAI
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", messages=messages, temperature=temperature,
                max_tokens=num_predict,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception:
            return ""

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
