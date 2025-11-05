"""
EditorContextMCP - Sublime Text Plugin
Exposes editor context via Model Context Protocol (MCP)
"""

import sublime
import sublime_plugin
import threading
import json
import http.server
import socketserver
from datetime import datetime


class EditorContextState:
    """Generates current state of the editor on-demand"""

    def get_state_snapshot(self):
        """Get a snapshot of the current state by querying Sublime directly"""
        active_files = []
        other_files = []
        project_folders = []
        seen_files = set()  # Track files we've already processed

        # Iterate through all windows (reversed to get frontmost-first order)
        for window in reversed(sublime.windows()):
            # Collect project folders from all windows
            folders = window.folders()
            for folder in folders:
                if folder not in project_folders:
                    project_folders.append(folder)

            # Get the active view in this window
            active_view = window.active_view()
            active_file_in_window = active_view.file_name() if active_view else None

            # Get all views in this window
            for view in window.views():
                file_name = view.file_name()
                if file_name and file_name not in seen_files:
                    seen_files.add(file_name)

                    # Get selection/cursor info for this view
                    selection_info = None
                    selections = view.sel()

                    if selections and len(selections) > 0:
                        # Get first selection/cursor
                        region = selections[0]

                        if not region.empty():
                            # Has actual selection
                            start_row, start_col = view.rowcol(region.begin())
                            end_row, end_col = view.rowcol(region.end())

                            selection_info = {
                                "start": {"line": start_row + 1, "column": start_col},
                                "end": {"line": end_row + 1, "column": end_col}
                            }
                        else:
                            # Just cursor position
                            cursor_row, cursor_col = view.rowcol(region.begin())
                            selection_info = {
                                "cursor": {"line": cursor_row + 1, "column": cursor_col}
                            }

                    # Create file object
                    file_obj = {
                        "path": file_name,
                        "selection": selection_info
                    }

                    # Add to appropriate list
                    if file_name == active_file_in_window:
                        active_files.append(file_obj)
                    else:
                        other_files.append(file_obj)

        return {
            "activeFiles": active_files,
            "otherFiles": other_files,
            "projectFolders": project_folders,
            "lastUpdated": datetime.now().isoformat()
        }



# Global state instance
editor_state = EditorContextState()


class MCPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Handles MCP protocol requests over HTTP"""

    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        """Handle MCP JSON-RPC requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        try:
            request = json.loads(body)
            response = self.handle_mcp_request(request)

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                },
                "id": request.get("id") if isinstance(request, dict) else None
            }
            self.send_response(500)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(error_response).encode())

    def handle_mcp_request(self, request):
        """Handle MCP protocol request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "resources": {}
                    },
                    "serverInfo": {
                        "name": "sublime-editor-context",
                        "version": "0.1.0"
                    }
                },
                "id": request_id
            }

        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "resources": [
                        {
                            "uri": "sublime-context://state",
                            "name": "Editor State",
                            "description": "Complete editor state with active files per window and other open files",
                            "mimeType": "application/json"
                        }
                    ]
                },
                "id": request_id
            }

        elif method == "resources/read":
            uri = params.get("uri")
            content = self.get_resource_content(uri)

            return {
                "jsonrpc": "2.0",
                "result": {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": content
                        }
                    ]
                },
                "id": request_id
            }

        else:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": "Method not found: {}".format(method)
                },
                "id": request_id
            }

    def get_resource_content(self, uri):
        """Get content for a specific resource URI"""
        if uri == "sublime-context://state":
            return json.dumps(editor_state.get_state_snapshot(), indent=2)
        else:
            raise ValueError("Unknown resource URI: {}".format(uri))


class MCPServer:
    """MCP Server running in background thread"""

    def __init__(self, port=8765):
        self.port = port
        self.server = None
        self.thread = None
        self.running = False

    def start(self):
        """Start the MCP server"""
        if self.running:
            return

        try:
            self.server = socketserver.TCPServer(("127.0.0.1", self.port), MCPRequestHandler)
            self.server.allow_reuse_address = True
            self.running = True

            self.thread = threading.Thread(target=self._run_server)
            self.thread.daemon = True
            self.thread.start()

            print("EditorContextMCP: Server started on http://127.0.0.1:{}".format(self.port))
        except Exception as e:
            print("EditorContextMCP: Failed to start server: {}".format(e))

    def _run_server(self):
        """Run the server (called in background thread)"""
        if self.server:
            self.server.serve_forever()

    def stop(self):
        """Stop the MCP server"""
        if self.server:
            self.server.shutdown()
            self.running = False
            print("EditorContextMCP: Server stopped")


# Global server instance
mcp_server = None


def plugin_loaded():
    """Called when plugin is loaded"""
    global mcp_server

    settings = sublime.load_settings("EditorContextMCP.sublime-settings")
    port = settings.get("mcp_server_port", 8765)

    mcp_server = MCPServer(port=port)
    mcp_server.start()


def plugin_unloaded():
    """Called when plugin is unloaded"""
    global mcp_server
    if mcp_server:
        mcp_server.stop()

class EditorContextShowStateCommand(sublime_plugin.TextCommand):
    """Command to show current editor state (for debugging)"""

    def run(self, edit):
        state = editor_state.get_state_snapshot()

        # Create a new buffer to show the state
        window = self.view.window()
        if window:
            new_view = window.new_file()
            new_view.set_name("Editor Context State")
            new_view.set_scratch(True)
            new_view.set_syntax_file("Packages/JavaScript/JSON.sublime-syntax")
            # Use run_command to insert text with its own edit object
            new_view.run_command('append', {'characters': json.dumps(state, indent=2)})
