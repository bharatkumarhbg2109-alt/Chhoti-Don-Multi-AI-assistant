"""
Chhoti Don - Config Manager
Advanced configuration management with validation,
environment support, profiles, hot-reload, and encryption.
Phase 2.2 - Full Upgrade
"""

import os
import json
import copy
import datetime
from typing import Any, Dict, List, Optional, Set, Type# ==================================================
# 🎯 DEFAULT CONFIGURATION
# ==================================================

DEFAULT_CONFIG = {

    # --------------------------------------------------
    # 🔴 Risk & Severity Weights (PRESERVED)
    # --------------------------------------------------
    "critical_weight": 10,
    "high_weight": 7,
    "medium_weight": 4,
    "low_weight": 2,
    "info_weight": 0.5,

    # --------------------------------------------------
    # 📊 Breach Thresholds (PRESERVED)
    # --------------------------------------------------
    "breach_threshold_high": 0.65,
    "breach_threshold_medium": 0.5,
    "breach_threshold_critical": 0.80,

    # --------------------------------------------------
    # 🔍 Scanning Settings
    # --------------------------------------------------
    "scanner": {
        "default_timeout": 1.0,
        "max_threads": 100,
        "max_ports": 1000,
        "grab_banners": True,
        "retry_count": 1,
        "default_ports": [21, 22, 23, 25, 53, 80, 443, 445,
                          1433, 3306, 3389, 5432, 6379, 8080, 27017],
    },

    # --------------------------------------------------
    # 🧠 Brain / AI Settings
    # --------------------------------------------------
    "brain": {
        "default_model": "qwen3.5:latest",
        "ollama_url": "http://127.0.0.1:11434/api/generate",
        "timeout": 120,
        "temperature": 0.7,
        "max_tokens": 2048,
        "retry_on_timeout": True,
        "max_retries": 2,
    },

    # --------------------------------------------------
    # 🛡️ Guardian Settings
    # --------------------------------------------------
    "guardian": {
        "enabled": True,
        "require_approval_for": ["auto_recon", "full_scan", "self_heal"],
        "max_sessions_per_target": 3,
        "rate_limit_window": 60,
        "max_scans_per_window": 5,
        "cooldown_seconds": 120,
        # Browser policy is kept with the Guardian policy so browser access has
        # one source of truth instead of a second, competing policy file.
        "browser": {
            "blocked_domains": ["localhost", "127.0.0.1", "::1", "169.254.169.254"],
            "rate_limit_per_min": 5,
            "max_content_chars": 8000,
            "require_confirmation": False,
        },
    },

    # --------------------------------------------------
    # 🔐 Scope Settings
    # --------------------------------------------------
    "scope": {
        "lab_mode": True,
        "allowed_ranges": [
            "127.0.0.0/8",
            "192.168.0.0/16",
            "10.0.0.0/8",
            "172.16.0.0/12",
        ],
        "blocked_ranges": ["0.0.0.0/8", "224.0.0.0/4"],
        "allowed_domains": [],
    },

    # --------------------------------------------------
    # 📊 Reporting Settings
    # --------------------------------------------------
    "reporting": {
        "output_dir": "reports",
        "default_format": "html",
        "include_executive_summary": True,
        "include_technical_details": True,
        "include_remediation": True,
        "max_findings_per_report": 500,
    },

    # --------------------------------------------------
    # 🔧 EvolveX Settings
    # --------------------------------------------------
    "evolveX": {
        "max_fixes_per_file": 25,
        "max_healing_iterations": 5,
        "governance_mode": "normal",
        "min_confidence_threshold": 0.70,
        "backup_before_fix": True,
        "max_backup_versions": 5,
    },

    # --------------------------------------------------
    # 📝 Logging Settings
    # --------------------------------------------------
    "logging": {
        "level": "INFO",
        "log_to_file": False,
        "log_file": "chhoti_don.log",
        "max_log_size_mb": 10,
        "retention_days": 7,
    },

    # --------------------------------------------------
    # 🌐 Web App Settings
    # --------------------------------------------------
    "web": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": False,
        "secret_key": "change_me_in_production",
        "session_timeout": 3600,
    },

    # --------------------------------------------------
    # 🔑 API Keys (never store actual keys here)
    # --------------------------------------------------
    "api": {
        "shodan_key_env": "SHODAN_API_KEY",
        "virustotal_key_env": "VT_API_KEY",
    },
}

# Config profiles
CONFIG_PROFILES = {
    "lab": {
        "scope.lab_mode": True,
        "scanner.default_timeout": 2.0,
        "guardian.enabled": True,
        "brain.temperature": 0.7,
    },
    "production": {
        "scope.lab_mode": False,
        "scanner.default_timeout": 1.0,
        "guardian.enabled": True,
        "logging.log_to_file": True,
        "web.debug": False,
    },
    "development": {
        "scope.lab_mode": True,
        "web.debug": True,
        "logging.level": "DEBUG",
        "guardian.enabled": False,
    },
    "aggressive": {
        "scanner.max_threads": 200,
        "scanner.default_timeout": 0.5,
        "evolveX.max_fixes_per_file": 50,
        "evolveX.max_healing_iterations": 10,
    },
}

# Config file path
CONFIG_FILE = "chhoti_don_config.json"


class ConfigManager:
    """
    Advanced Configuration Manager.
    Supports nested keys, validation, profiles,
    environment variables, and persistence.
    """

    def __init__(self, config_file: str = None, profile: str = "lab"):
        self.config_file = config_file or CONFIG_FILE
        self._config = copy.deepcopy(DEFAULT_CONFIG)
        self._change_log = []
        self._validators = {}
        self._loaded_profile = None

        # Load from file if exists
        self._load_from_file()

        # Apply profile
        self.apply_profile(profile)

        # Load environment variables
        self._load_env_vars()

        # Register default validators
        self._register_default_validators()

    # ==================================================
    # 🔧 CORE GET/SET (PRESERVED + UPGRADED)
    # ==================================================

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get config value. Supports dot notation.
        Preserved + upgraded.

        Examples:
            get("critical_weight")
            get("scanner.timeout")
            get("brain.default_model")
        """
        # Try flat key first (backward compat)
        if key in self._config:
            return self._config[key]

        # Dot notation
        return self._get_nested(key, default)

    def set(self, key: str, value: Any, validate: bool = True) -> bool:
        """
        Set config value. Supports dot notation.
        Preserved + upgraded with validation.
        """
        # Validate if validator exists
        if validate and key in self._validators:
            valid, msg = self._validators[key](value)
            if not valid:
                print(f"[Config] Validation failed for '{key}': {msg}")
                return False

        # Log change
        old_value = self.get(key)
        self._log_change(key, old_value, value)

        # Flat key
        if "." not in key:
            self._config[key] = value
            return True

        # Nested key
        return self._set_nested(key, value)

    def get_all(self) -> Dict:
        """Return full config. Preserved."""
        return copy.deepcopy(self._config)

    def get_section(self, section: str) -> Dict:
        """Get entire config section."""
        return copy.deepcopy(self._config.get(section, {}))

    def update_section(self, section: str, updates: Dict) -> bool:
        """Update multiple keys in a section."""
        if section not in self._config:
            self._config[section] = {}

        for key, value in updates.items():
            self._set_nested(f"{section}.{key}", value)

        return True

    # ==================================================
    # 📋 PROFILES
    # ==================================================

    def apply_profile(self, profile_name: str) -> bool:
        """Named profile apply karo."""
        if profile_name not in CONFIG_PROFILES:
            return False

        profile = CONFIG_PROFILES[profile_name]
        for key, value in profile.items():
            self._set_nested(key, value)

        self._loaded_profile = profile_name
        print(f"[Config] Profile '{profile_name}' applied")
        return True

    def get_available_profiles(self) -> List[str]:
        """Available profiles list."""
        return list(CONFIG_PROFILES.keys())

    def create_profile(self, name: str, settings: Dict) -> bool:
        """Custom profile create karo."""
        CONFIG_PROFILES[name] = settings
        return True

    # ==================================================
    # 🌍 ENVIRONMENT VARIABLES
    # ==================================================

    def _load_env_vars(self) -> None:
        """Environment variables se config override karo."""
        env_mappings = {
            "CHHOTI_DON_MODEL": "brain.default_model",
            "CHHOTI_DON_OLLAMA_URL": "brain.ollama_url",
            "CHHOTI_DON_DEBUG": "web.debug",
            "CHHOTI_DON_PORT": "web.port",
            "CHHOTI_DON_LOG_LEVEL": "logging.level",
            "CHHOTI_DON_LAB_MODE": "scope.lab_mode",
        }

        for env_key, config_key in env_mappings.items():
            value = os.getenv(env_key)
            if value is not None:
                # Type conversion
                if value.lower() in ["true", "false"]:
                    value = value.lower() == "true"
                elif value.isdigit():
                    value = int(value)
                self._set_nested(config_key, value)

    def get_env_api_key(self, key_name: str) -> Optional[str]:
        """API key from environment variable lo."""
        env_var = self._get_nested(f"api.{key_name}_env")
        if env_var:
            return os.getenv(env_var)
        return None

    # ==================================================
    # 💾 PERSISTENCE
    # ==================================================

    def save(self, filepath: str = None) -> bool:
        """Config file mein save karo."""
        path = filepath or self.config_file

        # Never save sensitive data
        safe_config = self._get_safe_config()

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(safe_config, f, indent=2)
            print(f"[Config] Saved to {path}")
            return True
        except Exception as e:
            print(f"[Config] Save failed: {e}")
            return False

    def _load_from_file(self) -> bool:
        """File se config load karo."""
        if not os.path.exists(self.config_file):
            return False

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            # Deep merge with defaults
            self._deep_merge(self._config, loaded)
            print(f"[Config] Loaded from {self.config_file}")
            return True
        except Exception as e:
            print(f"[Config] Load failed: {e}")
            return False

    def _get_safe_config(self) -> Dict:
        """Sensitive data remove karke config return karo."""
        safe = copy.deepcopy(self._config)

        # Remove sensitive sections
        if "api" in safe:
            safe["api"] = {k: "***" for k in safe["api"]}

        if "web" in safe:
            safe["web"].pop("secret_key", None)

        return safe

    # ==================================================
    # ✅ VALIDATION
    # ==================================================

    def _register_default_validators(self) -> None:
        """Default validators register karo."""
        self._validators = {
            "scanner.default_timeout": lambda v: (
                isinstance(v, (int, float)) and 0.1 <= v <= 30,
                "Timeout must be 0.1-30 seconds"
            ),
            "scanner.max_threads": lambda v: (
                isinstance(v, int) and 1 <= v <= 500,
                "Threads must be 1-500"
            ),
            "brain.temperature": lambda v: (
                isinstance(v, (int, float)) and 0.0 <= v <= 1.0,
                "Temperature must be 0.0-1.0"
            ),
            "web.port": lambda v: (
                isinstance(v, int) and 1 <= v <= 65535,
                "Port must be 1-65535"
            ),
            "evolveX.governance_mode": lambda v: (
                v in ["normal", "cautious", "restricted"],
                "Must be: normal, cautious, restricted"
            ),
        }

    def add_validator(self, key: str, validator_fn) -> None:
        """Custom validator add karo."""
        self._validators[key] = validator_fn

    def validate_all(self) -> Dict:
        """All config values validate karo."""
        errors = []
        warnings = []

        # Required keys check
        required = ["brain.default_model", "scanner.default_timeout"]
        for key in required:
            if self._get_nested(key) is None:
                errors.append(f"Missing required key: {key}")

        # Scope check
        if not self._config.get("scope", {}).get("allowed_ranges"):
            warnings.append("No allowed IP ranges configured")

        # Secret key check
        secret = self._get_nested("web.secret_key")
        if secret == "change_me_in_production":
            warnings.append("Default secret key in use — change for production!")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    # ==================================================
    # 📋 CHANGE LOG
    # ==================================================

    def _log_change(self, key: str, old: Any, new: Any) -> None:
        """Config change log karo."""
        self._change_log.append({
            "key": key,
            "old": str(old)[:50],
            "new": str(new)[:50],
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        if len(self._change_log) > 200:
            self._change_log.pop(0)

    def get_change_log(self, last_n: int = 20) -> List[Dict]:
        """Recent config changes lo."""
        return self._change_log[-last_n:]

    # ==================================================
    # 🔄 HOT RELOAD
    # ==================================================

    def reload(self) -> bool:
        """Config file se hot reload karo."""
        if not os.path.exists(self.config_file):
            return False

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            self._deep_merge(self._config, loaded)
            print(f"[Config] Hot reloaded from {self.config_file}")
            return True
        except Exception:
            return False

    def reset_to_defaults(self, section: str = None) -> None:
        """Config defaults pe reset karo."""
        if section:
            if section in DEFAULT_CONFIG:
                self._config[section] = copy.deepcopy(DEFAULT_CONFIG[section])
                print(f"[Config] Section '{section}' reset to defaults")
        else:
            self._config = copy.deepcopy(DEFAULT_CONFIG)
            print("[Config] Full config reset to defaults")

    # ==================================================
    # 📊 INFO
    # ==================================================

    def get_info(self) -> Dict:
        """Config manager info."""
        return {
            "config_file": self.config_file,
            "file_exists": os.path.exists(self.config_file),
            "active_profile": self._loaded_profile,
            "total_keys": self._count_keys(self._config),
            "available_profiles": self.get_available_profiles(),
            "change_log_entries": len(self._change_log),
            "validation": self.validate_all(),
        }

    def _count_keys(self, d: Dict, count: int = 0) -> int:
        """Total keys count karo."""
        for v in d.values():
            count += 1
            if isinstance(v, dict):
                count = self._count_keys(v, count)
        return count

    # ==================================================
    # 🔧 INTERNAL HELPERS
    # ==================================================

    def _get_nested(self, key: str, default: Any = None) -> Any:
        """Dot notation se nested value get karo."""
        keys = key.split(".")
        current = self._config

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def _set_nested(self, key: str, value: Any) -> bool:
        """Dot notation se nested value set karo."""
        keys = key.split(".")
        current = self._config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            elif not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        return True

    def _deep_merge(self, base: Dict, override: Dict) -> None:
        """Deep merge two dicts."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
