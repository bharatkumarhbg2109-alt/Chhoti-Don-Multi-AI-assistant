"""Public deploy adapters + pre-deploy secret preflight (Phase 6 — FINAL phase).

Deploy is the highest-risk, least-reversible action in the system, so this module
is deliberately thin and pure: it knows HOW to talk to each platform CLI (the
auth-check command, the preview/production deploy commands, and how to parse the
deployed URL), and it can scan a workspace for secrets that must not be uploaded.

It does NOT execute anything itself and it holds NO credentials. The guarded layer
(coding_agent.guarded._run_deploy) runs the CLI through the SAME injectable
``shell.run`` executor as Phase 4, behind an ALWAYS-individual human confirmation
that no session/auto approval can bypass. The agent relies entirely on each CLI's
OWN pre-existing auth state — it never logs in, creates accounts, or reads tokens.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from .config import SECRET_SCAN_MAX_FILE_BYTES


# ── adapters ──────────────────────────────────────────────────────────────────
@dataclass
class DeployAdapter:
    name: str
    program: str
    auth_check: List[str]          # read-only "am I logged in?" argv
    install_hint: str
    auth_hint: str
    supports_preview: bool = True  # False => the platform always publishes LIVE
    _url_domain: str = ""          # substring/domain to recognize the deployed URL

    def deploy_argv(self, prod: bool) -> List[str]:  # pragma: no cover - overridden
        raise NotImplementedError

    def parse_url(self, stdout: str, stderr: str) -> Optional[str]:
        """Extract the deployed URL from CLI output (best effort)."""
        text = f"{stdout or ''}\n{stderr or ''}"
        # Prefer a labeled line (Preview/Production/Website/Live URL: <url>).
        m = re.search(r"(?i)(?:preview|production|website|live|deployed|draft)[^\n:]*:\s*"
                      r"(https?://[^\s]+)", text)
        if m:
            return m.group(1).rstrip(".,)")
        # Else the first URL on the platform's domain.
        if self._url_domain:
            m = re.search(r"https?://[^\s]*" + re.escape(self._url_domain) + r"[^\s]*", text)
            if m:
                return m.group(0).rstrip(".,)")
        # Else any https URL.
        m = re.search(r"https?://[^\s]+", text)
        return m.group(0).rstrip(".,)") if m else None


class _Vercel(DeployAdapter):
    def __init__(self):
        super().__init__(name="vercel", program="vercel", auth_check=["vercel", "whoami"],
                         install_hint="npm i -g vercel", auth_hint="vercel login",
                         supports_preview=True, _url_domain="vercel.app")

    def deploy_argv(self, prod: bool) -> List[str]:
        argv = ["vercel", "deploy", "--yes"]
        if prod:
            argv.append("--prod")
        return argv


class _Netlify(DeployAdapter):
    def __init__(self):
        super().__init__(name="netlify", program="netlify", auth_check=["netlify", "status"],
                         install_hint="npm i -g netlify-cli", auth_hint="netlify login",
                         supports_preview=True, _url_domain="netlify.app")

    def deploy_argv(self, prod: bool) -> List[str]:
        argv = ["netlify", "deploy"]
        if prod:
            argv.append("--prod")
        return argv


class _GitHubPages(DeployAdapter):
    def __init__(self):
        # Auth via the gh CLI; publish via gh-pages. Pages has NO preview — it
        # always publishes live, so supports_preview=False forces the prod confirm.
        super().__init__(name="github-pages", program="gh-pages",
                         auth_check=["gh", "auth", "status"],
                         install_hint="npm i -g gh-pages  (and install the gh CLI)",
                         auth_hint="gh auth login", supports_preview=False,
                         _url_domain="github.io")

    def deploy_argv(self, prod: bool) -> List[str]:
        # Publishes ./dist to the gh-pages branch (prod flag does not change it).
        return ["gh-pages", "-d", "dist"]


_ADAPTERS: Dict[str, DeployAdapter] = {
    "vercel": _Vercel(),
    "netlify": _Netlify(),
    "github-pages": _GitHubPages(),
}
_ALIASES = {"gh-pages": "github-pages", "githubpages": "github-pages",
            "pages": "github-pages", "gh": "github-pages"}


def get_adapter(platform: str) -> Optional[DeployAdapter]:
    key = (platform or "").strip().lower()
    return _ADAPTERS.get(_ALIASES.get(key, key))


def list_platforms() -> List[str]:
    return list(_ADAPTERS.keys())


# ── auth check (read-only) ────────────────────────────────────────────────────
def check(platform: str, cwd: str, runner: Callable[..., Dict[str, Any]],
          timeout: float, output_cap: int) -> Dict[str, Any]:
    """Run the adapter's read-only auth-check via ``runner`` (shell.run). Reports
    whether the CLI is installed and whether it is already authenticated. The
    agent never sees tokens — only this pass/fail state."""
    adapter = get_adapter(platform)
    if adapter is None:
        return {"status": "error", "marker": "UNKNOWN_PLATFORM", "platform": platform,
                "known": list_platforms()}
    r = runner(adapter.auth_check, cwd=cwd, timeout=timeout, output_cap=output_cap)
    exit_code = r.get("exit_code")
    err = (r.get("stderr") or "").lower()
    installed = exit_code != 127 and "not found" not in err and "not recognized" not in err
    authed = bool(installed and exit_code == 0)
    return {"status": "success", "platform": platform, "installed": installed,
            "authed": authed, "exit_code": exit_code,
            "install_hint": adapter.install_hint, "auth_hint": adapter.auth_hint,
            "output": (r.get("stdout") or r.get("stderr") or "").strip()[:400]}


# ── secret preflight (the key safety feature) ─────────────────────────────────
_ENV_FILE_RE = re.compile(r"^\.env(\..+)?$")
_IGNORE_FILES = (".vercelignore", ".netlifyignore", ".gitignore")

# Credential patterns scanned for in text files that would be uploaded.
_CRED_PATTERNS = (
    ("private key block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("aws access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws secret", re.compile(r"(?i)aws_secret_access_key")),
    ("google api key", re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b")),
    ("slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,}\b")),
    ("secret assignment", re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password|passwd|access[_-]?key|client[_-]?secret)\b"
        r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-\.]{16,}")),
)

_SKIP_SCAN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip",
                  ".gz", ".tar", ".mp4", ".mp3", ".woff", ".woff2", ".ttf", ".lock",
                  ".map", ".min.js", ".min.css"}


def _env_ignored(root: str) -> bool:
    """True if an ignore file plausibly excludes .env from what gets uploaded."""
    for name in _IGNORE_FILES:
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for line in fh:
                    s = line.strip()
                    if s in (".env", ".env*", ".env.*", "*.env", ".env/") or s.startswith(".env"):
                        return True
        except OSError:
            continue
    return False


def secret_preflight(root: str) -> Dict[str, Any]:
    """Scan the workspace for secrets that would be uploaded on deploy.

    Findings block a deploy by default (the guarded layer only proceeds on an
    explicit acknowledgement). A `.env`/`.env.*` file is a finding UNLESS an
    ignore file (.vercelignore/.netlifyignore/.gitignore) covers it; credential
    patterns in any scanned file are always findings.
    """
    findings: List[Dict[str, Any]] = []
    env_files: List[str] = []
    ignored = _env_ignored(root)
    from .config import IGNORED_DIRS

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if _ENV_FILE_RE.match(fn):
                env_files.append(rel)
                if not ignored:
                    findings.append({"type": "env_file", "file": rel})
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in _SKIP_SCAN_EXT:
                continue
            try:
                if os.path.getsize(full) > SECRET_SCAN_MAX_FILE_BYTES:
                    continue
                with open(full, "r", encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
            except OSError:
                continue
            for label, rx in _CRED_PATTERNS:
                if rx.search(text):
                    findings.append({"type": "pattern", "file": rel, "pattern": label})
                    break

    return {"clean": len(findings) == 0, "findings": findings,
            "env_files": env_files, "env_ignored": ignored}
