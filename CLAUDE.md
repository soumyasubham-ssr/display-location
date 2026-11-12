# Display Location

Windows tray app that lets the owner reposition their second monitor (left / right / top / bottom of the primary) by dragging a tile in a small popup. See [README.md](README.md) and [docs/](docs/).

## AI role workflow

Role workflow: docs/AI_WORKFLOW.md

This project uses the role-based AI workflow (`role-workflow` skill). At the start of every chat, wait for the owner to assign a role with `Role: Manager | Tasker | Coder | Auditor | Advisor | QA` — never assume one. Once assigned, load the `role-workflow` skill, read the file above for this project's settings, and stay inside that role until the owner changes it.
