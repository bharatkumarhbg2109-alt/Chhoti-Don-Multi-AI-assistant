"""
Chhoti Don - Brain Router
Advanced intent detection and brain routing with
multi-language support, confidence scoring, and context awareness.
Phase 2.2 - Full Upgrade
"""

import time
import datetime
from typing import Tuple, Tuple

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from core.brain_registry import (
    BRAINS, get_brain, get_brain_model,
    get_system_prompt, get_temperature, list_brains
)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 120

# ==================================================
# 🎯 INTENT KEYWORDS (PRESERVED + EXPANDED)
# ==================================================

INTENT_KEYWORDS = {
    "coding": [
        "code likho", "code banao", "code do", "program banao", "script banao",
        "function likho", "function banao", "class banao", "write code", "generate code",
        "create function", "create script", "build a", "implement", "develop",
        "code chalao", "run karo", "execute karo", "chalao", "run this", "execute this",
        "debug karo", "fix karo", "error fix", "bug fix", "error hai", "bug hai",
        "kyu error", "error kyu", "fix this", "debug this", "error in",
        "code samjhao", "explain karo", "kya karta hai", "samjhao", "explain this code",
        "python mein", "javascript mein", "js mein", "c++ mein", "cpp mein",
        "sql mein", "bash mein", "in python", "in javascript", "in sql",
        "python code", "javascript code", "js code", "sql query", "bash script",
        "refactor", "optimize code", "code review",
    ],
    "debug": [
        "traceback", "exception", "nameerror", "typeerror", "syntaxerror",
        "indexerror", "keyerror", "valueerror", "importerror", "attributeerror",
        "zerodivisionerror", "runtimeerror", "error fix karo", "ye error kyu",
        "code kaam nahi kar raha", "not working", "broken code", "fix my code",
        "crash", "fails", "throwing error",
    ],
    "malware": [
        "hack", "exploit", "vulnerability", "malware", "virus", "trojan",
        "payload", "reverse shell", "sql injection", "xss", "csrf",
        "penetration", "pentest", "security audit", "threat", "attack",
        "cyber", "recon", "scan", "port scan", "nmap", "cve", "mitre",
        "ransomware", "backdoor", "keylogger", "zero day", "privilege escalation",
    ],
    "analytics": [
        "analyze", "analysis", "data", "stats", "statistics", "report",
        "chart", "graph", "trend", "pattern", "insight", "metrics",
        "dashboard", "visualize", "compare", "performance", "percentage",
        "dataset", "forecast", "predict",
    ],
    "research": [
        "research", "explain", "what is", "kya hai", "batao", "how does",
        "kaise kaam karta", "define", "meaning", "difference between",
        "fark kya hai", "compare", "history of", "tell me about",
        "summarize", "overview", "what are",
    ],
    "conversation": [
        "kya haal", "kaise ho", "hello", "hi", "hey", "baat karo",
        "bored", "chat", "mood", "feeling", "aaj", "kya soch rahe",
        "timepass", "mazak", "joke", "thanks", "shukriya", "acha",
        "good morning", "good night", "kya chal raha",
    ],
}

# Weighted intent scoring
INTENT_WEIGHTS = {
    "coding": 2.0,
    "debug": 2.5,
    "malware": 2.0,
    "analytics": 1.5,
    "research": 1.0,
    "conversation": 1.0,
}


# ==================================================
# 🔍 INTENT DETECTOR (PRESERVED + UPGRADED)
# ==================================================

def detect_intent(user_input: str) -> str:
    """
    Detect intent from user input.
    Preserved + upgraded with weighted scoring.
    """
    text = user_input.lower().strip()
    scores = {intent: 0.0 for intent in INTENT_KEYWORDS}

    for intent, keywords in INTENT_KEYWORDS.items():
        weight = INTENT_WEIGHTS.get(intent, 1.0)
        for keyword in keywords:
            if keyword in text:
                # Longer keyword = higher confidence
                kw_weight = 1.5 if len(keyword) > 8 else 1.0
                scores[intent] += weight * kw_weight

    best_intent = max(scores, key=scores.get)

    if scores[best_intent] == 0:
        return "default"

    # Debug → coding merge (preserved)
    if best_intent == "debug" and scores.get("coding", 0) > 0:
        return "coding"

    return best_intent


def detect_intent_with_confidence(user_input: str) -> Tuple[str, float]:
    """Intent + confidence score return karo."""
    text = user_input.lower().strip()
    scores = {intent: 0.0 for intent in INTENT_KEYWORDS}
    total_matches = 0

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                scores[intent] += 1
                total_matches += 1

    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]

    if best_score == 0:
        return "default", 0.3

    confidence = min(best_score / max(total_matches, 1) + 0.4, 0.99)
    return best_intent, round(confidence, 3)


# ==================================================
# 🧠 BRAIN ROUTER (PRESERVED)
# ==================================================

def route_task(task_type: str) -> dict:
    """Legacy function — preserved."""
    return get_brain(task_type)


def route_and_think(
    user_input: str,
    task_type: str = None,
    system_override: str = None,
    context: str = None,
) -> dict:
    """
    Full routing pipeline.
    Preserved + upgraded with context support.
    """
    start_time = time.time()

    intent = task_type if task_type else detect_intent(user_input)
    brain = get_brain(intent)
    model = brain.get("model", "mistral:latest")
    temperature = brain.get("temperature", 0.7)
    system_prompt = system_override or brain.get("system_prompt", "You are a helpful assistant.")

    # Add context to prompt if provided
    full_prompt = user_input
    if context:
        full_prompt = f"Context:\n{context}\n\nUser: {user_input}"

    response, success, error = _call_ollama(model, full_prompt, system_prompt, temperature)

    return {
        "intent": intent,
        "model": model,
        "response": response,
        "success": success,
        "error": error,
        "brain_config": brain,
        "execution_time_sec": round(time.time() - start_time, 3),
    }


# ==================================================
# 💻 CODING TOOL ROUTER (PRESERVED + UPGRADED)
# ==================================================

def route_coding_tool(user_input: str) -> dict:
    """
    Coding-specific tool routing.
    Preserved + upgraded.
    """
    text = user_input.lower()

    tool_map = [
        (["chalao", "run karo", "execute", "run this", "chala do", "output do", "chalaye"], "execute_code"),
        (["debug", "fix karo", "error fix", "bug fix", "error hai", "kaam nahi", "not working", "traceback"], "debug_code"),
        (["samjhao", "explain", "kya karta hai", "batao ye code", "what does", "describe"], "explain_code"),
        (["refactor", "optimize", "improve", "clean up"], "refactor_code"),
        (["banao", "likho", "generate", "write", "create", "bana do", "likh do", "implement"], "generate_code"),
    ]

    detected_tool = "generate_code"
    confidence = 0.5

    for keywords, tool in tool_map:
        for kw in keywords:
            if kw in text:
                detected_tool = tool
                confidence = 0.9
                break

    language = _detect_language_from_input(text)

    return {
        "tool_name": detected_tool,
        "extracted_language": language,
        "confidence": confidence,
    }


def _detect_language_from_input(text: str) -> str:
    """Programming language detect karo."""
    lang_map = [
        (["python", "py ", ".py", "django", "flask", "pandas", "numpy"], "python"),
        (["javascript", " js ", "node", "nodejs", ".js", "react", "vue", "typescript"], "javascript"),
        (["c++", "cpp", "c plus", "#include <iostream>"], "cpp"),
        (["bash", "shell", "sh script", "#!/bin/bash"], "bash"),
        (["sql", "query", "database", "select ", "insert ", "create table"], "sql"),
        (["c code", " c program", " in c ", "#include <stdio"], "c"),
        (["html", "css", "webpage", "web page", "div", "span"], "html"),
        (["java ", "spring", "maven", "android", ".java"], "java"),
        (["rust", "cargo", "fn main"], "rust"),
        (["go ", "golang", "package main"], "go"),
    ]

    for keywords, lang in lang_map:
        for kw in keywords:
            if kw in text:
                return lang

    return "python"


# ==================================================
# 🦙 OLLAMA CALLER (PRESERVED + UPGRADED)
# ==================================================

def _call_ollama(
    model: str,
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    stream: bool = False,
) -> tuple:
    """
    Ollama API call.
    Preserved + upgraded with better error handling.
    """
    if not REQUESTS_AVAILABLE:
        return None, False, "requests library not available"

    try:
        import requests as req

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": 2048,
            }
        }

        response = req.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)

        if response.status_code == 200:
            data = response.json()
            text = data.get("response", "").strip()
            return text, True, None
        else:
            error = f"Ollama HTTP {response.status_code}: {response.text[:200]}"
            return None, False, error

    except Exception as e:
        err_str = str(e)
        if "ConnectionError" in type(e).__name__ or "connection" in err_str.lower():
            return None, False, "Ollama server nahi mila! 'ollama serve' run karo."
        if "Timeout" in type(e).__name__:
            return None, False, f"Ollama timeout ({OLLAMA_TIMEOUT}s)"
        return None, False, f"Ollama error: {err_str}"


# ==================================================
# 🔧 UTILITIES (PRESERVED + UPGRADED)
# ==================================================

def get_available_brains() -> list:
    """All brains list karo."""
    return list_brains()


def check_ollama_status() -> dict:
    """Ollama server status check karo."""
    if not REQUESTS_AVAILABLE:
        return {"online": False, "message": "requests not installed"}

    try:
        import requests as req
        response = req.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            return {
                "online": True,
                "models_available": model_names,
                "message": f"✅ Ollama online! {len(model_names)} models available.",
            }
    except Exception:
        pass

    return {
        "online": False,
        "models_available": [],
        "message": "❌ Ollama offline! 'ollama serve' run karo.",
    }
