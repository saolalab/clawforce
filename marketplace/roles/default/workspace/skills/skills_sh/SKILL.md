---
name: skills-sh
description: Search and install agent skills from agentskill.sh, the AI agent skills directory.
homepage: https://agentskill.sh
metadata: {"clawbot":{"emoji":"📦"}}
---

# agentskill.sh

AI Agent Skills Directory — 99,000+ skills for Claude, Cursor, Copilot, and more.

## When to use

Use this skill when the user asks any of:
- "find a skill for …"
- "search for skills"
- "install a skill"
- "what skills are available?"
- "update my skills"

## Search

```bash
npx skills find "web scraping"
```

## Install

```bash
npx skills add owner/repo@skill-name -a cursor -y
```

Or for a repo with a single skill:

```bash
npx skills add owner/repo -a cursor -y
```

Replace `owner/repo@skill-name` with the slug from search results (e.g. `anthropics/skills@pdf`). Use `-y` to skip confirmation. Skills install to `workspace/.agents/skills/` and are loaded automatically by Clawbot.

## List installed

```bash
npx skills list
```

## Notes

- Requires Node.js (`npx` comes with it).
- No API key needed for search and install.
- Browse the directory at https://agentskill.sh
