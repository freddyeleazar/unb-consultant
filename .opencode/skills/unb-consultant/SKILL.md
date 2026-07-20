---
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
