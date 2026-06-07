# AGENTS.md — RJ Auto Metadata

> **Read this file first before any work on this repository.**

## Project Identity

- **Application**: RJ Auto Metadata — standalone desktop app for AI-powered media metadata generation
- **Language**: Python 3.9+
- **UI Framework**: CustomTkinter
- **AI SDK**: OpenAI SDK (used across all providers via OpenAI-compatible endpoints)
- **Version**: 3.12.3
- **License**: AGPL-3.0

## Repository Structure

```
main.py                 Entry point
src/
  api/                  Provider API modules + provider_manager.py dispatcher
  config/               Constants, measurement IDs, config load/save
  metadata/             ExifTool writer, categories
  processing/           Batch processing, format-specific handlers
  ui/                   CustomTkinter GUI (app.py ~1738 lines)
  utils/                Logging, file utils, system checks, analytics
docs/                   Architecture, policies, roadmap, handoff notes
tools/                  Bundled ExifTool, Ghostscript, FFmpeg (gitignored)
assets/                 Icons, QR code
```

## Required Reading Order

Before making any changes, read these files in order:

1. `AGENTS.md` (this file)
2. `docs/CURRENT_STATE.md` — where the project stands right now
3. `docs/ARCHITECTURE.md` — system design and request flow
4. `docs/ANALISYS_REFACTORING.md` — design source of truth for the v4 refactor
5. `docs/ROADMAP.md` — phased implementation plan
6. `docs/HANDOFF.md` — session continuity notes
7. `docs/GIT_POLICY.md` — branching and commit rules

## Current State Summary

- **Phase 0** (docs governance): Complete
- **Phase 1** (backend refactor): Pending — OpenAI compat migration, dynamic model fetch, dead code removal
- **Phase 2** (UI refactor): Pending — layout restructure, Fetch button, Custom provider, per-provider model state

## Branch Rules

- **Never** commit directly to `main` or `dev`.
- Always create a task branch from `dev`: `git switch -c task/<name> dev`
- Branch naming: `task/refactor-backend`, `task/refactor-ui`, `task/docs-governance`, etc.

## Commit Rules

- Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`, `style:`, `test:`
- Subject line: `<type>(<scope>): <description>` — max 72 characters
- Separate subject from body with a blank line
- Body explains WHY, not WHAT

## Hard Safety Rules

1. **Never** commit API keys, `.env` files, or contents of `api_jikaperlu/`.
2. **Never** commit `dist_nuitka/`, `*.zip`, `v*/` folders, or `logs` files.
3. **Never** modify `docs/ANALISYS_REFACTORING.md` — it is the design source of truth, read-only for agents.
4. **Do not push** unless explicitly instructed by the human user.
5. **Do not merge** to `dev` or `main` unless explicitly instructed by the human user.

## Verification Expectations

After any Python change, verify:

1. `python main.py` launches without errors.
2. Quick smoke test of the changed flow (e.g., select provider, fetch models, run a single file).

## Scope Discipline

Implement **only** what the current phase prompt specifies. Do not add extra features, refactors, or improvements beyond scope. If you notice something worth fixing outside scope, note it in `docs/HANDOFF.md` for a future phase.

## Code Comment Policy

- Comments should explain **WHY** (safety boundaries, API assumptions, non-obvious decisions).
- Do not leave debug artifacts or commented-out code in production.
- Do not add redundant comments that restate what the code does.

---

For detailed documentation, see the `docs/` folder.
