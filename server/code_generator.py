"""Open-KroWork Code Generator - Generate Flask web app projects.

Supports two modes:
1. Template assembly: AI provides html_body, python_logic, javascript fragments
2. Auto-generation: System generates complete app from description + config
"""

import json
import os
import re
from pathlib import Path
from string import Template


def get_template_dir() -> Path:
    """Get the templates directory."""
    plugin_root = os.environ.get("KROWORK_PLUGIN_ROOT", "")
    if plugin_root:
        return Path(plugin_root) / "templates"
    return Path(__file__).parent.parent / "templates"


def load_template(template_name: str, filename: str) -> str:
    """Load a template file from the templates directory."""
    template_path = get_template_dir() / template_name / filename
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Mode 1: Template Assembly (AI provides fragments)
# ---------------------------------------------------------------------------

def generate_web_app(
    app_name: str,
    title: str,
    description: str,
    html_body: str,
    python_logic: str,
    css_styles: str = "",
    javascript: str = "",
    extra_routes: str = "",
    imports: str = "",
    requirements: list = None,
) -> dict:
    """Generate a Flask web app from fragments provided by the AI."""
    main_template = load_template("web_app", "main.py.tpl")
    if not main_template:
        main_template = DEFAULT_MAIN_PY_TEMPLATE

    default_imports = "import os\nimport json\nfrom flask import Flask, send_file, request, jsonify"
    all_imports = default_imports
    if imports:
        all_imports = default_imports + "\n" + imports

    default_reqs = ["flask"]
    if requirements:
        for req in requirements:
            req_name = req.split("==")[0].split(">=")[0].split("<=")[0].strip().lower()
            if req_name != "flask":
                default_reqs.append(req)

    code = Template(main_template).safe_substitute(
        app_name=app_name,
        title=title,
        all_imports=all_imports,
        python_logic=python_logic,
        extra_routes=extra_routes,
    )

    html_template = load_template("web_app", "templates/index.html.tpl")
    if not html_template:
        html_template = DEFAULT_HTML_TEMPLATE

    html = Template(html_template).safe_substitute(
        title=title,
        description=description,
        html_body=html_body,
        css_styles=css_styles,
        javascript=javascript,
        app_name=app_name,
    )

    reqs_text = "\n".join(default_reqs)

    return {
        "code": code,
        "html_template": html,
        "requirements": reqs_text,
    }


# ---------------------------------------------------------------------------
# Mode 2: Auto-Generation (System generates complete app from description)
# ---------------------------------------------------------------------------

def auto_generate_app(app_name: str, description: str, config: dict = None) -> dict:
    """Automatically generate a complete, functional Flask app from description.

    This is the core auto-generation engine. It analyzes the description,
    determines the app type, and generates a fully working application
    with CRUD API routes and an interactive dark-themed UI.

    Args:
        app_name: Machine name for the app
        description: Natural language description of what the app does
        config: Optional configuration with keys:
            - entity_name: The main data entity (e.g., "stock", "note", "task")
            - fields: List of {name, type, label} dicts for the data model
            - api_url: External API endpoint (if applicable)
            - features: List of feature flags

    Returns:
        dict with keys: code, html_template, requirements
    """
    cfg = config or {}

    # Analyze description to determine app type
    app_type, entity_info = _analyze_description(app_name, description, cfg)

    # Generate based on detected type
    if app_type == "crud":
        return _generate_crud_app(app_name, description, entity_info)
    elif app_type == "api_dashboard":
        return _generate_api_dashboard_app(app_name, description, entity_info)
    elif app_type == "tool":
        return _generate_tool_app(app_name, description, entity_info)
    else:
        return _generate_crud_app(app_name, description, entity_info)


def _analyze_description(app_name: str, description: str, config: dict) -> tuple:
    """Analyze description to determine app type and extract entity info."""
    desc_lower = description.lower()
    name_lower = app_name.lower()

    # Extract entity info from config or infer from name
    if config.get("fields"):
        return config.get("app_type", "crud"), config

    entity_name = config.get("entity_name", "")
    fields = config.get("fields", [])

    # Detect app type from description keywords
    api_keywords = ["api", "股票", "stock", "天气", "weather", "汇率", "exchange",
                    "新闻", "news", "热点", "trending", "监控", "monitor", "追踪", "track"]
    tool_keywords = ["生成器", "generator", "转换", "convert", "计算", "calc",
                     "加密", "encrypt", "密码", "password", "格式化", "format",
                     "测试", "test"]

    is_api = any(kw in desc_lower for kw in api_keywords)
    is_tool = any(kw in desc_lower for kw in tool_keywords)

    if is_api:
        app_type = "api_dashboard"
    elif is_tool:
        app_type = "tool"
    else:
        app_type = "crud"

    # If no entity name provided, infer from app name
    if not entity_name:
        parts = name_lower.replace("_", "-").split("-")
        skip = {"app", "the", "a", "an", "my", "manager", "tracker", "tool",
                "system", "dashboard", "generator", "viewer", "editor", "analyzer"}
        meaningful = [p for p in parts if p not in skip and len(p) > 0]
        entity_name = meaningful[0] if meaningful else parts[-1] if parts else "item"

    # If no fields, generate sensible defaults
    if not fields:
        fields = _infer_fields(entity_name, desc_lower, app_type)

    entity_info = {
        "entity_name": entity_name,
        "entity_label": entity_name.replace("-", " ").replace("_", " ").title(),
        "fields": fields,
        "app_type": app_type,
        "app_name": app_name,
        "description": description,
    }

    return app_type, entity_info


def _infer_fields(entity_name: str, desc_lower: str, app_type: str) -> list:
    """Infer data fields from entity name and description."""
    # Common field patterns
    base_fields = [
        {"name": "title", "type": "text", "label": "标题"},
        {"name": "description", "type": "textarea", "label": "描述"},
    ]

    # Add status field for CRUD apps
    if app_type == "crud":
        base_fields.append({"name": "status", "type": "select", "label": "状态",
                           "options": ["pending", "done", "archived"]})

    # Add specific fields based on entity
    en = entity_name.lower()
    if en in ("stock", "股票"):
        return [
            {"name": "symbol", "type": "text", "label": "股票代码"},
            {"name": "name", "type": "text", "label": "股票名称"},
            {"name": "price", "type": "number", "label": "最新价"},
            {"name": "change_pct", "type": "number", "label": "涨跌幅(%)"},
            {"name": "analysis", "type": "textarea", "label": "分析"},
        ]
    elif en in ("note", "笔记", "notebook"):
        return [
            {"name": "title", "type": "text", "label": "标题"},
            {"name": "content", "type": "textarea", "label": "内容"},
            {"name": "tags", "type": "text", "label": "标签"},
        ]
    elif en in ("todo", "task", "任务"):
        return [
            {"name": "title", "type": "text", "label": "标题"},
            {"name": "description", "type": "textarea", "label": "描述"},
            {"name": "priority", "type": "select", "label": "优先级",
             "options": ["low", "medium", "high"]},
            {"name": "status", "type": "select", "label": "状态",
             "options": ["pending", "done"]},
        ]
    elif en in ("password", "密码"):
        return [
            {"name": "site", "type": "text", "label": "网站"},
            {"name": "username", "type": "text", "label": "用户名"},
            {"name": "password", "type": "text", "label": "密码"},
        ]
    elif en in ("bookmark", "书签", "收藏"):
        return [
            {"name": "title", "type": "text", "label": "标题"},
            {"name": "url", "type": "text", "label": "网址"},
            {"name": "description", "type": "textarea", "label": "描述"},
            {"name": "tags", "type": "text", "label": "标签"},
        ]

    return base_fields


def _pluralize(name: str) -> str:
    """Simple English pluralization."""
    if name.endswith("s") or name.endswith("x") or name.endswith("z"):
        return name + "es"
    elif name.endswith("y") and len(name) > 1 and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    else:
        return name + "s"


def _generate_crud_app(app_name: str, description: str, info: dict) -> dict:
    """Generate a complete CRUD application."""
    entity = info["entity_name"]
    entity_label = info["entity_label"]
    fields = info["fields"]

    # Generate Python code
    code = _build_crud_python(app_name, entity, fields)

    # Generate HTML
    html = _build_crud_html(app_name, description, entity, entity_label, fields)

    return {
        "code": code,
        "html_template": html,
        "requirements": "flask",
    }


def _build_crud_python(app_name: str, entity: str, fields: list) -> str:
    """Build complete Flask CRUD backend."""
    ep = _pluralize(entity)  # entity plural for routes
    import uuid
    from datetime import datetime

    # Build field defaults for create
    field_defaults = []
    for f in fields:
        if f["type"] == "number":
            field_defaults.append(f'        "{f["name"]}": data.get("{f["name"]}", 0)')
        elif f["type"] == "select":
            opts = f.get("options", [])
            default = opts[0] if opts else ""
            field_defaults.append(f'        "{f["name"]}": data.get("{f["name"]}", "{default}")')
        else:
            field_defaults.append(f'        "{f["name"]}": data.get("{f["name"]}", "")')

    fields_defaults_str = ",\n".join(field_defaults)
    update_fields = []
    for f in fields:
        update_fields.append(f'            if "{f["name"]}" in data:\n                item["{f["name"]}"] = data["{f["name"]}"]')
    update_fields_str = "\n".join(update_fields)

    return f'''import os
import json
import uuid
from datetime import datetime
from flask import Flask, send_file, request, jsonify

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

APP_NAME = "{app_name}"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, "{ep}.json")


def _load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_data(items):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "templates", "index.html"))


@app.route("/api/{ep}", methods=["GET"])
def get_items():
    items = _load_data()
    status = request.args.get("status")
    if status:
        items = [i for i in items if i.get("status") == status]
    return jsonify(items)


@app.route("/api/{ep}", methods=["POST"])
def create_item():
    data = request.get_json()
    if not data:
        return jsonify({{"error": "No data provided"}}), 400
    item = {{
        "id": str(uuid.uuid4())[:8],
{fields_defaults_str},
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }}
    items = _load_data()
    items.insert(0, item)
    _save_data(items)
    return jsonify(item), 201


@app.route("/api/{ep}/<item_id>", methods=["PUT"])
def update_item(item_id):
    data = request.get_json()
    items = _load_data()
    for item in items:
        if item["id"] == item_id:
{update_fields_str}
            item["updated_at"] = datetime.now().isoformat()
            _save_data(items)
            return jsonify(item)
    return jsonify({{"error": "Not found"}}), 404


@app.route("/api/{ep}/<item_id>", methods=["DELETE"])
def delete_item(item_id):
    items = _load_data()
    new_items = [i for i in items if i["id"] != item_id]
    if len(new_items) == len(items):
        return jsonify({{"error": "Not found"}}), 404
    _save_data(new_items)
    return jsonify({{"success": True}})


@app.route("/api/{ep}/clear", methods=["POST"])
def clear_items():
    items = _load_data()
    _save_data([])
    return jsonify({{"removed": len(items)}})


if __name__ == "__main__":
    port = int(os.environ.get("KROWORK_PORT", 5000))
    print(APP_NAME + " running at http://127.0.0.1:" + str(port))
    app.run(host="127.0.0.1", port=port, debug=False)
'''


def _build_crud_html(app_name, description, entity, entity_label, fields):
    """Build complete interactive HTML frontend for CRUD app."""
    ep = _pluralize(entity)  # plural form for API routes
    title = description.split("-")[0].strip() if "-" in description else description
    title = title.strip() or app_name.replace("-", " ").title()

    # Build form fields HTML
    form_fields = []
    for f in fields:
        fname = f["name"]
        flabel = f.get("label", fname)
        if f["type"] == "textarea":
            form_fields.append(f'            <textarea id="field-{fname}" placeholder="{flabel}..." style="min-height:60px"></textarea>')
        elif f["type"] == "select":
            opts = f.get("options", [])
            options_html = "\n".join(f'<option value="{o}">{o}</option>' for o in opts)
            form_fields.append(f'            <select id="field-{fname}" style="width:100%">\n              {options_html}\n            </select>')
        elif f["type"] == "number":
            form_fields.append(f'            <input type="number" id="field-{fname}" placeholder="{flabel}" step="any">')
        else:
            form_fields.append(f'            <input type="text" id="field-{fname}" placeholder="{flabel}...">')

    form_fields_html = "\n".join(form_fields)

    # Build JS field collection
    js_collect = ", ".join(f'"{f["name"]}": document.getElementById("field-{f["name"]}").value' for f in fields)
    js_clear = "; ".join(f'document.getElementById("field-{f["name"]}").value = ""' for f in fields)

    # Build item display fields for the list
    display_fields = []
    for f in fields:
        fname = f["name"]
        flabel = f.get("label", fname)
        if f["type"] == "select":
            display_fields.append(
                '<span class="badge badge-" + (item["' + fname + '"] === "done" || item["' + fname + '"] === "high" ? "green" : item["' + fname + '"] === "pending" || item["' + fname + '"] === "medium" ? "yellow" : "blue") + ">" + escHtml(item["' + fname + '"]) + "</span>'
            )
        elif f["type"] != "textarea" and fname not in ("id", "created_at", "updated_at"):
            display_fields.append(
                '<div class="item-field"><span class="field-label">' + flabel + ':</span> ' + '" + escHtml(String(item["' + fname + '"])) + "' + '</div>'
            )

    display_html = "\n                    ".join(display_fields)

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; min-height: 100vh; }}
        .header {{ background: #1a1a2e; padding: 16px 24px; border-bottom: 1px solid #2a2a3e; display: flex; align-items: center; justify-content: space-between; }}
        .header h1 {{ font-size: 20px; color: #00d4ff; font-weight: 600; }}
        .header .subtitle {{ font-size: 13px; color: #888; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 24px; }}
        .add-form {{ background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; padding: 20px; margin-bottom: 20px; }}
        .add-form h3 {{ color: #00d4ff; margin-bottom: 12px; font-size: 15px; }}
        .form-fields {{ display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }}
        input, select, textarea {{ background: #0f0f0f; border: 1px solid #2a2a3e; border-radius: 6px; padding: 10px 14px; color: #e0e0e0; font-size: 14px; outline: none; width: 100%; }}
        input:focus, select:focus, textarea:focus {{ border-color: #00d4ff; }}
        textarea {{ resize: vertical; font-family: inherit; }}
        button {{ background: #00d4ff; color: #0f0f0f; border: none; border-radius: 6px; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.2s; }}
        button:hover {{ background: #00b8d9; }}
        button.secondary {{ background: #2a2a3e; color: #e0e0e0; }}
        button.secondary:hover {{ background: #3a3a4e; }}
        button.danger {{ background: #ff4757; color: #fff; }}
        button.small {{ padding: 6px 12px; font-size: 12px; }}
        .filters {{ display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }}
        .filter-btn {{ background: #2a2a3e; color: #888; border: 1px solid #2a2a3e; border-radius: 20px; padding: 6px 16px; font-size: 13px; cursor: pointer; transition: all 0.2s; }}
        .filter-btn.active {{ background: rgba(0,212,255,0.15); color: #00d4ff; border-color: #00d4ff; }}
        .item-list {{ display: flex; flex-direction: column; gap: 8px; }}
        .item-card {{ background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; padding: 16px; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }}
        .item-card:hover {{ border-color: #3a3a4e; }}
        .item-content {{ flex: 1; }}
        .item-content .item-title {{ font-size: 15px; font-weight: 600; margin-bottom: 6px; }}
        .item-content .item-field {{ font-size: 13px; color: #aaa; margin-top: 4px; }}
        .item-content .field-label {{ color: #666; }}
        .item-content .item-date {{ font-size: 11px; color: #555; margin-top: 8px; }}
        .item-actions {{ display: flex; gap: 6px; flex-shrink: 0; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }}
        .badge-green {{ background: rgba(46,213,115,0.2); color: #2ed573; }}
        .badge-yellow {{ background: rgba(255,165,2,0.2); color: #ffa502; }}
        .badge-red {{ background: rgba(255,71,87,0.2); color: #ff4757; }}
        .badge-blue {{ background: rgba(0,212,255,0.2); color: #00d4ff; }}
        .empty {{ text-align: center; padding: 40px; color: #555; }}
        .stats {{ display: flex; gap: 16px; }}
        .stat {{ font-size: 13px; color: #888; }}
        .stat span {{ color: #00d4ff; font-weight: 600; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>{title}</h1>
            <div class="subtitle">{description}</div>
        </div>
        <div class="stats">
            <div class="stat">总计: <span id="total-count">0</span></div>
        </div>
    </div>
    <div class="container">
        <div class="add-form">
            <h3>+ 添加</h3>
            <div class="form-fields">
{form_fields_html}
            </div>
            <button onclick="addItem()">添加</button>
        </div>
        <div class="filters">
            <button class="filter-btn active" onclick="setFilter('all', this)">全部</button>
            <div style="flex:1"></div>
            <button class="secondary small" onclick="clearAll()">清除全部</button>
        </div>
        <div class="item-list" id="item-list"></div>
    </div>
    <script>
        let items = [];

        async function loadItems() {{
            const res = await fetch("/api/{ep}");
            items = await res.json();
            renderItems();
            document.getElementById("total-count").textContent = items.length;
        }}

        async function addItem() {{
            const data = {{ {js_collect} }};
            // Check at least one field has value
            const hasValue = Object.values(data).some(v => v && v.toString().trim());
            if (!hasValue) return;
            await fetch("/api/{entity}s", {{
                method: "POST",
                headers: {{"Content-Type": "application/json"}},
                body: JSON.stringify(data)
            }});
            {js_clear};
            loadItems();
        }}

        async function deleteItem(id) {{
            await fetch("/api/{ep}/" + id, {{method: "DELETE"}});
            loadItems();
        }}

        async function clearAll() {{
            await fetch("/api/{ep}/clear", {{method: "POST"}});
            loadItems();
        }}

        function setFilter(f, btn) {{
            document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            loadItems();
        }}

        function renderItems() {{
            const list = document.getElementById("item-list");
            if (!items.length) {{
                list.innerHTML = '<div class="empty"><p>暂无数据</p><p>点击上方添加按钮开始</p></div>';
                return;
            }}
            list.innerHTML = items.map(function(item) {{
                let fields = "";
                let title = escHtml(item.title || item.name || item.symbol || item.id);
                let dateStr = new Date(item.created_at).toLocaleString("zh-CN");
                return '<div class="item-card">'
                    + '<div class="item-content">'
                    + '<div class="item-title">' + title + '</div>'
                    + '{display_html}'
                    + '<div class="item-date">' + dateStr + '</div>'
                    + '</div>'
                    + '<div class="item-actions">'
                    + '<button class="danger small" onclick="deleteItem(\\'' + item.id + '\\')">删除</button>'
                    + '</div></div>';
            }}).join("");
        }}

        function escHtml(s) {{ const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }}

        loadItems();
    </script>
</body>
</html>'''


def _generate_api_dashboard_app(app_name: str, description: str, info: dict) -> dict:
    """Generate an API dashboard application (for stock, weather, news, etc.).

    Dashboard apps have a query input area, results display with stats cards,
    and optional chart rendering via Chart.js.
    """
    entity = info["entity_name"]
    entity_label = info["entity_label"]
    fields = info["fields"]
    title = description.split("-")[0].strip() if "-" in description else description
    title = title.strip() or app_name.replace("-", " ").title()
    ep = _pluralize(entity)

    # Python backend with search/query API endpoint
    code = _build_dashboard_python(app_name, entity, fields)

    # HTML with dashboard layout: query input + results + stats cards
    html = _build_dashboard_html(app_name, description, entity, entity_label, fields)

    return {
        "code": code,
        "html_template": html,
        "requirements": "flask\nrequests",
    }


def _generate_tool_app(app_name: str, description: str, info: dict) -> dict:
    """Generate a tool-type application (generators, converters, etc.).

    Tool apps have an input area, action button, and output/result display.
    """
    entity = info["entity_name"]
    entity_label = info["entity_label"]
    fields = info["fields"]
    title = description.split("-")[0].strip() if "-" in description else description
    title = title.strip() or app_name.replace("-", " ").title()

    # Python backend with tool logic
    code = _build_tool_python(app_name, entity, fields, description)

    # HTML with tool layout: input → action → output
    html = _build_tool_html(app_name, description, entity, entity_label, fields)

    return {
        "code": code,
        "html_template": html,
        "requirements": "flask",
    }


# ---------------------------------------------------------------------------
# Dashboard Template Builder
# ---------------------------------------------------------------------------

def _build_dashboard_python(app_name: str, entity: str, fields: list) -> str:
    """Build Flask backend for API dashboard app with query endpoint."""
    ep = _pluralize(entity)
    field_defaults = []
    for f in fields:
        if f["type"] == "number":
            field_defaults.append('        "' + f["name"] + '": data.get("' + f["name"] + '", 0)')
        else:
            field_defaults.append('        "' + f["name"] + '": data.get("' + f["name"] + '", "")')
    fields_defaults_str = ",\n".join(field_defaults)

    return '''import os
import json
import uuid
from datetime import datetime
from flask import Flask, send_file, request, jsonify

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

APP_NAME = "''' + app_name + '''"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, "''' + ep + '''.json")


def _load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_data(items):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "templates", "index.html"))


@app.route("/api/''' + ep + '''", methods=["GET"])
def get_items():
    items = _load_data()
    q = request.args.get("q", "").lower()
    if q:
        items = [i for i in items if any(q in str(v).lower() for v in i.values())]
    return jsonify(items)


@app.route("/api/''' + ep + '''", methods=["POST"])
def create_item():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    item = {
        "id": str(uuid.uuid4())[:8],
''' + fields_defaults_str + ''',
        "created_at": datetime.now().isoformat(),
    }
    items = _load_data()
    items.insert(0, item)
    _save_data(items)
    return jsonify(item), 201


@app.route("/api/''' + ep + '''/clear", methods=["POST"])
def clear_items():
    items = _load_data()
    _save_data([])
    return jsonify({"removed": len(items)})


@app.route("/api/''' + ep + '''/stats", methods=["GET"])
def get_stats():
    items = _load_data()
    stats = {"total": len(items)}
    # Compute numeric field averages
    for f in ["price", "change_pct", "amount", "count", "value", "score"]:
        nums = [i.get(f, 0) for i in items if isinstance(i.get(f), (int, float))]
        if nums:
            stats[f + "_avg"] = round(sum(nums) / len(nums), 2)
            stats[f + "_max"] = max(nums)
            stats[f + "_min"] = min(nums)
    return jsonify(stats)


if __name__ == "__main__":
    port = int(os.environ.get("KROWORK_PORT", 5000))
    print(APP_NAME + " running at http://127.0.0.1:" + str(port))
    app.run(host="127.0.0.1", port=port, debug=False)
'''


def _build_dashboard_html(app_name, description, entity, entity_label, fields):
    """Build dashboard HTML with stats cards, search, and data table."""
    title = description.split("-")[0].strip() if "-" in description else description
    title = title.strip() or app_name.replace("-", " ").title()
    ep = _pluralize(entity)

    # Table header columns
    th_cols = "".join("<th>" + f.get("label", f["name"]) + "</th>" for f in fields)
    # Table row cells
    td_cols = "".join('<td>" + escHtml(String(item["' + f["name"] + '"])) + "</td>' for f in fields)

    # Form fields for add form
    form_fields = []
    for f in fields:
        flabel = f.get("label", f["name"])
        if f["type"] == "textarea":
            form_fields.append('<textarea id="field-' + f["name"] + '" placeholder="' + flabel + '..." style="min-height:50px"></textarea>')
        elif f["type"] == "number":
            form_fields.append('<input type="number" id="field-' + f["name"] + '" placeholder="' + flabel + '" step="any">')
        else:
            form_fields.append('<input type="text" id="field-' + f["name"] + '" placeholder="' + flabel + '...">')
    form_html = "\n".join('            ' + ff for ff in form_fields)

    js_collect = ", ".join('"' + f["name"] + '": document.getElementById("field-' + f["name"] + '").value' for f in fields)
    js_clear = "; ".join('document.getElementById("field-' + f["name"] + '").value = ""' for f in fields)

    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>''' + title + '''</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; min-height: 100vh; }
        .header { background: #1a1a2e; padding: 16px 24px; border-bottom: 1px solid #2a2a3e; display: flex; align-items: center; justify-content: space-between; }
        .header h1 { font-size: 20px; color: #00d4ff; font-weight: 600; }
        .header .subtitle { font-size: 13px; color: #888; }
        .container { max-width: 1100px; margin: 0 auto; padding: 24px; }
        .stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 20px; }
        .stat-card { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; padding: 16px; text-align: center; }
        .stat-card .stat-value { font-size: 28px; font-weight: 700; color: #00d4ff; }
        .stat-card .stat-label { font-size: 12px; color: #888; margin-top: 4px; }
        .card { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
        .card h3 { color: #00d4ff; margin-bottom: 12px; font-size: 15px; }
        .form-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
        .form-row input, .form-row select { background: #0f0f0f; border: 1px solid #2a2a3e; border-radius: 6px; padding: 10px 14px; color: #e0e0e0; font-size: 14px; flex: 1; min-width: 120px; outline: none; }
        .form-row input:focus { border-color: #00d4ff; }
        textarea { background: #0f0f0f; border: 1px solid #2a2a3e; border-radius: 6px; padding: 10px 14px; color: #e0e0e0; font-size: 14px; width: 100%; min-height: 50px; resize: vertical; font-family: inherit; outline: none; }
        textarea:focus { border-color: #00d4ff; }
        button { background: #00d4ff; color: #0f0f0f; border: none; border-radius: 6px; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #00b8d9; }
        button.secondary { background: #2a2a3e; color: #e0e0e0; }
        button.danger { background: #ff4757; color: #fff; }
        button.small { padding: 6px 12px; font-size: 12px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid #2a2a3e; font-size: 13px; }
        th { color: #00d4ff; font-weight: 600; font-size: 12px; text-transform: uppercase; }
        tr:hover { background: rgba(0,212,255,0.03); }
        .empty { text-align: center; padding: 40px; color: #555; }
        .chart-container { position: relative; height: 250px; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>''' + title + '''</h1>
            <div class="subtitle">''' + description + '''</div>
        </div>
        <div style="display:flex;gap:8px">
            <button class="secondary small" onclick="clearAll()">清除数据</button>
        </div>
    </div>
    <div class="container">
        <div class="stats-row" id="stats-row">
            <div class="stat-card"><div class="stat-value" id="stat-total">0</div><div class="stat-label">总记录</div></div>
        </div>
        <div class="chart-container">
            <canvas id="dataChart"></canvas>
        </div>
        <div class="card">
            <h3>+ 添加数据</h3>
            <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:12px">
''' + form_html + '''
            </div>
            <button onclick="addItem()">添加</button>
        </div>
        <div class="card">
            <h3>数据列表</h3>
            <div style="overflow-x:auto">
                <table>
                    <thead><tr><th>#</th>''' + th_cols + '''<th>时间</th><th>操作</th></tr></thead>
                    <tbody id="data-table"></tbody>
                </table>
            </div>
            <div class="empty" id="empty-msg">暂无数据</div>
        </div>
    </div>
    <script>
        let items = [];
        let chart = null;

        async function loadItems() {
            const res = await fetch("/api/''' + ep + '''");
            items = await res.json();
            renderTable();
            loadStats();
        }

        async function loadStats() {
            try {
                const res = await fetch("/api/''' + ep + '''/stats");
                const stats = await res.json();
                document.getElementById("stat-total").textContent = stats.total || 0;
                // Update stat cards dynamically
                const row = document.getElementById("stats-row");
                let html = '<div class="stat-card"><div class="stat-value">' + (stats.total||0) + '</div><div class="stat-label">总记录</div></div>';
                for (let key of Object.keys(stats)) {
                    if (key === "total") continue;
                    let label = key.replace(/_/g, " ");
                    html += '<div class="stat-card"><div class="stat-value">' + stats[key] + '</div><div class="stat-label">' + label + '</div></div>';
                }
                row.innerHTML = html;
            } catch(e) {}
            updateChart();
        }

        async function addItem() {
            const data = { ''' + js_collect + ''' };
            await fetch("/api/''' + ep + '''", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify(data)
            });
            ''' + js_clear + ''';
            loadItems();
        }

        async function deleteItem(id) {
            await fetch("/api/''' + ep + '''/" + id, {method: "DELETE"});
            loadItems();
        }

        async function clearAll() {
            await fetch("/api/''' + ep + '''/clear", {method: "POST"});
            loadItems();
        }

        function renderTable() {
            const tbody = document.getElementById("data-table");
            const empty = document.getElementById("empty-msg");
            if (!items.length) {
                tbody.innerHTML = "";
                empty.style.display = "block";
                return;
            }
            empty.style.display = "none";
            tbody.innerHTML = items.map(function(item, i) {
                return "<tr><td>" + (i+1) + "</td>''' + td_cols + '''<td>" + new Date(item.created_at).toLocaleString("zh-CN") + "</td>"
                    + '<td><button class="danger small" onclick="deleteItem(\\'' + item.id + '\\')">删除</button></td></tr>';
            }).join("");
        }

        function updateChart() {
            // Find first numeric field for chart
            let numField = null;
            let labelField = null;
''' + ''.join('            if (!numField && items.length && typeof items[0]["' + f["name"] + '"] === "number") numField = "' + f["name"] + '";\n' for f in fields if f["type"] == "number") + '''
            for (let f of ["title", "name", "symbol", "id"]) {
                if (items.length && items[0][f] !== undefined) { labelField = f; break; }
            }
            if (!numField || !items.length) return;

            const labels = items.map(function(i) { return i[labelField] || i.id; });
            const data = items.map(function(i) { return i[numField] || 0; });
            const ctx = document.getElementById("dataChart");

            if (chart) chart.destroy();
            chart = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: labels.slice(0, 20),
                    datasets: [{
                        label: numField,
                        data: data.slice(0, 20),
                        backgroundColor: "rgba(0,212,255,0.3)",
                        borderColor: "#00d4ff",
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { labels: { color: "#888" } } },
                    scales: {
                        x: { ticks: { color: "#666" }, grid: { color: "#1a1a2e" } },
                        y: { ticks: { color: "#666" }, grid: { color: "#1a1a2e" } }
                    }
                }
            });
        }

        function escHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
        loadItems();
    </script>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Tool Template Builder
# ---------------------------------------------------------------------------

def _build_tool_python(app_name: str, entity: str, fields: list, description: str) -> str:
    """Build Flask backend for a tool app (input → process → output)."""
    ep = _pluralize(entity)

    return '''import os
import json
import uuid
from datetime import datetime
from flask import Flask, send_file, request, jsonify

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False

APP_NAME = "''' + app_name + '''"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

HISTORY_FILE = os.path.join(DATA_DIR, "history.json")


def _load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_history(items):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "templates", "index.html"))


@app.route("/api/process", methods=["POST"])
def process_input():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input provided"}), 400

    input_text = data.get("input", "")

    # Process the input (customize this logic per tool)
    result = {
        "input": input_text,
        "output": input_text,  # Default: echo back
        "char_count": len(input_text),
        "word_count": len(input_text.split()),
        "processed_at": datetime.now().isoformat(),
    }

    # Save to history
    record = {
        "id": str(uuid.uuid4())[:8],
        "input": input_text,
        "output": result.get("output", ""),
        "created_at": datetime.now().isoformat(),
    }
    history = _load_history()
    history.insert(0, record)
    if len(history) > 100:
        history = history[:100]
    _save_history(history)

    return jsonify(result)


@app.route("/api/history", methods=["GET"])
def get_history():
    items = _load_history()
    limit = request.args.get("limit", 20, type=int)
    return jsonify(items[:limit])


@app.route("/api/history/clear", methods=["POST"])
def clear_history():
    items = _load_history()
    _save_history([])
    return jsonify({"removed": len(items)})


if __name__ == "__main__":
    port = int(os.environ.get("KROWORK_PORT", 5000))
    print(APP_NAME + " running at http://127.0.0.1:" + str(port))
    app.run(host="127.0.0.1", port=port, debug=False)
'''


def _build_tool_html(app_name, description, entity, entity_label, fields):
    """Build tool HTML with input → action → output layout."""
    title = description.split("-")[0].strip() if "-" in description else description
    title = title.strip() or app_name.replace("-", " ").title()

    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>''' + title + '''</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; min-height: 100vh; }
        .header { background: #1a1a2e; padding: 16px 24px; border-bottom: 1px solid #2a2a3e; }
        .header h1 { font-size: 20px; color: #00d4ff; font-weight: 600; }
        .header .subtitle { font-size: 13px; color: #888; }
        .container { max-width: 800px; margin: 0 auto; padding: 24px; }
        .card { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
        .card h3 { color: #00d4ff; margin-bottom: 12px; font-size: 15px; }
        textarea { background: #0f0f0f; border: 1px solid #2a2a3e; border-radius: 6px; padding: 12px 14px; color: #e0e0e0; font-size: 14px; width: 100%; min-height: 100px; resize: vertical; font-family: monospace; outline: none; }
        textarea:focus { border-color: #00d4ff; }
        input { background: #0f0f0f; border: 1px solid #2a2a3e; border-radius: 6px; padding: 10px 14px; color: #e0e0e0; font-size: 14px; width: 100%; outline: none; }
        input:focus { border-color: #00d4ff; }
        button { background: #00d4ff; color: #0f0f0f; border: none; border-radius: 6px; padding: 12px 24px; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.2s; margin-top: 12px; }
        button:hover { background: #00b8d9; }
        button:disabled { background: #333; cursor: not-allowed; }
        button.secondary { background: #2a2a3e; color: #e0e0e0; }
        button.secondary:hover { background: #3a3a4e; }
        button.danger { background: #ff4757; color: #fff; }
        button.small { padding: 6px 12px; font-size: 12px; }
        .result-box { background: #0f0f0f; border: 1px solid #2a2a3e; border-radius: 6px; padding: 16px; margin-top: 12px; min-height: 60px; white-space: pre-wrap; word-break: break-all; font-family: monospace; font-size: 14px; }
        .result-box.error { border-color: #ff4757; color: #ff4757; }
        .result-box.success { border-color: #2ed573; color: #2ed573; }
        .stats { display: flex; gap: 16px; margin-top: 8px; }
        .stat { font-size: 12px; color: #888; }
        .stat span { color: #00d4ff; }
        .history-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #1a1a2e; font-size: 13px; }
        .history-item:last-child { border-bottom: none; }
        .history-input { color: #aaa; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 400px; }
        .history-date { color: #555; font-size: 11px; margin-left: 12px; }
        .loading { text-align: center; color: #888; padding: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>''' + title + '''</h1>
        <div class="subtitle">''' + description + '''</div>
    </div>
    <div class="container">
        <div class="card">
            <h3>输入</h3>
            <textarea id="input-text" placeholder="在此输入内容..."></textarea>
            <button onclick="processInput()" id="btn-process">执行</button>
            <button class="secondary" onclick="copyResult()" style="margin-left:8px">复制结果</button>
        </div>
        <div class="card" id="result-card" style="display:none">
            <h3>结果</h3>
            <div class="result-box" id="result-output"></div>
            <div class="stats" id="result-stats"></div>
        </div>
        <div class="card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                <h3 style="margin:0">历史记录</h3>
                <button class="danger small" onclick="clearHistory()">清除</button>
            </div>
            <div id="history-list"><div class="loading">加载中...</div></div>
        </div>
    </div>
    <script>
        async function processInput() {
            const input = document.getElementById("input-text").value;
            if (!input.trim()) return;

            const btn = document.getElementById("btn-process");
            btn.disabled = true;
            btn.textContent = "处理中...";

            try {
                const res = await fetch("/api/process", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({input: input})
                });
                const data = await res.json();

                const card = document.getElementById("result-card");
                const output = document.getElementById("result-output");
                const stats = document.getElementById("result-stats");

                card.style.display = "block";
                output.textContent = data.output || JSON.stringify(data, null, 2);
                output.className = "result-box" + (data.error ? " error" : " success");

                let statsHtml = "";
                if (data.char_count !== undefined) statsHtml += '<div class="stat">字符数: <span>' + data.char_count + '</span></div>';
                if (data.word_count !== undefined) statsHtml += '<div class="stat">词数: <span>' + data.word_count + '</span></div>';
                stats.innerHTML = statsHtml;

                loadHistory();
            } catch(e) {
                const card = document.getElementById("result-card");
                const output = document.getElementById("result-output");
                card.style.display = "block";
                output.textContent = "错误: " + e.message;
                output.className = "result-box error";
            }

            btn.disabled = false;
            btn.textContent = "执行";
        }

        function copyResult() {
            const text = document.getElementById("result-output").textContent;
            navigator.clipboard.writeText(text).then(function() {
                const btn = document.querySelector('[onclick="copyResult()"]');
                btn.textContent = "已复制!";
                setTimeout(function() { btn.textContent = "复制结果"; }, 1500);
            });
        }

        async function loadHistory() {
            const res = await fetch("/api/history?limit=10");
            const items = await res.json();
            const list = document.getElementById("history-list");
            if (!items.length) {
                list.innerHTML = '<div style="text-align:center;color:#555;padding:20px">暂无历史</div>';
                return;
            }
            list.innerHTML = items.map(function(item) {
                let dateStr = new Date(item.created_at).toLocaleString("zh-CN");
                return '<div class="history-item">'
                    + '<span class="history-input">' + escHtml(item.input) + '</span>'
                    + '<span class="history-date">' + dateStr + '</span>'
                    + '</div>';
            }).join("");
        }

        async function clearHistory() {
            await fetch("/api/history/clear", {method: "POST"});
            loadHistory();
        }

        function escHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

        loadHistory();
    </script>
</body>
</html>'''


# ---------------------------------------------------------------------------
# Templates (fallback when files not found)
# ---------------------------------------------------------------------------

DEFAULT_MAIN_PY_TEMPLATE = """$all_imports

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

APP_NAME = "$app_name"
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)

$python_logic

@app.route("/")
def index():
    return send_file(os.path.join(os.path.dirname(__file__), "templates", "index.html"))

$extra_routes

if __name__ == "__main__":
    port = int(os.environ.get("KROWORK_PORT", 5000))
    print(APP_NAME + " running at http://127.0.0.1:" + str(port))
    app.run(host="127.0.0.1", port=port, debug=False)
"""

DEFAULT_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f0f0f; color: #e0e0e0; min-height: 100vh; }
        .header { background: #1a1a2e; padding: 16px 24px; border-bottom: 1px solid #2a2a3e; display: flex; align-items: center; justify-content: space-between; }
        .header h1 { font-size: 18px; color: #00d4ff; font-weight: 600; }
        .header .subtitle { font-size: 13px; color: #888; }
        .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
        .card { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
        input, select, textarea { background: #0f0f0f; border: 1px solid #2a2a3e; border-radius: 6px; padding: 10px 14px; color: #e0e0e0; font-size: 14px; outline: none; width: 100%; }
        input:focus, select:focus, textarea:focus { border-color: #00d4ff; }
        button { background: #00d4ff; color: #0f0f0f; border: none; border-radius: 6px; padding: 10px 20px; font-size: 14px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #00b8d9; }
        button:disabled { background: #333; cursor: not-allowed; }
        button.secondary { background: #2a2a3e; color: #e0e0e0; }
        button.secondary:hover { background: #3a3a4e; }
        .result { margin-top: 16px; padding: 16px; background: #0f0f0f; border-radius: 6px; border: 1px solid #2a2a3e; }
        .error { color: #ff4757; background: rgba(255, 71, 87, 0.1); border-color: #ff4757; }
        .success { color: #2ed573; }
        .loading { text-align: center; padding: 20px; color: #888; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid #2a2a3e; }
        th { color: #00d4ff; font-weight: 600; font-size: 13px; text-transform: uppercase; }
        a { color: #00d4ff; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .badge-green { background: rgba(46, 213, 115, 0.2); color: #2ed573; }
        .badge-red { background: rgba(255, 71, 87, 0.2); color: #ff4757; }
        .badge-yellow { background: rgba(255, 165, 2, 0.2); color: #ffa502; }
        .badge-blue { background: rgba(0, 212, 255, 0.2); color: #00d4ff; }
        $css_styles
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>$title</h1>
            <div class="subtitle">$description</div>
        </div>
    </div>
    <div class="container">
        $html_body
    </div>
    <script>
        $javascript
    </script>
</body>
</html>"""
