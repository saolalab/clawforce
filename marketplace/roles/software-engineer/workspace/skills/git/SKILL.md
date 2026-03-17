---
name: git
description: "Version control with git. Clone, branch, commit, push. Required for repo workflows."
metadata: {"clawbot":{"emoji":"📦","requires":{"bins":["git"]}}}
---

# Git Skill

Use `git` for version control. Essential for tasks that involve pulling code, making changes, and creating PRs.

## Common workflow (code tasks)

1. **Clone or pull** — `git clone <url>` or `git pull origin main`
2. **Branch** — `git checkout -b feature/description`
3. **Edit** — Make changes (prefer coding tools: Claude Code, Gemini CLI, Codex CLI)
4. **Stage and commit** — `git add .` then `git commit -m "message"`
5. **Push** — `git push -u origin <branch>`
6. **Create PR** — Use `gh pr create` (see github skill)

## Key commands

```bash
git status
git branch --show-current
git log --oneline -5
git diff
git remote -v
```

GIT_AUTHOR_NAME and GIT_AUTHOR_EMAIL are set by the agent's variables for commits.
