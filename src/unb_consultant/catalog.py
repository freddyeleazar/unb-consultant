"""Thematic catalog generation for expert notebooks.

Uses NotebookLM itself to analyze all sources and produce
a thematic catalog table showing topic coverage and question types.
"""

import json
import tempfile
from pathlib import Path

from unb_consultant.auth import _notebooklm_cmd
from unb_consultant.config import get_config
from unb_consultant.i18n import _


CATALOG_PROMPT = """Analyze ALL sources in this notebook and produce a THEMATIC CATALOG.
For each major topic area, list:
1. Topic name
2. Approximate percentage of total content it represents
3. Number of source files covering it
4. Specific types of questions you can answer (be concrete: e.g., XML structure, API calls, scoring formulas)
5. Your confidence level (high/medium/low)

Output ONLY a markdown table with columns: Topic Name | % Content | Sources | Questions I Can Answer | Confidence
Do NOT include any introductory or concluding text."""


def generate_catalog(
    name: str,
    output_path: str | None = None,
    save_as_note: bool = True,
    yes: bool = False,
) -> dict:
    """Generate or update thematic catalog for an expert.
    
    Args:
        name: Expert name.
        output_path: If set, write catalog markdown to this file.
        save_as_note: If True, save catalog as a NotebookLM note.
        yes: Auto-confirm.
    
    Returns:
        dict with result.
    """
    config = get_config()
    expert = config.get_expert(name)
    if not expert:
        return {"status": "error", "error": _("expert_not_found", name=name)}

    notebook_id = expert.get("notebook_id", "")
    if not notebook_id:
        return {"status": "error", "error": "Expert has no notebook ID."}

    # Write prompt to temp file
    prompt_file = Path(tempfile.mktemp(suffix=".txt"))
    try:
        prompt_file.write_text(CATALOG_PROMPT, encoding="utf-8")
    except OSError as e:
        return {"status": "error", "error": f"Cannot write prompt file: {e}"}

    print(_("catalog_generating"))

    try:
        cmd = ["ask", "-n", notebook_id, "--prompt-file", str(prompt_file)]
        if save_as_note:
            cmd.extend(["--save-as-note", "--note-title", "Thematic Catalog"])
        cmd.append("--json")

        result = _notebooklm_cmd(*cmd)
    finally:
        prompt_file.unlink(missing_ok=True)

    if result.returncode != 0:
        return {"status": "error", "error": result.stderr.strip()}

    try:
        data = json.loads(result.stdout)
        catalog_text = data.get("answer", "")
        conversation_id = data.get("conversation_id", "")
    except json.JSONDecodeError:
        catalog_text = result.stdout.strip()
        conversation_id = ""

    if not catalog_text:
        return {"status": "error", "error": _("catalog_fail", reason="Empty response")}

    # Update config
    config.update_expert(name, {
        "catalog": {
            "generated_at": __import__("datetime").datetime.now().isoformat(),
            "conversation_id": conversation_id,
            "text": catalog_text[:500],  # Store preview
        }
    })

    print(_("catalog_ok"))

    # Write to file if requested
    if output_path:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(catalog_text, encoding="utf-8")
        print(_("catalog_saved", path=str(out)))

    return {
        "status": "ok",
        "catalog": catalog_text,
        "conversation_id": conversation_id,
    }
