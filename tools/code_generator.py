"""
Chhoti Don - Code Generator Tool
Generates code in multiple languages using AI brain.
"""

import re
from typing import Generator

SUPPORTED_LANGUAGES = ["python", "javascript", "js", "c", "cpp", "c++", "sql", "bash", "shell", "html", "css"]

LANGUAGE_ALIASES = {
    "js": "javascript",
    "c++": "cpp",
    "shell": "bash",
    "py": "python",
}

LANGUAGE_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "cpp": ".cpp",
    "c": ".c",
    "sql": ".sql",
    "bash": ".sh",
    "html": ".html",
    "css": ".css",
}


def detect_language(prompt: str) -> str:
    """Auto-detect language from user prompt."""
    prompt_lower = prompt.lower()

    # Priority order — pehle specific keywords check karo
    priority_checks = [
        (["bash", "shell script", "sh script", "#!/bin/bash", "terminal script"], "bash"),
        (["javascript", " js ", "node.js", "nodejs", "jquery", "react"], "javascript"),
        (["c++", "cpp", "#include <iostream>"], "cpp"),
        (["python", "django", "flask", "pandas", "numpy"], "python"),
        (["sql", "select ", "insert into", "create table", "database query"], "sql"),
        (["c code", " c program", "#include <stdio"], "c"),
        (["html", "css", "webpage"], "html"),
    ]

    for keywords, lang in priority_checks:
        for kw in keywords:
            if kw in prompt_lower:
                return lang

    return "python"  # Default


def extract_code_from_response(response: str) -> str:
    """Extract clean code from AI markdown response."""
    # Try to extract from code blocks
    pattern = r"```(?:\w+)?\n([\s\S]*?)```"
    matches = re.findall(pattern, response)
    if matches:
        return "\n\n".join(matches).strip()
    return response.strip()


def generate_code(input_data: dict) -> dict:
    """
    Generate code based on user prompt.

    input_data keys:
        - prompt (str): What to build
        - language (str, optional): Target language
        - context (str, optional): Extra context/requirements
        - brain (obj, optional): Brain instance for AI generation
    """
    prompt = input_data.get("prompt", "")
    language = input_data.get("language", "").lower()
    context = input_data.get("context", "")
    brain = input_data.get("brain", None)

    if not prompt:
        return {
            "status": "error",
            "message": "Prompt is required for code generation.",
            "code": None,
            "language": None
        }

    # Auto-detect language if not provided
    if not language:
        language = detect_language(prompt)
    language = LANGUAGE_ALIASES.get(language, language)

    if language not in [LANGUAGE_ALIASES.get(l, l) for l in SUPPORTED_LANGUAGES]:
        language = "python"

    # Build AI prompt
    system_prompt = f"""You are Chhoti Don's coding engine — an expert programmer.
Your job is to write clean, working, well-commented {language} code.
RULES:
- Write ONLY code inside triple backticks (```{language} ... ```)
- Add brief inline comments
- No extra explanation outside the code block
- Code must be complete and runnable
- Follow best practices for {language}
"""

    user_prompt = f"Write {language} code for: {prompt}"
    if context:
        user_prompt += f"\n\nAdditional context: {context}"

    # Use brain if available
    if brain:
        try:
            raw_response = brain.think(user_prompt, system_override=system_prompt)
            generated_code = extract_code_from_response(raw_response)
        except Exception as e:
            generated_code = f"# Code generation failed: {str(e)}\n# Prompt: {prompt}"
    else:
        # Fallback template
        generated_code = _fallback_template(language, prompt)

    return {
        "status": "success",
        "language": language,
        "extension": LANGUAGE_EXTENSIONS.get(language, ".txt"),
        "prompt": prompt,
        "code": generated_code,
        "lines": len(generated_code.splitlines()),
        "message": f"✅ Code generated in {language} ({len(generated_code.splitlines())} lines)"
    }


def _fallback_template(language: str, prompt: str) -> str:
    """Basic fallback if brain is unavailable."""
    templates = {
        "python": f'# TODO: {prompt}\ndef main():\n    pass\n\nif __name__ == "__main__":\n    main()',
        "javascript": f'// TODO: {prompt}\nfunction main() {{\n    // implement here\n}}\nmain();',
        "cpp": f'// TODO: {prompt}\n#include <iostream>\nusing namespace std;\nint main() {{\n    // implement\n    return 0;\n}}',
        "c": f'// TODO: {prompt}\n#include <stdio.h>\nint main() {{\n    // implement\n    return 0;\n}}',
        "sql": f'-- TODO: {prompt}\nSELECT * FROM table_name WHERE condition;',
        "bash": f'#!/bin/bash\n# TODO: {prompt}\necho "Hello from Chhoti Don"',
    }
    return templates.get(language, f"# TODO: {prompt}")
