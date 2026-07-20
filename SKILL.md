---
name: unb-consultant
description: >
  Universal NotebookLM-Based Consultant. Create and query AI experts
  via NotebookLM (Gemini Notebook). Activates on explicit user request
  or when the agent detects a domain that could benefit from an expert.
---

# unb-consultant

CLI + MCP tool for creating and querying NotebookLM (Gemini Notebook) experts.

## Modes

### Mode 1: Manual (user explicitly asks)
- "Create an expert on [topic]" → `create_expert`
- "Ask the [name] expert about [question]" → `ask_expert`
- "Generate the catalog for [name]" → `generate_catalog`
- "Generate a skill for [name]" → `generate_skill`

### Mode 2: Proactive suggestion (agent detects domain)
- Detect domain keywords from user's project description
- Call `suggest_experts(domain_keywords=[...])`
- If matched, suggest to the user: "I can create a NotebookLM expert on [domain]..."
- **NEVER** create an expert without explicit user confirmation.
- **NEVER** write files to the project without explicit user confirmation.

## Available Tools (MCP)

| Tool | Confirmation Required | Description |
|------|----------------------|-------------|
| `create_expert` | Yes | Create a new NotebookLM expert |
| `ask_expert` | No | Ask a question to an expert |
| `list_experts` | No | List all registered experts |
| `add_sources` | Yes | Add sources to an existing expert |
| `generate_catalog` | Yes | Generate thematic catalog |
| `delete_expert` | Yes | Delete an expert |
| `generate_skill` | Yes if writing files | Generate SKILL.md for a project |
| `suggest_experts` | No | Suggest creating an expert by domain |
| `auth_check` | No | Check authentication status |

## Known Domains (suggest_experts)

| Keywords | Suggested Name | Sources |
|----------|---------------|---------|
| CVSS, CVE, vulnerability | `cvss-v4` | first.org CVSS spec |
| FAIR, risk analysis | `fair-analysis` | fairinstitute.org |
| MusicXML, music notation | `musicxml` | musicxml.com |
| Skyrim, Creation Kit | `skyrim-creation-kit` | ck.uesp.net |
| 0 A.D., modding | `0ad-modding` | 0ad wiki |

## Common Workflow

```
User: "I'm working on CVSS vulnerability scoring"

Agent: (calls suggest_experts(["cvss", "vulnerability", "scoring"]))
       → matched: cvss-v4
       → "I can create a NotebookLM expert on CVSS v4.0 using
          FIRST.org's official specification. This would let you
          query the standard without loading the 70-page PDF.
          Would you like me to create it?"

User: "Yes, go ahead."

Agent: (calls create_expert("cvss-v4", urls=[...], auto=True))
       → Expert created.
       → Catalog generated.
       → Skill generated.
       → "Done. You can now ask questions like:
          'Ask the cvss-v4 expert how the base score is calculated'"

### Suggested next steps (when create_expert returns without --auto)

When `create_expert` returns `suggested_next_steps`, inform the user and ask
if they want to proceed with catalog and/or skill generation. For each step:
- Read the description aloud
- Ask "Would you like me to do that?"
- **NEVER** execute these steps without user confirmation.

User: "Ask cvss-v4 how PR is scored"

Agent: (calls ask_expert("cvss-v4", "How is PR metric scored in CVSS v4.0?"))
       → Returns answer with citations.
```

## CLI Fallback (when MCP tools are not available)

Some models or providers do not support MCP tools. In that case, use these
CLI commands directly via the bash tool instead:

### Equivalence Table

| MCP Tool | CLI Command |
|----------|-------------|
| `ask_expert` | `unb ask "<name>" "<question>" [--json]` |
| `list_experts` | `unb expert list` |
| `create_expert` | `unb expert create "<name>" --url "..." [--file ...] [--auto]` |
| `delete_expert` | `unb expert delete "<name>" [--yes]` |
| `generate_catalog` | `unb catalog "<name>" [--output ./catalog.md]` |
| `generate_skill` | `unb skill-gen "<name>" [--auto]` |
| `add_sources` | `unb source add "<name>" --url "..." [--file ...] [--directory ...]` |
| `suggest_experts` | `unb suggest <keyword> [<keyword> ...]` |
| `auth_check` | `unb auth check --test --json` |

### Rules

1. Prefer MCP tools when available (they are faster and more structured).
2. If MCP tools are not visible, fall back to CLI commands.
3. Always quote arguments with double quotes in PowerShell.
4. NEVER execute destructive commands (delete, overwrite) without user confirmation.
5. Use `--json` with `ask` to get structured answers with source citations.

### Example (no MCP)

```
User: "List available experts"
Agent: → unb expert list
       → Shows table of registered experts

User: "Ask the 0ad-modding-reference expert about VFS"
Agent: → unb ask "0ad-modding-reference" "How does VFS work?" --json
       → Returns answer with citations
```

## Installation (for user reference)

```bash
pipx install "unb-consultant[browser]"
unb login
```
