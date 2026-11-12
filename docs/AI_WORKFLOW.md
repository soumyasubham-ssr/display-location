# AI Project Roles & Workflow

**Last Updated:** 2026-11-12
**Status:** Active convention — governs how AI sessions operate on this project

This project uses the **role-workflow** skill (Manager, Tasker, Coder, Auditor, Advisor, QA). The skill holds the full role definitions; this file holds **this project's settings and any project-specific rules**, which override the skill's defaults.

The owner assigns a role at the start of each chat with `Role: <name>`. The AI must not assume a role.

---

## Project Settings

```yaml
# Where the shared project memory lives
docs_dir: docs
tasks_dir: docs/tasks
changelog: docs/CHANGELOG.md
task_id_format: TASK-NNN / BUG-NNN    # file names: TASK-012-short-slug.md

# Roles available in this project
roles_enabled: [Manager, Tasker, Coder, Auditor, Advisor, QA]

auditor:
  git_sync: off              # project is not a git repository yet (2026-11-12)
  git_scope: audited
  branch_policy: new-branch
  scan_chat_sessions: true
  verify_sources:
    - code
    - git history            # once the repo is initialised
    - Windows display state  # Settings → System → Display, or `python -m display_location --list`

qa_targets:
  - app from source: python -m display_location   (from the project venv)
  - packaged exe: dist/DisplayLocation.exe
  - unit tests: python -m pytest
```

---

## Project-specific notes

- **Read first:** [REQUIREMENTS.md](REQUIREMENTS.md) → [ARCHITECTURE.md](ARCHITECTURE.md) → [DECISIONS.md](DECISIONS.md) → [ROADMAP.md](ROADMAP.md) → the task in [tasks/](tasks/).
- **Scope guard:** this app only moves the *second monitor's position*. Independent taskbars / per-monitor desktops are handled by Windhawk mods (see DECISIONS D-001) — do not build them here.
- **Windows-only.** All display changes go through the Win32 API in `src/display_location/displays.py`; nothing else may call `ChangeDisplaySettingsEx`.
- **Safety:** any code path that changes the display layout must keep the revert path working (REQUIREMENTS FR-07). Coder and QA must test revert before finishing a task that touches display changes.
- **OneDrive:** the project folder is inside OneDrive. Keep the virtual environment and heavy build output out of sync (see DECISIONS D-008).
- **QA:** test with the real two-monitor setup, at mixed scaling (e.g. 100 % + 125 %) if available, and with one monitor unplugged.

---

## Change History

| Date | Change | Reason |
|---|---|---|
| 2026-11-12 | File created from the role-workflow skill template | Adopt the role-based workflow in this project |
