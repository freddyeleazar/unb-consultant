"""Source management for existing experts.

Add individual files, URLs, directories, or Drive documents
to an already-created NotebookLM expert.
"""

import json
import os
import re
import time
from pathlib import Path

from unb_consultant.auth import _notebooklm_cmd, auth_check
from unb_consultant.config import get_config
from unb_consultant.i18n import _
from unb_consultant.page_scraper import scrape_page_sync_with_fallback
from unb_consultant.tier import get_source_limit


def add_sources(
    expert_name: str,
    urls: list[str] | None = None,
    files: list[Path] | None = None,
    directory: Path | None = None,
    drive_docs: list[str] | None = None,
    yes: bool = False,
    no_scrape: bool = False,
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
    scrape_failed_urls = []

    for i, src in enumerate(to_add):
        label = f"[{i+1}/{len(to_add)}]"
        if src["type"] == "file":
            print(f"  {label} {Path(src['value']).name}... ", end="", flush=True)
            r = _notebooklm_cmd("source", "add", "-n", notebook_id, src["value"], "--json")
        elif src["type"] == "url":
            url_val = src["value"]
            short_url = url_val[:60]
            if no_scrape:
                print(f"  {label} {short_url}... ", end="", flush=True)
                r = _notebooklm_cmd("source", "add", "-n", notebook_id, url_val, "--json")
            else:
                print(f"  {label} {short_url}... ", end="", flush=True)
                text, pdf, used_fallback = scrape_page_sync_with_fallback(url_val)

                if text:
                    text_prefix = f"page_{re.sub(r'[^a-zA-Z0-9]+', '_', url_val[:40])}"
                    r_text = _notebooklm_cmd("source", "add", "-n", notebook_id,
                                             "--type", "text", "--title", text_prefix,
                                             text, "--json")
                    if r_text and r_text.returncode == 0:
                        try:
                            sd = json.loads(r_text.stdout)
                            sid = sd.get("source", {}).get("id", "?")
                            print(f"TEXT OK ({sid[:8]})", end="")
                            uploaded.append({"id": sid, "type": "scraped_text", "value": url_val})
                        except json.JSONDecodeError:
                            print("TEXT OK", end="")
                            uploaded.append({"id": "?", "type": "scraped_text", "value": url_val})
                    else:
                        print("TEXT FAILED", end="")

                    if pdf:
                        r_pdf = _notebooklm_cmd("source", "add", "-n", notebook_id, pdf, "--json")
                        try:
                            os.remove(pdf)
                        except Exception:
                            pass
                        if r_pdf and r_pdf.returncode == 0:
                            try:
                                sd = json.loads(r_pdf.stdout)
                                sid = sd.get("source", {}).get("id", "?")
                                print(f" + PDF OK ({sid[:8]})")
                                uploaded.append({"id": sid, "type": "scraped_pdf", "value": url_val})
                            except json.JSONDecodeError:
                                print(" + PDF OK")
                                uploaded.append({"id": "?", "type": "scraped_pdf", "value": url_val})
                        else:
                            print(" + PDF FAILED")
                    else:
                        print()
                elif used_fallback:
                    print(f"  {label} {short_url}... SCRAPE FAILED, adding directly... ", end="", flush=True)
                    r = _notebooklm_cmd("source", "add", "-n", notebook_id, url_val, "--json")
                    scrape_failed_urls.append(url_val)
        elif src["type"] == "drive_doc":
            print(f"  {label} Drive doc... ", end="", flush=True)
            r = _notebooklm_cmd("source", "add-drive", "-n", notebook_id, src["value"], "--json")

        if src["type"] != "url" or no_scrape:
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

    if scrape_failed_urls:
        print()
        print("[!] The following URLs could not be scraped and were added directly:")
        for u in scrape_failed_urls:
            print(f"  - {u}")

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
