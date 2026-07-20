"""Project initialization for unb-consultant.

Sets up a project to use unb-consultant by creating the necessary
skill files and AGENTS.md entries. This is the fallback for models
that do not support MCP tools.
"""

from pathlib import Path

from unb_consultant.i18n import _
from unb_consultant.skill_gen import detect_project_structure
from unb_consultant.config import get_config

UNB_SKILL_CONTENT = """---
name: unb-consultant
description: >
  Universal NotebookLM-Based Consultant. Create and query AI experts
  via NotebookLM (Gemini Notebook). Use CLI commands directly.
---

# unb-consultant

CLI tool for creating and querying NotebookLM (Gemini Notebook) experts.

## Commands

| Action | Command |
|--------|---------|
| List experts | `unb expert list` |
| Ask expert | `unb ask "<name>" "<question>" [--json]` |
| Create expert | `unb expert create "<name>" --url "..." [--file ...] [--auto]` |
| Delete expert | `unb expert delete "<name>" [--yes]` |
| Suggest domains | `unb suggest <keyword> [<keyword> ...]` |
| Generate catalog | `unb catalog "<name>" [--output ./catalog.md]` |
| Generate skill | `unb skill-gen "<name>" [--auto]` |
| Add sources | `unb source add "<name>" --url "..." [--file ...] [--directory ...]` |
| Auth check | `unb auth check --test --json` |
| Refresh auth | `unb auth refresh` |
| Login | `unb login` |
| Init project | `unb init [--auto]` |

## Protocol

- When the user asks to list, query, create, or manage experts, use the
  commands above via the bash tool.
- Prefer `unb ask` with `--json` for answers with source citations.
- NEVER execute destructive commands (delete, overwrite) without user
  confirmation.
- If a command fails with auth errors, suggest `unb auth refresh`.
"""


AGENTS_UNB_BLOCK_HEADER = "## unb-consultant (NotebookLM Expert)"

AGENTS_UNB_BLOCK = f"""
{AGENTS_UNB_BLOCK_HEADER}

Available CLI commands (for models without MCP support):

| Task | Command |
|------|---------|
| List experts | `unb expert list` |
| Ask expert | `unb ask "<name>" "<question>"` |
| Create expert | `unb expert create "<name>" --url "..."` |
| Suggest domain | `unb suggest <keyword>` |

{{skills_list}}
The file `.opencode/skills/unb-consultant/SKILL.md` has the full reference.
"""


def _get_skills_list() -> str:
    """Get formatted list of skill directories for experts in config."""
    config = get_config()
    experts = config.list_experts()
    if not experts:
        return ""
    lines = []
    lines.append("\n### Skills disponibles en este proyecto\n")
    for name in sorted(experts.keys()):
        lines.append(f"- `unb-{name}` -- experto en `{name}`")
    lines.append("")
    return "\n".join(lines)


def _agents_block_with_skills() -> str:
    """Generate the AGENTS.md block with current skills list."""
    skills = _get_skills_list()
    return AGENTS_UNB_BLOCK.format(skills_list=skills)


def init_project(
    path: str | None = None,
    auto: bool = False,
    dry_run: bool = False,
) -> dict:
    """Initialize a project to use unb-consultant.
    
    Creates skill files and AGENTS.md entries so that agents without
    MCP support can discover and use unb-consultant commands.
    
    Args:
        path: Project directory. Defaults to current directory.
        auto: Auto-confirm all decisions.
        dry_run: Preview what would be done without writing files.
    
    Returns:
        dict with result.
    """
    project = Path(path or ".").resolve()
    print(f"Initializing unb-consultant in: {project}")
    print()

    structure = detect_project_structure(str(project))
    actions = []

    # ─── Step 1: Ensure skills directory exists ───
    if structure["skills_dir"]:
        skills_base = structure["skills_dir"]
    else:
        skills_base = project / ".opencode" / "skills"
        if not dry_run:
            if not auto:
                resp = input(_("skill_no_structure")).strip().lower()
                if resp not in ("y", "yes"):
                    return {"status": "aborted"}
            skills_base.mkdir(parents=True, exist_ok=True)
        actions.append(f"Create {skills_base}")

    # ─── Step 2: Write SKILL.md ───
    skill_dir = skills_base / "unb-consultant"
    skill_path = skill_dir / "SKILL.md"

    if skill_path.exists():
        if dry_run:
            actions.append(f"Would update {skill_path} (exists)")
        else:
            if not auto:
                resp = input(f"  {skill_path} already exists. Overwrite? [y/N] ").strip().lower()
                if resp not in ("y", "yes"):
                    print("  Skipped SKILL.md")
                else:
                    skill_dir.mkdir(parents=True, exist_ok=True)
                    skill_path.write_text(UNB_SKILL_CONTENT, encoding="utf-8")
                    actions.append(f"Updated {skill_path}")
            else:
                skill_dir.mkdir(parents=True, exist_ok=True)
                skill_path.write_text(UNB_SKILL_CONTENT, encoding="utf-8")
                actions.append(f"Updated {skill_path}")
    else:
        if dry_run:
            actions.append(f"Would create {skill_path}")
        else:
            skill_dir.mkdir(parents=True, exist_ok=True)
            skill_path.write_text(UNB_SKILL_CONTENT, encoding="utf-8")
            actions.append(f"Created {skill_path}")

    # ─── Step 3: Handle AGENTS.md ───
    agents_path = project / "AGENTS.md"
    block_content = _agents_block_with_skills()

    if agents_path.exists():
        content = agents_path.read_text(encoding="utf-8", errors="replace")
        if AGENTS_UNB_BLOCK_HEADER in content:
            actions.append("AGENTS.md already has unb-consultant block. Skipping.")
        else:
            if dry_run:
                actions.append(f"Would append unb-consultant block to {agents_path}")
            else:
                with open(agents_path, "a", encoding="utf-8") as f:
                    f.write(block_content)
                actions.append(f"Appended unb-consultant block to {agents_path}")
    else:
        if dry_run:
            actions.append(f"Would create {agents_path} with unb-consultant instructions")
        else:
            if not auto:
                resp = input(_("skill_agents_not_found")).strip().lower()
                if resp not in ("y", "yes"):
                    print("  Skipped AGENTS.md")
                else:
                    agents_path.write_text(
                        "# Project Setup\n" + block_content,
                        encoding="utf-8",
                    )
                    actions.append(f"Created {agents_path}")
            else:
                agents_path.write_text(
                    "# Project Setup\n" + block_content,
                    encoding="utf-8",
                )
                actions.append(f"Created {agents_path}")

    # ─── Step 4: Offer catalog/skill-gen for registered experts ───
    if not dry_run and not auto:
        config = get_config()
        experts = config.list_experts()
        if experts:
            expert_names = list(experts.keys())
            print(f"\nFound registered expert(s): {', '.join(expert_names)}")
            resp = input("  Generate catalog and local skill for these experts? [y/N] ").strip().lower()
            if resp in ("y", "yes"):
                for ename in expert_names:
                    print(f"\n  Processing '{ename}'...")
                    # Generate catalog
                    print(f"    Catalog... ", end="", flush=True)
                    from unb_consultant.catalog import generate_catalog
                    cat_result = generate_catalog(name=ename)
                    if cat_result.get("status") == "ok":
                        print("OK")
                        actions.append(f"Generated catalog for '{ename}'")
                    else:
                        print(f"FAILED: {cat_result.get('error', 'Unknown error')}")
                        return {"status": "error", "error": f"Catalog generation failed for '{ename}': {cat_result.get('error', 'Unknown')}"}

                    # Generate skill
                    print(f"    Skill... ", end="", flush=True)
                    from unb_consultant.skill_gen import generate_skill
                    skill_result = generate_skill(name=ename, auto=True)
                    if skill_result.get("status") == "ok":
                        print("OK")
                        actions.append(f"Generated skill for '{ename}'")
                    else:
                        print(f"FAILED: {skill_result.get('error', 'Unknown error')}")
                        return {"status": "error", "error": f"Skill generation failed for '{ename}': {skill_result.get('error', 'Unknown')}"}

                # Regenerate AGENTS.md block with updated skill list
                agents_path = project / "AGENTS.md"
                new_block = _agents_block_with_skills()
                if agents_path.exists():
                    content = agents_path.read_text(encoding="utf-8", errors="replace")
                    if AGENTS_UNB_BLOCK_HEADER in content:
                        # Replace existing block (skipped earlier, but now we have skills)
                        import re
                        pattern = re.compile(rf"\n{re.escape(AGENTS_UNB_BLOCK_HEADER)}.+?(?=\n##|\Z)", re.DOTALL)
                        new_content = pattern.sub(new_block, content)
                        agents_path.write_text(new_content, encoding="utf-8")
                        actions.append("Updated AGENTS.md with skill references")

    # ─── Summary ───
    if dry_run:
        print("\n[Dry run] Would perform these actions:")
        for a in actions:
            print(f"  \u2022 {a}")
        return {"status": "dry_run", "actions": actions}

    print(f"\n{_('done')}")
    for a in actions:
        print(f"  \u2022 {a}")

    return {
        "status": "ok",
        "project": str(project),
        "skills_dir": str(skills_base),
        "actions": actions,
    }
