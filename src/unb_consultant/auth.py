"""Authentication management for unb-consultant.

Wraps notebooklm-py CLI commands for login, auth check, and cookie refresh.
"""

import subprocess
import json
import sys
from pathlib import Path

from unb_consultant.i18n import _


def _notebooklm_cmd(*args) -> subprocess.CompletedProcess:
    """Run a notebooklm command and return result."""
    # Try to find notebooklm in the same venv or PATH
    # The user has notebooklm-py installed globally or in PATH
    cmd = ["notebooklm"] + list(args)
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120
        )
    except FileNotFoundError:
        raise RuntimeError(
            "notebooklm not found in PATH. Install it: pipx install 'notebooklm-py[browser]'"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("notebooklm command timed out.")


def auth_check(test: bool = False) -> dict:
    """Check authentication status.
    
    Args:
        test: If True, makes a network call to verify cookies against Google.
    
    Returns:
        dict with status and check details.
    """
    cmd = ["auth", "check"]
    if test:
        cmd.append("--test")
    cmd.append("--json")

    result = _notebooklm_cmd(*cmd)
    if result.returncode != 0:
        return {
            "status": "error",
            "error": result.stderr.strip() or result.stdout.strip(),
        }

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "error": "Failed to parse notebooklm output"}


def login(browser_cookies: str | None = None) -> dict:
    """Authenticate with Google via browser.
    
    Args:
        browser_cookies: Browser name to extract cookies from 
                        (e.g., "chrome", "edge", "firefox").
                        If None, opens interactive Playwright browser.
    
    Returns:
        dict with login result.
    """
    print(_("auth_login_opening"))

    cmd = ["login"]
    if browser_cookies:
        cmd.extend(["--browser-cookies", browser_cookies])

    result = _notebooklm_cmd(*cmd)

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "Could not decrypt" in stderr:
            return {
                "status": "error",
                "error": "Could not decrypt browser cookies. Try interactive login: unb login",
            }
        return {"status": "error", "error": stderr or result.stdout.strip()}

    return {"status": "ok", "detail": result.stdout.strip()}


def refresh() -> dict:
    """Refresh authentication cookies.
    
    Returns:
        dict with refresh result.
    """
    print(_("auth_refreshing"))
    result = _notebooklm_cmd("auth", "refresh", "--json")

    if result.returncode != 0:
        return {"status": "error", "error": result.stderr.strip()}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "ok", "detail": "Refresh completed"}


_AUTH_PATTERNS = [
    "authentication expired",
    "redirected to: accounts.google.com",
    "not authenticated",
    "login to re-authenticate",
    "unexpected error: authentication",
]


def _is_auth_error(result: subprocess.CompletedProcess) -> bool:
    """Check if a notebooklm command failed due to authentication issues."""
    if result.returncode == 0:
        return False
    output = ((result.stderr or "") + (result.stdout or "")).lower()
    return any(p in output for p in _AUTH_PATTERNS)


_reauth_attempted = False


def _notebooklm_cmd_with_reauth(*args, max_retries: int = 1) -> subprocess.CompletedProcess:
    """Run a notebooklm command with automatic re-authentication on auth errors.
    
    On auth failure:
        1. Try auth refresh (silent cookie renewal)
        2. Try login with browser cookies (Chrome)
        3. If all fail, return the original error
    
    Uses a global flag to prevent infinite re-auth loops.
    """
    global _reauth_attempted

    result = _notebooklm_cmd(*args)

    if _is_auth_error(result) and max_retries > 0 and not _reauth_attempted:
        _reauth_attempted = True

        ref_result = refresh()
        if ref_result.get("status") == "ok":
            result = _notebooklm_cmd(*args)
            if not _is_auth_error(result):
                _reauth_attempted = False
                return result

        login_result = login(browser_cookies="chrome")
        if login_result.get("status") == "ok":
            result = _notebooklm_cmd(*args)
            if not _is_auth_error(result):
                _reauth_attempted = False
                return result

        _reauth_attempted = False

    return result
