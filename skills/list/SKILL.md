---
description: "List all KroWork apps and their status"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_list_apps
---

# KroWork: List Apps

Show all KroWork apps with their status and details.

## Workflow

### Step 1: Fetch Apps

Use `mcp__krowork__krowork_list_apps` to get the complete list.

### Step 2: Display

Present the apps in a clear table format:

| # | Name | Description | Version | Status | Created |
|---|------|-------------|---------|--------|---------|

If there are no apps yet, suggest using `/krowork:create` to create their first app.

### Step 3: Suggest Actions

After listing, mention available commands:
- `/krowork:run <name>` - Run an app
- `/krowork:improve <name>` - Improve an app
- `/krowork:delete <name>` - Delete an app
