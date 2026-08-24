"""Tests for cyber_engine.guardian.operator_guard - ContextVar-based approval."""

import pytest
from cyber_engine.guardian.operator_guard import (
    OperatorGuard,
    use_approver,
    approve_all,
    deny_all,
    request_approval,
)


class TestOperatorGuardProtectedActions:
    """Protected action identification (unchanged logic, must still work)."""

    def setup_method(self):
        self.guard = OperatorGuard()

    @pytest.mark.parametrize("action", ["self_heal", "auto_fix", "patch_apply", "code_rewrite"])
    def test_protected_actions_identified(self, action):
        assert self.guard.requires_approval(action) is True

    @pytest.mark.parametrize("action", ["fs_read_file", "fs_list_dir", "web_search", "read_code"])
    def test_non_protected_actions_not_flagged(self, action):
        assert self.guard.requires_approval(action) is False

    @pytest.mark.parametrize("path", ["main.py", "core/brain.py", "src/manager.py"])
    def test_protected_files_detected(self, path):
        assert self.guard.is_protected_file(path) is True

    def test_non_protected_file_passes(self):
        assert self.guard.is_protected_file("tools/sandbox.py") is False

    def test_assess_action_high_fs(self):
        result = self.guard.assess_action("fs_delete_file")
        assert result["risk_level"] == "high"
        assert result["requires_confirmation"] is True

    def test_assess_action_medium_fs(self):
        result = self.guard.assess_action("fs_write_file")
        assert result["risk_level"] == "medium"
        assert result["requires_confirmation"] is True

    def test_assess_action_readonly_fs(self):
        result = self.guard.assess_action("fs_read_file")
        assert result["risk_level"] == "low"
        assert result["requires_confirmation"] is False


class TestRequestPermissionContextVar:
    """request_permission() uses ContextVar, never input()."""

    def setup_method(self):
        self.guard = OperatorGuard()

    def test_no_provider_deny_fail_safe(self):
        """(a) No provider set -> DENY (fail-safe)."""
        assert self.guard.request_permission("self_heal") is False

    def test_approve_all_provider_approves(self):
        """(b) approve_all provider -> APPROVE."""
        with use_approver(approve_all):
            assert self.guard.request_permission("self_heal") is True
            assert self.guard.request_permission("auto_fix") is True

    def test_deny_all_provider_denies(self):
        """(c) deny_all provider -> DENY."""
        with use_approver(deny_all):
            assert self.guard.request_permission("self_heal") is False

    def test_provider_error_denies_fail_safe(self):
        """Provider exception -> DENY (fail-safe)."""
        def broken(action):
            raise RuntimeError("broken")

        with use_approver(broken):
            assert self.guard.request_permission("self_heal") is False

    def test_context_reset_restores_default(self):
        """After context exits, approval reverts to DENY."""
        with use_approver(approve_all):
            assert self.guard.request_permission("self_heal") is True
        # Outside the context -> no provider -> DENY
        assert self.guard.request_permission("self_heal") is False

    def test_request_approval_module_level(self):
        """request_approval() module-level function works the same way."""
        assert request_approval("self_heal") is False  # no provider
        with use_approver(approve_all):
            assert request_approval("self_heal") is True

    def test_readonly_fs_auto_allowed(self):
        """Read-only fs actions do not need approval even with no provider."""
        result = self.guard.assess_action("fs_list_dir")
        assert result["requires_confirmation"] is False
        assert result["risk_level"] == "low"
