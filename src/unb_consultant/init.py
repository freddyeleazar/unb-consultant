"""Project initialization for unb-consultant.

Sets up a project to use unb-consultant by creating the necessary
skill files and AGENTS.md entries. This is the fallback for models
that do not support MCP tools.
"""

from pathlib import Path

from unb_consultant.i18n import _
from unb_consultant.skill_gen import detect_project_structure

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
| Generate catalog | `unb catalog "<name>"` |
| Generate skill | `unb skill-gen "<name>" [--auto]` |
| Add sources | `unb source add "<name>" --url "..."` |
| Auth check | `unb auth check --test` |
| Login | `unb login` |

## Protocol

- When the user asks to list, query, create, or manage experts, use the
  commands above via the bash tool.
- Prefer `unb ask` with `--json` for answers with source citations.
- NEVER execute destructive commands (delete, overwrite) without user
  confirmation.
- If a command fails with auth errors, suggest `unb auth refresh`.
"""

AGENTS_UNB_BLOCK = """
## unb-consultant (NotebookLM Expert)

Available CLI commands (for models without MCP support):

| Task | Command |
|------|---------|
| List experts | `unb expert list` |
| Ask expert | `unb ask "<name>" "<question>"` |
| Create expert | `unb expert create "<name>" --url "..."` |
| Suggest domain | `unb suggest <keyword>` |

The file `.opencode/skills/unb-consultant/SKILL.md` has the full reference.
"""


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
        agent_type = structure["agent_type"]
    else:
        skills_base = project / ".opencode" / "skills"
        agent_type = "opencode"
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

    if agents_path.exists():
        content = agents_path.read_text(encoding="utf-8", errors="replace")
        if "## unb-consultant" in content:
            if dry_run:
                actions.append(f"Would skip AGENTS.md (already has unb-consultant block)")
            else:
                actions.append("AGENTS.md already has unb-consultant block. Skipping.")
        else:
            if dry_run:
                actions.append(f"Would append unb-consultant block to {agents_path}")
            else:
                with open(agents_path, "a", encoding="utf-8") as f:
                    f.write(AGENTS_UNB_BLOCK)
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
                        "# Project Setup\n" + AGENTS_UNB_BLOCK,
                        encoding="utf-8",
                    )
                    actions.append(f"Created {agents_path}")
            else:
                agents_path.write_text(
                    "# Project Setup\n" + AGENTS_UNB_BLOCK,
                    encoding="utf-8",
                )
                actions.append(f"Created {agents_path}")

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
