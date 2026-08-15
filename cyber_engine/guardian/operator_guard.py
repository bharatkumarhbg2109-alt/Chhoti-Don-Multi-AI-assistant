"""
EvolveX Guardian Layer
Controls high-risk autonomous actions.
"""

class OperatorGuard:
    """Class Description"""

    def __init__(self):
        self.protected_actions = {
            "self_heal",
            "auto_fix",
            "patch_apply",
            "code_rewrite",
        }

        self.protected_files = {
            "main.py",
            "manager.py",
            "brain.py",
        }

        # Read-only coding-agent filesystem actions. Like the "web_" read tools,
        # these are LOW risk and auto-allow (no confirmation). Kept as an explicit
        # allowlist — NOT a broad "fs_" prefix — so state-changing actions stay OUT
        # of the low tier and must be granted a confirmation path of their own.
        self.readonly_fs_actions = {
            "fs_list_dir",
            "fs_read_file",
            "fs_search",
        }

        # State-changing coding-agent filesystem actions (Phase 2). These NEVER
        # auto-allow — assess_action forces requires_confirmation=True so the
        # guarded layer must obtain a human approval before committing.
        #   MEDIUM: create/overwrite/edit content, make a directory.
        #   HIGH  : delete a file (stronger warning in the confirm prompt).
        self.medium_fs_actions = {
            "fs_write_file",
            "fs_create_file",
            "fs_edit_file",
            "fs_make_dir",
        }
        self.high_fs_actions = {
            "fs_delete_file",
        }

    # -----------------------------------------
    # Check if action requires approval
    # -----------------------------------------
        """Function Description"""
    def requires_approval(self, action_name):
        """Function Description"""
        return action_name in self.protected_actions

    # -----------------------------------------
    # Check if file is protected
        """Function Description"""
    # -----------------------------------------
        """Function Description"""
    def is_protected_file(self, file_path):
        """Function Description"""
        for protected in self.protected_files:
            if protected in file_path:
                return True
        return False

    # -----------------------------------------
        """Function Description"""
    # Request permission from operator
        """Function Description"""
    # -----------------------------------------
        """Function Description"""
    def request_permission(self, action_name):
        """Function Description"""
        print(f"\n[Guardian] Action '{action_name}' requires approval.")
        decision = input("Approve? (yes/no): ").strip().lower()
        return decision == "yes"

    def assess_action(self, action_name, target=None):
        """Return a non-mutating Guardian assessment for a proposed action.

        Browser reads are deliberately low-risk, but still pass through the
        existing Guardian so all executable capabilities have a common audit
        and confirmation hook.
        """
        # State-changing fs actions always require confirmation; other actions
        # only if they are in the protected set.
        if action_name in self.high_fs_actions:
            risk_level, risk_score, requires_confirmation = "high", 80, True
        elif action_name in self.medium_fs_actions:
            risk_level, risk_score, requires_confirmation = "medium", 50, True
        elif action_name.startswith("web_") or action_name in self.readonly_fs_actions:
            risk_level, risk_score, requires_confirmation = "low", 10, self.requires_approval(action_name)
        else:
            risk_level, risk_score, requires_confirmation = "unknown", 0, self.requires_approval(action_name)
        return {
            "action": action_name,
            "target": target,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "requires_confirmation": requires_confirmation,
        }
