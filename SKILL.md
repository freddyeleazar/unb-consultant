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
       → "Done. You can now ask questions like:
          'Ask the cvss-v4 expert how the base score is calculated'"

User: "Ask cvss-v4 how PR is scored"

Agent: (calls ask_expert("cvss-v4", "How is PR metric scored in CVSS v4.0?"))
       → Returns answer with citations.
```

## Installation (for user reference)

```bash
pipx install "unb-consultant[browser]"
unb login
```
