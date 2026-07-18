"""Module Description"""

from collections import defaultdict

class TelemetryEngine:

    def __init__(self):
        ...
        self.rule_success = defaultdict(int)
        self.rule_failure = defaultdict(int)

    def get_dynamic_confidence(self, rule_name, base_confidence):
        success = self.rule_success[rule_name]
        failure = self.rule_failure[rule_name]

        dynamic = base_confidence + (success * 0.005) - (failure * 0.01)

        # clamp between safe bounds

        return max(0.60, min(0.99, dynamic))

        # =================================================
        # Core Counters
        # =================================================
        self.total_executions = 0
        self.success_count = 0
        self.error_count = 0
        self.blocked_count = 0

        # =================================================
        # Timing
        # =================================================
        self.total_execution_time = 0.0
        self.peak_execution_time = 0.0
        self.min_execution_time = None

        # =================================================
        # Tool Usage
        # =================================================
        self.tool_usage = defaultdict(int)
        self.tool_success = defaultdict(int)
        self.tool_failure = defaultdict(int)

        # =================================================
        # Failure Pattern Memory
        # =================================================
        self.failure_streak = defaultdict(int)
        self.error_type_frequency = defaultdict(int)
        self.tool_health_score = defaultdict(lambda: 1.0)
        self.last_error_code = None

        # =================================================
        # Trend & Pattern Tracking
        # =================================================
        self.consecutive_failures = 0
        self.max_consecutive_failures = 0
        self.execution_history = []

        # =================================================
        # Last Execution Snapshot
        # =================================================
        self.last_execution_status = None
        self.last_execution_time = 0.0

    # =================================================
    # RECORD EXECUTION
    # =================================================
    def record(self, module_name, status, execution_time, error_code=None):

        self.total_executions += 1
        self.tool_usage[module_name] += 1

        # Timing
        if execution_time:
            self.total_execution_time += execution_time

            if execution_time > self.peak_execution_time:
                self.peak_execution_time = execution_time

            if self.min_execution_time is None:
                self.min_execution_time = execution_time
            elif execution_time < self.min_execution_time:
                self.min_execution_time = execution_time

        # Status
        self.last_execution_status = status
        self.last_execution_time = execution_time or 0.0

        if status == "success":
            self.success_count += 1
            self.tool_success[module_name] += 1
            self.consecutive_failures = 0
            self.failure_streak[module_name] = 0

        elif status in ["error", "blocked"]:
            self.error_count += 1
            self.tool_failure[module_name] += 1
            self.consecutive_failures += 1
            self.failure_streak[module_name] += 1

            if self.consecutive_failures > self.max_consecutive_failures:
                self.max_consecutive_failures = self.consecutive_failures

            if error_code:
                self.error_type_frequency[error_code] += 1
                self.last_error_code = error_code

        # Update health score
        total = self.tool_success[module_name] + self.tool_failure[module_name]
        if total > 0:
            health = self.tool_success[module_name] / total
            self.tool_health_score[module_name] = round(health, 4)

        # Rolling history
        self.execution_history.append(status)
        if len(self.execution_history) > 50:
            self.execution_history.pop(0)

    # =================================================
    # TOOL RELIABILITY
    # =================================================
    def get_tool_reliability(self, module_name):
        return self.tool_health_score.get(module_name, 1.0)

    # =================================================
    # FAILURE MEMORY ACCESS
    # =================================================
    def get_failure_streak(self, module_name):
        return self.failure_streak.get(module_name, 0)

    def get_error_frequency(self, error_code):
        return self.error_type_frequency.get(error_code, 0)

    def is_repeated_error(self, error_code, threshold=3):
        return self.error_type_frequency.get(error_code, 0) >= threshold

    # =================================================
    # BASIC EXTRACTION (NEW)
    # =================================================
    def get_preferred_tools(self, threshold=0.7):
        return [
            tool for tool, score in self.tool_health_score.items()
            if score >= threshold
        ]

    def get_avoid_tools(self, reliability_threshold=0.4, streak_threshold=3):
        avoid = []

        for tool, score in self.tool_health_score.items():
            if score < reliability_threshold:
                avoid.append(tool)

        for tool, streak in self.failure_streak.items():
            if streak >= streak_threshold and tool not in avoid:
                avoid.append(tool)

        return avoid

    def get_system_state(self):
        return {
            "unstable": self.detect_instability(),
            "recent_success_rate": self.get_recent_success_rate(),
            "consecutive_failures": self.consecutive_failures
        }

    def get_planner_bias_snapshot(self):
        """
        Clean structured telemetry extraction for planner layer.
        """
        return {
            "preferred_tools": self.get_preferred_tools(),
            "avoid_tools": self.get_avoid_tools(),
            "system_state": self.get_system_state(),
            "last_error_code": self.last_error_code
        }

    def get_health_summary(self):
        """
        Lightweight summary for quick decision logic.
        """
        return {
            "system_unstable": self.detect_instability(),
            "success_ratio": (
                self.success_count / self.total_executions
                if self.total_executions else 0
            ),
            "most_used_tool": max(self.tool_usage, key=self.tool_usage.get)
            if self.tool_usage else None
        }

    # =================================================
    # TREND ANALYSIS
    # =================================================
    def get_recent_success_rate(self):
        if not self.execution_history:
            return 0

        successes = self.execution_history.count("success")
        return round(successes / len(self.execution_history), 4)

    def detect_instability(self):
        if self.consecutive_failures >= 3:
            return True

        if self.get_recent_success_rate() < 0.4:
            return True

        return False

    # =================================================
    # METRICS
    # =================================================
    def get_metrics(self):

        if self.total_executions == 0:
            avg_time = 0
            success_ratio = 0
            error_rate = 0
            block_rate = 0
        else:
            avg_time = round(
                self.total_execution_time / self.total_executions, 4
            )

            success_ratio = round(
                self.success_count / self.total_executions, 4
            )

            error_rate = round(
                self.error_count / self.total_executions, 4
            )

            block_rate = round(
                self.blocked_count / self.total_executions, 4
            )

        most_used_tool = None
        if self.tool_usage:
            most_used_tool = max(self.tool_usage, key=self.tool_usage.get)

        return {
            "total_executions": self.total_executions,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "blocked_count": self.blocked_count,
            "average_execution_time": avg_time,
            "tool_usage": dict(self.tool_usage),

            "success_ratio": success_ratio,
            "error_rate": error_rate,
            "block_rate": block_rate,
            "most_used_tool": most_used_tool,

            "peak_execution_time": round(self.peak_execution_time, 4),
            "min_execution_time": round(self.min_execution_time, 4)
            if self.min_execution_time is not None else 0,

            "tool_health_score": dict(self.tool_health_score),
            "failure_streak": dict(self.failure_streak),
            "error_type_frequency": dict(self.error_type_frequency),
            "recent_success_rate": self.get_recent_success_rate(),
            "consecutive_failures": self.consecutive_failures,
            "max_consecutive_failures": self.max_consecutive_failures,
            "system_unstable": self.detect_instability(),
            "last_error_code": self.last_error_code,

            # NEW
            "planner_bias_snapshot": self.get_planner_bias_snapshot(),
            "health_summary": self.get_health_summary(),

            "last_execution_status": self.last_execution_status,
            "last_execution_time": round(self.last_execution_time, 4)
        }


    # =================================================
    # RESET TELEMETRY
    # =================================================
    def reset(self):
        self.__init__()

