"""
Chhoti Don - Safety Policy

A small, deterministic classifier that decides how a chat message about
security topics should be handled BEFORE it reaches the model or the internal
agent pipeline:

  * "refuse"      - an operational request to carry out an attack. Return a safe
                    refusal plus a defensive redirection (rendered as a normal
                    assistant message, never a server error).
  * "educational" - a defensive / conceptual security question. Answer it with a
                    safe, defence-oriented explanation via the normal LLM path.
  * "allow"       - not attack-related. Route normally.

This keeps benign educational questions ("explain DDOS attack") away from the
offensive multi-step planner and gives operational-attack requests a consistent,
safe refusal — without ever raising or exposing internals.
"""

from __future__ import annotations

import re
from typing import Dict

# Attack techniques / malicious artefacts that mark a message as security-topical.
# Intentionally specific (not the bare word "cyber") so UI phrases like
# "show cyber engine status" are not misclassified.
_ATTACK_TERMS = [
    "ddos", "dos attack", "denial of service", "denial-of-service",
    "botnet", "malware", "ransomware", "spyware", "rootkit", "keylogger",
    "trojan", "worm", "virus payload", "computer virus",
    "sql injection", "sqli", "xss", "cross-site scripting", "csrf",
    "phishing", "spear phishing", "brute force", "brute-force",
    "credential stuffing", "password cracking", "crack a password",
    "privilege escalation", "backdoor", "reverse shell", "bind shell",
    "remote access trojan", "command and control", "c2 server",
    "man in the middle", "mitm", "arp spoofing", "dns spoofing",
    "buffer overflow", "zero day", "zero-day", "syn flood", "packet flood",
    "port flooding", "exploit kit", "drive-by download", "sql inject",
    "session hijacking", "clickjacking", "dll injection", "code injection",
    "exploit", "hack into", "hacking into",
]

# Phrasing that signals an OPERATIONAL request to carry out / build an attack.
_OFFENSIVE_MARKERS = [
    "how to perform", "how to do", "how to carry out", "how to launch",
    "how to execute", "how to conduct", "how to run a", "how to build",
    "how to create", "how to make", "how to write", "how to develop",
    "how to set up", "how to start a", "how do i perform", "how do i launch",
    "how do i do", "how do i build", "how do i create", "how do i make",
    "how do i execute", "how do i carry out", "how can i perform",
    "how can i launch", "how can i hack", "how can i attack", "how can i build",
    "how to hack", "how to attack", "how to breach", "how to exploit",
    "how to bypass", "how to ddos", "how to dos",
    "steps to", "step by step", "step-by-step", "tutorial on", "guide to",
    "guide for", "walk me through", "show me how to", "teach me to",
    "teach me how to", "help me hack", "help me attack", "help me build a",
    "give me code to", "code to attack", "code for a", "script to attack",
    "script for a", "write a script to", "write code to", "generate a payload",
    "create a payload", "make a payload", "build a botnet", "launch a",
    "perform a", "carry out a", "conduct a", "execute a",
]

# Strong defensive intent — if present, always treat as a safe educational
# question even when an attack term is mentioned ("how to detect/prevent X").
_DEFENSIVE_STRONG = [
    "protect", "prevent", "defend", "defence", "defense", "mitigat", "detect",
    "harden", "secure against", "secure my", "safeguard", "countermeasure",
    "incident response", "remediat", "respond to",
]

# Verbs that, combined with a malicious artefact, indicate a request to CREATE
# an attack tool ("write ransomware", "build a botnet").
_CREATION_VERBS = [
    "write", "create", "build", "make", "develop", "code", "program",
    "generate", "deploy", "launch", "perform", "execute", "conduct",
    "carry out", "spread", "distribute", "install a", "set up a",
]

# Malicious artefacts whose creation is never assisted.
_MALICIOUS_ARTIFACTS = [
    "ransomware", "malware", "spyware", "rootkit", "keylogger", "trojan",
    "worm", "botnet", "backdoor", "reverse shell", "bind shell", "payload",
    "exploit", "remote access trojan", "computer virus", "virus payload",
]

# Third-person / conceptual question phrasing ("how does X work", "what is X").
# These are educational even when a creation verb appears ("how does malware
# spread"); they are NOT imperative requests to build something.
_CONCEPTUAL_MARKERS = [
    "how does", "how do they", "how is", "how are", "what is", "what are",
    "what's", "what does", "explain", "describe", "define", "overview",
    "difference between", "why does", "why do ", "why is", "why are",
    "tell me about", "learn about", "understand",
]


def _find_term(text: str) -> str | None:
    for term in _ATTACK_TERMS:
        if term in text:
            return term
    return None


def _pretty_topic(term: str | None) -> str:
    if not term:
        return "that attack"
    mapping = {
        "ddos": "DDoS attack", "dos attack": "DoS attack",
        "denial of service": "denial-of-service attack",
        "sql injection": "SQL injection attack", "sqli": "SQL injection attack",
        "xss": "cross-site scripting attack", "phishing": "phishing attack",
        "ransomware": "ransomware", "malware": "malware", "botnet": "botnet",
        "reverse shell": "reverse shell", "exploit": "exploit",
    }
    return mapping.get(term, term)


def evaluate(message: str) -> Dict:
    """Classify a message. Returns {action, category, term, message}."""
    text = (message or "").lower().strip()
    term = _find_term(text)

    if not term:
        return {"action": "allow", "category": None, "term": None, "message": None}

    # 1. Strong defensive framing always wins → safe educational answer.
    if any(m in text for m in _DEFENSIVE_STRONG):
        return {"action": "educational", "category": "security_education", "term": term, "message": None}

    # 2. Explicit operational how-to phrasing → refuse.
    has_offensive = any(m in text for m in _OFFENSIVE_MARKERS)
    # ...or an imperative request to CREATE a malicious artefact — but not a
    # third-person conceptual question about one ("how does malware spread").
    is_conceptual = any(m in text for m in _CONCEPTUAL_MARKERS)
    creates_artifact = (
        any(v in text for v in _CREATION_VERBS)
        and any(a in text for a in _MALICIOUS_ARTIFACTS)
        and not is_conceptual
    )
    if has_offensive or creates_artifact:
        return {
            "action": "refuse",
            "category": "policy_refusal",
            "term": term,
            "message": _refusal_message(term),
        }

    # 3. A security topic asked conceptually → educational (safe explanation),
    #    never routed into an attack-planning pipeline.
    return {"action": "educational", "category": "security_education", "term": term, "message": None}


def _refusal_message(term: str | None) -> str:
    topic = _pretty_topic(term)
    return (
        f"I can't provide instructions for carrying out a {topic} -- that would be "
        f"operational guidance for attacking systems.\n\n"
        f"If you're learning about this defensively, I'm glad to help with the safe side:\n"
        f"- **How it works** conceptually and why it's effective\n"
        f"- **How to detect** it (indicators, logs, monitoring)\n"
        f"- **How to prevent and mitigate** it (controls, rate limiting, filtering, hardening)\n"
        f"- **Incident response** and recovery guidance\n\n"
        f"Just ask me to *explain* {topic} or *how to defend against* it."
    )


def educational_prompt(message: str) -> str:
    """Wrap a security question so the model answers defensively and safely."""
    return (
        "You are a defensive cybersecurity educator. Give a clear, accurate, "
        "conceptual explanation for learning and defense. Do NOT provide "
        "step-by-step operational attack instructions, exploit code, or payloads. "
        "Emphasise detection, prevention and mitigation where relevant.\n\n"
        f"Question: {message}"
    )
