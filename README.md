<p align="center">
  <img width="200" height="200" alt="workFlow" src="https://github.com/user-attachments/assets/41cebbbc-f2f4-464e-baa1-d83ecc290998" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Claude_Code-MCP_Server-blue?style=for-the-badge" alt="Claude Code MCP">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=for-the-badge" alt="Platform">
</p>

<h1 align="center">Open-KroWork</h1>

<p align="center"><strong>Turn a sentence into a desktop app. Zero code. Zero tokens after creation.</strong></p>

<p align="center">
  Open-KroWork is a <a href="https://docs.anthropic.com/en/docs/claude-code">Claude Code</a> plugin that converts natural language workflows<br>
  into standalone local applications. Describe what you want, get a working app with a desktop shortcut.
</p>

<p align="center">
  <a href="./README.md">English</a> | <a href="./README_CN.md">中文</a>
</p>

---

> **About this project:** Open-KroWork is an open-source implementation of the [KroWork](https://krowork.com/) concept — turning natural language workflows into local desktop apps. This is a community-driven project and is **not** affiliated with Kuaishou (快手) or the official KroWork team. Built as an [MCP server](https://modelcontextprotocol.io/) for [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

---

## What It Does

```
You:  "Build me a stock tracker — input a ticker, show price trends and generate an analysis report"
KroWork: Creates a complete web app, installs dependencies, puts a shortcut on your desktop.
You:  Double-click the shortcut. App runs. No Claude needed anymore.
```

**Core idea:** "Run it once, make it an app."

| Before KroWork | After KroWork |
|---|---|
| Repeat the same prompt every day | Double-click a desktop shortcut |
| Burn tokens on repetitive tasks | Zero tokens — runs locally |
| Results vary each time | Deterministic, 100% reproducible |
| Data goes to cloud APIs | All data stays on your machine |

---

## Demo

### Create an app in one sentence

```
> /krowork:create "Todo Manager - a clean task tracker with priority and status"

✓ App "todo-manager" created
✓ Dependencies installed (flask)
✓ Desktop shortcut created: ~/Desktop/KroWork - Todo Manager.lnk
✓ Running at http://127.0.0.1:5000
```

### What you get

A complete Flask web application with:
- Dark-themed responsive UI
- Full CRUD API (Create / Read / Update / Delete)
- Interactive frontend with real-time updates
- Desktop shortcut — double-click to launch, zero terminal needed

### Auto-improve with one command

```
> /krowork:improve todo-manager "add CSV export and search"

✓ Added CSV export (download button)
✓ Added search functionality (filter by keyword)
✓ Updated to v1.0.2
```

---

## Features

### App Lifecycle

| Feature | Command | Description |
|---|---|---|
| Create | `/krowork:create` | Auto-generate a complete app from description |
| Run | `/krowork:run` | Start app in a sandboxed subprocess |
| Improve | `/krowork:improve` | Auto-improve: add fields, export, search, theme, schedule |
| Delete | `/krowork:delete` | Remove app and all files |

### 33 MCP Tools

<details>
<summary><strong>App Management (10)</strong></summary>

- `krowork_create_app` — Create app from description (auto-generates code)
- `krowork_list_apps` — List all apps
- `krowork_get_app` — Get app details + source code
- `krowork_run_app` — Start app, returns URL
- `krowork_stop_app` — Stop running app
- `krowork_update_app` — Update code/template/requirements
- `krowork_delete_app` — Delete app permanently
- `krowork_app_status` — Check running status
- `krowork_get_app_log` — Get app logs
- `krowork_create_shortcut` — Create desktop shortcut
</details>

<details>
<summary><strong>Web Scraping (7)</strong></summary>

- `krowork_scrape_page` — Fetch page: title, text, links, metadata
- `krowork_scrape_elements` — Extract elements by CSS selector
- `krowork_scrape_rss` — Parse RSS/Atom feeds
- `krowork_scrape_table` — Extract HTML tables
- `krowork_scrape_api` — Call REST API endpoints
- `krowork_monitor_page` — Detect page content changes
- `krowork_preprocess_content` — Clean content for AI summarization
</details>

<details>
<summary><strong>Data Sources (4)</strong></summary>

- `krowork_register_datasource` — Register API/RSS/Web/File/SQLite source
- `krowork_list_datasources` — List registered sources
- `krowork_fetch_datasource` — Fetch data from a source
- `krowork_delete_datasource` — Remove a source
</details>

<details>
<summary><strong>Export & Import (2)</strong></summary>

- `krowork_export_app` — Package app as `.krowork` archive
- `krowork_import_app` — Import app from `.krowork` archive
</details>

<details>
<summary><strong>Scheduling (3)</strong></summary>

- `krowork_create_schedule` — Schedule app (daily/weekly/interval)
- `krowork_list_schedules` — List scheduled tasks
- `krowork_delete_schedule` — Remove scheduled task
</details>

<details>
<summary><strong>Cross-Device Sync (5)</strong></summary>

- `krowork_sync_configure` — Set sync folder (OneDrive/Dropbox/etc.)
- `krowork_sync_push` — Push local apps to sync folder
- `krowork_sync_pull` — Pull remote apps from sync folder
- `krowork_sync_status` — Check what needs sync
- `krowork_sync_list_remote` — List apps in sync folder
</details>

<details>
<summary><strong>Auto-Improve (2)</strong></summary>

- `krowork_auto_improve` — One-command app improvement
- `krowork_list_improvements` — Show available improvements
</details>

### 11 Slash Commands (Skills)

| Command | What It Does |
|---|---|
| `/krowork:create` | Create a new app from natural language |
| `/krowork:list` | Show all apps |
| `/krowork:run` | Run an app |
| `/krowork:improve` | Improve an app (auto + manual) |
| `/krowork:delete` | Delete an app |
| `/krowork:scrape` | Scrape web pages, RSS, APIs |
| `/krowork:datasource` | Manage data sources |
| `/krowork:summarize` | AI-powered web content summarization |
| `/krowork:share` | Export/import apps for sharing |
| `/krowork:schedule` | Schedule apps to run automatically |
| `/krowork:sync` | Sync apps across devices |

### Auto-Improve: One Command, Six Improvements

| Type | Example Instruction |
|---|---|
| Add field | `"add a tags field"` |
| Add export | `"add CSV export"` / `"add markdown export"` |
| Add search | `"add search functionality"` |
| Add sorting | `"add sorting by time"` |
| Change theme | `"change to green theme"` / `"switch to light mode"` |
| Schedule | `"run daily at 8am"` |
| Highlight | `"highlight AI-related content in red"` |
| Add data source | `"add a new API data source"` |

---

## Quick Start

### Prerequisites

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed
- Python 3.9+

### Install

```bash
git clone https://github.com/YOUR_USERNAME/open-krowork.git
cd open-krowork

# Install Python dependencies (3 packages only)
pip install -r requirements.txt
```

### Usage Mode 1: Plugin (Recommended)

```bash
claude --plugin-dir /path/to/open-krowork
```

`--plugin-dir` loads `.claude-plugin/plugin.json` and registers the MCP server automatically.

**What you get:**

| Feature | Available |
|---|---|
| Slash commands (`/krowork:create`, `/krowork:run`, etc.) | Yes |
| MCP tools (called by Claude automatically) | Yes |
| Skills workflow (guided step-by-step) | Yes |

**How to use:** Type `/krowork:create`, `/krowork:list`, `/krowork:run`, etc. directly.

### Usage Mode 2: MCP Server (Global)

If you want KroWork available in **every** Claude Code session, regardless of directory:

```bash
# Register once:
claude mcp add krowork -s user -- python /path/to/open-krowork/server/main.py

# Then just run `claude` from anywhere:
claude
```

**What you get:**

| Feature | Available |
|---|---|
| Slash commands (`/krowork:create`, etc.) | No |
| MCP tools (called by Claude automatically) | Yes |
| Skills workflow | No |

**How to use:** No slash commands. Just describe what you want in natural language and Claude will call the tools automatically. Examples:

```
You:  Create a bookmark manager app with tags
Claude: [calls krowork_create_app("bookmark-manager", "Bookmark Manager - ...")]

You:  List all my apps
Claude: [calls krowork_list_apps]

You:  Run the bookmark-manager app
Claude: [calls krowork_run_app("bookmark-manager")]
```

Run `claude mcp list` to verify. Both modes can coexist.

**Dependencies** (only 3):

| Package | Version | Used By |
|---|---|---|
| `requests` | >=2.28 | Web scraping, data sources, API calls |
| `beautifulsoup4` | >=4.11 | HTML parsing, web scraping |
| `Pillow` | >=9.0 | App icon generation |

Restart Claude Code and KroWork is ready. Run `claude mcp list` to verify.

### Usage

```bash
# Start Claude Code
claude

# Create your first app
> /krowork:create "Bookmark Manager - save and organize web bookmarks with tags"

# Run it
> /krowork:run bookmark-manager

# Improve it
> /krowork:improve bookmark-manager "add search and CSV export"

# Now double-click the desktop shortcut — your app runs without Claude!
```

---

## Architecture

```
open-krowork/
├── requirements.txt          # Python dependencies (3 packages)
├── install.sh                # One-click installer (macOS/Linux)
├── install.bat               # One-click installer (Windows)
├── settings.json             # User settings
├── hooks/
│   └── hooks.json            # Lifecycle hooks
├── server/                   # Core engine (registered via `claude mcp add`)
│   ├── main.py              # MCP server (33 tools, stdio transport)
│   ├── app_manager.py       # App CRUD + desktop shortcuts
│   ├── code_generator.py    # Auto-code generation (3 templates)
│   ├── auto_improve.py      # Structured auto-improvement
│   ├── sandbox.py           # Sandboxed subprocess runner
│   ├── scraper.py           # Web scraping (10 functions)
│   ├── datasource.py        # Data source registry (5 types)
│   ├── app_export.py        # Export/import (.krowork archives)
│   ├── scheduler.py         # OS-level task scheduling
│   ├── sync.py              # Cross-device sync
│   └── icon_generator.py    # App icon generation
└── skills/                  # 11 slash commands
    ├── create/
    ├── improve/
    ├── scrape/
    ├── summarize/
    ├── sync/
    └── ...
```

### How It Works

```
Natural Language Description
         ↓
   AI analyzes intent (CRUD / Dashboard / Tool)
         ↓
   Generates Flask backend + dark-themed HTML frontend
         ↓
   Creates venv, installs dependencies
         ↓
   Desktop shortcut (.lnk / .desktop)
         ↓
   User double-clicks → app runs locally, zero tokens
```

### Auto-Code Generation

The code generator analyzes descriptions and generates one of three app types:

| Type | Generated When | Features |
|---|---|---|
| **CRUD** | Generic data management | Full CRUD API + list/add/delete UI |
| **Dashboard** | Stock/weather/news keywords | Stats cards + Chart.js graphs + search |
| **Tool** | Generator/converter keywords | Input → Process → Output + history |

---

## Security

- **Local-first**: All code runs in subprocess sandboxes on your machine
- **Zero upload**: App data never leaves your device
- **Permission-based**: Destructive operations require explicit confirmation
- **Isolated venvs**: Each app has its own virtual environment

---

## Roadmap

- [x] Phase 1 — Core: Plugin framework, code generation, app lifecycle
- [x] Phase 2 — Experience: Web scraping, desktop shortcuts, data sources
- [x] Phase 3 — Ecosystem: Export/import, scheduling, more templates
- [x] Phase 4 — Advanced: Cross-device sync, auto-improve, content analysis
- [ ] Phase 5 — Community: App marketplace, team sharing, plugin API

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- Built on [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Plugin SDK
- Powered by [Flask](https://flask.palletsprojects.com/) for app generation
- Uses [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) for web scraping
- Charts via [Chart.js](https://www.chartjs.org/)
