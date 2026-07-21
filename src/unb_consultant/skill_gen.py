"""Skill generation for unb-consultant.

Generates SKILL.md files and AGENTS.md snippets for integrating
an expert into an AI agent project. Detects project structure
to avoid overwriting existing files and avoid redundancy.
"""

from pathlib import Path
from datetime import datetime

from unb_consultant.config import get_config, Config
from unb_consultant.i18n import _
from unb_consultant.tier import detect_tier

# ─── Project structure detection ───

SKILL_DIRS = [
    (".opencode/skills", "opencode"),
    (".claude/skills", "claude"),
    (".agents/skills", "agents"),
]


def detect_project_structure(path: str | Path = ".") -> dict:
    """Detect the agent skill structure in a project directory.
    
    Returns:
        dict with:
        - skills_dir: Path | None
        - agent_type: str | None
        - has_agents_md: bool
        - existing_skills: list of dicts with name, notebook_id
    """
    project = Path(path).resolve()

    skills_dir = None
    agent_type = None

    for dirname, atype in SKILL_DIRS:
        candidate = project / dirname
        if candidate.is_dir():
            skills_dir = candidate
            agent_type = atype
            break

    # Check for AGENTS.md
    agents_md = project / "AGENTS.md"
    has_agents_md = agents_md.is_file()

    # Scan existing skills for notebook references
    existing_skills = []
    if skills_dir:
        for skill_path in skills_dir.iterdir():
            if skill_path.is_dir():
                md_file = skill_path / "SKILL.md"
            elif skill_path.name == "SKILL.md":
                md_file = skill_path
            else:
                continue
            if md_file.is_file():
                info = _parse_skill_metadata(md_file)
                if info:
                    existing_skills.append(info)

    return {
        "skills_dir": skills_dir,
        "agent_type": agent_type,
        "has_agents_md": has_agents_md,
        "agents_md_path": agents_md if has_agents_md else None,
        "existing_skills": existing_skills,
    }


def _parse_skill_metadata(path: Path) -> dict | None:
    """Extract expert name and notebook_id from a SKILL.md file."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    name = None
    notebook_id = None
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("## Notebook ID"):
            continue
        if line.startswith("`") and len(line) > 10 and "-" in line:
            # Could be a notebook ID in backticks
            candidate = line.strip("`").strip()
            if len(candidate) > 20 and "-" in candidate:
                notebook_id = candidate
        if line.startswith("# ") and "Expert" in line:
            name = line[2:].replace(" Expert", "").strip().lower()

    if name or notebook_id:
        return {"name": name, "notebook_id": notebook_id, "path": str(path)}
    return None


def _check_skill_conflict(
    expert_name: str,
    notebook_id: str,
    structure: dict,
) -> str:
    """Check if a skill already exists for this expert.
    
    Returns one of:
    - "no_conflict": No existing skill for this expert.
    - "same_expert": Skill exists with same notebook_id.
    - "different_expert": Skill exists with different notebook_id.
    """
    for existing in structure.get("existing_skills", []):
        if existing.get("name") == expert_name:
            if existing.get("notebook_id") == notebook_id:
                return "same_expert"
            return "different_expert"
    return "no_conflict"


_SKILL_TEMPLATE = """---
name: unb-{name}
description: >
  NotebookLM expert for {description}.
  Ответы с цитатами из источников.
  Создан через unb-consultant.
---

# {title}

## Notebook ID
`{notebook_id}`

## Thematic Catalog
{catalog}

## Protocol
- Only act when the user explicitly asks.
- Query: `unb ask "{name}" "<question>" [--json]`
- Auth check before querying: `unb auth check --test --json`
- If auth fails: `unb auth refresh`
"""

_AGENTS_SNIPPET = """
## {title} Expert (NotebookLM)
For {description} questions with cited answers:
```powershell
unb ask "{name}" "<question>" [--json]
```
Skill: `.opencode/skills/unb-{name}/SKILL.md`
"""


def generate_skill(
    name: str,
    output_path: str | None = None,
    auto: bool = False,
    no_agents: bool = False,
    dry_run: bool = False,
    update: bool = False,
    project_path: str | None = None,
) -> dict:
    """Generate a SKILL.md file for an expert.
    
    Detects project structure and handles conflicts.
    
    Args:
        project_path: Project root directory for skill creation.
                      Defaults to current directory.
    """
    config = get_config()
    expert = config.get_expert(name)
    if not expert:
        return {"status": "error", "error": _("expert_not_found", name=name)}

    notebook_id = expert.get("notebook_id", "")
    description = expert.get("description", name)
    catalog_text = expert.get("catalog", {}).get("text", "*No catalog generated yet. Run 'unb catalog' first.*")

    title = name.replace("-", " ").title()

    # Determine output location
    if output_path:
        skill_path = Path(output_path)
    else:
        # Auto-detect project structure
        print(_("skill_detecting"))
        structure = detect_project_structure(path=project_path or ".")

        if not structure["skills_dir"]:
            if dry_run:
                return {"status": "dry_run",
                        "message": f"Would create .opencode/skills/{name}/SKILL.md"}

            if not auto:
                resp = input(_("skill_no_structure")).strip().lower()
                if resp not in ("y", "yes"):
                    return {"status": "aborted"}
            structure["skills_dir"] = Path(".opencode/skills")
            structure["skills_dir"].mkdir(parents=True, exist_ok=True)

        skill_path = structure["skills_dir"] / f"unb-{name}" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)

        # Check conflicts
        if skill_path.exists():
            conflict = _check_skill_conflict(name, notebook_id, structure)
            if conflict == "same_expert":
                if dry_run:
                    return {"status": "dry_run",
                            "message": _("skill_exists_same")}
                if not update:
                    return {"status": "ok", "message": _("skill_exists_same")}
            elif conflict == "different_expert":
                if not auto:
                    resp = input(_("skill_exists_diff")).strip().lower()
                    if resp not in ("y", "yes"):
                        return {"status": "aborted"}
                # Fall through to overwrite

        # Handle AGENTS.md
        if not no_agents and structure.get("agents_md_path"):
            agents_path = structure["agents_md_path"]
            print(_("skill_agents_found"))
            _inject_into_agents(
                agents_path,
                name,
                title,
                description,
                dry_run=dry_run,
            )

    # Generate SKILL.md content
    content = _SKILL_TEMPLATE.format(
        name=name,
        description=description,
        title=title,
        notebook_id=notebook_id,
        catalog=catalog_text,
    )

    if dry_run:
        return {
            "status": "dry_run",
            "path": str(skill_path),
            "content": content,
        }

    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(content, encoding="utf-8")
    print(_("skill_created", path=str(skill_path)))

    return {
        "status": "ok",
        "path": str(skill_path),
    }


def _inject_into_agents(
    agents_path: Path,
    name: str,
    title: str,
    description: str,
    dry_run: bool = False,
):
    """Add or update an AGENTS.md entry for an expert.
    
    Avoids duplicate entries by checking for existing block.
    """
    try:
        content = agents_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        print(_("skill_agents_not_found"))
        return

    block_header = f"## {title} Expert (NotebookLM)"
    if block_header in content:
        print(_("skill_agents_entry_exists"))
        return

    snippet = _AGENTS_SNIPPET.format(
        name=name,
        title=title,
        description=description,
    )

    if dry_run:
        print(f"  Would append to {agents_path}:")
        print(snippet)
        return

    # Append to end of file
    with open(agents_path, "a", encoding="utf-8") as f:
        f.write(snippet)

    print(_("skill_agents_entry_added"))
