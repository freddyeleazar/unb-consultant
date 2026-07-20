# unb-consultant

Universal NotebookLM-Based Consultant. Create and query AI experts powered by Google Gemini Notebook (formerly NotebookLM).

## Installation

```bash
pipx install "unb-consultant[browser]"
```

Or with cookie extraction support:
```bash
pipx install "unb-consultant[browser,cookies]"
```

## Quick Start

```bash
# Authenticate
unb login

# Create an expert
unb expert create "cvss-v4" \
  --url "https://www.first.org/cvss/v4-0/specification-document" \
  --desc "CVSS v4.0 scoring expert"

# Ask a question
unb ask "cvss-v4" "How is the base score calculated?"

# List experts
unb expert list
```

## MCP Server

For AI agent integration, start the MCP server:

```bash
unb mcp
```

Then configure in your `opencode.json`:

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

## Commands

| Command | Description |
|---------|-------------|
| `unb login` | Authenticate with Google |
| `unb auth check --test` | Verify authentication |
| `unb expert create NAME` | Create a new expert |
| `unb expert list` | List all experts |
| `unb expert delete NAME` | Delete an expert |
| `unb ask NAME QUESTION` | Ask a question |
| `unb catalog NAME` | Generate thematic catalog |
| `unb skill-gen NAME` | Generate SKILL.md |
| `unb source add NAME` | Add sources to expert |
| `unb mcp` | Start MCP server |
| `unb setup` | Interactive setup |
