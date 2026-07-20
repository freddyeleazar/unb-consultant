"""Source management for existing experts.

Add individual files, URLs, directories, or Drive documents
to an already-created NotebookLM expert.
"""

import json
import time
from pathlib import Path

from unb_consultant.auth import _notebooklm_cmd, auth_check
from unb_consultant.config import get_config
from unb_consultant.i18n import _
from unb_consultant.tier import get_source_limit


def add_sources(
    expert_name: str,
    urls: list[str] | None = None,
    files: list[Path] | None = None,
    directory: Path | None = None,
    drive_docs: list[str] | None = None,
    yes: bool = False,
) -> dict:
    """Add sources to an existing expert.
    
    Returns dict with result.
    """
    config = get_config()
    expert = config.get_expert(expert_name)
    if not expert:
        return {"status": "error", "error": _("expert_not_found", name=expert_name)}

    notebook_id = expert.get("notebook_id", "")
    if not notebook_id:
        return {"status": "error", "error": "Expert has no notebook ID."}

    # Auth check
    check = auth_check(test=True)
    if check.get("status") != "ok" or not check.get("checks", {}).get("token_fetch"):
        return {"status": "error", "error": _("auth_expired")}

    # Collect sources to add
    to_add = []
    if urls:
        for u in urls:
            to_add.append({"type": "url", "value": u})
    if files:
        for f in files:
            p = Path(f)
            if p.exists():
                to_add.append({"type": "file", "value": str(p)})
            else:
                print(f"  [!] {_('not_found', item=str(p))}")
    if directory:
        d = Path(directory)
        if d.is_dir():
            for ext in ("*.md", "*.txt", "*.pdf", "*.rst"):
                for fp in sorted(d.glob(ext)):
                    to_add.append({"type": "file", "value": str(fp)})
        else:
            print(f"  [!] {_('not_found', item=str(d))}")
    if drive_docs:
        for doc_id in drive_docs:
            to_add.append({"type": "drive_doc", "value": doc_id})

    if not to_add:
        return {"status": "error", "error": "No sources to add."}

    # Check tier limit
    limit = get_source_limit()
    current_count = expert.get("sources_count", 0)
    if current_count + len(to_add) > limit:
        print(_("sources_limit_warn",
                limit=limit, current=current_count, adding=len(to_add)))
        if not yes:
            resp = input(_("proceed")).strip().lower()
            if resp not in ("y", "yes"):
                return {"status": "aborted"}

    # Upload
    print(_("sources_uploading", count=len(to_add)))
    uploaded = []
    failed = []

    for i, src in enumerate(to_add):
        label = f"[{i+1}/{len(to_add)}]"
        if src["type"] == "file":
            print(f"  {label} {Path(src['value']).name}... ", end="", flush=True)
            r = _notebooklm_cmd("source", "add", "-n", notebook_id, src["value"], "--json")
        elif src["type"] == "url":
            print(f"  {label} {src['value'][:60]}... ", end="", flush=True)
            r = _notebooklm_cmd("source", "add", "-n", notebook_id, src["value"], "--json")
        elif src["type"] == "drive_doc":
            print(f"  {label} Drive doc... ", end="", flush=True)
            r = _notebooklm_cmd("source", "add-drive", "-n", notebook_id, src["value"], "--json")

        if r and r.returncode == 0:
            try:
                sd = json.loads(r.stdout)
                sid = sd.get("source", {}).get("id", "?")
                print(f"OK ({sid[:8]})")
                uploaded.append({"id": sid, "type": src["type"], "value": src["value"]})
            except json.JSONDecodeError:
                print("OK")
                uploaded.append({"id": "?", "type": src["type"], "value": src["value"]})
        else:
            err = (r.stderr.strip() or r.stdout.strip() or "Unknown error")[:80] if r else "No response"
            print(f"FAILED: {err}")
            failed.append({"type": src["type"], "value": src["value"], "error": err})

        time.sleep(0.5)

    # Update config
    existing_sources = expert.get("sources", [])
    existing_sources.extend(uploaded)
    config.update_expert(expert_name, {
        "sources": existing_sources,
        "sources_count": len(existing_sources),
        "sources_failed": expert.get("sources_failed", []) + failed,
    })

    print()
    print(_("sources_ok", ok=len(uploaded), total=len(to_add)))
    if failed:
        print(_("sources_fail", fail=len(failed)))
        for fs in failed:
            print(f"  - {fs.get('value', '?')}: {fs.get('error', '?')}")

    return {
        "status": "ok",
        "uploaded": len(uploaded),
        "failed": len(failed),
    }
