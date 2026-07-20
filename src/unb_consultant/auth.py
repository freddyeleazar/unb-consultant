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
