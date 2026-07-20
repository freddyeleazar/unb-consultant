# unb-consultant

Universal NotebookLM-Based Consultant.

## MCP Server Setup

For AI agent integration, add to your `opencode.json`:

```json
{
  "mcpServers": {
    "unb-consultant": {
      "command": "unb",
      "args": ["mcp"]
    }
  }
}
```

## Protocol

- **Mode 1 (Manual):** Only act when the user explicitly asks.
- **Mode 2 (Proactive):** May suggest creating an expert when detecting a domain match. **Always wait for user confirmation.**
- **Never** modify project files without explicit user request.
- **Never** create or delete experts without user confirmation.

## Commands

| Action | Command |
|--------|---------|
| Login | `unb login` |
| Check auth | `unb auth check --test` |
| Refresh auth | `unb auth refresh` |
| Create expert | `unb expert create <name> --url "..." [--auto]` |
| List experts | `unb expert list` |
| Ask expert | `unb ask <name> "<question>"` |
| Add sources | `unb source add <name> --url "..."` |
| Generate catalog | `unb catalog <name>` |
| Generate skill | `unb skill-gen <name>` |
| Start MCP | `unb mcp` |
| Show tier | `unb tier` |

## Language

The CLI auto-detects your locale. Override with `--lang en` or `UNB_LANG=es`.
