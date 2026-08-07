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
        requires_confirmation = self.requires_approval(action_name)
        return {
            "action": action_name,
            "target": target,
            "risk_level": "low" if action_name.startswith("web_") else "unknown",
            "risk_score": 10 if action_name.startswith("web_") else 0,
            "requires_confirmation": requires_confirmation,
        }
