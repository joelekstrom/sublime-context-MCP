# Sublime Text Editor Context

When the user asks about code without specifying which file ("this code", "Does this look good?", "Review this"), **always check `sublime-context://state` first** to see what they have open and selected.

## Resource: `sublime-context://state`

Returns JSON with `activeFiles` (one per window, frontmost first), `otherFiles`, `projectFolders`.

Each file has `path` and `selection`:
- `{"start": {"line": N, "column": M}, "end": {...}}` if text selected (lines 1-indexed, columns 0-indexed)
- `{"cursor": {"line": N, "column": M}}` if just cursor
- `null` if no selection

**How to use:**
1. Filter to working directory from `<env>`
2. Prioritize `activeFiles[0]` (frontmost window's active file)
3. If `selection.start` and `selection.end` exist, read those lines from the file - that's what user wants help with
4. Reference locations with line numbers ("file.py:45")
