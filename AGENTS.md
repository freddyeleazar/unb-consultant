# unb-consultant

Universal NotebookLM-Based Consultant.

## MCP vs CLI Protocol

This tool provides both MCP tools (for models that support them) and CLI
commands (fallback for models without MCP support).

### If MCP tools are available (check your tool list)
Use them directly: `create_expert`, `ask_expert`, `list_experts`, etc.
They are faster and return structured data.

### If MCP tools are NOT available (fallback)
Use the CLI commands from the table below via the bash tool.
See SKILL.md for the full equivalence table.

| Task | MCP Tool | CLI Fallback |
|------|----------|-------------|
| Create expert | `create_expert` | `unb expert create <name> --url "..." [--auto]` |
| List experts | `list_experts` | `unb expert list` |
| Ask question | `ask_expert` | `unb ask <name> "<question>" [--json]` |
| Suggest domain | `suggest_experts` | `unb suggest <keyword> ...` |
| Delete expert | `delete_expert` | `unb expert delete <name>` |
| Generate catalog | `generate_catalog` | `unb catalog <name>` |
| Generate skill | `generate_skill` | `unb skill-gen <name>` |
| Add sources | `add_sources` | `unb source add <name> --url "..."` |
| Auth check | `auth_check` | `unb auth check --test` |

## Protocol

- **Mode 1 (Manual):** Only act when the user explicitly asks.
- **Mode 2 (Proactive):** May suggest creating an expert when detecting a domain
  match. **Always wait for user confirmation.**
- **Never** modify project files without explicit user request.
- **Never** create or delete experts without user confirmation.

## Commands

| Action | Command |
|--------|---------|
| Login | `unb login` |
| Check auth | `unb auth check --test` |
| Refresh auth | `unb auth refresh` |
| Suggest domain | `unb suggest cvss musicxml skyrim` |
| Create expert | `unb expert create <name> --url "..." [--auto]` |
| List experts | `unb expert list` |
| Ask expert | `unb ask <name> "<question>" [--json]` |
| Add sources | `unb source add <name> --url "..."` |
| Generate catalog | `unb catalog <name>` |
| Generate skill | `unb skill-gen <name>` |

## Language

The CLI auto-detects your locale. Override with `--lang en` or `UNB_LANG=es`.
