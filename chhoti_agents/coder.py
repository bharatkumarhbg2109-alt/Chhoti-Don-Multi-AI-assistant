"""
Chhoti Don - Coder Agent
Advanced software engineering agent with code generation,
debugging, optimization, review, and testing capabilities.
Phase 2.2 - Full Upgrade
"""
import re
import time
import datetime
from typing import Any, Dict, List, Optional
 
from chhoti_agents.base import BaseAgent
from core.brain import Brain
 
 
class CoderAgent(BaseAgent):

    """
    Advanced Senior Software Engineer Agent.
    Preserved interface + full coding capabilities.
    """

    def __init__(self, brain=None):
        super().__init__(
            name="CoderAgent",
            role="Senior Software Engineer",
            goal="Design and generate clean, scalable, production-ready code",
            brain=brain or Brain(),
        )
        self._brain_type = "coding"
        self.default_language = "python"

    # ==================================================
    # 💻 MAIN ACT (PRESERVED + UPGRADED)
    # ==================================================

    def act(self, task: str) -> Any:
        """
        Execute coding task.
        Preserved + upgraded with multi-mode routing.
        """
        task_lower = task.lower()
        language = self._detect_language(task)

        # Route to specialized method
        if any(kw in task_lower for kw in ["debug", "fix", "error", "bug", "traceback", "exception"]):
            return self._debug_code(task, language)

        elif any(kw in task_lower for kw in ["explain", "samjhao", "what does", "kya karta"]):
            return self._explain_code(task, language)

        elif any(kw in task_lower for kw in ["review", "check", "improve", "optimize", "refactor"]):
            return self._review_code(task, language)

        elif any(kw in task_lower for kw in ["test", "unit test", "pytest", "write test"]):
            return self._generate_tests(task, language)

        elif any(kw in task_lower for kw in ["document", "docstring", "comment", "readme"]):
            return self._document_code(task, language)

        else:
            return self._generate_code(task, language)

    # ==================================================
    # 🔧 CODING METHODS (NEW)
    # ==================================================

    def _generate_code(self, task: str, language: str = "python") -> Dict:
        """Code generate karo — main function."""
        prompt = (
            f"You are a highly experienced {language} developer.\n\n"
            f"Task:\n{task}\n\n"
            "Instructions:\n"
            "- Write clean, well-structured production-ready code\n"
            "- Add meaningful comments and docstrings\n"
            "- Follow best practices and design patterns\n"
            "- Handle edge cases and errors\n"
            f"- Wrap code in: ```{language} ... ```"
        )

        system_prompt = (
            f"You are Chhoti Don's expert {language} engineer. "
            "Generate complete, working, production-quality code. "
            f"Always use ```{language} ``` code blocks."
        )

        response = self.brain.think(task, brain_type="coding", system_override=system_prompt)
        code = self._extract_code(response)

        return {
            "task": task[:100],
            "language": language,
            "code": code,
            "full_response": response,
            "agent": self.name,
            "action": "generate",
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    def _debug_code(self, task: str, language: str = "python") -> Dict:
        """Code debug karke fix karo."""
        code_block = self._extract_code(task)
        error_msg = self._extract_error(task)

        prompt = (
            f"Fix this {language} code.\n\n"
            f"ERROR:\n{error_msg or 'See code below'}\n\n"
            f"CODE:\n```{language}\n{code_block or task}\n```\n\n"
            "Provide:\n"
            "EXPLANATION: [what was wrong — 2-3 lines]\n"
            f"FIXED_CODE:\n```{language}\n[complete fixed code]\n```"
        )

        system_prompt = (
            "You are Chhoti Don's debugging specialist. "
            "Find the root cause, explain clearly, provide complete fixed code."
        )

        response = self.brain.think(prompt, brain_type="debug", system_override=system_prompt)
        fixed_code = self._extract_code(response)
        explanation = self._extract_explanation(response)

        return {
            "task": task[:100],
            "language": language,
            "original_code": code_block,
            "error": error_msg,
            "fixed_code": fixed_code,
            "explanation": explanation,
            "full_response": response,
            "agent": self.name,
            "action": "debug",
        }

    def _explain_code(self, task: str, language: str = "python") -> Dict:
        """Code explain karo."""
        code_block = self._extract_code(task) or task

        prompt = (
            f"Explain this {language} code clearly:\n\n"
            f"```{language}\n{code_block}\n```\n\n"
            "Explain:\n"
            "1. What it does (overview)\n"
            "2. How it works (step by step)\n"
            "3. Key functions/classes\n"
            "4. Potential improvements"
        )

        response = self.brain.think(prompt, brain_type="coding")

        return {
            "task": task[:100],
            "language": language,
            "code": code_block,
            "explanation": response,
            "agent": self.name,
            "action": "explain",
        }

    def _review_code(self, task: str, language: str = "python") -> Dict:
        """Code review aur optimization."""
        code_block = self._extract_code(task) or task

        prompt = (
            f"Review and optimize this {language} code:\n\n"
            f"```{language}\n{code_block}\n```\n\n"
            "Provide:\n"
            "ISSUES: [list of problems found]\n"
            "OPTIMIZATIONS: [suggested improvements]\n"
            f"IMPROVED_CODE:\n```{language}\n[optimized version]\n```\n"
            "SCORE: [code quality score /10]"
        )

        response = self.brain.think(prompt, brain_type="coding")
        improved = self._extract_code(response)

        return {
            "task": task[:100],
            "language": language,
            "original_code": code_block,
            "review": response,
            "improved_code": improved,
            "agent": self.name,
            "action": "review",
        }

    def _generate_tests(self, task: str, language: str = "python") -> Dict:
        """Unit tests generate karo."""
        code_block = self._extract_code(task) or task

        prompt = (
            f"Write comprehensive unit tests for this {language} code:\n\n"
            f"```{language}\n{code_block}\n```\n\n"
            "Include:\n"
            "- Happy path tests\n"
            "- Edge case tests\n"
            "- Error handling tests\n"
            f"Use {'pytest' if language == 'python' else 'appropriate testing framework'}"
        )

        response = self.brain.think(prompt, brain_type="coding")
        test_code = self._extract_code(response)

        return {
            "task": task[:100],
            "language": language,
            "source_code": code_block,
            "test_code": test_code,
            "full_response": response,
            "agent": self.name,
            "action": "generate_tests",
        }

    def _document_code(self, task: str, language: str = "python") -> Dict:
        """Code documentation generate karo."""
        code_block = self._extract_code(task) or task

        prompt = (
            f"Add comprehensive documentation to this {language} code:\n\n"
            f"```{language}\n{code_block}\n```\n\n"
            "Add:\n"
            "- Module docstring\n"
            "- Class/function docstrings\n"
            "- Inline comments for complex logic\n"
            "- Type hints where missing"
        )

        response = self.brain.think(prompt, brain_type="coding")
        documented = self._extract_code(response)

        return {
            "task": task[:100],
            "language": language,
            "original_code": code_block,
            "documented_code": documented,
            "agent": self.name,
            "action": "document",
        }

    # ==================================================
    # 🔧 HELPERS
    # ==================================================

    def _detect_language(self, task: str) -> str:
        """Programming language detect karo."""
        task_lower = task.lower()
        lang_map = [
            (["python", ".py", "django", "flask", "pandas"], "python"),
            (["javascript", " js ", "nodejs", ".js", "react"], "javascript"),
            (["typescript", ".ts", "tsx"], "typescript"),
            (["c++", "cpp", "c plus"], "cpp"),
            (["java ", ".java", "spring"], "java"),
            (["bash", "shell", "#!/bin/bash"], "bash"),
            (["sql", "select ", "insert into"], "sql"),
            (["html", "css", "webpage"], "html"),
            (["rust", "cargo", "fn main"], "rust"),
            (["go ", "golang", "package main"], "go"),
        ]

        for keywords, lang in lang_map:
            if any(kw in task_lower for kw in keywords):
                return lang

        # Check code blocks
        code_match = re.search(r"```(\w+)", task)
        if code_match:
            return code_match.group(1)

        return self.default_language

    def _extract_code(self, text: str) -> Optional[str]:
        """Code block extract karo."""
        if not text:
            return None
        pattern = r"```(?:\w+)?\n?([\s\S]*?)```"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_error(self, text: str) -> Optional[str]:
        """Error message extract karo."""
        patterns = [
            r"((?:Traceback|Error|Exception)[\s\S]*?)(?:\n\n|```|$)",
            r"(?:error|exception)[:\s]+([^\n]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)[:500]
        return None

    def _extract_explanation(self, text: str) -> Optional[str]:
        """Explanation extract karo from debug response."""
        match = re.search(r"EXPLANATION[:\s]+([\s\S]*?)(?:FIXED_CODE|```|$)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:500]
        return None

    def generate_boilerplate(self, project_type: str, language: str = "python") -> Dict:
        """Boilerplate code generate karo."""
        prompt = f"Generate a complete {project_type} boilerplate in {language} with best practices."
        return self._generate_code(prompt, language)

    def analyze_complexity(self, code: str) -> Dict:
        """Code complexity analyze karo."""
        lines = code.split('\n')
        functions = len(re.findall(r'def\s+\w+', code))
        classes = len(re.findall(r'class\s+\w+', code))
        comments = len([l for l in lines if l.strip().startswith('#')])
        imports = len(re.findall(r'^import|^from', code, re.MULTILINE))

        return {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
            "comment_lines": comments,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "comment_ratio": round(comments / max(len(lines), 1) * 100, 1),
        }
