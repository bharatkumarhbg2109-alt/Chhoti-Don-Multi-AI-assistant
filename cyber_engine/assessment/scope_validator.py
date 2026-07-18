"""
Chhoti Don - Scope Validator
Advanced target validation with whitelist/blacklist,
domain validation, CIDR support, and audit logging.
Phase 2.2 - Full Upgrade
"""

import ipaddress
import socket
import re
from typing import Dict, List, Optional, Tuple
# ==================================================

ALLOWED_IP_RANGES = [
    "127.0.0.0/8",       # Loopback
    "192.168.0.0/16",    # Private Class C
    "10.0.0.0/8",        # Private Class A
    "172.16.0.0/12",     # Private Class B
]

# Known dangerous/blacklisted ranges
BLACKLISTED_RANGES = [
    "0.0.0.0/8",         # Reserved
    "169.254.0.0/16",    # Link-local
    "224.0.0.0/4",       # Multicast
    "240.0.0.0/4",       # Reserved
    "255.255.255.255/32" # Broadcast
]

# Critical infrastructure IPs — NEVER scan
CRITICAL_IPS = [
    "8.8.8.8",           # Google DNS
    "8.8.4.4",           # Google DNS
    "1.1.1.1",           # Cloudflare DNS
    "1.0.0.1",           # Cloudflare DNS
]

# Allowed domains whitelist (optional)
ALLOWED_DOMAINS = []

# Scope validation audit log
_scope_audit_log = []

# Lab mode — if True, only private IPs allowed
LAB_MODE = True


# ==================================================
# 🧠 CORE VALIDATION (PRESERVED + UPGRADED)
# ==================================================

def validate_target(target: str, mode: str = "lab") -> Dict:
    """
    Original structured validation — preserved + upgraded.

    Args:
        target: IP address or hostname
        mode: 'lab' (private only) | 'authorized' (any IP with auth)

    Returns:
        Dict with allowed, reason, metadata
    """
    if not target or not isinstance(target, str):
        return _denied("Empty or invalid target provided")

    target = target.strip()

    # Basic sanitization
    if len(target) > 255:
        return _denied("Target too long — possible injection attempt")

    # Try IP validation first
    try:
        ip = ipaddress.ip_address(target)
        return _validate_ip(ip, target, mode)

    except ValueError:
        # Try as hostname
        return _validate_hostname(target, mode)


def _validate_ip(ip: ipaddress.IPv4Address, target: str, mode: str) -> Dict:
    """IP address validate karo."""

    # Critical IP check
    if str(ip) in CRITICAL_IPS:
        _audit(target, "BLOCKED", "Critical infrastructure IP")
        return _denied("Critical infrastructure IP — scanning not allowed")

    # Blacklist check
    for blacklisted in BLACKLISTED_RANGES:
        try:
            if ip in ipaddress.ip_network(blacklisted):
                _audit(target, "BLOCKED", f"Blacklisted range: {blacklisted}")
                return _denied(f"IP in blacklisted range: {blacklisted}")
        except ValueError:
            pass

    # Lab mode — only private IPs
    if mode == "lab" or LAB_MODE:
        for net in ALLOWED_IP_RANGES:
            try:
                if ip in ipaddress.ip_network(net):
                    _audit(target, "ALLOWED", f"Private range: {net}")
                    return _allowed(target, str(ip), f"Private IP in allowed range: {net}")
            except ValueError:
                pass

        _audit(target, "BLOCKED", "Outside lab ranges")
        return _denied("Target outside permitted lab ranges. Enable authorized mode for external targets.")

    # Authorized mode — public IPs allowed with warning
    _audit(target, "ALLOWED_EXTERNAL", "Authorized mode")
    return _allowed(target, str(ip), "External IP — authorized mode", warning="External target — ensure proper authorization")


def _validate_hostname(target: str, mode: str) -> Dict:
    """Hostname validate karo."""

    # Basic hostname format check
    hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
    if not re.match(hostname_pattern, target):
        return _denied("Invalid hostname format")

    # Domain whitelist check (if configured)
    if ALLOWED_DOMAINS:
        allowed = any(target.endswith(d) or target == d for d in ALLOWED_DOMAINS)
        if not allowed:
            return _denied(f"Domain not in whitelist")

    # DNS resolution
    try:
        resolved_ip = socket.gethostbyname(target)
        ip = ipaddress.ip_address(resolved_ip)

        result = _validate_ip(ip, target, mode)
        if result.get("allowed"):
            result["resolved_ip"] = resolved_ip
            result["hostname"] = target

        return result

    except socket.gaierror:
        _audit(target, "BLOCKED", "DNS resolution failed")
        return _denied("DNS resolution failed — hostname not reachable")


# ==================================================
# 🚀 BOOLEAN WRAPPER (PRESERVED)
# ==================================================

def validate_target_scope(target: str) -> bool:
    """Boolean-compatible validation — preserved."""
    result = validate_target(target)
    return result.get("allowed", False)


# ==================================================
# 🌐 RESOLVE + VALIDATE (PRESERVED + UPGRADED)
# ==================================================

def validate_and_resolve(target: str) -> Dict:
    """
    Hostname resolution + validation.
    Preserved + upgraded with full metadata.
    """
    try:
        ipaddress.ip_address(target)
        return validate_target(target)
    except ValueError:
        return _validate_hostname(target, "lab")


# ==================================================
# 🎯 ADVANCED VALIDATION FUNCTIONS
# ==================================================

def validate_port_range(ports: List[int]) -> Dict:
    """
    Port list validate karo.

    Returns:
        Dict with valid_ports, invalid_ports, warnings
    """
    valid = []
    invalid = []
    warnings = []

    for port in ports:
        if not isinstance(port, int):
            invalid.append(port)
            continue

        if 1 <= port <= 65535:
            valid.append(port)
        else:
            invalid.append(port)

    # Warnings for sensitive ports
    sensitive_ports = {
        22: "SSH — ensure authorization",
        23: "Telnet — plaintext protocol",
        445: "SMB — handle with care",
        3389: "RDP — high risk",
    }
    for port in valid:
        if port in sensitive_ports:
            warnings.append(f"Port {port}: {sensitive_ports[port]}")

    return {
        "valid_ports": valid,
        "invalid_ports": invalid,
        "warnings": warnings,
        "total_valid": len(valid),
        "allowed": len(valid) > 0
    }


def validate_scan_request(target: str, ports: List[int], scan_type: str = "basic") -> Dict:
    """
    Full scan request validate karo — target + ports + type.

    Returns:
        Complete validation result with all checks
    """
    results = {
        "target": target,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "allowed": False,
        "warnings": [],
        "blocks": [],
    }

    # Target validation
    target_result = validate_target(target)
    if not target_result.get("allowed"):
        results["blocks"].append(f"Target: {target_result.get('reason')}")
        results["allowed"] = False
        return results

    results["target_validation"] = target_result

    # Port validation
    if ports:
        port_result = validate_port_range(ports)
        results["port_validation"] = port_result
        results["warnings"].extend(port_result.get("warnings", []))

        if not port_result.get("allowed"):
            results["blocks"].append("No valid ports in request")

    # Scan type validation
    allowed_types = ["basic", "quick", "full", "stealth", "aggressive"]
    if scan_type not in allowed_types:
        results["warnings"].append(f"Unknown scan type: {scan_type}")

    if scan_type == "aggressive":
        results["warnings"].append("Aggressive scan type — high detection risk")

    # Final decision
    results["allowed"] = len(results["blocks"]) == 0
    return results


def add_allowed_range(cidr: str) -> bool:
    """Custom CIDR range add karo allowed list mein."""
    try:
        ipaddress.ip_network(cidr)
        if cidr not in ALLOWED_IP_RANGES:
            ALLOWED_IP_RANGES.append(cidr)
        return True
    except ValueError:
        return False


def add_allowed_domain(domain: str) -> None:
    """Domain whitelist mein add karo."""
    if domain not in ALLOWED_DOMAINS:
        ALLOWED_DOMAINS.append(domain)


def set_lab_mode(enabled: bool) -> None:
    """Lab mode toggle karo."""
    global LAB_MODE
    LAB_MODE = enabled


def get_scope_audit_log(last_n: int = 20) -> List[Dict]:
    """Scope validation audit log lo."""
    return _scope_audit_log[-last_n:]


# ==================================================
# 🔧 INTERNAL HELPERS
# ==================================================

def _allowed(target: str, ip: str, reason: str, warning: str = None) -> Dict:
    result = {
        "allowed": True,
        "target": target,
        "ip": ip,
        "reason": reason,
    }
    if warning:
        result["warning"] = warning
    return result


def _denied(reason: str) -> Dict:
    return {
        "allowed": False,
        "reason": reason,
    }


def _audit(target: str, action: str, reason: str) -> None:
    """Audit log entry."""
    _scope_audit_log.append({
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "target": target,
        "action": action,
        "reason": reason,
    })
    if len(_scope_audit_log) > 500:
        _scope_audit_log.pop(0)
