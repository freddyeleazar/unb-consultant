"""Tier detection for NotebookLM subscription.

Detects the user's NotebookLM subscription tier to determine
the maximum number of sources per notebook.
"""

import json
import re
from typing import Literal

from unb_consultant.auth import _notebooklm_cmd
from unb_consultant.config import get_config
from unb_consultant.i18n import _

TierName = Literal["standard", "plus", "pro", "ultra"]

TIER_LIMITS: dict[TierName, int] = {
    "standard": 50,
    "plus": 100,
    "pro": 300,
    "ultra": 600,
}

DEFAULT_TIER: TierName = "standard"
TARGET_USAGE = 0.80  # Use 80% of tier limit by default


def detect_tier() -> tuple[TierName, int]:
    """Detect the NotebookLM subscription tier (in-memory only).

    Sets the tier in the config's in-memory cache but does NOT persist
    to disk. Use cache_tier() to persist explicitly.

    Tries, in order:
    1. Config file (cached value)
    2. AccountLimits.tier from notebooklm-py API
    3. UNB_NOTEBOOKLM_TIER env var
    4. Fallback to Standard (50)

    Returns:
        Tuple of (tier_name, source_limit)
    """
    config = get_config()

    # 1. Check config cache
    cached = config.tier
    if cached and cached.lower() in TIER_LIMITS:
        tier = cached.lower()
        return tier, TIER_LIMITS[tier]

    # 2. Try to detect via notebooklm-py (in-memory only, no disk write)
    try:
        result = _notebooklm_cmd("metadata", "--json")
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for key in ["tier", "plan", "account_tier", "limits"]:
                val = data.get(key)
                if val:
                    tier_name = str(val).lower().strip()
                    if tier_name in TIER_LIMITS:
                        config.tier = tier_name  # in-memory only
                        return tier_name, TIER_LIMITS[tier_name]
                    for tn, limit in TIER_LIMITS.items():
                        if str(limit) in str(val):
                            config.tier = tn  # in-memory only
                            return tn, limit
    except Exception:
        pass

    # 3. Check env var
    import os
    env_tier = os.environ.get("UNB_NOTEBOOKLM_TIER", "").lower()
    if env_tier in TIER_LIMITS:
        config.tier = env_tier  # in-memory only
        return env_tier, TIER_LIMITS[env_tier]

    # 4. Fallback
    return DEFAULT_TIER, TIER_LIMITS[DEFAULT_TIER]


def cache_tier() -> tuple[TierName, int]:
    """Detect the NotebookLM subscription tier AND persist to disk.

    Unlike detect_tier(), this explicitly persists the detected tier
    to disk. Use this only when creating/updating experts, NOT in
    read-only commands like 'expert list', 'tier', or 'setup'.
    
    Returns:
        Tuple of (tier_name, source_limit)
    """
    tier_name, limit = detect_tier()
    config = get_config()
    config.persist_tier(tier_name)
    return tier_name, limit


def get_source_limit() -> int:
    """Get the maximum number of sources per notebook."""
    _, limit = detect_tier()
    return limit


def get_target_source_count() -> int:
    """Get the recommended target source count (80% of limit)."""
    limit = get_source_limit()
    return int(limit * TARGET_USAGE)


def format_tier_info() -> str:
    """Return a human-readable tier info string."""
    tier, limit = detect_tier()
    target = get_target_source_count()
    return _("tier_detected", tier=tier.upper(), limit=limit) + "\n" + \
           _("merger_target", target=target, pct=int(TARGET_USAGE * 100), limit=limit)
