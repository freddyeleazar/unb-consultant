"""CLI for unb-consultant.

Click-based command-line interface for creating and querying
NotebookLM experts.
"""

import sys
import click
from pathlib import Path

from unb_consultant import __version__
from unb_consultant.i18n import _, set_lang, get_lang
from unb_consultant.config import get_config
from unb_consultant.auth import auth_check as _auth_check
from unb_consultant.auth import login as _login
from unb_consultant.auth import refresh as _refresh
from unb_consultant.expert import create_expert, list_experts, delete_expert, format_expert_table
from unb_consultant.ask import ask_expert
from unb_consultant.catalog import generate_catalog
from unb_consultant.skill_gen import generate_skill
from unb_consultant.source import add_sources
from unb_consultant.tier import format_tier_info


@click.group()
@click.version_option(version=__version__, prog_name="unb")
@click.option("--lang", type=click.Choice(["en", "es"]),
              help="Override language detection.")
def cli(lang):
    """Universal NotebookLM-Based Consultant.

    Create and query AI experts powered by NotebookLM (Gemini).
    """
    if lang:
        set_lang(lang)
    # Apply config language if set
    config = get_config()
    if config.lang and not lang:
        set_lang(config.lang)


# ─── Auth commands ───

@cli.command()
@click.option("--browser-cookies", type=str,
              help="Browser name to extract cookies from (chrome, edge, firefox)")
def login(browser_cookies):
    """Authenticate with Google via browser."""
    result = _login(browser_cookies=browser_cookies)
    if result.get("status") == "ok":
        detail = result.get("detail", "")
        # Extract email from notebooklm output
        import re
        m = re.search(r'Account:\s*(\S+@\S+)', detail)
        email = m.group(1) if m else "unknown"
        click.echo(_("auth_login_ok", email=email))
    else:
        click.echo(f"{_('error')}: {result.get('error', 'Login failed')}", err=True)
        sys.exit(1)


@cli.group()
def auth():
    """Authentication management."""


@auth.command("check")
@click.option("--test", is_flag=True, help="Make network call to verify cookies")
@click.option("--json", "json_output", is_flag=True, help="JSON output")
def auth_check_cmd(test, json_output):
    """Check authentication status."""
    click.echo(_("auth_checking"))
    result = _auth_check(test=test)

    if json_output:
        import json as _json
        click.echo(_json.dumps(result, indent=2))
        return

    if result.get("status") == "ok":
        token_ok = result.get("checks", {}).get("token_fetch", False)
        if token_ok:
            click.echo(_("auth_ok"))
        elif test:
            click.echo(f"{_('error')}: {_('auth_expired')}")
            click.echo(f"  Run: unb auth refresh")
        else:
            click.echo(f"{_('warning')}: Use --test for full validation")
            click.echo(f"  Storage: {result.get('details', {}).get('storage_path', '?')}")
    else:
        err = result.get("error", "Unknown")
        if isinstance(err, dict):
            err = str(err.get("error", err))
        click.echo(f"{_('error')}: {err[:200]}", err=True)


@auth.command("refresh")
def auth_refresh_cmd():
    """Refresh authentication cookies."""
    result = _refresh()
    if result.get("status") == "ok":
        click.echo(_("auth_refresh_ok"))
    else:
        err = result.get("error", "Refresh failed")
        if isinstance(err, dict):
            err = str(err.get("error", err))
        click.echo(f"{_('error')}: {err[:200]}", err=True)


# ─── Expert commands ───

@cli.group()
def expert():
    """Create, list, and delete experts."""


@expert.command("create")
@click.argument("name")
@click.option("--desc", "-d", help="Expert description")
@click.option("--url", "-u", multiple=True, help="Source URL (can be repeated)")
@click.option("--file", "-f", "files", multiple=True,
              type=click.Path(exists=True), help="Local file (can be repeated)")
@click.option("--directory", type=click.Path(exists=True, file_okay=False),
              help="Directory with source files (.md, .txt, .pdf)")
@click.option("--drive-doc", multiple=True, help="Google Drive document ID")
@click.option("--auto", is_flag=True,
              help="Auto-generate catalog + skill after creation")
@click.option("--dry-run", is_flag=True,
              help="Preview merge plan without creating")
@click.option("--force", is_flag=True,
              help="Overwrite existing expert with same name")
@click.option("--yes", is_flag=True, hidden=True)
def expert_create(name, desc, url, files, directory, drive_doc,
                  auto, dry_run, force, yes):
    """Create a new NotebookLM expert.

    NAME: Expert name (lowercase letters, numbers, and hyphens only).
    """
    result = create_expert(
        name=name,
        description=desc or "",
        urls=list(url) if url else None,
        files=[Path(f) for f in files] if files else None,
        directory=Path(directory) if directory else None,
        drive_docs=list(drive_doc) if drive_doc else None,
        auto=auto,
        dry_run=dry_run,
        force=force,
        yes=yes,
    )

    if result.get("status") == "error":
        click.echo(f"{_('error')}: {result['error']}", err=True)
        sys.exit(1)
    elif result.get("status") == "aborted":
        click.echo(_("aborted"))
        sys.exit(0)

    # Show suggested next steps
    suggested = result.get("suggested_next_steps")
    if suggested:
        click.echo(f"\n{_('next_steps')}")
        for step in suggested:
            click.echo(f"  \u2022 {step['description']}: {step['command']}")


@expert.command("list")
def expert_list():
    """List all registered experts."""
    experts = list_experts()
    if not experts:
        click.echo(_("expert_list_empty"))
        return
    click.echo(format_expert_table(experts))


@expert.command("adopt")
@click.argument("name")
@click.argument("notebook_id")
@click.option("--desc", "-d", help="Expert description")
@click.option("--force", is_flag=True, help="Overwrite existing")
def expert_adopt(name, notebook_id, desc, force):
    """Register an existing NotebookLM notebook as an expert.

    NAME: Name for the expert.
    NOTEBOOK_ID: Existing NotebookLM notebook ID.
    """
    from unb_consultant.expert import adopt_expert as _adopt
    result = _adopt(
        notebook_id=notebook_id,
        name=name,
        description=desc or "",
        force=force,
    )
    if result.get("status") == "error":
        click.echo(f"{_('error')}: {result['error']}", err=True)
        sys.exit(1)

@expert.command("delete")
@click.argument("name")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def expert_delete(name, yes):
    """Delete an expert and its notebook.

    NAME: Expert name to delete.
    """
    result = delete_expert(name=name, yes=yes)
    if result.get("status") == "error":
        click.echo(f"{_('error')}: {result['error']}", err=True)
        sys.exit(1)
    elif result.get("status") == "aborted":
        click.echo(_("aborted"))
        sys.exit(0)
    else:
        click.echo(result.get("message", _("done")))


# ─── Source commands ───

@cli.group()
def source():
    """Add sources to an existing expert."""


@source.command("add")
@click.argument("name")
@click.option("--url", "-u", multiple=True, help="Source URL")
@click.option("--file", "-f", "files", multiple=True,
              type=click.Path(exists=True), help="Local file")
@click.option("--directory", type=click.Path(exists=True, file_okay=False),
              help="Directory with source files")
@click.option("--drive-doc", multiple=True, help="Google Drive document ID")
@click.option("--yes", is_flag=True, help="Skip confirmation")
def source_add(name, url, files, directory, drive_doc, yes):
    """Add sources to an existing expert.

    NAME: Expert name to add sources to.
    """
    result = add_sources(
        expert_name=name,
        urls=list(url) if url else None,
        files=[Path(f) for f in files] if files else None,
        directory=Path(directory) if directory else None,
        drive_docs=list(drive_doc) if drive_doc else None,
        yes=yes,
    )

    if result.get("status") == "error":
        click.echo(f"{_('error')}: {result['error']}", err=True)
        sys.exit(1)
    elif result.get("status") == "aborted":
        click.echo(_("aborted"))
        sys.exit(0)


# ─── Ask command ───

@cli.command()
@click.argument("name")
@click.argument("question")
@click.option("--json", "json_output", is_flag=True,
              help="Output JSON with references")
def ask(name, question, json_output):
    """Ask a question to an expert.

    NAME: Expert name.
    QUESTION: Question text.
    """
    result = ask_expert(
        name=name,
        question=question,
        json_output=json_output,
    )

    if result.get("status") == "error":
        click.echo(f"{_('error')}: {result['error']}", err=True)
        sys.exit(1)

    if json_output:
        import json as _json
        click.echo(_json.dumps(result, indent=2))
    else:
        click.echo(result.get("answer", ""))


# ─── Suggest command ───

@cli.command()
@click.argument("keywords", nargs=-1, required=True)
def suggest(keywords):
    """Suggest domain matches for creating an expert.

    KEYWORDS: Domain keywords to match (e.g. cvss musicxml skyrim).
    """
    from unb_consultant.mcp_server import suggest_experts

    result = suggest_experts(domain_keywords=list(keywords))

    if result.get("matched"):
        click.echo(f"Found {len(result['suggestions'])} domain match(es):")
        for s in result["suggestions"]:
            click.echo(f"  \u2022 {s['domain']} ({s['rationale']})")
            if s.get("recommended_sources"):
                src = s["recommended_sources"][0]
                click.echo(f"    unb expert create \"{s['suggested_name']}\" --url \"{src}\"")
    else:
        click.echo(result.get("message", "No domain matches found."))


# ─── Catalog command ───

@cli.command()
@click.argument("name")
@click.option("--output", "-o", type=click.Path(),
              help="Write catalog to file")
@click.option("--no-note", is_flag=True,
              help="Don't save catalog as NotebookLM note")
@click.option("--yes", is_flag=True, hidden=True)
def catalog(name, output, no_note, yes):
    """Generate thematic catalog for an expert.

    NAME: Expert name.
    """
    result = generate_catalog(
        name=name,
        output_path=output,
        save_as_note=not no_note,
        yes=yes,
    )

    if result.get("status") == "error":
        click.echo(f"{_('error')}: {result['error']}", err=True)
        sys.exit(1)

    if not output:
        # Print catalog preview
        catalog_text = result.get("catalog", "")
        if catalog_text:
            click.echo()
            click.echo(catalog_text[:2000])  # Preview


# ─── Skill generation ───

@cli.command("skill-gen")
@click.argument("name")
@click.option("--output", "-o", type=click.Path(),
              help="Output path for SKILL.md")
@click.option("--auto", is_flag=True,
              help="Auto-confirm all decisions")
@click.option("--no-agents", is_flag=True,
              help="Don't modify AGENTS.md")
@click.option("--dry-run", is_flag=True,
              help="Preview what would be done")
@click.option("--update", is_flag=True,
              help="Update existing skill")
def skill_gen(name, output, auto, no_agents, dry_run, update):
    """Generate a SKILL.md for an expert.

    NAME: Expert name.
    """
    result = generate_skill(
        name=name,
        output_path=output,
        auto=auto,
        no_agents=no_agents,
        dry_run=dry_run,
        update=update,
    )

    if result.get("status") == "error":
        click.echo(f"{_('error')}: {result['error']}", err=True)
        sys.exit(1)
    elif result.get("status") == "aborted":
        click.echo(_("aborted"))
        sys.exit(0)
    elif result.get("status") == "dry_run":
        if "content" in result:
            click.echo(result["content"])
        else:
            click.echo(result.get("message", "(dry run)"))


# ─── MCP server ───

@cli.command()
def mcp():
    """Start MCP server (stdio transport)."""
    from unb_consultant.mcp_server import create_server

    server = create_server()
    if server is None:
        click.echo("mcp package not installed. Install: pip install mcp", err=True)
        sys.exit(1)

    click.echo(_("mcp_starting"), err=True)

    try:
        from mcp.server.stdio import stdio_server
        import anyio
        anyio.run(server.run, stdio_server())
    except ImportError:
        click.echo("mcp server dependencies not available.", err=True)
        sys.exit(1)


# ─── Init command ───

@cli.command()
@click.option("--auto", is_flag=True, help="Auto-confirm all decisions")
@click.option("--dry-run", is_flag=True, help="Preview actions without writing")
@click.option("--path", type=click.Path(exists=True, file_okay=False),
              help="Project directory (default: current)")
def init(auto, dry_run, path):
    """Initialize current project for unb-consultant.

    Creates .opencode/skills/unb-consultant/SKILL.md and AGENTS.md
    entries so agents without MCP support can discover and use unb.
    """
    from unb_consultant.init import init_project as _init

    result = _init(path=path, auto=auto, dry_run=dry_run)

    if result.get("status") == "error":
        click.echo(f"{_('error')}: {result['error']}", err=True)
        sys.exit(1)
    elif result.get("status") == "aborted":
        click.echo(_("aborted"))
        sys.exit(0)


# ─── Setup command ───

@cli.command()
def setup():
    """Interactive setup: detect tier, check auth, show config."""
    config = get_config()

    click.echo("=== unb-consultant setup ===\n")

    # Language
    click.echo(f"Language: {get_lang().upper()} (set with --lang or UNB_LANG)")

    # Auth
    click.echo(_("auth_checking"))
    import json
    result = _auth_check(test=True)
    if result.get("status") == "ok" and result.get("checks", {}).get("token_fetch"):
        click.echo(f"  {_('auth_ok')}")
    else:
        click.echo(f"  {_('auth_expired')}")

    # Tier
    click.echo(format_tier_info())

    # Experts count
    count = config.expert_count()
    click.echo(f"\nExperts registered: {count}")
    if count > 0:
        experts = list_experts()
        click.echo(format_expert_table(experts))

    # Config path
    click.echo(f"\nConfig: {Path.home() / '.unb-consultant' / 'config.json'}")


# ─── Tier info command ───

@cli.command("tier")
def tier_info():
    """Show NotebookLM subscription tier info."""
    click.echo(format_tier_info())


if __name__ == "__main__":
    cli()
