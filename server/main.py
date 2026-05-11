"""Open-KroWork MCP Server - stdio transport.

Provides tools for creating, managing, running, and deleting local apps.
"""

import json
import os
import sys
import traceback

# Ensure local imports work regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_manager import create_app, list_apps, get_app, update_app, delete_app, create_shortcut_for_app
from code_generator import auto_generate_app
from sandbox import start_app, stop_app, get_app_status, list_running_apps, get_app_log
from scraper import (fetch_page, extract_elements, scrape_rss, scrape_table,
                     scrape_multi_page, extract_text_from_pdf,
                     scrape_paginated, scrape_with_auth, scrape_api, monitor_page,
                     preprocess_content)
from datasource import (register_source, list_sources, get_source, delete_source,
                        fetch_data)
from app_export import export_app, import_app, list_exported
from scheduler import (create_schedule, delete_schedule, list_schedules, get_schedule)
from sync import (configure_sync, get_sync_config, disable_sync,
                  sync_push, sync_pull, sync_status, sync_list_remote)
from auto_improve import auto_improve, list_improvements


# --- MCP Protocol Helpers ---

def send_result(result: dict):
    """Send a JSON-RPC result response."""
    msg = {"jsonrpc": "2.0", "id": _current_id, "result": result}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def send_error(code: int, message: str, data=None):
    """Send a JSON-RPC error response."""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    msg = {"jsonrpc": "2.0", "id": _current_id, "error": error}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


_current_id = None

# --- Tool Definitions ---

TOOLS = [
    {
        "name": "krowork_create_app",
        "description": (
            "Create a new KroWork local app. If 'code' is not provided, "
            "automatically generates a complete working application based on "
            "the description. Generates project structure with Flask web server, "
            "creates a desktop shortcut, and installs dependencies in the background. "
            "The app will be ready to run shortly after creation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name for the app (lowercase, hyphens allowed)",
                },
                "description": {
                    "type": "string",
                    "description": "Human-readable description of what the app does. "
                    "Be specific about features, data fields, and behavior. "
                    "Example: 'Stock analysis tool - input stock code, show price trends and analysis report'",
                },
                "code": {
                    "type": "string",
                    "description": "Optional: The main Python (Flask) application code. "
                    "If omitted, the system auto-generates a complete app from the description.",
                },
                "requirements": {
                    "type": "string",
                    "description": "pip requirements (one per line), e.g. 'flask\\nrequests'",
                },
                "html_template": {
                    "type": "string",
                    "description": "Optional: HTML template for the web UI. "
                    "If omitted, auto-generated from the description.",
                },
                "config": {
                    "type": "object",
                    "description": "Optional app configuration. "
                    "Can include: entity_name, fields (array of {name, type, label}), "
                    "features, api_url, etc.",
                },
            },
            "required": ["app_name", "description"],
        },
    },
    {
        "name": "krowork_list_apps",
        "description": "List all KroWork apps with their status.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "krowork_get_app",
        "description": (
            "Get detailed info about a specific KroWork app, including full source code."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to inspect",
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "krowork_run_app",
        "description": (
            "Start a KroWork app in a local subprocess. Returns the URL to access it."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to run",
                },
                "port": {
                    "type": "integer",
                    "description": "Optional port number (auto-assigned if omitted)",
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "krowork_stop_app",
        "description": "Stop a running KroWork app.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to stop",
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "krowork_update_app",
        "description": (
            "Update an existing KroWork app's code, template, requirements, or config."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to update",
                },
                "code": {
                    "type": "string",
                    "description": "Updated main Python code",
                },
                "html_template": {
                    "type": "string",
                    "description": "Updated HTML template",
                },
                "requirements": {
                    "type": "string",
                    "description": "Updated pip requirements",
                },
                "description": {
                    "type": "string",
                    "description": "Updated description",
                },
                "config": {
                    "type": "object",
                    "description": "Updated configuration",
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "krowork_delete_app",
        "description": "Delete a KroWork app and all its files permanently.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to delete",
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "krowork_app_status",
        "description": "Check the running status of a KroWork app.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to check",
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "krowork_get_app_log",
        "description": "Get the recent log output of a running KroWork app.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app",
                },
                "tail": {
                    "type": "integer",
                    "description": "Number of recent log lines to return (default: 50)",
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "krowork_create_shortcut",
        "description": (
            "Create or recreate a desktop shortcut for an existing KroWork app. "
            "Double-clicking the shortcut starts the app and opens the browser."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to create a shortcut for",
                },
            },
            "required": ["app_name"],
        },
    },
    # --- Web Scraping Tools ---
    {
        "name": "krowork_scrape_page",
        "description": (
            "Fetch a web page and extract its title, text content, links, and metadata. "
            "Useful for reading web content or gathering information from URLs."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "timeout": {"type": "integer", "description": "Request timeout in seconds (default: 30)"},
                "cache_ttl": {"type": "integer", "description": "Cache TTL in seconds (default: 300, 0 to disable)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "krowork_scrape_elements",
        "description": (
            "Extract specific elements from a web page using CSS selectors. "
            "Returns text, URLs, and attributes of matching elements."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch"},
                "selector": {"type": "string", "description": "CSS selector (e.g., 'h2 a', '.article-title')"},
            },
            "required": ["url", "selector"],
        },
    },
    {
        "name": "krowork_scrape_rss",
        "description": "Parse an RSS or Atom feed and return its entries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "RSS/Atom feed URL"},
                "max_items": {"type": "integer", "description": "Max items to return (default: 20)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "krowork_scrape_table",
        "description": "Extract data from an HTML table on a web page.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL containing the table"},
                "table_index": {"type": "integer", "description": "Which table to extract, 0-based (default: 0)"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "krowork_scrape_api",
        "description": "Call a REST API endpoint and return the JSON response.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "API endpoint URL"},
                "method": {"type": "string", "description": "HTTP method (default: GET)"},
                "body": {"type": "object", "description": "Request body (for POST/PUT)"},
                "headers": {"type": "object", "description": "Custom headers"},
                "params": {"type": "object", "description": "Query parameters"},
                "json_path": {"type": "string", "description": "Dot-notation path to extract (e.g., 'data.items')"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "krowork_monitor_page",
        "description": (
            "Check if a web page's content has changed since the last check. "
            "Useful for monitoring pages for updates."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to monitor"},
                "selector": {"type": "string", "description": "CSS selector for content to track"},
            },
            "required": ["url", "selector"],
        },
    },
    {
        "name": "krowork_preprocess_content",
        "description": (
            "Fetch a web page and preprocess its content for AI summarization. "
            "Returns cleaned text, key points (headings), metadata, and stats. "
            "The caller (Claude) should then use its own AI capabilities to "
            "produce summaries, analyses, or translations based on this data."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch and preprocess"},
                "max_length": {"type": "integer", "description": "Max text length (default: 8000)"},
            },
            "required": ["url"],
        },
    },
    # --- Data Source Tools ---
    {
        "name": "krowork_register_datasource",
        "description": "Register a data source for repeated use (REST API, RSS, web scraping, local file, or SQLite).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Human-readable name for the data source"},
                "source_type": {"type": "string", "description": "Type: rest_api, rss, web_scrape, local_file, sqlite"},
                "config": {"type": "object", "description": "Source-specific config (url, method, headers, params, etc.)"},
            },
            "required": ["name", "source_type", "config"],
        },
    },
    {
        "name": "krowork_list_datasources",
        "description": "List all registered data sources.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "krowork_fetch_datasource",
        "description": "Fetch data from a registered data source by name.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_name": {"type": "string", "description": "Name of the registered data source"},
            },
            "required": ["source_name"],
        },
    },
    {
        "name": "krowork_delete_datasource",
        "description": "Delete a registered data source.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the data source to delete"},
            },
            "required": ["name"],
        },
    },
    # --- App Export/Import Tools ---
    {
        "name": "krowork_export_app",
        "description": (
            "Export a KroWork app as a .krowork archive for sharing. "
            "The archive contains all source code, templates, and metadata."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the app to export"},
                "output_path": {"type": "string", "description": "Optional output file path (defaults to Desktop)"},
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "krowork_import_app",
        "description": (
            "Import a KroWork app from a .krowork archive. "
            "Creates a new app with full functionality and desktop shortcut."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "krowork_path": {"type": "string", "description": "Path to the .krowork archive file"},
                "new_name": {"type": "string", "description": "Optional new name for the imported app"},
            },
            "required": ["krowork_path"],
        },
    },
    # --- Scheduler Tools ---
    {
        "name": "krowork_create_schedule",
        "description": (
            "Schedule a KroWork app to run automatically at specified times. "
            "Supports daily, weekly, interval, and one-time schedules."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the app to schedule"},
                "schedule_type": {"type": "string", "description": "Type: daily, weekly, interval, once (default: daily)"},
                "time_str": {"type": "string", "description": "Time in HH:MM format (default: 08:00)"},
                "days": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Weekday names for weekly schedule (e.g., ['monday', 'friday'])",
                },
            },
            "required": ["app_name"],
        },
    },
    {
        "name": "krowork_list_schedules",
        "description": "List all scheduled tasks.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "krowork_delete_schedule",
        "description": "Remove a scheduled task for an app.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the app"},
            },
            "required": ["app_name"],
        },
    },
    # --- Cross-Device Sync Tools ---
    {
        "name": "krowork_sync_configure",
        "description": (
            "Configure cross-device sync by pointing to a cloud-synced folder "
            "(e.g., OneDrive/KroWork, Dropbox/Apps/KroWork, or any shared folder). "
            "Apps are synced as .krowork packages. Data stays in user's control."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_dir": {"type": "string", "description": "Path to sync folder"},
                "device_name": {"type": "string", "description": "Optional device name for conflict resolution"},
            },
            "required": ["target_dir"],
        },
    },
    {
        "name": "krowork_sync_push",
        "description": "Push local apps to the sync target folder. Only pushes changed apps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "force": {"type": "boolean", "description": "Force push all apps (default: false)"},
            },
        },
    },
    {
        "name": "krowork_sync_pull",
        "description": "Pull new/updated apps from the sync target folder.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "overwrite": {"type": "boolean", "description": "Overwrite local changes (default: false)"},
            },
        },
    },
    {
        "name": "krowork_sync_status",
        "description": "Check sync status: what needs to be pushed or pulled.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "krowork_sync_list_remote",
        "description": "List apps available in the sync target folder.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    # --- Auto-Improve ---
    {
        "name": "krowork_auto_improve",
        "description": (
            "Automatically improve an existing app with a single instruction. "
            "Handles common improvements without rewriting the entire app: "
            "add fields, add export (CSV/JSON/Markdown), add search, add sorting, "
            "change theme colors. For complex changes, returns guidance for Claude "
            "to manually rewrite."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the app to improve"},
                "instruction": {
                    "type": "string",
                    "description": "Natural language improvement instruction. "
                    "Examples: '加一个标签字段', 'add CSV export', 'add search', '换成绿色主题'",
                },
            },
            "required": ["app_name", "instruction"],
        },
    },
    {
        "name": "krowork_list_improvements",
        "description": "List available auto-improvements for an app.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the app"},
            },
            "required": ["app_name"],
        },
    },
]


# --- Tool Dispatch ---

def handle_tool_call(name: str, arguments: dict) -> dict:
    """Dispatch a tool call to the appropriate handler."""

    if name == "krowork_create_app":
        code = arguments.get("code", "")
        html_template = arguments.get("html_template", "")
        requirements = arguments.get("requirements", "")
        app_name = arguments["app_name"]
        description = arguments["description"]
        config = arguments.get("config")

        # Auto-generate complete app when code is empty or just a skeleton
        is_skeleton = (
            not code.strip()
            or code.strip().startswith("@")  # Just decorators, no logic
            or (code.count("@app.route") <= 1 and code.count("def ") <= 2)
        )
        if is_skeleton or not html_template.strip():
            generated = auto_generate_app(app_name, description, config)
            if not code.strip():
                code = generated["code"]
            if not html_template.strip():
                html_template = generated["html_template"]
            if not requirements.strip():
                requirements = generated["requirements"]

        result = create_app(
            app_name=app_name,
            description=description,
            code=code,
            requirements=requirements,
            html_template=html_template,
            config=config,
        )

    elif name == "krowork_list_apps":
        result = list_apps()

    elif name == "krowork_get_app":
        result = get_app(arguments["app_name"])

    elif name == "krowork_run_app":
        result = start_app(
            app_name=arguments["app_name"],
            port=arguments.get("port"),
        )

    elif name == "krowork_stop_app":
        result = stop_app(arguments["app_name"])

    elif name == "krowork_update_app":
        result = update_app(
            app_name=arguments["app_name"],
            code=arguments.get("code"),
            html_template=arguments.get("html_template"),
            requirements=arguments.get("requirements"),
            description=arguments.get("description"),
            config=arguments.get("config"),
        )

    elif name == "krowork_delete_app":
        result = delete_app(arguments["app_name"])

    elif name == "krowork_app_status":
        result = get_app_status(arguments["app_name"])

    elif name == "krowork_get_app_log":
        result = get_app_log(
            app_name=arguments["app_name"],
            tail=arguments.get("tail", 50),
        )

    elif name == "krowork_create_shortcut":
        result = create_shortcut_for_app(arguments["app_name"])

    # --- Web Scraping ---
    elif name == "krowork_scrape_page":
        result = fetch_page(
            url=arguments["url"],
            timeout=arguments.get("timeout", 30),
            cache_ttl=arguments.get("cache_ttl", 300),
        )

    elif name == "krowork_scrape_elements":
        result = extract_elements(
            url=arguments["url"],
            selector=arguments["selector"],
        )

    elif name == "krowork_scrape_rss":
        result = scrape_rss(
            url=arguments["url"],
            max_items=arguments.get("max_items", 20),
        )

    elif name == "krowork_scrape_table":
        result = scrape_table(
            url=arguments["url"],
            table_index=arguments.get("table_index", 0),
        )

    elif name == "krowork_scrape_api":
        result = scrape_api(
            url=arguments["url"],
            method=arguments.get("method", "GET"),
            body=arguments.get("body"),
            headers=arguments.get("headers"),
            params=arguments.get("params"),
            json_path=arguments.get("json_path", ""),
        )

    elif name == "krowork_monitor_page":
        result = monitor_page(
            url=arguments["url"],
            selector=arguments["selector"],
        )

    elif name == "krowork_preprocess_content":
        result = preprocess_content(
            url=arguments["url"],
            max_length=arguments.get("max_length", 8000),
        )

    # --- Data Sources ---
    elif name == "krowork_register_datasource":
        result = register_source(
            name=arguments["name"],
            source_type=arguments["source_type"],
            config=arguments["config"],
        )

    elif name == "krowork_list_datasources":
        result = list_sources()

    elif name == "krowork_fetch_datasource":
        result = fetch_data(arguments["source_name"])

    elif name == "krowork_delete_datasource":
        result = delete_source(arguments["name"])

    # --- Export/Import ---
    elif name == "krowork_export_app":
        result = export_app(
            app_name=arguments["app_name"],
            output_path=arguments.get("output_path"),
        )

    elif name == "krowork_import_app":
        result = import_app(
            krowork_path=arguments["krowork_path"],
            new_name=arguments.get("new_name"),
        )

    # --- Scheduler ---
    elif name == "krowork_create_schedule":
        result = create_schedule(
            app_name=arguments["app_name"],
            schedule_type=arguments.get("schedule_type", "daily"),
            time_str=arguments.get("time_str", "08:00"),
            days=arguments.get("days"),
        )

    elif name == "krowork_list_schedules":
        result = list_schedules()

    elif name == "krowork_delete_schedule":
        result = delete_schedule(arguments["app_name"])

    # --- Cross-Device Sync ---
    elif name == "krowork_sync_configure":
        result = configure_sync(
            target_dir=arguments["target_dir"],
            device_name=arguments.get("device_name", ""),
        )

    elif name == "krowork_sync_push":
        result = sync_push(force=arguments.get("force", False))

    elif name == "krowork_sync_pull":
        result = sync_pull(overwrite=arguments.get("overwrite", False))

    elif name == "krowork_sync_status":
        result = sync_status()

    elif name == "krowork_sync_list_remote":
        result = sync_list_remote()

    # --- Auto-Improve ---
    elif name == "krowork_auto_improve":
        result = auto_improve(
            app_name=arguments["app_name"],
            instruction=arguments["instruction"],
        )

    elif name == "krowork_list_improvements":
        result = list_improvements(arguments["app_name"])

    else:
        return {
            "content": [
                {"type": "text", "text": f"Unknown tool: {name}"}
            ],
            "isError": True,
        }

    # Check for errors returned by handlers
    if "error" in result:
        return {
            "content": [
                {"type": "text", "text": f"Error: {result['error']}"}
            ],
            "isError": True,
        }

    return {
        "content": [
            {"type": "text", "text": json.dumps(result, indent=2, ensure_ascii=False)}
        ],
    }


# --- JSON-RPC Message Handling ---

def handle_initialize(params: dict) -> dict:
    """Handle the initialize request."""
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {
                "listChanged": False,
            },
        },
        "serverInfo": {
            "name": "krowork",
            "version": "0.1.0",
        },
    }


def process_message(msg: dict):
    """Process a single JSON-RPC message."""
    global _current_id
    _current_id = msg.get("id")

    method = msg.get("method", "")
    params = msg.get("params", {})

    # Notifications (no id) - just acknowledge
    if "id" not in msg:
        return

    if method == "initialize":
        send_result(handle_initialize(params))

    elif method == "initialized":
        # Notification, no response needed
        pass

    elif method == "tools/list":
        send_result({"tools": TOOLS})

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        try:
            result = handle_tool_call(tool_name, arguments)
            send_result(result)
        except Exception as e:
            send_error(-32603, f"Tool execution error: {e}", traceback.format_exc())

    elif method == "ping":
        send_result({})

    else:
        send_error(-32601, f"Method not found: {method}")


def main():
    """Main entry point - read JSON-RPC from stdin."""
    # Log to stderr for debugging
    print("Open-KroWork MCP Server starting (stdio)...", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
            process_message(msg)
        except json.JSONDecodeError as e:
            error_msg = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"},
            }
            sys.stdout.write(json.dumps(error_msg) + "\n")
            sys.stdout.flush()
        except Exception as e:
            print(f"Error processing message: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    main()
