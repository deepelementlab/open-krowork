"""Open-KroWork Auto-Improve - Structured automatic improvements for existing apps.

Handles common improvement types without requiring Claude to rewrite the entire app.
For complex changes, falls back to the manual improve workflow (Claude reads and edits).

Supported auto-improvements:
  - add_field:      Add a new data field to CRUD apps
  - add_export:     Add CSV/JSON export endpoint
  - add_search:     Add search/filter functionality
  - add_sort:       Add sorting by any field
  - add_pagination: Add pagination to the list view
  - change_theme:   Change the color theme
  - add_chart:      Add a chart to dashboard apps
  - regenerate:     Fully regenerate from updated description (fallback)
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from app_manager import get_app, get_app_dir, app_exists, update_app


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def auto_improve(app_name: str, instruction: str) -> dict:
    """Automatically improve an app based on a natural language instruction.

    Analyzes the instruction, determines the improvement type, and applies
    structured changes to the app's code and HTML template.

    Args:
        app_name: Name of the app to improve
        instruction: Natural language improvement instruction

    Returns:
        dict with success info and changes made
    """
    if not app_exists(app_name):
        return {"error": f"App '{app_name}' not found"}

    # Get current app state
    app_info = get_app(app_name)
    if "error" in app_info:
        return app_info

    code = app_info.get("code", "")
    html = app_info.get("html_template", "")
    requirements = app_info.get("requirements", "")
    description = app_info.get("description", "")

    if not code or not html:
        return {"error": "App has no code or template to improve"}

    # Analyze the instruction to determine improvement type
    imp_type, params = _analyze_instruction(instruction)

    # Apply the improvement
    changes = []

    if imp_type == "add_field":
        result = _apply_add_field(code, html, params)
        changes.append(f"Added field: {params.get('field_name', 'new_field')}")
    elif imp_type == "add_export":
        result = _apply_add_export(code, html, params)
        changes.append(f"Added export: {params.get('format', 'csv')}")
    elif imp_type == "add_search":
        result = _apply_add_search(code, html, params)
        changes.append("Added search functionality")
    elif imp_type == "add_sort":
        result = _apply_add_sort(code, html, params)
        changes.append("Added sorting")
    elif imp_type == "change_theme":
        result = _apply_change_theme(html, params)
        changes.append(f"Changed theme to: {params.get('theme', 'green')}")
    elif imp_type == "add_schedule":
        result = _apply_add_schedule(app_name, params)
        changes.append(f"Scheduled: {params.get('schedule_type', 'daily')} at {params.get('time_str', '08:00')}")
    elif imp_type == "add_datasource":
        result = _apply_add_datasource(app_name, code, html, params)
        changes.append(f"Added data source: {params.get('source_type', 'rest_api')}")
    elif imp_type == "add_highlight":
        result = _apply_add_highlight(html, params)
        changes.append(f"Added highlighting for: {params.get('keyword', '')} ({params.get('color', 'red')})")
    else:
        # Fall back to full regeneration with updated description
        return {
            "auto_improved": False,
            "reason": "Complex change requires Claude to analyze and rewrite",
            "suggestion": (
                f"Use the manual improve workflow instead:\n"
                f"1. krowork_get_app('{app_name}') to read current code\n"
                f"2. Claude analyzes and plans changes\n"
                f"3. krowork_update_app with modified code/html\n"
                f"4. krowork_run_app to preview"
            ),
            "instruction": instruction,
            "app_name": app_name,
        }

    if "error" in result:
        return {"error": result["error"], "app_name": app_name}

    # For schedule/datasource, the apply function handles everything
    # (no code/html update needed)
    if imp_type in ("add_schedule", "add_datasource"):
        return {
            "auto_improved": True,
            "improvement_type": imp_type,
            "changes": changes,
            "app_name": app_name,
            "message": f"App '{app_name}' improved: {'; '.join(changes)}",
            **result,
        }

    # For code/html changes, apply updates
    new_code = result.get("code", code)
    new_html = result.get("html", html)
    new_reqs = result.get("requirements", requirements)

    update_result = update_app(
        app_name=app_name,
        code=new_code,
        html_template=new_html,
        requirements=new_reqs if new_reqs != requirements else None,
    )

    if "error" in update_result:
        return update_result

    return {
        "auto_improved": True,
        "improvement_type": imp_type,
        "changes": changes,
        "new_version": update_result.get("version"),
        "app_name": app_name,
        "message": f"App '{app_name}' improved: {'; '.join(changes)}",
    }


# ---------------------------------------------------------------------------
# Instruction Analysis
# ---------------------------------------------------------------------------

def _analyze_instruction(instruction: str) -> tuple:
    """Analyze instruction to determine improvement type and parameters."""
    inst = instruction.lower().strip()

    # Add field
    field_patterns = [
        r"加(一)?个(.+?)字段",
        r"add\s+(?:a\s+)?(.+?)\s+field",
        r"增加(.+?)列",
        r"添加(.+?)属性",
    ]
    for pat in field_patterns:
        m = re.search(pat, inst)
        if m:
            field_name = m.group(m.lastindex).strip()
            return "add_field", {"field_name": field_name}

    # Add export
    if any(kw in inst for kw in ["导出", "export", "下载", "download", "csv", "json", "excel"]):
        fmt = "csv"
        if "json" in inst:
            fmt = "json"
        elif "excel" in inst or "xlsx" in inst:
            fmt = "csv"  # Use CSV for simplicity
        elif "markdown" in inst or "md" in inst:
            fmt = "markdown"
        return "add_export", {"format": fmt}

    # Add search
    if any(kw in inst for kw in ["搜索", "search", "查找", "filter", "筛选", "过滤", "查询"]):
        return "add_search", {}

    # Add sort
    if any(kw in inst for kw in ["排序", "sort", "排列", "order"]):
        return "add_sort", {}

    # Change theme
    if any(kw in inst for kw in ["主题", "theme", "颜色", "color", "配色", "暗色", "亮色",
                                  "风格", "style", "换肤", "皮肤"]):
        theme = "default"
        if any(t in inst for t in ["绿", "green", "翠"]):
            theme = "green"
        elif any(t in inst for t in ["紫", "purple", "粉"]):
            theme = "purple"
        elif any(t in inst for t in ["橙", "orange", "暖"]):
            theme = "orange"
        elif any(t in inst for t in ["红", "red"]):
            theme = "red"
        elif any(t in inst for t in ["亮", "light", "白", "white"]):
            theme = "light"
        return "change_theme", {"theme": theme}

    # Schedule task (check BEFORE datasource to avoid "add api" conflict)
    if any(kw in inst for kw in ["定时", "schedule", "每天", "每周", "自动运行", "定期",
                                  "cron", "定时任务", "计划任务",
                                  "daily", "weekly", "hourly", "automatically",
                                  "every day", "every week"]):
        # Also match "at 8am" / "at 9:30" patterns (but not "add a field")
        at_time_match = re.search(r"\bat\s+\d", inst)
        schedule_type = "daily"
        time_str = "08:00"
        # Parse time (support: 8am, 9:30, 21:30, 8点, 早上8点)
        time_match = re.search(r"(\d{1,2})[点时:：](\d{0,2})", inst)
        am_pm_match = re.search(r"(\d{1,2})(am|pm)", inst)
        if time_match:
            h = time_match.group(1).zfill(2)
            m = (time_match.group(2) or "00").zfill(2)
            time_str = f"{h}:{m}"
        elif am_pm_match:
            h = int(am_pm_match.group(1))
            ampm = am_pm_match.group(2)
            if ampm == "pm" and h < 12:
                h += 12
            elif ampm == "am" and h == 12:
                h = 0
            time_str = f"{str(h).zfill(2)}:00"
        elif any(kw in inst for kw in ["早上", "早晨", "morning"]):
            time_str = "08:00"
        elif any(kw in inst for kw in ["晚上", "evening", "夜间"]):
            time_str = "20:00"
        elif any(kw in inst for kw in ["中午", "noon"]):
            time_str = "12:00"
        if any(kw in inst for kw in ["每周", "weekly", "周一", "周二", "周三", "周四", "周五", "周六", "周日"]):
            schedule_type = "weekly"
        elif any(kw in inst for kw in ["每小时", "hourly"]):
            schedule_type = "interval"
            time_str = "60"  # minutes
        elif any(kw in inst for kw in ["每分钟", "every minute"]):
            schedule_type = "interval"
            time_str = "1"
        return "add_schedule", {"schedule_type": schedule_type, "time_str": time_str}

    # Add data source
    if any(kw in inst for kw in ["数据源", "datasource", "数据来源", "增加源", "add source",
                                  "rss", "feed", "接口", "api"]):
        source_type = "rest_api"
        if "rss" in inst or "feed" in inst or "订阅" in inst:
            source_type = "rss"
        elif "网页" in inst or "scrape" in inst or "抓取" in inst:
            source_type = "web_scrape"
        return "add_datasource", {"source_type": source_type}

    # Data display / highlighting
    if any(kw in inst for kw in ["高亮", "highlight", "标红", "标黄", "标绿",
                                  "标记", "强调", "醒目"]):
        keyword = ""
        # Try to extract the keyword to highlight
        kw_match = re.search(r"[\"「『](.+?)[」』\"]", inst)
        if kw_match:
            keyword = kw_match.group(1)
        else:
            # Try "XXX相关内容" pattern
            kw_match2 = re.search(r"(.+?)(相关|内容|关键词)", inst)
            if kw_match2:
                keyword = kw_match2.group(1).strip()
        color = "red"
        if any(c in inst for c in ["黄", "yellow", "warn"]):
            color = "yellow"
        elif any(c in inst for c in ["绿", "green"]):
            color = "green"
        elif any(c in inst for c in ["蓝", "blue"]):
            color = "blue"
        return "add_highlight", {"keyword": keyword, "color": color}

    return "unknown", {}


# ---------------------------------------------------------------------------
# Improvement Implementations
# ---------------------------------------------------------------------------

def _apply_add_field(code: str, html: str, params: dict) -> dict:
    """Add a new field to a CRUD app."""
    field_name = params.get("field_name", "new_field")
    # Sanitize field name
    safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', field_name).strip('_').lower()
    if not safe_name:
        safe_name = "new_field"

    label = field_name

    # Determine field type heuristically
    field_type = "text"
    if any(kw in safe_name for kw in ["price", "amount", "count", "num", "score", "rate", "age"]):
        field_type = "number"
    elif any(kw in safe_name for kw in ["desc", "content", "note", "body", "detail", "remark", "content"]):
        field_type = "textarea"
    elif any(kw in safe_name for kw in ["status", "type", "category", "priority", "level"]):
        field_type = "select"
    elif any(kw in safe_name for kw in ["date", "time", "created", "updated", "deadline"]):
        field_type = "text"

    # --- Modify Python code ---

    # 1. Add field default in create_item
    if field_type == "number":
        default_val = "0"
        new_field_line = f'        "{safe_name}": data.get("{safe_name}", 0),'
    elif field_type == "select":
        default_val = '""'
        new_field_line = f'        "{safe_name}": data.get("{safe_name}", ""),'
    else:
        default_val = '""'
        new_field_line = f'        "{safe_name}": data.get("{safe_name}", ""),'

    # Insert after last field default in create_item
    # Find the "updated_at" field in item dict and insert before it
    insert_marker = '        "created_at"'
    if insert_marker in code:
        code = code.replace(insert_marker, new_field_line + "\n" + insert_marker, 1)

    # 2. Add update handling
    update_line = f'            if "{safe_name}" in data:\n                item["{safe_name}"] = data["{safe_name}"]'
    # Find the "updated_at" assignment in update_item and insert before it
    update_marker = '            item["updated_at"] = datetime.now().isoformat()'
    if update_marker in code:
        code = code.replace(update_marker, update_line + "\n" + update_marker, 1)

    # --- Modify HTML ---

    # 1. Add form field
    if field_type == "textarea":
        form_html = f'            <textarea id="field-{safe_name}" placeholder="{label}..." style="min-height:60px"></textarea>'
    elif field_type == "select":
        form_html = f'            <select id="field-{safe_name}" style="width:100%"><option value="">选择{label}...</option></select>'
    elif field_type == "number":
        form_html = f'            <input type="number" id="field-{safe_name}" placeholder="{label}" step="any">'
    else:
        form_html = f'            <input type="text" id="field-{safe_name}" placeholder="{label}...">'

    # Insert before the add button
    button_marker = '            <button onclick="addItem()">'
    if button_marker in html:
        html = html.replace(button_marker, form_html + "\n" + button_marker, 1)

    # 2. Add to JS data collection
    js_collect_pattern = r'const data = \{ ([^}]+) \}'
    m = re.search(js_collect_pattern, html)
    if m:
        existing = m.group(1).rstrip(",")
        new_collect = f'{existing}, "{safe_name}": document.getElementById("field-{safe_name}").value'
        html = html.replace(m.group(0), f"const data = {{ {new_collect} }}", 1)

    # 3. Add to JS clear
    clear_pattern = r'document\.getElementById\("field-[^"]+"\)\.value = ""'
    clears = re.findall(clear_pattern, html)
    if clears:
        last_clear = clears[-1]
        new_clear = f'document.getElementById("field-{safe_name}").value = ""'
        html = html.replace(last_clear, last_clear + "; " + new_clear, 1)

    # 4. Add to display in renderItems
    display_line = '<div class="item-field"><span class="field-label">' + label + ':</span> " + escHtml(String(item["' + safe_name + '"])) + "</div>'
    # Insert before item-date div
    date_marker = '<div class="item-date">'
    if date_marker in html:
        html = html.replace(date_marker, display_line + "\n                    " + date_marker, 1)

    return {"code": code, "html": html}


def _apply_add_export(code: str, html: str, params: dict) -> dict:
    """Add an export endpoint and download button."""
    fmt = params.get("format", "csv")

    # Add import if not present
    if "import csv" not in code and "import io" not in code:
        import_line = "import csv\nimport io"
        code = code.replace("import os\n", "import os\n" + import_line + "\n", 1)

    # Find the data file variable
    data_file_match = re.search(r'DATA_FILE = .*?"([^"]+)"', code)
    ep_name = data_file_match.group(1).replace(".json", "") if data_file_match else "items"

    if fmt == "csv":
        export_route = f'''

@app.route("/api/{ep_name}/export/csv", methods=["GET"])
def export_csv():
    import csv
    import io
    items = _load_data()
    if not items:
        return jsonify({{"error": "No data"}}), 404
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=items[0].keys())
    writer.writeheader()
    writer.writerows(items)
    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={{"Content-Disposition": "attachment; filename=export.csv"}}
    )
'''
    elif fmt == "json":
        export_route = f'''

@app.route("/api/{ep_name}/export/json", methods=["GET"])
def export_json():
    items = _load_data()
    from flask import Response
    return Response(
        json.dumps(items, ensure_ascii=False, indent=2),
        mimetype="application/json",
        headers={{"Content-Disposition": "attachment; filename=export.json"}}
    )
'''
    else:  # markdown
        export_route = f'''

@app.route("/api/{ep_name}/export/markdown", methods=["GET"])
def export_markdown():
    items = _load_data()
    if not items:
        return jsonify({{"error": "No data"}}), 404
    lines = ["# Export", ""]
    for item in items:
        for k, v in item.items():
            lines.append(f"- **{{k}}**: {{v}}")
        lines.append("")
    from flask import Response
    return Response(
        "\\n".join(lines),
        mimetype="text/markdown",
        headers={{"Content-Disposition": "attachment; filename=export.md"}}
    )
'''

    # Insert before if __name__
    main_marker = '\nif __name__ == "__main__":'
    if main_marker in code:
        code = code.replace(main_marker, export_route + main_marker, 1)

    # Add export button to HTML
    export_btn = f'<button class="secondary small" onclick="exportData()">导出 {fmt.upper()}</button>'
    # Insert near the clear button
    clear_marker = 'onclick="clearAll()"'
    if clear_marker in html:
        html = html.replace(clear_marker, clear_marker + "</button>\n            " + export_btn, 1)

    # Add JS function
    export_js = f'''
        async function exportData() {{
            window.open("/api/{ep_name}/export/{fmt}", "_blank");
        }}
'''
    # Insert before the final loadItems() call
    load_marker = "        loadItems();\n    </script>"
    if load_marker in html:
        html = html.replace(load_marker, export_js + load_marker, 1)

    return {"code": code, "html": html}


def _apply_add_search(code: str, html: str, params: dict) -> dict:
    """Add search/filter to the list API and UI."""
    # Find the API endpoint name
    data_file_match = re.search(r'DATA_FILE = .*?"([^"]+)"', code)
    ep_name = data_file_match.group(1).replace(".json", "") if data_file_match else "items"

    # Check if search already exists in code
    if 'request.args.get("q"' not in code and "request.args.get('q'" not in code:
        # Insert search logic after the first _load_data() in GET route
        # Strategy: find "items = _load_data()" in the GET handler and add search after it
        load_data_marker = "items = _load_data()"
        search_insert = '    items = _load_data()\n    q = request.args.get("q", "").lower()\n    if q:\n        items = [i for i in items if any(q in str(v).lower() for v in i.values())]'

        # Only replace the FIRST occurrence (in the GET handler)
        if load_data_marker in code:
            code = code.replace(load_data_marker, search_insert, 1)

    # Add search input to HTML
    search_input = '<input type="text" id="search-input" placeholder="搜索..." oninput="searchItems()" style="flex:1;max-width:300px">'
    # Insert in the filters div
    filters_marker = '<div class="filters">'
    if filters_marker in html:
        html = html.replace(filters_marker, filters_marker + "\n            " + search_input, 1)

    # Add search JS function
    search_js = '''
        async function searchItems() {
            const q = document.getElementById("search-input").value;
            const res = await fetch("/api/''' + ep_name + '''?q=" + encodeURIComponent(q));
            items = await res.json();
            renderItems();
            document.getElementById("total-count").textContent = items.length;
        }
'''
    load_marker = "        loadItems();\n    </script>"
    if load_marker in html:
        html = html.replace(load_marker, search_js + load_marker, 1)

    return {"code": code, "html": html}


def _apply_add_sort(code: str, html: str, params: dict) -> dict:
    """Add sorting capability to the list."""
    # Add sort support to the JS renderItems function
    sort_js = '''
        let sortField = "";
        let sortAsc = true;

        function toggleSort(field) {
            if (sortField === field) {
                sortAsc = !sortAsc;
            } else {
                sortField = field;
                sortAsc = true;
            }
            renderItems();
        }

'''
    load_marker = "        loadItems();\n    </script>"
    if load_marker in html:
        html = html.replace(load_marker, sort_js + load_marker, 1)

    # Modify renderItems to sort
    render_start = "function renderItems()"
    if render_start in html:
        # Add sort logic at the start of renderItems
        old_render_check = "if (!items.length)"
        sort_logic = (
            "// Apply sorting\n"
            "            let sorted = items.slice();\n"
            "            if (sortField) {\n"
            "                sorted.sort(function(a, b) {\n"
            "                    let va = a[sortField] || '';\n"
            "                    let vb = b[sortField] || '';\n"
            "                    if (!isNaN(va) && !isNaN(vb)) { va = Number(va); vb = Number(vb); }\n"
            "                    if (va < vb) return sortAsc ? -1 : 1;\n"
            "                    if (va > vb) return sortAsc ? 1 : -1;\n"
            "                    return 0;\n"
            "                });\n"
            "            }\n"
            "            items = sorted;\n"
            "            "
        )
        html = html.replace(old_render_check, sort_logic + old_render_check, 1)

    # Add sort button to filters
    sort_btn = '<button class="secondary small" onclick="toggleSort(\'created_at\')">按时间排序</button>'
    clear_marker = 'onclick="clearAll()"'
    if clear_marker in html:
        html = html.replace(clear_marker, clear_marker + "</button>\n            " + sort_btn, 1)

    return {"code": code, "html": html}


def _apply_change_theme(html: str, params: dict) -> dict:
    """Change the color theme of the app."""
    theme = params.get("theme", "default")

    themes = {
        "green": {
            "accent": "#00e676",
            "accent_hover": "#00c853",
            "bg": "#0f0f0f",
            "card": "#1a1a2e",
        },
        "purple": {
            "accent": "#bb86fc",
            "accent_hover": "#9b59b6",
            "bg": "#0f0f0f",
            "card": "#1a1a2e",
        },
        "orange": {
            "accent": "#ff9100",
            "accent_hover": "#e65100",
            "bg": "#0f0f0f",
            "card": "#1a1a2e",
        },
        "red": {
            "accent": "#ff5252",
            "accent_hover": "#d32f2f",
            "bg": "#0f0f0f",
            "card": "#1a1a2e",
        },
        "light": {
            "accent": "#0066cc",
            "accent_hover": "#004499",
            "bg": "#f5f5f5",
            "card": "#ffffff",
        },
    }

    t = themes.get(theme, themes["green"])

    # Replace accent colors
    html = html.replace("#00d4ff", t["accent"])
    html = html.replace("#00b8d9", t["accent_hover"])

    # For light theme, also change text and background
    if theme == "light":
        html = html.replace("background: #0f0f0f", "background: #f5f5f5")
        html = html.replace("background: #1a1a2e", "background: #ffffff")
        html = html.replace("color: #e0e0e0", "color: #333333")
        html = html.replace("color: #888", "color: #666")
        html = html.replace("color: #555", "color: #999")
        html = html.replace("color: #aaa", "color: #666")
        html = html.replace("border: 1px solid #2a2a3e", "border: 1px solid #ddd")
        html = html.replace("border: 1px solid #2a2a3e", "border: 1px solid #ddd")

    return {"html": html}


# ---------------------------------------------------------------------------
# List available auto-improvements
# ---------------------------------------------------------------------------

def list_improvements(app_name: str) -> dict:
    """List available auto-improvements for a specific app."""
    if not app_exists(app_name):
        return {"error": f"App '{app_name}' not found"}

    return {
        "app_name": app_name,
        "available_improvements": [
            {
                "type": "add_field",
                "description": "添加新数据字段",
                "example": "加一个标签字段 / add a tag field",
            },
            {
                "type": "add_export",
                "description": "添加数据导出功能",
                "example": "加一个导出CSV按钮 / add CSV export",
            },
            {
                "type": "add_search",
                "description": "添加搜索/筛选功能",
                "example": "加一个搜索框 / add search",
            },
            {
                "type": "add_sort",
                "description": "添加排序功能",
                "example": "添加排序 / add sorting",
            },
            {
                "type": "change_theme",
                "description": "更换颜色主题",
                "example": "换成绿色主题 / change to green theme",
            },
            {
                "type": "add_schedule",
                "description": "设置定时自动运行",
                "example": "每天早上8点自动运行 / schedule daily at 8am",
            },
            {
                "type": "add_datasource",
                "description": "增加数据源",
                "example": "增加RSS数据源 / add a new API source",
            },
            {
                "type": "add_highlight",
                "description": "关键词高亮/标色",
                "example": "Anthropic相关内容标红 / highlight keywords in red",
            },
        ],
        "fallback": "For other changes, Claude will read and rewrite the code manually",
    }


def _apply_add_schedule(app_name: str, params: dict) -> dict:
    """Set up a scheduled task for the app."""
    from scheduler import create_schedule

    result = create_schedule(
        app_name=app_name,
        schedule_type=params.get("schedule_type", "daily"),
        time_str=params.get("time_str", "08:00"),
    )

    if "error" in result:
        return result

    return {
        "schedule": result,
    }


def _apply_add_datasource(app_name: str, code: str, html: str, params: dict) -> dict:
    """Add a data source to an app by updating its code to fetch from the source.

    This is a guided operation - it adds scaffold code for fetching data,
    but the user/Claude needs to fill in the specific API URL.
    """
    source_type = params.get("source_type", "rest_api")

    # Check if requests is already imported
    has_requests = "import requests" in code

    if not has_requests:
        # Add requests import
        code = code.replace("import os\n", "import os\nimport requests\n", 1)

    # Add a generic data source fetch route
    data_file_match = re.search(r'DATA_FILE = .*?"([^"]+)"', code)
    ep_name = data_file_match.group(1).replace(".json", "") if data_file_match else "items"

    fetch_route = '''

@app.route("/api/fetch_external", methods=["POST"])
def fetch_external():
    """Fetch data from external source. Configure URL in the request body."""
    data = request.get_json() or {}
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "url is required"}), 400
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return jsonify({"status": "ok", "data": resp.json() if "json" in resp.headers.get("Content-Type", "") else resp.text[:5000]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
'''

    main_marker = '\nif __name__ == "__main__":'
    if main_marker in code and "fetch_external" not in code:
        code = code.replace(main_marker, fetch_route + main_marker, 1)

    # Add a fetch button to HTML
    fetch_btn = '<button class="secondary small" onclick="fetchExternal()">Fetch Data</button>'
    clear_marker = 'onclick="clearAll()"'
    if clear_marker in html and "fetchExternal" not in html:
        html = html.replace(clear_marker, clear_marker + "</button>\n            " + fetch_btn, 1)

    # Add fetch JS
    fetch_js = '''
        async function fetchExternal() {
            const url = prompt("Enter the data source URL:");
            if (!url) return;
            const res = await fetch("/api/fetch_external", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({url: url})
            });
            const data = await res.json();
            if (data.error) { alert("Error: " + data.error); return; }
            alert("Fetched successfully! Check console for data.");
            console.log("External data:", data);
        }
'''
    load_marker = "        loadItems();\n    </script>"
    if load_marker in html and "fetchExternal" not in html:
        html = html.replace(load_marker, fetch_js + load_marker, 1)

    return {
        "code": code,
        "html": html,
        "requirements": "flask\nrequests" if not has_requests else None,
        "note": "External fetch route added. Use krowork_register_datasource to configure specific sources.",
    }


def _apply_add_highlight(html: str, params: dict) -> dict:
    """Add keyword highlighting to the item display."""
    keyword = params.get("keyword", "")
    color = params.get("color", "red")

    color_map = {
        "red": {"bg": "rgba(255,71,87,0.25)", "text": "#ff4757", "border": "#ff4757"},
        "yellow": {"bg": "rgba(255,165,2,0.25)", "text": "#ffa502", "border": "#ffa502"},
        "green": {"bg": "rgba(46,213,115,0.25)", "text": "#2ed573", "border": "#2ed573"},
        "blue": {"bg": "rgba(0,212,255,0.25)", "text": "#00d4ff", "border": "#00d4ff"},
    }
    c = color_map.get(color, color_map["red"])

    # Add highlight CSS
    highlight_css = f'''
        .highlight-keyword {{ background: {c["bg"]}; color: {c["text"]}; padding: 1px 4px; border-radius: 3px; font-weight: 600; }}
'''

    # Insert CSS before </style>
    style_marker = "    </style>"
    if style_marker in html:
        html = html.replace(style_marker, highlight_css + style_marker, 1)

    # Add highlight JS function
    keyword_escaped = keyword.replace("'", "\\'").replace('"', '\\"') if keyword else ""
    highlight_js = f'''
        function highlightKeyword(text) {{
            if (!text || !'{keyword_escaped}') return text;
            let safe = escHtml(text);
            let kw = escHtml('{keyword_escaped}');
            if (!kw) return safe;
            let regex = new RegExp('(' + kw.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + ')', 'gi');
            return safe.replace(regex, '<span class="highlight-keyword">$1</span>');
        }}
'''

    load_marker = "        loadItems();\n    </script>"
    if load_marker in html and "highlightKeyword" not in html:
        html = html.replace(load_marker, highlight_js + load_marker, 1)

    return {"html": html}
