---
description: "Improve an existing KroWork app with new features or fixes"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_auto_improve, mcp__krowork__krowork_list_improvements, mcp__krowork__krowork_get_app, mcp__krowork__krowork_update_app, mcp__krowork__krowork_list_apps, mcp__krowork__krowork_run_app, mcp__krowork__krowork_stop_app, mcp__krowork__krowork_app_status, mcp__krowork__krowork_get_app_log, Read, Write
---

# KroWork: Improve App

Iteratively improve an existing KroWork app using natural language instructions.

## Two Modes

### Mode 1: Auto-Improve (One-Click, Preferred)

For common improvements, use `krowork_auto_improve` which handles changes structurally without rewriting the entire app:

```
krowork_auto_improve(app_name="reading-list", instruction="加一个标签字段")
krowork_auto_improve(app_name="todo-app", instruction="add CSV export")
krowork_auto_improve(app_name="notes", instruction="add search")
krowork_auto_improve(app_name="tracker", instruction="换成绿色主题")
```

**Supported auto-improvements:**
| Type | Example Instructions |
|------|---------------------|
| Add field | "加一个标签字段", "add a tag field" |
| Add export | "加一个导出CSV按钮", "add JSON export" |
| Add search | "加一个搜索框", "add search" |
| Add sorting | "添加排序", "add sorting" |
| Change theme | "换成绿色主题", "change to purple" |

Auto-improve returns `"auto_improved": true` on success, or falls back to Mode 2.

### Mode 2: Manual Improve (Claude Rewrites)

For complex changes that auto-improve can't handle (new routes, API integration, UI redesign):

1. `krowork_get_app` — Read current code and HTML
2. Analyze and plan changes
3. Generate updated code and HTML
4. `krowork_update_app` — Write the changes
5. `krowork_run_app` — Preview

## Workflow

### Step 1: Identify the App

The user input `$ARGUMENTS` should contain:
- An app name (or partial match)
- The improvement instructions

### Step 2: Try Auto-Improve First

**Always try `krowork_auto_improve` first.** This is faster, more reliable, and doesn't risk breaking existing code.

Use `krowork_list_improvements` to see what's available if unsure.

### Step 3: Fallback to Manual if Needed

If `krowork_auto_improve` returns `"auto_improved": false`, fall back to manual mode:
1. Read the current code with `krowork_get_app`
2. Plan and implement changes
3. Update with `krowork_update_app`

### Step 4: Preview

Run the updated app with `krowork_run_app` and tell the user the URL.

### Step 5: Confirm

Ask if the improvement looks good. If more changes needed, repeat from Step 2.
