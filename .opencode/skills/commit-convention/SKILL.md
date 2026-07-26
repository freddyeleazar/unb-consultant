---
name: commit-convention
description: Use when the user asks to commit, make a commit, write a commit message, or create a release. Enforces Conventional Commits and changelog rules for unb-consultant.
---

# Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/).

## Format

```
<type>(<scope>): <description>
```

- `<type>` and `<description>` are required, `<scope>` is optional.
- Description: imperative, lowercase, no period at end, max 72 chars.

## Types

| Type       | Usage                                    |
|------------|------------------------------------------|
| `feat`     | A new feature                            |
| `fix`      | A bug fix                                |
| `refactor` | Code change that neither fixes nor adds   |
| `docs`     | Documentation only (README, CHANGELOG)   |
| `test`     | Adding or fixing tests                   |
| `chore`    | Build, CI, dependencies, release bump    |
| `bump`     | Version bump + changelog update (legacy) |

## Scope (optional)

Use the version number in parentheses for release commits:
- `refactor(v0.1.9): ...`
- `fix(v0.1.8): ...`
- `chore(v0.2.0): release`

## Release workflow

1. **Review README.md** — ensure it reflects the latest features, commands,
   and usage examples
2. **Update CHANGELOG.md** — move items from [Unreleased] to a new version
   entry following Keep a Changelog format
3. **Bump version** in `pyproject.toml` and `src/unb_consultant/__init__.py`
4. **Commit** using Conventional Commits: `chore(vX.Y.Z): release`
5. **Tag** the commit: `git tag vX.Y.Z`
6. **Push** both branch and tags: `git push && git push --tags`

The GitHub Action will auto-publish to PyPI when a `v*` tag is pushed.
