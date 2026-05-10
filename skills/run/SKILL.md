---
description: "Run a previously created KroWork app"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_run_app, mcp__krowork__krowork_list_apps, mcp__krowork__krowork_stop_app, mcp__krowork__krowork_app_status, mcp__krowork__krowork_get_app_log
---

# KroWork: Run App

Run a previously created KroWork app on your local machine.

## Workflow

### Step 1: Determine the App

The user input `$ARGUMENTS` may contain:
- An exact app name (e.g., "todo-app")
- A partial name or description
- Nothing (list all available apps)

If the user specified an app name, run it directly.
If the input is unclear or empty, use `mcp__krowork__krowork_list_apps` to show all available apps and ask which one to run.

### Step 2: Start the App

Use `mcp__krowork__krowork_run_app` with the app name. This will:
- Start the Flask server in a subprocess
- Wait for the server to be ready
- Automatically open the browser
- Return the URL

### Step 3: Verify and Show Result

After starting, use `mcp__krowork__krowork_app_status` to verify the app is running.

If the app started successfully, tell the user:
- The URL where the app is running
- That the browser should have opened automatically
- How to stop it: `/krowork:delete` or just close this session

If the app failed to start, use `mcp__krowork__krowork_get_app_log` to get the error details and show them to the user.
