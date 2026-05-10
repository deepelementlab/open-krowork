---
description: "Export or import KroWork apps for sharing"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_export_app, mcp__krowork__krowork_import_app, mcp__krowork__krowork_list_apps
---

# KroWork: Share Apps

Export KroWork apps as .krowork archives for sharing, or import apps from archives.

## Workflow - Export

### Step 1: Identify App

The user input `$ARGUMENTS` should specify which app to export.

If unclear, use `krowork_list_apps` to show available apps.

### Step 2: Export

Use `krowork_export_app` with the app name. The archive will be saved to the Desktop by default.

### Step 3: Confirm

Tell the user:
- The export file path and size
- That the recipient can import using `/krowork:share import <path>`

## Workflow - Import

### Step 1: Locate Archive

The user input should contain the path to a `.krowork` file.

### Step 2: Import

Use `krowork_import_app` with the archive path. Optionally specify a new name.

### Step 3: Verify

After import, the app is ready to use. Suggest running it with `/krowork:run`.

## Archive Contents

A `.krowork` archive contains:
- `manifest.json` - Package metadata
- `app.json` - App configuration
- `main.py` - Backend code
- `templates/index.html` - Frontend
- `requirements.txt` - Dependencies
