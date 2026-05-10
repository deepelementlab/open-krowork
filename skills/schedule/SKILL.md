---
description: "Schedule KroWork apps to run automatically"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_create_schedule, mcp__krowork__krowork_list_schedules, mcp__krowork__krowork_delete_schedule, mcp__krowork__krowork_list_apps
---

# KroWork: Schedule

Schedule KroWork apps to run automatically at specified times using OS-level task scheduling.

## Workflow

### Step 1: Identify App and Schedule

The user input `$ARGUMENTS` should contain:
- The app name to schedule
- When to run it (e.g., "every day at 8am", "every 30 minutes", "every monday at 9am")

If the app name is unclear, use `krowork_list_apps` to show available apps.

### Step 2: Parse Schedule Type

Determine the schedule type from the user's description:

| User Says | Type | Parameters |
|-----------|------|------------|
| "every day at 8am" | daily | time: "08:00" |
| "every monday at 9am" | weekly | time: "09:00", days: ["monday"] |
| "every 30 minutes" | interval | command: "30" (minutes) |
| "once at 3pm tomorrow" | once | time: "15:00" |

### Step 3: Create Schedule

Use `krowork_create_schedule` with the parsed parameters. This creates an OS-level scheduled task:
- **Windows**: Task Scheduler via schtasks
- **macOS**: launchd via plist
- **Linux**: cron job

### Step 4: Confirm

Tell the user:
- The schedule type and time
- That the app will run automatically
- How to manage: `/krowork:schedule list` to view, `/krowork:schedule delete` to remove

## Managing Schedules

- **List all**: Use `krowork_list_schedules`
- **Delete**: Use `krowork_delete_schedule` with the app name
