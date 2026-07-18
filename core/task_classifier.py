"""
Chhoti Don - Task Classifier
User input se task type detect karta hai.
Hinglish + English dono supported.
"""


# ==================================================
# 🎯 KEYWORD MAPS
# ==================================================

CODING_KEYWORDS = [
    # Generate
    "code banao", "code likho", "code do", "program banao", "script banao",
    "function banao", "function likho", "class banao", "write code",
    "generate code", "create function", "create script", "build a",
    "implement", "develop", "bana do", "likh do",
    # Execute
    "code chalao", "run karo", "execute karo", "chalao", "run this",
    "execute this", "chala do",
    # Debug
    "debug karo", "fix karo", "error fix", "bug fix", "error hai",
    "bug hai", "kyu error", "fix this", "debug this", "not working",
    "kaam nahi kar raha", "broken",
    # Explain
    "code samjhao", "explain karo", "kya karta hai ye code",
    "explain this code", "samjhao ye", "code explain",
    # Language keywords
    "python mein", "javascript mein", "js mein", "c++ mein", "cpp mein",
    "sql mein", "bash mein", "in python", "in javascript", "in sql",
    "python code", "javascript code", "sql query", "bash script",
    # Error types
    "nameerror", "typeerror", "syntaxerror", "indexerror", "keyerror",
    "valueerror", "importerror", "attributeerror", "zerodivisionerror",
    "traceback", "exception",
    # Code syntax
    "def ", "class ", "import ", "function(", "SELECT ", "#!/",
    "```python", "```javascript", "```sql", "```bash", "```cpp",
]

MALWARE_KEYWORDS = [
    "malware", "payload", "shellcode", "exploit", "hack", "vulnerability",
    "virus", "trojan", "reverse shell", "sql injection", "xss", "csrf",
    "penetration", "pentest", "security audit", "threat", "attack",
    "cyber", "recon", "port scan", "nmap", "brute force", "phishing",
    "ransomware", "backdoor", "keylogger", "zero day",
]

ANALYTICS_KEYWORDS = [
    "analyze", "analysis", "statistics", "trend", "data", "stats",
    "report", "chart", "graph", "insight", "metrics", "dashboard",
    "visualize", "compare", "performance", "percentage", "average",
    "dataset", "pattern", "forecast",
]

RESEARCH_KEYWORDS = [
    "what is", "kya hai", "batao", "how does", "kaise kaam karta",
    "define", "meaning", "difference between", "fark kya hai",
    "history of", "tell me about", "explain", "samjhao",
    "research", "find out", "look up",
]

CONVERSATION_KEYWORDS = [
    "kya haal", "kaise ho", "hello", "hi ", "hey", "baat karo",
    "bored", "chat", "mood", "feeling", "aaj", "kya soch rahe",
    "timepass", "mazak", "joke", "good morning", "good night",
    "shukriya", "thanks", "thank you", "acha", "theek hai",
]


# ==================================================
# 🔍 MAIN DETECT FUNCTION
# ==================================================

def detect_task(prompt: str) -> str:
    """
    Prompt se task type detect karo.

    Returns one of:
        'coding', 'malware', 'analytics', 'research',
        'conversation', 'default'
    """
    p = prompt.lower()

    # Score system — har category ke liye score calculate karo
    scores = {
        "coding": 0,
        "malware": 0,
        "analytics": 0,
        "research": 0,
        "conversation": 0,
    }

    for kw in CODING_KEYWORDS:
        if kw in p:
            scores["coding"] += 2 if len(kw) > 6 else 1

    for kw in MALWARE_KEYWORDS:
        if kw in p:
            scores["malware"] += 2

    for kw in ANALYTICS_KEYWORDS:
        if kw in p:
            scores["analytics"] += 1

    for kw in RESEARCH_KEYWORDS:
        if kw in p:
            scores["research"] += 1

    for kw in CONVERSATION_KEYWORDS:
        if kw in p:
            scores["conversation"] += 1

    # Best match
    best = max(scores, key=scores.get)

    if scores[best] == 0:
        return "default"

    return best


def detect_coding_action(prompt: str) -> str:
    """
    Coding task ke andar specific action detect karo.

    Returns: 'generate', 'execute', 'debug', 'explain'
    """
    p = prompt.lower()

    execute_kw = ["chalao", "run karo", "execute", "run this", "chala do", "output do"]
    debug_kw = ["debug", "fix karo", "error fix", "bug", "not working",
                "kaam nahi", "traceback", "exception", "error hai"]
    explain_kw = ["samjhao", "explain", "kya karta hai", "batao ye code", "what does"]

    for kw in execute_kw:
        if kw in p:
            return "execute"

    for kw in debug_kw:
        if kw in p:
            return "debug"

    for kw in explain_kw:
        if kw in p:
            return "explain"

    return "generate"  # default coding action


def detect_language(prompt: str) -> str:
    """
    Prompt se programming language detect karo.

    Returns: 'python', 'javascript', 'cpp', 'c', 'sql', 'bash', 'html'
    """
    p = prompt.lower()

    lang_map = [
        (["python", "py ", ".py", "django", "flask", "pandas"], "python"),
        (["javascript", " js ", "node", "nodejs", ".js", "react", "vue"], "javascript"),
        (["c++", "cpp", "c plus plus", "#include <iostream>"], "cpp"),
        (["bash", "shell script", "sh script", "#!/bin/bash", "terminal script"], "bash"),
        (["sql", " query", "database", "select ", "insert into", "create table"], "sql"),
        ([" c code", " c program", "in c ", "#include <stdio"], "c"),
        (["html", "css", "webpage", "web page"], "html"),
    ]

    for keywords, lang in lang_map:
        for kw in keywords:
            if kw in p:
                return lang

    return "python"  # default
