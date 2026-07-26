# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.1] - 2026-07-25

### Fixed
- Windows compatibility: replaced `async_playwright()` with `sync_playwright()`
  to avoid event-loop conflicts with Chromium subprocesses
- Text source upload now writes to a temporary file instead of passing inline
  text, avoiding shell argument limits and `--type` flag issues with
  notebooklm-py
- `_wait_for_sources()` no longer blocks for 10 minutes when a source has
  `status: "error"` — exits early instead

## [0.3.0] - 2026-07-25

### Added
- Playwright universal URL processor: all URLs are scraped via stealth
  Playwright (text + PDF) instead of being sent directly to NotebookLM,
  bypassing Googlebot limitations (Cloudflare, Anubis, JS-heavy pages)
- **Multimodal PDF support:** NotebookLM processes images embedded in PDFs
  visually (confirmed empirically — hand-drawn diagrams, colors, handwritten
  codes are read correctly, not just via OCR). Each scraped page generates
  both a TEXT source (clean text) and a PDF source (with images) so
  NotebookLM can leverage its built-in multimodal understanding
- `--no-scrape` flag for `unb expert create` and `unb source add` to
  skip Playwright and use direct URL upload (original behaviour)
- Google Cache fallback when Playwright fails
- New optional extra: `pip install 'unb-consultant[scraping]'` plus
  `playwright install chromium`

## [0.2.1] - 2026-07-25

### Added
- Welcome message after `unb login` or `unb setup` when no experts exist,
  showing examples and a tip about natural-language agent support

## [0.2.0] - 2026-07-20

### Fixed
- UnboundLocalError when using `unb expert create --file` in non-dry-run mode
  (duplicate import shadowing module-level import)
- `_missing_skills` detection now correctly checks for `catalog.md` in addition to `SKILL.md`

## [0.1.9] - 2026-07-20

### Refactored
- `SKILL.md` now references a separate `catalog.md` file instead of embedding
  the full catalog text, avoiding stale data when the catalog is updated
- `skill_gen.py` writes `catalog.md` as a standalone file alongside `SKILL.md`
- `catalog.py` stores the FULL catalog text in config (previously truncated to 500 chars)

## [0.1.8] - 2026-07-20

### Fixed
- `unb init --auto` now runs catalog generation and skill-gen automatically
- `init.py` is re-evaluable: detects experts without local skills and skips completed ones
- `init.py` passes `project_path` to `generate_skill()` so files land in the correct directory
- `skill_gen.py` accepts a `project_path` parameter for non-CWD target directories

## [0.1.7] - 2026-07-20

### Added
- `unb expert list --json` outputs structured JSON with full metadata
  (notebook_id, tier, catalog dates)
- Critical rule: project setup (`unb init`) is now **required** before any `unb` operations

## [0.1.6] - 2026-07-20

### Fixed
- Test data (exp1, exp2) no longer leaks into the real config file
  (added module-level backup/restore fixture)
- `tier.setter` and `lang.setter` no longer trigger `save()` on read-only commands
- Atomic config writes via `.tmp` file + rename (prevents partial writes)
- Added `cache_tier()` for explicit tier persistence; `detect_tier()` sets in-memory only

## [0.1.5] - 2026-07-20

### Fixed
- Complete rewrite of `unb init`: now offers catalog + skill-gen generation
  for registered experts after creating SKILL.md
- Full AGENTS.md documentation for all commands (catalog, skill-gen, etc.)
- AGENTS.md now lists skills per expert

## [0.1.4] - 2026-07-20

### Fixed
- `UnicodeDecodeError` on Windows cp1252 by adding `encoding='utf-8', errors='replace'`
  to `subprocess.run()` in auth.py
- Improved agent error handling directives in global AGENTS.md and SKILL.md
- Agents must NOT read unb source code

## [0.1.3] - 2026-07-20

### Added
- `unb init` command to set up `.opencode/skills/unb-consultant/SKILL.md`
  and AGENTS.md entries in any project
- Agents should suggest `unb init` when a project lacks configuration
- Pre-flight check for unb-consultant config before CLI fallback

## [0.1.2] - 2026-07-20

### Added
- `unb suggest` CLI command for domain/expert suggestions
- CLI fallback documentation for non-MCP models in AGENTS.md

## [0.1.1] - 2026-07-20

### Added
- `suggested_next_steps` returned by `create_expert` (catalog + skill-gen suggestions)
- CLI shows suggestions as bullet points after expert creation
- SKILL.md directive for agents to ask user before proceeding
- i18n strings (EN and ES) for suggestions

### Fixed
- Dry-run mode now returns early before authentication attempts

## [0.1.0] - 2026-07-20

### Added
- Initial release of unb-consultant
- Create, list, delete, and query NotebookLM experts
- MCP server for AI agent integration
- Multi-language CLI (auto-detect locale)
