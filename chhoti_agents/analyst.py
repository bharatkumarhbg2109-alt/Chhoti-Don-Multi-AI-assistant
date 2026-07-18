"""
Chhoti Don - Analyst Agent
Advanced data analysis agent with statistical analysis,
pattern detection, visualization suggestions, and reporting.
Phase 2.2 - Full Upgrade
"""

import re
import json
import time
import datetime
from typing import Any, Dict, List, Optional, Optional

from chhoti_agents.base import BaseAgent


class AnalystAgent(BaseAgent):
    """
    Advanced Data Analyst Agent.
    Preserved interface + full analytical capabilities.
    """

    def __init__(self, brain=None):
        super().__init__(
            name="AnalystAgent",
            role="Senior Data Analyst",
            goal="Extract deep insights, patterns, and actionable intelligence from data",
            brain=brain,
        )
        self._brain_type = "analytics"
        self.analysis_cache: Dict = {}

    # ==================================================
    # 🔍 MAIN ACT (PRESERVED + UPGRADED)
    # ==================================================

    def act(self, task: str) -> Any:
        """
        Execute analytical task.
        Preserved + upgraded with multi-mode analysis.
        """
        task_lower = task.lower()

        # Route to specialized analysis
        if any(kw in task_lower for kw in ["compare", "vs", "versus", "fark"]):
            return self._comparative_analysis(task)

        elif any(kw in task_lower for kw in ["trend", "pattern", "over time", "growth"]):
            return self._trend_analysis(task)

        elif any(kw in task_lower for kw in ["risk", "threat", "danger", "vulnerability"]):
            return self._risk_analysis(task)

        elif any(kw in task_lower for kw in ["summarize", "summary", "overview", "brief"]):
            return self._summarize(task)

        elif any(kw in task_lower for kw in ["statistics", "stats", "average", "mean", "median"]):
            return self._statistical_analysis(task)

        elif self._contains_numbers(task):
            return self._numerical_analysis(task)

        else:
            return self._general_analysis(task)

    # ==================================================
    # 📊 ANALYSIS METHODS (NEW)
    # ==================================================

    def _general_analysis(self, task: str) -> Dict:
        """General analysis with brain."""
        if self.brain:
            system_prompt = (
                f"You are {self.name}, a {self.role}. "
                "Analyze the given data/task and provide: "
                "1) Key findings 2) Patterns identified 3) Actionable recommendations. "
                "Be concise, structured, and data-driven."
            )
            response = self.brain.think(task, brain_type="analytics", system_override=system_prompt)

            return {
                "analysis_type": "general",
                "task": task[:100],
                "insights": response,
                "agent": self.name,
                "timestamp": datetime.datetime.utcnow().isoformat(),
            }

        return {
            "analysis_type": "general",
            "task": task[:100],
            "insights": f"Analysis of: {task}",
            "recommendations": ["Gather more data", "Define metrics", "Set baseline"],
        }

    def _comparative_analysis(self, task: str) -> Dict:
        """Two items/datasets compare karo."""
        if self.brain:
            prompt = (
                f"Compare the following and provide structured analysis:\n{task}\n\n"
                "Format:\n"
                "SIMILARITIES: [list]\n"
                "DIFFERENCES: [list]\n"
                "RECOMMENDATION: [which is better and why]"
            )
            response = self.brain.think(prompt, brain_type="analytics")
            return {
                "analysis_type": "comparative",
                "task": task[:100],
                "comparison": response,
                "agent": self.name,
            }

        # Rule-based fallback
        items = re.findall(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)\b', task)
        return {
            "analysis_type": "comparative",
            "items_detected": items[:2],
            "comparison": f"Comparing: {' vs '.join(items[:2]) if len(items) >= 2 else task}",
            "recommendation": "Need more data for definitive comparison",
        }

    def _trend_analysis(self, task: str) -> Dict:
        """Trend aur patterns analyze karo."""
        numbers = self._extract_numbers(task)

        trend_result = {
            "analysis_type": "trend",
            "task": task[:100],
        }

        if numbers and len(numbers) >= 3:
            trend = self._calculate_trend(numbers)
            trend_result.update({
                "data_points": numbers,
                "trend_direction": trend["direction"],
                "trend_strength": trend["strength"],
                "average": trend["average"],
                "min": min(numbers),
                "max": max(numbers),
                "range": max(numbers) - min(numbers),
            })
        elif self.brain:
            response = self.brain.think(
                f"Analyze trends in: {task}",
                brain_type="analytics"
            )
            trend_result["insights"] = response
        else:
            trend_result["insights"] = f"Trend analysis for: {task}"

        return trend_result

    def _risk_analysis(self, task: str) -> Dict:
        """Risk assessment karo."""
        if self.brain:
            prompt = (
                f"Perform risk analysis for:\n{task}\n\n"
                "Provide: 1) Risk Level (Low/Medium/High/Critical) "
                "2) Key risk factors 3) Mitigation strategies"
            )
            response = self.brain.think(prompt, brain_type="analytics")
            return {
                "analysis_type": "risk",
                "task": task[:100],
                "risk_assessment": response,
                "agent": self.name,
            }

        # Rule-based risk keywords
        risk_level = "low"
        risk_keywords = {
            "critical": ["critical", "exploit", "breach", "compromised"],
            "high": ["vulnerable", "attack", "malware", "threat"],
            "medium": ["risk", "potential", "possible", "concern"],
        }

        task_lower = task.lower()
        for level, keywords in risk_keywords.items():
            if any(kw in task_lower for kw in keywords):
                risk_level = level
                break

        return {
            "analysis_type": "risk",
            "task": task[:100],
            "risk_level": risk_level.upper(),
            "recommendation": self._get_risk_recommendation(risk_level),
        }

    def _statistical_analysis(self, task: str) -> Dict:
        """Statistical analysis karo."""
        numbers = self._extract_numbers(task)

        if not numbers:
            return {
                "analysis_type": "statistical",
                "message": "No numerical data found in task",
                "task": task[:100],
            }

        n = len(numbers)
        mean = sum(numbers) / n
        sorted_nums = sorted(numbers)
        median = sorted_nums[n // 2] if n % 2 == 1 else (sorted_nums[n//2-1] + sorted_nums[n//2]) / 2

        variance = sum((x - mean) ** 2 for x in numbers) / n
        std_dev = variance ** 0.5

        return {
            "analysis_type": "statistical",
            "data_points": numbers,
            "count": n,
            "mean": round(mean, 4),
            "median": round(median, 4),
            "std_dev": round(std_dev, 4),
            "variance": round(variance, 4),
            "min": min(numbers),
            "max": max(numbers),
            "range": round(max(numbers) - min(numbers), 4),
            "sum": round(sum(numbers), 4),
        }

    def _numerical_analysis(self, task: str) -> Dict:
        """Numbers detect hone pe quick analysis."""
        numbers = self._extract_numbers(task)
        stats = self._statistical_analysis(task) if numbers else {}

        return {
            "analysis_type": "numerical",
            "task": task[:100],
            "numbers_found": numbers,
            "statistics": stats,
        }

    def _summarize(self, task: str) -> Dict:
        """Content summarize karo."""
        if self.brain:
            prompt = f"Summarize the following concisely in 3-5 key points:\n{task}"
            response = self.brain.think(prompt, brain_type="analytics")
            return {
                "analysis_type": "summary",
                "summary": response,
                "agent": self.name,
            }

        words = task.split()
        return {
            "analysis_type": "summary",
            "summary": f"Summary: {' '.join(words[:30])}{'...' if len(words) > 30 else ''}",
            "word_count": len(words),
        }

    # ==================================================
    # 📊 REPORTING (NEW)
    # ==================================================

    def generate_report(self, data: Dict, report_type: str = "standard") -> Dict:
        """Structured analysis report generate karo."""
        return {
            "report_type": report_type,
            "generated_by": self.name,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "executive_summary": self._build_executive_summary(data),
            "findings": data,
            "recommendations": self._extract_recommendations(data),
        }

    def _build_executive_summary(self, data: Dict) -> str:
        analysis_type = data.get("analysis_type", "general")
        return f"Analysis completed by {self.name}. Type: {analysis_type}."

    def _extract_recommendations(self, data: Dict) -> List[str]:
        recs = []
        if "risk_level" in data:
            level = data["risk_level"]
            if level in ["CRITICAL", "HIGH"]:
                recs.append("Immediate action required")
            elif level == "MEDIUM":
                recs.append("Schedule review within 1 week")
        if not recs:
            recs.append("Monitor and review periodically")
        return recs

    # ==================================================
    # 🔧 HELPERS
    # ==================================================

    def _extract_numbers(self, text: str) -> List[float]:
        """Numbers extract karo from text."""
        try:
            return [float(x) for x in re.findall(r'-?\d+\.?\d*', text)]
        except Exception:
            return []

    def _contains_numbers(self, text: str) -> bool:
        return bool(re.search(r'\d+', text))

    def _calculate_trend(self, numbers: List[float]) -> Dict:
        if len(numbers) < 2:
            return {"direction": "insufficient_data", "strength": 0, "average": 0}

        n = len(numbers)
        avg = sum(numbers) / n

        # Simple linear trend
        increases = sum(1 for i in range(1, n) if numbers[i] > numbers[i-1])
        decreases = sum(1 for i in range(1, n) if numbers[i] < numbers[i-1])

        if increases > decreases:
            direction = "upward"
            strength = round(increases / (n - 1), 2)
        elif decreases > increases:
            direction = "downward"
            strength = round(decreases / (n - 1), 2)
        else:
            direction = "stable"
            strength = 0.5

        return {"direction": direction, "strength": strength, "average": round(avg, 2)}

    def _get_risk_recommendation(self, level: str) -> str:
        recs = {
            "critical": "URGENT: Immediate action required. Escalate to security team.",
            "high": "HIGH PRIORITY: Address within 24 hours.",
            "medium": "MEDIUM PRIORITY: Schedule remediation within 1 week.",
            "low": "LOW PRIORITY: Monitor and review in next cycle.",
        }
        return recs.get(level, "Review and assess further.")
