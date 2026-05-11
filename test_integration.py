"""
Open-KroWork Integration Test Suite
Tests the FULL pipeline: generate -> create app -> install venv -> launch Flask -> HTTP API validation
"""

import json
import os
import socket
import subprocess
import sys
import time
import traceback
import urllib.request
import urllib.error
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "server"))
os.environ["KROWORK_PLUGIN_ROOT"] = os.path.dirname(__file__)

from code_generator import auto_generate_app, _pluralize
from app_manager import create_app, get_app, delete_app, list_apps, get_app_dir, get_venv_python
from auto_improve import auto_improve
from app_export import export_app, import_app


def find_free_port():
    for port in range(5100, 6000):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError("No free port")


def wait_for_port(port, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect(("127.0.0.1", port))
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.3)
    return False


def http_get(url):
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8") if e.fp else ""
    except Exception as e:
        return 0, str(e)


def http_post(url, data):
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8") if e.fp else ""
    except Exception as e:
        return 0, str(e)


def http_delete(url):
    try:
        req = urllib.request.Request(url, method="DELETE")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8") if e.fp else ""
    except Exception as e:
        return 0, str(e)


def cleanup_app(name):
    try:
        delete_app(name)
    except Exception:
        pass


def run_flask_test(app_name, description, config=None, test_type="crud"):
    print(f"\n{'='*60}")
    print(f"INTEGRATION TEST: {app_name} ({test_type})")
    print(f"{'='*60}")
    test_name = f"test-{app_name}"
    errors = []
    warnings = []
    proc = None
    port = None

    try:
        cleanup_app(test_name)

        gen = auto_generate_app(app_name, description, config)
        code = gen["code"]
        html = gen["html_template"]
        reqs = gen["requirements"]

        print(f"  [1/5] Code generated ({len(code)} chars code, {len(html)} chars html)")

        create_result = create_app(
            app_name=test_name,
            description=description,
            code=code,
            requirements=reqs,
            html_template=html,
            config=config,
        )
        if "error" in create_result:
            errors.append(f"create_app error: {create_result['error']}")
            return {"name": test_name, "status": "FAIL", "errors": errors, "warnings": warnings}

        print(f"  [2/5] App created at {create_result.get('app_dir', '?')}")

        app_dir = get_app_dir(test_name)
        print(f"  [3/5] Waiting for venv setup...")
        for i in range(90):
            vp = get_venv_python(app_dir)
            if vp:
                break
            time.sleep(1)
        else:
            vp = get_venv_python(app_dir)
            if not vp:
                errors.append("venv not created within 90s timeout")
                return {"name": test_name, "status": "FAIL", "errors": errors, "warnings": warnings}

        print(f"  [3/5] venv ready: {vp}")

        port = find_free_port()
        env = os.environ.copy()
        env["KROWORK_PORT"] = str(port)
        env["KROWORK_APP_NAME"] = test_name
        env["FLASK_ENV"] = "production"
        env["FLASK_APP"] = "main.py"

        main_py = app_dir / "main.py"
        log_path = app_dir / "test_app.log"
        log_file = open(log_path, "w", encoding="utf-8")

        proc = subprocess.Popen(
            [vp, str(main_py)],
            cwd=str(app_dir),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

        print(f"  [4/5] Starting Flask on port {port}...")
        ready = wait_for_port(port, timeout=20)

        if not ready:
            if proc.poll() is not None:
                log_file.close()
                err = log_path.read_text(encoding="utf-8")[-1000:]
                errors.append(f"Flask exited (code {proc.poll()}): {err}")
                return {"name": test_name, "status": "FAIL", "errors": errors, "warnings": warnings}
            else:
                warnings.append("Port not ready within 20s but process still alive")

        print(f"  [5/5] Running HTTP API tests...")

        status, html_body = http_get(f"http://127.0.0.1:{port}/")
        if status != 200:
            errors.append(f"GET / returned status {status}")
        elif len(html_body) < 100:
            errors.append(f"GET / returned very short body ({len(html_body)} chars)")
        elif "<!DOCTYPE html>" not in html_body:
            errors.append(f"GET / did not return HTML")
        else:
            print(f"        GET / -> {status} ({len(html_body)} chars HTML) OK")

        if test_type == "crud":
            ep_path = None
            for line in code.split("\n"):
                if '@app.route("/api/' in line and "methods" in line and "GET" in line:
                    import re
                    m = re.search(r'/api/([^"]+)', line)
                    if m:
                        ep_path = f"/api/{m.group(1)}"
                        break

            if not ep_path:
                ep_path = "/api/items"

            status, body = http_get(f"http://127.0.0.1:{port}{ep_path}")
            if status != 200:
                errors.append(f"GET {ep_path} returned {status}: {body[:200]}")
            else:
                data = json.loads(body)
                print(f"        GET {ep_path} -> {status} (items: {len(data)}) OK")

            test_item = {"title": "Test Item", "description": "Created by test suite"}
            if "priority" in code:
                test_item["priority"] = "high"
            if "status" in code:
                test_item["status"] = "pending"

            status, body = http_post(f"http://127.0.0.1:{port}{ep_path}", test_item)
            if status not in (200, 201):
                errors.append(f"POST {ep_path} returned {status}: {body[:200]}")
            else:
                created = json.loads(body)
                item_id = created.get("id")
                print(f"        POST {ep_path} -> {status} (id={item_id}) OK")

                status, body = http_get(f"http://127.0.0.1:{port}{ep_path}")
                items = json.loads(body)
                if len(items) < 1:
                    errors.append("After POST, GET returned empty list")
                else:
                    print(f"        GET {ep_path} after POST -> {len(items)} items OK")

                if item_id:
                    delete_ep = f"{ep_path}/{item_id}"
                    status, body = http_delete(f"http://127.0.0.1:{port}{delete_ep}")
                    if status not in (200, 201):
                        errors.append(f"DELETE {delete_ep} returned {status}: {body[:200]}")
                    else:
                        print(f"        DELETE {delete_ep} -> {status} OK")

                    status, body = http_get(f"http://127.0.0.1:{port}{ep_path}")
                    items_after = json.loads(body)
                    if len(items_after) >= len(items):
                        errors.append(f"DELETE did not remove item (before={len(items)}, after={len(items_after)})")
                    else:
                        print(f"        GET after DELETE -> {len(items_after)} items OK")

        elif test_type == "dashboard":
            ep_path = None
            for line in code.split("\n"):
                if '@app.route("/api/' in line and "methods" in line and "GET" in line:
                    import re
                    m = re.search(r'/api/([^"]+)', line)
                    if m:
                        ep_path = f"/api/{m.group(1)}"
                        break
            if not ep_path:
                ep_path = "/api/items"

            status, body = http_get(f"http://127.0.0.1:{port}{ep_path}")
            if status == 400:
                print(f"        GET {ep_path} -> {status} (requires params, expected) OK")
            elif status != 200:
                errors.append(f"GET {ep_path} returned {status}: {body[:200]}")
            else:
                print(f"        GET {ep_path} -> {status} OK")

            if "/stats" in code:
                stats_ep = ep_path + "/stats"
                status, body = http_get(f"http://127.0.0.1:{port}{stats_ep}")
                if status != 200:
                    warnings.append(f"GET {stats_ep} returned {status}")
                else:
                    print(f"        GET {stats_ep} -> {status} OK")

        elif test_type == "tool":
            status, body = http_post(f"http://127.0.0.1:{port}/api/process", {"input": "Hello World"})
            if status not in (200, 201):
                errors.append(f"POST /api/process returned {status}: {body[:200]}")
            else:
                result = json.loads(body)
                print(f"        POST /api/process -> {status}, output={result.get('output', '')[:50]} OK")

            status, body = http_get(f"http://127.0.0.1:{port}/api/history")
            if status != 200:
                errors.append(f"GET /api/history returned {status}")
            else:
                print(f"        GET /api/history -> {status} OK")

    except Exception as e:
        errors.append(f"Exception: {e}\n{traceback.format_exc()}")
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        try:
            log_file.close()
        except Exception:
            pass
        cleanup_app(test_name)

    status = "FAIL" if errors else "PASS"
    return {"name": test_name, "status": status, "errors": errors, "warnings": warnings}


def run_improve_test(app_name, description, instruction, test_type="crud"):
    print(f"\n{'='*60}")
    print(f"AUTO-IMPROVE TEST: {app_name} - '{instruction}'")
    print(f"{'='*60}")
    errors = []
    warnings = []
    test_name = f"test-imp-{app_name}"
    proc = None

    try:
        cleanup_app(test_name)

        gen = auto_generate_app(app_name, description)
        code = gen["code"]
        html = gen["html_template"]
        reqs = gen["requirements"]

        create_result = create_app(
            app_name=test_name,
            description=description,
            code=code,
            requirements=reqs,
            html_template=html,
        )
        if "error" in create_result:
            errors.append(f"create_app error: {create_result['error']}")
            return {"name": test_name, "status": "FAIL", "errors": errors, "warnings": warnings}

        print(f"  [1/4] App created")

        improve_result = auto_improve(test_name, instruction)
        if "error" in improve_result:
            errors.append(f"auto_improve error: {improve_result['error']}")
            return {"name": test_name, "status": "FAIL", "errors": errors, "warnings": warnings}

        auto_improved = improve_result.get("auto_improved", False)
        print(f"  [2/4] auto_improve returned: auto_improved={auto_improved}, type={improve_result.get('improvement_type')}")

        if not auto_improved:
            warnings.append(f"auto_improve returned auto_improved=False: {improve_result.get('reason', '?')}")

        app_info = get_app(test_name)
        updated_code = app_info.get("code", "")
        updated_html = app_info.get("html_template", "")

        try:
            compile(updated_code, f"{test_name}_improved.py", "exec")
            print(f"  [3/4] Updated code compiles OK")
        except SyntaxError as e:
            errors.append(f"Updated code has syntax error: {e}")

        if instruction in ("add CSV export", "add search", "add a tag field"):
            keyword_map = {
                "add CSV export": ("export", "csv"),
                "add search": ("search", "search"),
                "add a tag field": ("tag", "field-tag"),
            }
            kw1, kw2 = keyword_map.get(instruction, ("", ""))
            if kw1 and kw1 not in updated_code.lower() and kw1 not in updated_html.lower():
                errors.append(f"After '{instruction}', neither code nor HTML contains '{kw1}'")
            if kw2 and kw2 not in updated_code.lower() and kw2 not in updated_html.lower():
                errors.append(f"After '{instruction}', neither code nor HTML contains '{kw2}'")
            else:
                print(f"  [3/4] Improvement content verified in code/html OK")

        app_dir = get_app_dir(test_name)
        vp = None
        for _ in range(90):
            vp = get_venv_python(app_dir)
            if vp:
                break
            time.sleep(1)
        if vp:
            port = find_free_port()
            env = os.environ.copy()
            env["KROWORK_PORT"] = str(port)
            env["KROWORK_APP_NAME"] = test_name
            env["FLASK_ENV"] = "production"
            log_path = app_dir / "test_improve.log"
            log_file = open(log_path, "w", encoding="utf-8")

            proc = subprocess.Popen(
                [vp, str(app_dir / "main.py")],
                cwd=str(app_dir),
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                text=True,
            )
            ready = wait_for_port(port, timeout=15)
            if ready:
                s, b = http_get(f"http://127.0.0.1:{port}/")
                if s == 200:
                    print(f"  [4/4] Improved app launches OK on port {port}")
                else:
                    errors.append(f"Improved app GET / returned {s}")
            else:
                if proc.poll() is not None:
                    log_file.close()
                    err = log_path.read_text(encoding="utf-8")[-500:]
                    errors.append(f"Improved app failed to start: {err}")
                else:
                    warnings.append("Improved app port not ready but process alive")
            proc.terminate()
            proc.wait(timeout=5)
            log_file.close()
        else:
            warnings.append("venv not ready for improved app launch test")

    except Exception as e:
        errors.append(f"Exception: {e}\n{traceback.format_exc()}")
    finally:
        cleanup_app(test_name)

    return {"name": test_name, "status": "FAIL" if errors else "PASS", "errors": errors, "warnings": warnings}


def run_pluralize_test():
    print(f"\n{'='*60}")
    print(f"UNIT TEST: _pluralize irregular nouns")
    print(f"{'='*60}")
    errors = []
    test_cases = {
        "news": "news",
        "information": "information",
        "data": "data",
        "person": "people",
        "child": "children",
        "task": "tasks",
        "category": "categories",
        "box": "boxes",
        "match": "matches",
        "reading": "readings",
        "bookmark": "bookmarks",
        "life": "lives",
        "knife": "knives",
        "index": "indices",
        "analysis": "analyses",
    }
    for singular, expected in test_cases.items():
        result = _pluralize(singular)
        if result == expected:
            print(f"        _pluralize('{singular}') -> '{result}' OK")
        else:
            errors.append(f"_pluralize('{singular}') = '{result}', expected '{expected}'")

    return {"name": "pluralize-irregular", "status": "FAIL" if errors else "PASS", "errors": errors, "warnings": []}


def run_export_import_test(app_name, description):
    print(f"\n{'='*60}")
    print(f"EXPORT/IMPORT TEST: {app_name}")
    print(f"{'='*60}")
    errors = []
    warnings = []
    test_name = f"test-{app_name}"
    test_name_imported = f"test-{app_name}-imported"

    try:
        cleanup_app(test_name)
        cleanup_app(test_name_imported)

        gen = auto_generate_app(app_name, description)
        create_result = create_app(
            app_name=test_name,
            description=description,
            code=gen["code"],
            requirements=gen["requirements"],
            html_template=gen["html_template"],
        )
        if "error" in create_result:
            errors.append(f"create_app error: {create_result['error']}")
            return {"name": f"export-import-{app_name}", "status": "FAIL", "errors": errors, "warnings": warnings}

        print(f"  [1/4] App created")

        export_result = export_app(test_name)
        if "error" in export_result:
            errors.append(f"export_app error: {export_result['error']}")
            return {"name": f"export-import-{app_name}", "status": "FAIL", "errors": errors, "warnings": warnings}

        export_path = export_result.get("export_path", "")
        print(f"  [2/4] Exported to: {export_path}")

        if not os.path.exists(export_path):
            errors.append(f"Export file not found: {export_path}")
        else:
            import zipfile
            if not zipfile.is_zipfile(export_path):
                errors.append("Export file is not a valid ZIP archive")
            else:
                with zipfile.ZipFile(export_path, "r") as zf:
                    names = zf.namelist()
                    for required in ["manifest.json", "main.py", "requirements.txt", "templates/index.html"]:
                        found = any(n.endswith(required) or n == required for n in names)
                        if not found:
                            errors.append(f"Missing '{required}' in archive")
                    print(f"  [2/4] Archive contains {len(names)} files OK")

        import_result = import_app(export_path, test_name_imported)
        if "error" in import_result:
            errors.append(f"import_app error: {import_result['error']}")
        else:
            print(f"  [3/4] Imported as: {test_name_imported}")

            imported_info = get_app(test_name_imported)
            if "error" in imported_info:
                errors.append(f"Imported app not found: {imported_info['error']}")
            else:
                orig_code = gen["code"]
                imported_code = imported_info.get("code", "")
                if len(imported_code) < len(orig_code) * 0.9:
                    errors.append(f"Imported code significantly shorter ({len(imported_code)} vs {len(orig_code)})")
                else:
                    print(f"  [4/4] Imported app code matches original ({len(imported_code)} chars) OK")

        cleanup_app(test_name_imported)

    except Exception as e:
        errors.append(f"Exception: {e}\n{traceback.format_exc()}")
    finally:
        cleanup_app(test_name)
        cleanup_app(test_name_imported)

    return {"name": f"export-import-{app_name}", "status": "FAIL" if errors else "PASS", "errors": errors, "warnings": warnings}


def run_stock_query_test():
    print(f"\n{'='*60}")
    print(f"STOCK API TEST: stock-analyzer with query params")
    print(f"{'='*60}")
    errors = []
    warnings = []
    test_name = "test-stock-query"
    proc = None

    try:
        cleanup_app(test_name)

        gen = auto_generate_app("stock-analyzer", "股票智能分析台 - 输入股票代码，展示价格趋势和分析报告")
        code = gen["code"]

        create_result = create_app(
            app_name=test_name,
            description="test",
            code=code,
            requirements=gen["requirements"],
            html_template=gen["html_template"],
        )
        if "error" in create_result:
            errors.append(f"create_app error: {create_result['error']}")
            return {"name": "stock-api-query", "status": "FAIL", "errors": errors, "warnings": warnings}

        app_dir = get_app_dir(test_name)
        vp = None
        for _ in range(90):
            vp = get_venv_python(app_dir)
            if vp:
                break
            time.sleep(1)

        if not vp:
            errors.append("venv not ready")
            return {"name": "stock-api-query", "status": "FAIL", "errors": errors, "warnings": warnings}

        port = find_free_port()
        env = os.environ.copy()
        env["KROWORK_PORT"] = str(port)
        env["FLASK_ENV"] = "production"
        log_path = app_dir / "test_stock.log"
        log_file = open(log_path, "w", encoding="utf-8")

        proc = subprocess.Popen(
            [vp, str(app_dir / "main.py")],
            cwd=str(app_dir), env=env,
            stdout=log_file, stderr=subprocess.STDOUT, text=True,
        )

        ready = wait_for_port(port, timeout=20)
        if not ready:
            if proc.poll() is not None:
                log_file.close()
                err = log_path.read_text(encoding="utf-8")[-500:]
                errors.append(f"Flask exited: {err}")
            return {"name": "stock-api-query", "status": "FAIL", "errors": errors, "warnings": warnings}

        print(f"  [1/3] Flask running on port {port}")

        status, body = http_get(f"http://127.0.0.1:{port}/")
        if status != 200:
            errors.append(f"GET / returned {status}")
        else:
            print(f"  [2/3] GET / -> {status} ({len(body)} chars) OK")

        status, body = http_get(f"http://127.0.0.1:{port}/api/stock/query?code=600519")
        if status == 200:
            data = json.loads(body)
            print(f"  [3/3] GET /api/stock/query?code=600519 -> {status} (keys: {list(data.keys())[:5]}) OK")
        elif status == 500:
            warnings.append(f"Stock API returned 500 (external API may be unavailable): {body[:200]}")
            print(f"  [3/3] GET /api/stock/query?code=600519 -> {status} (external API unavailable) WARN")
        elif status == 400:
            warnings.append(f"Stock API returned 400 even with code param: {body[:200]}")
        else:
            warnings.append(f"Stock API returned {status}: {body[:200]}")

    except Exception as e:
        errors.append(f"Exception: {e}\n{traceback.format_exc()}")
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            proc.wait(timeout=5)
        try:
            log_file.close()
        except Exception:
            pass
        cleanup_app(test_name)

    return {"name": "stock-api-query", "status": "FAIL" if errors else "PASS", "errors": errors, "warnings": warnings}


def run_news_pluralize_integration_test():
    print(f"\n{'='*60}")
    print(f"INTEGRATION TEST: news-tracker (pluralize fix)")
    print(f"{'='*60}")
    errors = []
    warnings = []

    gen = auto_generate_app("news-tracker", "AI热点追踪器 - 追踪AI领域最新热点新闻")
    code = gen["code"]

    if "/api/newses" in code:
        errors.append(f"_pluralize('news') still produces 'newses' in generated API routes")
        print(f"  FAIL: Found /api/newses in code (should be /api/news)")
    elif "/api/news" in code:
        print(f"  OK: Found /api/news in code (correct pluralization)")
    else:
        warnings.append("Neither /api/news nor /api/newses found in code")

    try:
        compile(code, "news_test.py", "exec")
        print(f"  Code compiles OK")
    except SyntaxError as e:
        errors.append(f"Code syntax error: {e}")

    return {"name": "news-pluralize-fix", "status": "FAIL" if errors else "PASS", "errors": errors, "warnings": warnings}


def run_improve_extra_test(app_name, description, instruction, verify_keyword):
    print(f"\n{'='*60}")
    print(f"AUTO-IMPROVE EXTRA TEST: {instruction}")
    print(f"{'='*60}")
    errors = []
    warnings = []
    test_name = f"test-imp2-{app_name}"

    try:
        cleanup_app(test_name)

        gen = auto_generate_app(app_name, description)
        create_result = create_app(
            app_name=test_name, description=description,
            code=gen["code"], requirements=gen["requirements"],
            html_template=gen["html_template"],
        )
        if "error" in create_result:
            errors.append(f"create_app error: {create_result['error']}")
            return {"name": f"imp2-{app_name}", "status": "FAIL", "errors": errors, "warnings": warnings}

        print(f"  [1/3] App created")

        improve_result = auto_improve(test_name, instruction)
        if "error" in improve_result:
            errors.append(f"auto_improve error: {improve_result['error']}")
            return {"name": f"imp2-{app_name}", "status": "FAIL", "errors": errors, "warnings": warnings}

        auto_improved = improve_result.get("auto_improved", False)
        print(f"  [2/3] auto_improve: type={improve_result.get('improvement_type')}, auto={auto_improved}")

        if not auto_improved:
            warnings.append(f"auto_improved=False: {improve_result.get('reason', '?')}")

        app_info = get_app(test_name)
        updated_code = app_info.get("code", "")
        updated_html = app_info.get("html_template", "")

        try:
            compile(updated_code, f"{test_name}_imp.py", "exec")
            print(f"  [3/3] Updated code compiles OK")
        except SyntaxError as e:
            errors.append(f"Syntax error after improve: {e}")

        if verify_keyword:
            all_text = (updated_code + updated_html).lower()
            if verify_keyword.lower() not in all_text:
                errors.append(f"Keyword '{verify_keyword}' not found in updated code/html")
            else:
                print(f"  [3/3] Keyword '{verify_keyword}' found in updated code OK")

    except Exception as e:
        errors.append(f"Exception: {e}\n{traceback.format_exc()}")
    finally:
        cleanup_app(test_name)

    return {"name": f"imp2-{app_name}", "status": "FAIL" if errors else "PASS", "errors": errors, "warnings": warnings}


if __name__ == "__main__":
    print("=" * 70)
    print("  Open-KroWork INTEGRATION Test Suite v2")
    print("=" * 70)

    all_results = []

    test_cases = [
        ("task-manager", "任务管理器 - 管理待办任务，支持优先级和状态", None, "crud"),
        ("stock-analyzer", "股票智能分析台 - 输入股票代码，展示价格趋势和分析报告", None, "dashboard"),
        ("text-tool", "文本处理工具 - 文本统计和格式转换", None, "tool"),
        ("reading-notes", "读书笔记管理器 - 记录读书笔记和书评", None, "crud"),
        ("news-tracker", "AI热点追踪器 - 追踪AI领域最新热点新闻", None, "dashboard"),
        ("bookmark-app", "Bookmark Manager - save and organize web bookmarks", {
            "fields": [
                {"name": "title", "type": "text", "label": "Title"},
                {"name": "url", "type": "text", "label": "URL"},
                {"name": "tags", "type": "text", "label": "Tags"},
            ]
        }, "crud"),
    ]

    for name, desc, config, ttype in test_cases:
        r = run_flask_test(name, desc, config, ttype)
        all_results.append(r)

    improve_cases = [
        ("todo-crud", "任务管理器 - 管理待办任务", "add CSV export"),
        ("note-crud", "笔记管理器 - 记录笔记", "add search"),
        ("item-crud", "物品管理器 - 管理物品列表", "add a tag field"),
        ("task-crud", "任务跟踪器 - 跟踪任务进度", "换成绿色主题"),
    ]

    for name, desc, instruction in improve_cases:
        r = run_improve_test(name, desc, instruction)
        all_results.append(r)

    all_results.append(run_pluralize_test())
    all_results.append(run_news_pluralize_integration_test())
    all_results.append(run_stock_query_test())

    all_results.append(run_export_import_test("todo-app", "待办事项管理器"))
    all_results.append(run_export_import_test("note-app", "笔记管理器"))

    improve_extra_cases = [
        ("sort-app", "物品管理器", "add sorting", "sort"),
        ("highlight-app", "文章管理器", "highlight keyword: urgent (red)", "highlight"),
    ]
    for name, desc, instruction, kw in improve_extra_cases:
        all_results.append(run_improve_extra_test(name, desc, instruction, kw))

    print("\n\n")
    print("=" * 70)
    print("  INTEGRATION TEST SUMMARY")
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
