# Workspace Layout

Organize files into folders instead of dumping everything in the root.
Use `workspace_tree` to get a hierarchical overview; use `list_dir` for one-level listing.

## Recommended Folders

| Folder | Purpose |
|--------|---------|
| `docs/` | Documents, notes, specs, meeting notes |
| `projects/` | Project-specific work (one subfolder per project) |
| `outputs/` | Generated reports, exports, artifacts |
| `drafts/` | Work in progress, temporary drafts |
| `.agents/` | System: memory, skills, heartbeat (do not create user files here) |

## Rules

1. **Create folders first** — Before writing a file, choose the right folder. Create it if needed (`write_file` creates parent dirs).
2. **Use `workspace_tree` for overview** — Prefer `workspace_tree` over repeated `list_dir` when exploring structure.
3. **Avoid root clutter** — Only put top-level items (README, config) in root; everything else goes in a folder.
4. **Project isolation** — Use `projects/<name>/` for multi-file work (e.g. `projects/analysis-2024/`, `projects/report-q1/`).
