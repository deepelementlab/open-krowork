---
description: "Delete a KroWork app permanently"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_delete_app, mcp__krowork__krowork_list_apps, mcp__krowork__krowork_stop_app
---

# KroWork: Delete App

Permanently delete a KroWork app and all its files.

## Workflow

### Step 1: Identify the App

The user input `$ARGUMENTS` should contain the app name to delete.

If the name is unclear, use `mcp__krowork__krowork_list_apps` and ask which app to delete.

### Step 2: Confirm Deletion

**IMPORTANT**: Always confirm with the user before deleting. Show:
- App name
- App description
- Warning: "This action is irreversible. All app files, data, and virtual environment will be permanently deleted."

Wait for explicit confirmation (e.g., "yes", "confirm", "delete it").

### Step 3: Stop if Running

If the app is currently running, stop it first using `mcp__krowork__krowork_stop_app`.

### Step 4: Delete

Use `mcp__krowork__krowork_delete_app` with the confirmed app name.

### Step 5: Confirm Result

Tell the user the app has been deleted successfully. If there was an error, show the error message.

## Safety Rules

- NEVER delete without explicit user confirmation
- Always show what will be deleted before confirming
- If the user says "cancel" or "no", abort immediately
