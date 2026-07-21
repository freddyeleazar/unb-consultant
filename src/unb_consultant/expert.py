"""Expert lifecycle management for unb-consultant.

Create, list, and delete NotebookLM experts, managing source uploads
and registration in the local config.
"""

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from datetime import datetime

from unb_consultant.auth import _notebooklm_cmd, auth_check
from unb_consultant.config import get_config
from unb_consultant.i18n import _
from unb_consultant.merger import plan_merge, execute_merge, print_plan_summary
from unb_consultant.tier import detect_tier, cache_tier, get_source_limit, get_target_source_count


def create_expert(
    name: str,
    description: str = "",
    urls: list[str] | None = None,
    files: list[Path] | None = None,
    directory: Path | None = None,
    drive_docs: list[str] | None = None,
    auto: bool = False,
    dry_run: bool = False,
    force: bool = False,
    yes: bool = False,
) -> dict:
    """Create a new NotebookLM expert.
    
    Returns dict with creation result.
    """
    # Validate name
    import re
    if not re.match(r'^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$', name):
        return {"status": "error", "error": _("expert_name_invalid")}

    config = get_config()

    # Check duplicate
    existing = config.get_expert(name)
    if existing:
        if force:
            print(_("expert_force", name=name))
        else:
            return {"status": "error", "error": _("expert_name_taken", name=name)}

    # Detect tier (no network call)
    tier, limit = detect_tier()

    # Early return for dry-run (no auth needed)
    if dry_run:
        raw_files: list[Path] = []
        if files:
            for f_arg in files:
                p = Path(f_arg)
                if p.exists():
                    raw_files.append(p)
        if directory:
            d = Path(directory)
            if d.is_dir():
                for ext in ("*.md", "*.txt", "*.pdf", "*.rst"):
                    raw_files.extend(sorted(d.glob(ext)))
                raw_files = list(dict.fromkeys(raw_files))
        if raw_files:
            from unb_consultant.merger import plan_merge, print_plan_summary
            target = get_target_source_count()
            url_count = len(urls) if urls else 0
            file_target = max(1, target - url_count)
            plan = plan_merge(raw_files, target_count=file_target, tier_limit=limit)
            print_plan_summary(plan)
        else:
            print("Dry-run: no local files to merge. URLs will be uploaded directly.")
            print(f"Tier: {tier.upper()} ({limit} sources limit)")
        return {"status": "dry_run", "plan": str(plan) if raw_files else "urls-only"}

    # Auth check
    print(_("auth_checking"))
    check = auth_check(test=True)
    if check.get("status") != "ok" or not check.get("checks", {}).get("token_fetch"):
        return {"status": "error", "error": _("auth_expired")}

    print(format_tier_info())
    print()

    # Collect raw files
    raw_files: list[Path] = []
    if files:
        for f in files:
            p = Path(f)
            if p.exists():
                raw_files.append(p)
            else:
                print(f"  [!] {_('not_found', item=str(p))}")

    if directory:
        for ext in ("*.md", "*.txt", "*.pdf", "*.rst"):
            raw_files.extend(sorted(Path(directory).glob(ext)))
        raw_files = list(dict.fromkeys(raw_files))  # deduplicate

    if urls:
        pass  # URLs are uploaded directly, not merged

    # Plan merging for local files
    merged_dir = None
    all_sources: list[dict] = []  # Will hold (source_type, source_value)

    if raw_files:
        target = get_target_source_count()
        # Calculate how many URL slots we need
        url_count = len(urls) if urls else 0
        file_target = target - url_count
        if file_target < 1:
            file_target = 1

        plan = plan_merge(raw_files, target_count=file_target, tier_limit=limit)

        print(_("tier_limit_used",
                pct=int(plan.merged_count / limit * 100),
                used=plan.merged_count + url_count,
                limit=limit,
                free=limit - plan.merged_count - url_count))
        print()

        if not yes and not auto:
            print_plan_summary(plan)
            resp = input(_("proceed")).strip().lower()
            if resp not in ("y", "yes"):
                print(_("aborted"))
                return {"status": "aborted"}

        # Execute merge
        merged_dir = Path(tempfile.mkdtemp(prefix=f"unb_{name}_"))
        written = execute_merge(plan, merged_dir)
        for wp in written:
            all_sources.append({"type": "file", "value": str(wp)})
    else:
        # No local files, just URLs will be added
        pass

    # Add URLs as sources
    if urls:
        for u in urls:
            all_sources.append({"type": "url", "value": u})

    # Add drive docs
    if drive_docs:
        for d in drive_docs:
            all_sources.append({"type": "drive_doc", "value": d})

    # Create notebook
    print(_("expert_creating", name=name))
    result = _notebooklm_cmd("create", name, "--json")
    if result.returncode != 0:
        if merged_dir:
            shutil.rmtree(merged_dir, ignore_errors=True)
        return {"status": "error", "error": result.stderr.strip() or result.stdout.strip()}

    try:
        create_data = json.loads(result.stdout)
        notebook_id = create_data.get("notebook", {}).get("id", "")
    except json.JSONDecodeError:
        if merged_dir:
            shutil.rmtree(merged_dir, ignore_errors=True)
        return {"status": "error", "error": "Failed to parse notebook creation response"}

    # Set context
    _notebooklm_cmd("use", notebook_id)

    # Upload sources
    uploaded_sources = []
    failed_sources = []

    print(_("sources_uploading", count=len(all_sources)))

    for i, src in enumerate(all_sources):
        label = f"[{i+1}/{len(all_sources)}]"
        if src["type"] == "file":
            print(f"  {label} {Path(src['value']).name}... ", end="", flush=True)
            r = _notebooklm_cmd("source", "add", src["value"], "--json")
        elif src["type"] == "url":
            print(f"  {label} {src['value'][:60]}... ", end="", flush=True)
            r = _notebooklm_cmd("source", "add", src["value"], "--json")
        elif src["type"] == "drive_doc":
            print(f"  {label} Drive doc... ", end="", flush=True)
            r = _notebooklm_cmd("source", "add-drive", src["value"], "--json")

        if r and r.returncode == 0:
            try:
                sd = json.loads(r.stdout)
                sid = sd.get("source", {}).get("id", "?")
                print(f"OK ({sid[:8]})")
                uploaded_sources.append({"id": sid, "type": src["type"], "value": src["value"]})
            except json.JSONDecodeError:
                print("OK")
                uploaded_sources.append({"id": "?", "type": src["type"], "value": src["value"]})
        else:
            err = (r.stderr.strip() or r.stdout.strip() or "Unknown error")[:80] if r else "No response"
            print(f"FAILED: {err}")
            failed_sources.append({"type": src["type"], "value": src["value"], "error": err})

        time.sleep(0.5)  # Rate limiting

    # Wait for sources to be indexed
    if uploaded_sources:
        print(_("sources_waiting"))
        _wait_for_sources(notebook_id, timeout=600)
        print(_("sources_ready"))

    # Register in config
    expert_data = {
        "notebook_id": notebook_id,
        "title": name,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "tier": tier,
        "sources": uploaded_sources,
        "sources_failed": failed_sources,
        "sources_count": len(uploaded_sources),
        "catalog": {"generated_at": None, "note_id": None},
    }

    if force and existing:
        config.update_expert(name, expert_data)
    else:
        config.add_expert(name, expert_data)

    # Cleanup temp directory
    if merged_dir:
        shutil.rmtree(merged_dir, ignore_errors=True)

    result_data = {
        "status": "ok",
        "expert": name,
        "notebook_id": notebook_id,
        "sources_uploaded": len(uploaded_sources),
        "sources_failed": len(failed_sources),
    }

    if not auto:
        result_data["suggested_next_steps"] = [
            {
                "tool": "catalog",
                "command": f'unb catalog "{name}"',
                "description": _("suggest_catalog"),
            },
            {
                "tool": "skill-gen",
                "command": f'unb skill-gen "{name}"',
                "description": _("suggest_skill_gen"),
            },
        ]

    print()
    print(_("expert_created", name=name))
    print(_("expert_notebook", id=notebook_id))
    print(_("sources_ok", ok=len(uploaded_sources), total=len(all_sources)))
    if failed_sources:
        print(_("sources_fail", fail=len(failed_sources)))
        for fs in failed_sources:
            print(f"  - {fs.get('value', '?')}: {fs.get('error', '?')}")

    return result_data


def list_experts() -> list[dict]:
    """List all registered experts.
    
    Returns list of expert dicts.
    """
    config = get_config()
    experts = config.list_experts()
    result = []
    for name, data in sorted(experts.items()):
        result.append({
            "name": name,
            "notebook_id": data.get("notebook_id", ""),
            "description": data.get("description", ""),
            "sources": data.get("sources_count", 0),
            "created_at": data.get("created_at", ""),
            "catalog": data.get("catalog", {}).get("generated_at"),
        })
    return result


def delete_expert(name: str, yes: bool = False) -> dict:
    """Delete an expert and its notebook.
    
    Returns dict with deletion result.
    """
    config = get_config()
    expert = config.get_expert(name)
    if not expert:
        return {"status": "error", "error": _("expert_not_found", name=name)}

    if not yes:
        resp = input(_("expert_delete_confirm", name=name)).strip().lower()
        if resp not in ("y", "yes"):
            return {"status": "aborted"}

    # Delete notebook from Google
    notebook_id = expert.get("notebook_id", "")
    if notebook_id:
        r = _notebooklm_cmd("delete", "-n", notebook_id, "--yes")
        if r.returncode != 0:
            print(f"  [!] {r.stderr.strip()}")

    # Remove from config
    config.remove_expert(name)

    return {"status": "ok", "message": _("expert_deleted", name=name)}


def _wait_for_sources(notebook_id: str, timeout: int = 600, poll_interval: int = 5):
    """Wait for all sources in a notebook to be ready."""
    import time as _time
    start = _time.time()
    while _time.time() - start < timeout:
        r = _notebooklm_cmd("source", "list", "-n", notebook_id, "--json")
        if r.returncode == 0:
            try:
                data = json.loads(r.stdout)
                sources = data.get("sources", [])
                if all(s.get("status") == "ready" for s in sources):
                    return True
                processing = sum(1 for s in sources if s.get("status") != "ready")
                if processing > 0:
                    pass  # Still waiting
            except json.JSONDecodeError:
                pass
        _time.sleep(poll_interval)
    return False  # Timeout


def format_expert_table(experts: list[dict]) -> str:
    """Format experts list as a table string."""
    if not experts:
        return _("expert_list_empty")

    lines = []
    lines.append("")
    lines.append(f"  {'Name':<25} {'Sources':>8} {'Tier':<8} {'Created':<20}")
    lines.append(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*20}")

    for exp in experts:
        name = exp["name"]
        src = str(exp.get("sources", 0))
        tier = exp.get("tier", "?")
        created = (exp.get("created_at", "") or "")[:10]
        lines.append(f"  {name:<25} {src:>8} {tier:<8} {created:<20}")

    lines.append("")
    return "\n".join(lines)


def format_tier_info() -> str:
    """Return tier info string."""
    from unb_consultant.tier import detect_tier
    tier, limit = detect_tier()
    target = get_target_source_count()
    return (
        _("tier_detected", tier=tier.upper(), limit=limit) + "\n" +
        _("merger_target", target=target, pct=int(80), limit=limit)
    )


def adopt_expert(
    notebook_id: str,
    name: str,
    description: str = "",
    force: bool = False,
) -> dict:
    """Register an existing NotebookLM notebook as an unb expert.
    
    Args:
        notebook_id: Existing NotebookLM notebook ID.
        name: Name to register as.
        description: Optional description.
        force: Overwrite if name already exists.
    
    Returns dict with result.
    """
    import re
    if not re.match(r'^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$', name):
        return {"status": "error", "error": _("expert_name_invalid")}

    config = get_config()

    existing = config.get_expert(name)
    if existing and not force:
        return {"status": "error", "error": _("expert_name_taken", name=name)}

    # Get source count from notebook
    tier, limit = detect_tier()
    sources_count = 0

    r = _notebooklm_cmd("source", "list", "-n", notebook_id, "--json")
    if r.returncode == 0:
        try:
            data = json.loads(r.stdout)
            sources_count = len(data.get("sources", []))
        except json.JSONDecodeError:
            pass

    expert_data = {
        "notebook_id": notebook_id,
        "title": name,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "tier": tier,
        "sources": [],
        "sources_count": sources_count,
        "catalog": {"generated_at": None, "note_id": None},
        "adopted": True,
    }

    if force and existing:
        config.update_expert(name, expert_data)
    else:
        config.add_expert(name, expert_data)

    print(_("expert_created", name=name))
    print(_("expert_notebook", id=notebook_id))

    return {
        "status": "ok",
        "expert": name,
        "notebook_id": notebook_id,
        "sources_count": sources_count,
    }
