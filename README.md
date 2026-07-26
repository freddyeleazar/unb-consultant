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
| `unb auth refresh` | Refresh authentication tokens |
| `unb expert create NAME` | Create a new expert (`--url`, `--file`, `--auto`) |
| `unb expert list` | List all experts (`--json` for structured output) |
| `unb expert delete NAME` | Delete an expert (`--yes` to skip confirmation) |
| `unb ask NAME QUESTION` | Ask a question (`--json` for citations) |
| `unb suggest KEYWORD ...` | Suggest expert domains by keywords |
| `unb catalog NAME` | Generate thematic catalog |
| `unb skill-gen NAME` | Generate SKILL.md (`--auto` for automatic) |
| `unb source add NAME` | Add sources to expert |
| `unb init` | Set up unb-consultant in a project (`--auto`) |
| `unb setup` | Interactive setup wizard |
| `unb mcp` | Start MCP server |

## Development

### Prerequisites

- Python 3.10+
- Google account (for NotebookLM)

### Local setup

```bash
git clone https://github.com/freddyeleazar/unb-consultant.git
cd unb-consultant
pip install -e ".[browser,dev]"
```

### Testing

```bash
pytest
```

### Releasing

See [AGENTS.md](AGENTS.md) for the release workflow. The project uses
[Conventional Commits](https://www.conventionalcommits.org/) and
[Keep a Changelog](https://keepachangelog.com/).
