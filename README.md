# Sublime Editor Context MCP

A Sublime Text plugin that exposes your editor context (open files, selections, cursor positions) to agents via the Model Context Protocol (MCP). The instructions below assume Claude Code, but should be easy to adjust.

## Installation

1. **Install the plugin**: Copy this folder to your Sublime Text Packages directory
   - Open Sublime Text
   - Go to `Preferences > Browse Packages...`
   - Copy this entire folder into the Packages directory

2. **Add to your global Claude context**: Append `.claude/CLAUDE.md` to `~/.claude/CLAUDE.md`
   - This tells Claude Code to check the Sublime context when you ask about code
   - Only needs to be done once globally

3. **Configure Claude Code**: Add the MCP server to Claude Code's settings
   - Run `claude mcp add sublime-context http://127.0.0.1:8765 --transport http`

## Usage

The plugin automatically starts an MCP server on port 8765 when Sublime Text loads.

### Verify it's working

Use the Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P`):
- Run: `Editor Context: Show State`

This opens a new buffer showing your current editor state as JSON.

### With agent

Once configured, your agent can see:
- Which files you have open across all windows
- Which file is active in each window (frontmost window first)
- What text you have selected
- Cursor positions when nothing is selected
- Your project folders

Ask questions like:
- "What am I working on right now?"
- "Help me fix this function" (with code selected)
- "What files do I have open?"

## MCP Resource

The plugin exposes one resource:

- **URI**: `sublime-context://state`
- **Returns**: JSON with `activeFiles`, `otherFiles`, `projectFolders`, and `lastUpdated`

See `.claude/CLAUDE.md` for detailed documentation on the data structure.

## Configuration

Default port is 8765. To change it:

`Preferences > Package Settings > Editor Context MCP > Settings`:

```json
{
    "mcp_server_port": 8765
}
```

## Troubleshooting

**Server won't start?**
- Check Sublime Text console: `View > Show Console`
- Check if port 8765 is in use: `lsof -i :8765`

**State not updating?**
- Run `Editor Context: Show State` command to verify
- The state is generated on-demand when MCP requests it
