"""
Chhoti Don - Code Debugger Tool
Analyzes errors, explains bugs, and suggests/applies fixes.
"""

import re
from typing import List, Type

# Common error patterns mapped to friendly explanations
ERROR_PATTERNS = {
    "python": [
        (r"NameError: name '(\w+)' is not defined", "Variable '{0}' use hone se pehle define nahi hua."),
        (r"SyntaxError: (.+)", "Syntax galat hai: {0}"),
        (r"IndentationError: (.+)", "Indentation problem hai: {0}"),
        (r"TypeError: (.+)", "Type mismatch hai: {0}"),
        (r"IndexError: (.+)", "List/array index out of range: {0}"),
        (r"KeyError: (.+)", "Dictionary mein key {0} exist nahi karti."),
        (r"AttributeError: (.+)", "Attribute ya method exist nahi karta: {0}"),
        (r"ImportError: (.+)", "Module import nahi hua: {0}"),
        (r"ModuleNotFoundError: (.+)", "Module nahi mila: {0}"),
        (r"ZeroDivisionError", "Zero se division ho raha hai — divisor check karo."),
        (r"FileNotFoundError: (.+)", "File nahi mili: {0}"),
        (r"ValueError: (.+)", "Galat value pass ki gayi: {0}"),
        (r"RecursionError", "Infinite recursion ho rahi hai — base case check karo."),
    ],
    "javascript": [
        (r"ReferenceError: (\w+) is not defined", "Variable '{0}' define nahi hai."),
        (r"TypeError: (.+)", "Type error: {0}"),
        (r"SyntaxError: (.+)", "Syntax galat hai: {0}"),
        (r"RangeError: (.+)", "Range exceed ho gayi: {0}"),
        (r"Cannot read propert(?:y|ies) of (undefined|null)", "Null/undefined object pe property access ho rahi hai."),
    ],
    "cpp": [
        (r"error: '(\w+)' was not declared", "'{0}' declare nahi hua is scope mein."),
        (r"error: (.+)", "Compiler error: {0}"),
        (r"segmentation fault", "Segfault — memory access issue hai, pointers check karo."),
        (r"undefined reference to '(.+)'", "Function/variable '{0}' link nahi hua."),
    ],
    "c": [
        (r"error: '(\w+)' undeclared", "'{0}' declare nahi hua."),
        (r"segmentation fault", "Segfault — NULL pointer ya array bounds check karo."),
        (r"error: (.+)", "Compiler error: {0}"),
    ],
    "bash": [
        (r"command not found", "Command exist nahi karta — PATH ya spelling check karo."),
        (r"permission denied", "Permission nahi hai — chmod se fix karo."),
        (r"No such file or directory", "File ya directory exist nahi karti."),
    ],
    "sql": [
        (r"no such table: (\w+)", "Table '{0}' exist nahi karti."),
        (r"syntax error", "SQL syntax galat hai."),
        (r"no such column: (\w+)", "Column '{0}' exist nahi karta."),
        (r"UNIQUE constraint failed", "Duplicate value insert ho raha hai unique column mein."),
    ]
}


def debug_code(input_data: dict) -> dict:
    """
    Analyze code + error and return diagnosis + fix suggestions.

    input_data keys:
        - code (str): The buggy code
        - error (str): Error message/traceback
        - language (str): Programming language
        - brain (obj, optional): Brain instance for AI-powered fix
    """
    code = input_data.get("code", "")
    error = input_data.get("error", "")
    language = input_data.get("language", "python").lower()
    brain = input_data.get("brain", None)

    if not code and not error:
        return {
            "status": "error",
            "message": "Code aur error dono provide karo debug ke liye.",
            "diagnosis": None,
            "fix": None
        }

    # Step 1: Pattern-based diagnosis
    diagnosis = _pattern_diagnose(error, language)

    # Step 2: AI-powered fix if brain available
    fixed_code = None
    explanation = None

    if brain and code:
        try:
            ai_result = _ai_debug(brain, code, error, language)
            fixed_code = ai_result.get("fixed_code")
            explanation = ai_result.get("explanation")
        except Exception as e:
            explanation = f"AI debug failed: {str(e)}"

    # Step 3: Build diff summary
    diff_summary = None
    if fixed_code and code:
        diff_summary = _simple_diff(code, fixed_code)

    return {
        "status": "success",
        "language": language,
        "original_code": code,
        "error_input": error,
        "diagnosis": diagnosis,
        "explanation": explanation or diagnosis,
        "fixed_code": fixed_code,
        "diff_summary": diff_summary,
        "message": "🐛 Debug complete! Fix suggestion ready." if fixed_code else "🔍 Diagnosis ready."
    }


def explain_code(input_data: dict) -> dict:
    """
    Explain what a piece of code does.

    input_data keys:
        - code (str): Code to explain
        - language (str): Programming language
        - brain (obj, optional): Brain instance
        - detail_level (str): 'simple' or 'detailed'
    """
    code = input_data.get("code", "")
    language = input_data.get("language", "python").lower()
    brain = input_data.get("brain", None)
    detail_level = input_data.get("detail_level", "simple")

    if not code:
        return {
            "status": "error",
            "message": "Explain karne ke liye code do.",
            "explanation": None
        }

    # Quick stats
    lines = len(code.splitlines())
    functions = len(re.findall(r'\bdef \w+|function \w+|void \w+\s*\(|int \w+\s*\(', code))
    imports = len(re.findall(r'^\s*(import|#include|require|using)', code, re.MULTILINE))

    stats = {
        "total_lines": lines,
        "functions_detected": functions,
        "imports_detected": imports,
        "language": language
    }

    # AI explanation
    explanation = None
    if brain:
        try:
            level_desc = "simple aur beginner-friendly" if detail_level == "simple" else "detailed aur technical"
            prompt = f"""Is {language} code ko {level_desc} tarike se explain karo:

```{language}
{code}
```

Explain karo:
1. Ye code kya karta hai (overview)
2. Har important part kya kar raha hai
3. Koi potential issues hain toh batao
Hinglish mein explain karo."""

            explanation = brain.think(prompt)
        except Exception as e:
            explanation = f"AI explanation unavailable: {str(e)}"

    if not explanation:
        explanation = _basic_explain(code, language)

    return {
        "status": "success",
        "language": language,
        "code": code,
        "stats": stats,
        "explanation": explanation,
        "message": "✅ Code explanation ready!"
    }


# ==================================================
# 🔧 Internal Helpers
# ==================================================

def _pattern_diagnose(error: str, language: str) -> str:
    """Match error to known patterns and return diagnosis."""
    if not error:
        return "Koi error message nahi diya — code manually review karo."

    patterns = ERROR_PATTERNS.get(language, [])
    for pattern, message_template in patterns:
        match = re.search(pattern, error, re.IGNORECASE)
        if match:
            groups = match.groups()
            try:
                return message_template.format(*groups)
            except Exception:
                return message_template

    return f"Error detected: {error[:200]}"


def _ai_debug(brain, code: str, error: str, language: str) -> dict:
    """Use AI brain to generate fixed code."""
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

    response = brain.think(prompt)

    # Extract explanation
    explanation = ""
    exp_match = re.search(r"EXPLANATION:\s*(.+?)(?=FIXED_CODE:|```|$)", response, re.DOTALL)
    if exp_match:
        explanation = exp_match.group(1).strip()

    # Extract fixed code
    code_match = re.search(r"```(?:\w+)?\n([\s\S]*?)```", response)
    fixed_code = code_match.group(1).strip() if code_match else None

    return {
        "explanation": explanation,
        "fixed_code": fixed_code
    }


def _simple_diff(original: str, fixed: str) -> str:
    """Generate a simple diff summary."""
    orig_lines = original.splitlines()
    fixed_lines = fixed.splitlines()

    added = len(fixed_lines) - len(orig_lines)
    changed = sum(1 for a, b in zip(orig_lines, fixed_lines) if a != b)

    parts = []
    if changed > 0:
        parts.append(f"{changed} line(s) changed")
    if added > 0:
        parts.append(f"{added} line(s) added")
    elif added < 0:
        parts.append(f"{abs(added)} line(s) removed")

    return ", ".join(parts) if parts else "Minor formatting changes"


def _basic_explain(code: str, language: str) -> str:
    """Basic fallback explanation without AI."""
    lines = len(code.splitlines())
    funcs = re.findall(r'\bdef (\w+)|function (\w+)', code)
    func_names = [f[0] or f[1] for f in funcs]

    explanation = f"Ye {language} code hai jisme {lines} lines hain."
    if func_names:
        explanation += f" Isme ye functions hain: {', '.join(func_names)}."
    else:
        explanation += " Koi named function nahi dikh raha."

    return explanation
