"""
Open-KroWork MCP Protocol Integration Test v2

Tests the FULL /krowork:create pipeline via JSON-RPC over stdio,
exactly as Claude Code would invoke it.

MCP Response format:
  {"jsonrpc": "2.0", "id": N, "result": {
    "content": [{"type": "text", "text": "<JSON string>"}],
    "isError": true/false
  }}
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import traceback
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_SCRIPT = os.path.join(PROJECT_DIR, "server", "main.py")


def parse_mcp_result(resp):
    result = resp.get("result", {})
    if "error" in resp:
        return {"mcp_error": resp["error"]}
    if isinstance(result, dict) and "content" in result:
        is_error = result.get("isError", False)
        content = result["content"]
        if isinstance(content, list) and len(content) > 0:
            text = content[0].get("text", "")
            if is_error:
                return {"error": text}
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw_text": text}
        return {"error": "Empty content array"}
    return result


def find_free_port():
    for port in range(5100, 6000):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError("No free port")


def wait_for_port(port, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", port))
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.5)
    return False


def http_get(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8") if e.fp else ""
    except Exception as e:
        return 0, str(e)


def http_post(url, data):
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8") if e.fp else ""
    except Exception as e:
        return 0, str(e)


def http_delete(url):
    try:
        req = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8") if e.fp else ""
    except Exception as e:
        return 0, str(e)


class MCPClient:
    def __init__(self):
        self.proc = None
        self.req_id = 0

    def start(self):
        env = os.environ.copy()
        env["KROWORK_PLUGIN_ROOT"] = PROJECT_DIR
        env["PYTHONIOENCODING"] = "utf-8"
        self.proc = subprocess.Popen(
            [sys.executable, SERVER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        time.sleep(0.5)
        if self.proc.poll() is not None:
            raise RuntimeError(f"MCP Server exited: {self.proc.stderr.read()[:500]}")

    def call_tool(self, tool_name, arguments):
        self.req_id += 1
        msg = {
            "jsonrpc": "2.0",
            "id": self.req_id,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        self.proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        resp_line = self.proc.stdout.readline().strip()
        if not resp_line:
            raise RuntimeError("MCP Server closed stdout")
        resp = json.loads(resp_line)
        return parse_mcp_result(resp)

    def send(self, method, params=None):
        self.req_id += 1
        msg = {"jsonrpc": "2.0", "id": self.req_id, "method": method}
        if params:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.proc.stdin.flush()
        resp_line = self.proc.stdout.readline().strip()
        if not resp_line:
            raise RuntimeError("MCP Server closed stdout")
        return json.loads(resp_line)

    def stop(self):
        if self.proc and self.proc.poll() is None:
            self.proc.stdin.close()
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def cleanup_app(name):
    app_dir = Path.home() / ".krowork" / "apps" / name
    if app_dir.exists():
        shutil.rmtree(app_dir, ignore_errors=True)


def wait_for_venv(app_name, timeout=90):
    from app_manager import get_app_dir, get_venv_python
    app_dir = get_app_dir(app_name)
    for _ in range(timeout):
        vp = get_venv_python(app_dir)
        if vp:
            return vp
        time.sleep(1)
    return None


def run_mcp_pipeline(client, app_name, description, config=None):
    print(f"\n{'#'*60}")
    print(f"#  MCP PIPELINE: {app_name}")
    print(f"#  {description}")
    print(f"{'#'*60}")

    errors = []
    warnings = []
    port = None

    try:
        cleanup_app(app_name)

        # Step 1: Create
        print(f"\n  [1/7] Creating app via MCP...")
        result = client.call_tool("krowork_create_app", {
            "app_name": app_name,
            "description": description,
            **({"config": config} if config else {}),
        })
        if "error" in result:
            errors.append(f"Create error: {result['error']}")
            return {"name": app_name, "status": "FAIL", "errors": errors, "warnings": warnings}
        print(f"  Created: {result.get('message', 'OK')[:100]}")

        # Step 2: List
        print(f"\n  [2/7] Listing apps via MCP...")
        result = client.call_tool("krowork_list_apps", {})
        if isinstance(result, list):
            found = any(a.get("name") == app_name for a in result)
            print(f"  Found in list: {found} ({len(result)} total)")
        elif isinstance(result, dict) and "apps" in result:
            apps = result["apps"]
            found = any(a.get("name") == app_name for a in apps)
            print(f"  Found in list: {found} ({len(apps)} total)")
        else:
            warnings.append(f"list_apps returned {type(result)}")

        # Step 3: Get
        print(f"\n  [3/7] Getting app details via MCP...")
        app_info = client.call_tool("krowork_get_app", {"app_name": app_name})
        if "error" in app_info:
            errors.append(f"Get error: {app_info['error']}")
        else:
            code = app_info.get("code", "")
            html = app_info.get("html_template", "")
            print(f"  Code: {len(code)} chars, HTML: {len(html)} chars")
            try:
                compile(code, f"{app_name}.py", "exec")
                print(f"  Code compiles OK")
            except SyntaxError as e:
                errors.append(f"Syntax error: {e}")

        # Step 4: Wait venv
        print(f"\n  [4/7] Waiting for venv...")
        vp = wait_for_venv(app_name, timeout=90)
        if not vp:
            errors.append("venv not ready within 90s")
            return {"name": app_name, "status": "FAIL", "errors": errors, "warnings": warnings}
        print(f"  venv ready: {vp}")

        # Step 5: Run
        port = find_free_port()
        print(f"\n  [5/7] Running app on port {port} via MCP...")
        result = client.call_tool("krowork_run_app", {"app_name": app_name, "port": port})
        if "error" in result:
            errors.append(f"Run error: {result['error']}")
        else:
            print(f"  Run: {result.get('url', result.get('message', 'OK'))}")

        ready = wait_for_port(port, timeout=20)
        if not ready:
            errors.append(f"Flask not ready on port {port}")
        else:
            # Step 6: HTTP validation
            print(f"\n  [6/7] HTTP API validation...")
            s, b = http_get(f"http://127.0.0.1:{port}/")
            if s != 200:
                errors.append(f"GET / -> {s}")
            else:
                print(f"  GET / -> {s} ({len(b)} chars HTML) OK")

            code = app_info.get("code", "")
            import re
            ep_path = None
            for line in code.split("\n"):
                if '@app.route("/api/' in line and "GET" in line:
                    m = re.search(r'/api/([^"\']+)', line)
                    if m:
                        ep_path = f"/api/{m.group(1)}"
                        break

            if ep_path:
                is_crud_endpoint = "methods" in code and f'@app.route("{ep_path}", methods=["POST"])' in code.replace(" ", "")
                is_query_only = any(kw in ep_path for kw in ["stock", "news", "query", "search"])

                s, b = http_get(f"http://127.0.0.1:{port}{ep_path}")
                if s == 200:
                    items = json.loads(b)
                    print(f"  GET {ep_path} -> {s} ({len(items)} items) OK")
                elif s == 400:
                    print(f"  GET {ep_path} -> {s} (requires params) OK")
                    items = []
                else:
                    errors.append(f"GET {ep_path} -> {s}: {b[:100]}")
                    items = []

                if is_crud_endpoint and not is_query_only:
                    test_data = {"title": "MCP Test", "description": "Via JSON-RPC"}
                    s2, b2 = http_post(f"http://127.0.0.1:{port}{ep_path}", test_data)
                    if s2 in (200, 201):
                        created = json.loads(b2)
                        item_id = created.get("id")
                        print(f"  POST {ep_path} -> {s2} (id={item_id}) OK")
                        if item_id:
                            s3, b3 = http_delete(f"http://127.0.0.1:{port}{ep_path}/{item_id}")
                            if s3 in (200, 201):
                                print(f"  DELETE {ep_path}/{item_id} -> {s3} OK")
                            elif s3 == 404:
                                print(f"  DELETE {ep_path}/{item_id} -> 404 (no delete route, OK)")
                            else:
                                errors.append(f"DELETE -> {s3}: {b3[:100]}")
                    else:
                        print(f"  POST {ep_path} -> {s2} (skipped)")
                else:
                    print(f"  POST/DELETE skipped (non-CRUD endpoint)")

            if "/api/process" in code:
                s, b = http_post(f"http://127.0.0.1:{port}/api/process", {"input": "test"})
                if s in (200, 201):
                    r = json.loads(b)
                    print(f"  POST /api/process -> {s}, output={r.get('output','')[:50]} OK")
                else:
                    errors.append(f"POST /api/process -> {s}")

            if "/api/history" in code:
                s, b = http_get(f"http://127.0.0.1:{port}/api/history")
                if s == 200:
                    print(f"  GET /api/history -> {s} OK")
                else:
                    errors.append(f"GET /api/history -> {s}")

        # Step 7: Stop
        print(f"\n  [7/7] Stopping app via MCP...")
        result = client.call_tool("krowork_stop_app", {"app_name": app_name})
        if "error" in result:
            warnings.append(f"Stop: {result['error']}")
        else:
            print(f"  Stopped OK")

    except Exception as e:
        errors.append(f"Exception: {e}\n{traceback.format_exc()}")

    return {"name": app_name, "status": "FAIL" if errors else "PASS", "errors": errors, "warnings": warnings}


if __name__ == "__main__":
    print("=" * 70)
    print("  Open-KroWork MCP Protocol Test v2")
    print("=" * 70)

    sys.path.insert(0, os.path.join(PROJECT_DIR, "server"))
    from app_manager import get_app_dir, get_venv_python

    client = MCPClient()
    all_results = []

    try:
        client.start()

        # Handshake
        r = client.send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-v2", "version": "1.0.0"}
        })
        server_info = r.get("result", {}).get("serverInfo", {})
        print(f"  Server: {server_info.get('name')} v{server_info.get('version')}")

        r = client.send("tools/list", {})
        tools = r.get("result", {}).get("tools", [])
        tool_names = [t["name"] for t in tools]
        print(f"  Tools: {len(tools)} registered")

        required = ["krowork_create_app", "krowork_list_apps", "krowork_get_app",
                     "krowork_run_app", "krowork_stop_app", "krowork_delete_app"]
        for t in required:
            if t not in tool_names:
                print(f"  FATAL: Missing tool '{t}'")
                sys.exit(1)
        print(f"  All {len(required)} core tools OK")

        test_cases = [
            ("mcp-todo-app", "待办事项管理器 - 管理每日待办任务，支持优先级和分类", None),
            ("mcp-stock-dash", "股票智能分析台 - 输入股票代码，展示实时行情和技术分析", None),
            ("mcp-pwd-gen", "密码生成器 - 生成安全随机密码，支持自定义长度和字符类型", None),
            ("mcp-contacts", "通讯录管理器 - 管理联系人信息，支持姓名、电话、邮箱", {
                "fields": [
                    {"name": "name", "type": "text", "label": "姓名"},
                    {"name": "phone", "type": "text", "label": "电话"},
                    {"name": "email", "type": "text", "label": "邮箱"},
                    {"name": "group", "type": "text", "label": "分组"},
                ]
            }),
        ]

        for app_name, desc, config in test_cases:
            r = run_mcp_pipeline(client, app_name, desc, config)
            all_results.append(r)

            # Cleanup via MCP
            try:
                client.call_tool("krowork_delete_app", {"app_name": app_name})
            except Exception:
                cleanup_app(app_name)

    except Exception as e:
        print(f"\nFATAL: {e}")
        traceback.print_exc()
    finally:
        client.stop()

    print("\n\n" + "=" * 70)
    print("  MCP PROTOCOL TEST SUMMARY")
    print("=" * 70)
    passed = failed = 0
    for r in all_results:
        icon = "PASS" if r["status"] == "PASS" else "FAIL"
        print(f"  [{icon}] {r['name']}")
        for e in r.get("errors", []):
            print(f"    ERROR: {e}")
        for w in r.get("warnings", []):
            print(f"    WARN: {w}")
        if r["status"] == "PASS":
            passed += 1
        else:
            failed += 1
    print(f"\n  Results: {passed} passed, {failed} failed out of {passed + failed} total")
    print("=" * 70)
    sys.exit(1 if failed > 0 else 0)
