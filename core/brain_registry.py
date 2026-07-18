"""
Chhoti Don - Brain Registry
Central registry for all AI brain configurations.
Phase 2.2 - Full Upgrade
"""

from typing import Dict, List, Optional, Optional

BRAINS: Dict[str, Dict] = {
    "coding": {
        "model": "mistral:latest",
        "temperature": 0.3,
        "max_tokens": 4096,
        "system_prompt": (
            "You are Chhoti Don's expert coding engine. "
            "Write clean, working, well-commented code. "
            "Always wrap code in triple backticks with language: ```python ... ```. "
            "Be concise and accurate."
        ),
        "description": "Code generation and debugging",
        "capabilities": ["generate", "debug", "explain", "refactor"],
        "priority": 1,
    },
    "debug": {
        "model": "mistral:latest",
        "temperature": 0.2,
        "max_tokens": 2048,
        "system_prompt": (
            "You are Chhoti Don's debugging specialist. "
            "Analyze errors precisely. Explain what went wrong. "
            "Always provide: 1) Bug explanation 2) Fixed code in backticks."
        ),
        "description": "Bug fixing and error analysis",
        "capabilities": ["debug", "fix", "analyze_error"],
        "priority": 2,
    },
    "malware": {
        "model": "mistral:latest",
        "temperature": 0.4,
        "max_tokens": 3072,
        "system_prompt": (
            "You are Chhoti Don's cybersecurity analysis engine. "
            "Analyze threats, vulnerabilities, and attack patterns. "
            "Provide MITRE ATT&CK mappings where relevant. "
            "For authorized penetration testing and research only."
        ),
        "description": "Cybersecurity and malware analysis",
        "capabilities": ["threat_analysis", "exploit_research", "security_audit"],
        "priority": 3,
    },
    "analytics": {
        "model": "mistral:latest",
        "temperature": 0.5,
        "max_tokens": 2048,
        "system_prompt": (
            "You are Chhoti Don's data analytics engine. "
            "Analyze data patterns, generate insights, explain trends. "
            "Use tables and bullet points for clarity."
        ),
        "description": "Data analysis and insights",
        "capabilities": ["analyze", "trend", "report", "visualize"],
        "priority": 4,
    },
    "research": {
        "model": "mistral:latest",
        "temperature": 0.6,
        "max_tokens": 3072,
        "system_prompt": (
            "You are Chhoti Don's research engine. "
            "Provide accurate, detailed explanations. "
            "Be comprehensive yet concise. "
            "Respond in the same language as the question."
        ),
        "description": "Research and knowledge retrieval",
        "capabilities": ["explain", "research", "compare", "summarize"],
        "priority": 5,
    },
    "conversation": {
        "model": "mistral:latest",
        "temperature": 0.8,
        "max_tokens": 1024,
        "system_prompt": (
            "You are Chhoti Don — a friendly AI bestie. "
            "Chat naturally in Hinglish (Hindi-English mix). "
            "Be casual, fun, and helpful."
        ),
        "description": "Casual conversation and chitchat",
        "capabilities": ["chat", "joke", "advice"],
        "priority": 6,
    },
    "planner": {
        "model": "mistral:latest",
        "temperature": 0.2,
        "max_tokens": 1024,
        "system_prompt": (
            "You are Chhoti Don's planning engine. "
            "Return ONLY valid JSON. No explanation. "
            "Plan multi-step tasks efficiently."
        ),
        "description": "Task planning and step sequencing",
        "capabilities": ["plan", "sequence", "orchestrate"],
        "priority": 7,
    },
    "reviewer": {
        "model": "mistral:latest",
        "temperature": 0.1,
        "max_tokens": 512,
        "system_prompt": (
            "You are a strict quality reviewer. "
            "If correct, respond EXACTLY: APPROVED. "
            "If incorrect, provide the corrected version only."
        ),
        "description": "Quality review and validation",
        "capabilities": ["review", "validate", "approve"],
        "priority": 8,
    },
    "default": {
        "model": "mistral:latest",
        "temperature": 0.7,
        "max_tokens": 2048,
        "system_prompt": (
            "You are Chhoti Don — an advanced AI assistant. "
            "Be helpful, accurate, and friendly. "
            "Respond in the same language as the user (Hinglish preferred)."
        ),
        "description": "General purpose assistant",
        "capabilities": ["general", "help", "answer"],
        "priority": 99,
    },
}

BRAIN_ALIASES: Dict[str, str] = {
    "code": "coding", "coder": "coding",
    "fix": "debug", "bugfix": "debug",
    "security": "malware", "cyber": "malware", "pentest": "malware",
    "data": "analytics", "analysis": "analytics",
    "search": "research", "info": "research",
    "chat": "conversation", "talk": "conversation",
    "plan": "planner", "review": "reviewer", "check": "reviewer",
}

_brain_usage: Dict[str, int] = {}


def get_brain(brain_type: str) -> Dict:
    canonical = BRAIN_ALIASES.get(brain_type, brain_type)
    brain = BRAINS.get(canonical) or BRAINS["default"]
    _brain_usage[canonical] = _brain_usage.get(canonical, 0) + 1
    return dict(brain)


def get_brain_model(brain_type: str) -> str:
    return get_brain(brain_type).get("model", "mistral:latest")


def get_system_prompt(brain_type: str) -> str:
    return get_brain(brain_type).get("system_prompt", "You are a helpful assistant.")


def get_temperature(brain_type: str) -> float:
    return get_brain(brain_type).get("temperature", 0.7)


def get_max_tokens(brain_type: str) -> int:
    return get_brain(brain_type).get("max_tokens", 2048)


def list_brains() -> List[str]:
    return list(BRAINS.keys())


def register_brain(name: str, config: Dict) -> bool:
    required = ["model", "system_prompt"]
    if not all(k in config for k in required):
        return False
    BRAINS[name] = {
        "model": config["model"],
        "temperature": config.get("temperature", 0.7),
        "max_tokens": config.get("max_tokens", 2048),
        "system_prompt": config["system_prompt"],
        "description": config.get("description", "Custom brain"),
        "capabilities": config.get("capabilities", []),
        "priority": config.get("priority", 50),
        "custom": True,
    }
    return True


def update_brain_model(brain_type: str, new_model: str) -> bool:
    if brain_type not in BRAINS:
        return False
    BRAINS[brain_type]["model"] = new_model
    return True


def get_brain_for_task(capabilities_needed: List[str]) -> str:
    for brain_name, config in sorted(BRAINS.items(), key=lambda x: x[1].get("priority", 99)):
        if any(cap in config.get("capabilities", []) for cap in capabilities_needed):
            return brain_name
    return "default"


def get_usage_stats() -> Dict:
    return {
        "brain_usage": dict(_brain_usage),
        "total_calls": sum(_brain_usage.values()),
        "most_used": max(_brain_usage, key=_brain_usage.get) if _brain_usage else None,
    }
