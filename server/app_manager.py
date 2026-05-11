"""Open-KroWork App Manager - CRUD operations for local apps."""

import json
import os
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from icon_generator import generate_icon_for_app


def get_apps_dir() -> Path:
    """Get the root directory for all KroWork apps."""
    custom = os.environ.get("KROWORK_APPS_DIR", "")
    if custom:
        return Path(custom).expanduser()
    return Path.home() / ".krowork" / "apps"


def get_app_dir(app_name: str) -> Path:
    """Get the directory for a specific app."""
    return get_apps_dir() / _sanitize_name(app_name)


def app_exists(app_name: str) -> bool:
    """Check if an app exists."""
    app_dir = get_app_dir(app_name)
    return app_dir.exists() and (app_dir / "app.json").exists()


def _sanitize_name(app_name: str) -> str:
    """Convert an app name to a safe directory/slug name."""
    # Try to transliterate common patterns
    safe_name = app_name.lower().replace(" ", "-").replace("_", "-")
    safe_name = "".join(c for c in safe_name if (c.isascii() and c.isalnum()) or c == "-")
    # Remove leading/trailing hyphens and collapse consecutive hyphens
    while "--" in safe_name:
        safe_name = safe_name.replace("--", "-")
    safe_name = safe_name.strip("-")
    if not safe_name:
        # Non-ASCII name: generate a stable slug from hash
        import hashlib
        safe_name = "app-" + hashlib.md5(app_name.encode()).hexdigest()[:6]
    return safe_name


def create_app(app_name: str, description: str, code: str = "",
               requirements: str = "", html_template: str = "",
               config: dict = None) -> dict:
    """Create a new KroWork app with the given code and metadata.

    If code is empty, auto-generates a complete app from the description.
    """
    # Auto-generate when no code provided
    if not code.strip() or not html_template.strip():
        from code_generator import auto_generate_app
        generated = auto_generate_app(app_name, description, config)
        if not code.strip():
            code = generated["code"]
        if not html_template.strip():
            html_template = generated["html_template"]
        if not requirements.strip():
            requirements = generated["requirements"]

    app_id = _sanitize_name(app_name)
    app_dir = get_apps_dir() / app_id

    if app_dir.exists():
        return {"error": f"App '{app_name}' already exists at {app_dir}"}

    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "templates").mkdir(exist_ok=True)
    (app_dir / "data").mkdir(exist_ok=True)

    # Write app metadata
    app_meta = {
        "id": app_id,
        "name": app_name,
        "description": description,
        "version": "1.0.0",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "status": "setting_up",
        "template": "web_app",
        "config": config or {},
    }
    (app_dir / "app.json").write_text(
        json.dumps(app_meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Write main application code
    (app_dir / "main.py").write_text(code, encoding="utf-8")

    # Write requirements.txt (always include flask)
    if requirements:
        req_lines = [l.strip() for l in requirements.strip().splitlines() if l.strip()]
        if not any(l.lower().startswith("flask") for l in req_lines):
            req_lines.insert(0, "flask")
        (app_dir / "requirements.txt").write_text("\n".join(req_lines), encoding="utf-8")
    else:
        (app_dir / "requirements.txt").write_text("flask", encoding="utf-8")
        requirements = "flask"

    # Write HTML template
    if html_template:
        (app_dir / "templates" / "index.html").write_text(
            html_template, encoding="utf-8"
        )

    final_req = requirements

    def _bg_setup():
        import traceback as _tb
        try:
            _create_launcher(app_dir, app_name, description)
            _create_shortcut(app_dir, app_name, description)
        except Exception as e:
            try:
                with open(app_dir / ".setup.log", "a", encoding="utf-8") as lf:
                    lf.write(f"[launcher/shortcut error] {e}\n{_tb.format_exc()}\n")
            except Exception:
                pass
        try:
            ok = _setup_venv(app_dir, final_req)
            _update_app_status(app_dir, "ready" if ok else "setup_failed")
        except Exception as e:
            _update_app_status(app_dir, "setup_failed")
            try:
                with open(app_dir / ".setup.log", "a", encoding="utf-8") as lf:
                    lf.write(f"[venv error] {e}\n{_tb.format_exc()}\n")
            except Exception:
                pass

    t = threading.Thread(target=_bg_setup, daemon=True)
    t.start()

    return {
        "success": True,
        "app_id": app_id,
        "app_name": app_name,
        "app_dir": str(app_dir),
        "shortcut": None,
        "status": "setting_up",
        "message": (
            f"App '{app_name}' created at {app_dir}. "
            f"Launcher, shortcut and dependencies are being set up in background — "
            f"the app will be ready to run shortly."
        ),
    }


def list_apps() -> dict:
    """List all KroWork apps."""
    apps_dir = get_apps_dir()
    if not apps_dir.exists():
        return {"apps": [], "total": 0}

    apps = []
    for entry in sorted(apps_dir.iterdir()):
        app_json_path = entry / "app.json"
        if entry.is_dir() and app_json_path.exists():
            try:
                meta = json.loads(app_json_path.read_text(encoding="utf-8"))
                apps.append({
                    "id": meta.get("id", entry.name),
                    "name": meta.get("name", entry.name),
                    "description": meta.get("description", ""),
                    "version": meta.get("version", "1.0.0"),
                    "status": meta.get("status", "created"),
                    "created_at": meta.get("created_at", ""),
                    "updated_at": meta.get("updated_at", ""),
                    "dir": str(entry),
                })
            except (json.JSONDecodeError, OSError):
                apps.append({
                    "name": entry.name,
                    "description": "(metadata error)",
                    "status": "error",
                    "dir": str(entry),
                })

    return {"apps": apps, "total": len(apps)}


def get_app(app_name: str) -> dict:
    """Get metadata about a specific app (no full code/HTML to keep responses small)."""
    app_dir = get_app_dir(app_name)
    app_json = app_dir / "app.json"

    if not app_json.exists():
        return {"error": f"App '{app_name}' not found"}

    try:
        meta = json.loads(app_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"Failed to read app metadata: {e}"}

    # Count lines of code (lightweight)
    main_py = app_dir / "main.py"
    code_lines = 0
    if main_py.exists():
        code_lines = len(main_py.read_text(encoding="utf-8").splitlines())

    html_path = app_dir / "templates" / "index.html"
    html_lines = 0
    if html_path.exists():
        html_lines = len(html_path.read_text(encoding="utf-8").splitlines())

    return {
        "id": meta.get("id", app_name),
        "name": meta.get("name", app_name),
        "description": meta.get("description", ""),
        "version": meta.get("version", "1.0.0"),
        "status": meta.get("status", "created"),
        "created_at": meta.get("created_at", ""),
        "updated_at": meta.get("updated_at", ""),
        "template": meta.get("template", "web_app"),
        "config": meta.get("config", {}),
        "dir": str(app_dir),
        "code_lines": code_lines,
        "html_lines": html_lines,
    }


def update_app(app_name: str, code: str = None, html_template: str = None,
               requirements: str = None, description: str = None,
               config: dict = None) -> dict:
    """Update an existing app's code, template, or metadata."""
    app_dir = get_app_dir(app_name)
    app_json = app_dir / "app.json"

    if not app_json.exists():
        return {"error": f"App '{app_name}' not found"}

    try:
        meta = json.loads(app_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"Failed to read app metadata: {e}"}

    # Update code
    if code is not None:
        (app_dir / "main.py").write_text(code, encoding="utf-8")
        # Clear cached bytecode so changes take effect immediately
        pycache = app_dir / "__pycache__"
        if pycache.exists():
            shutil.rmtree(pycache, ignore_errors=True)

    # Update HTML template
    if html_template is not None:
        (app_dir / "templates").mkdir(exist_ok=True)
        (app_dir / "templates" / "index.html").write_text(
            html_template, encoding="utf-8"
        )

    # Update requirements and reinstall (in background to avoid blocking MCP)
    if requirements is not None:
        (app_dir / "requirements.txt").write_text(requirements, encoding="utf-8")
        meta["status"] = "setting_up"

    # Update metadata
    if description is not None:
        meta["description"] = description
    if config is not None:
        meta["config"] = config

    # Bump version
    parts = meta.get("version", "1.0.0").split(".")
    parts[-1] = str(int(parts[-1]) + 1)
    meta["version"] = ".".join(parts)
    meta["updated_at"] = datetime.now().isoformat()

    (app_dir / "app.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Start background venv rebuild AFTER writing metadata to avoid race
    if requirements is not None:
        ready_marker = app_dir / ".venv-ready"
        if ready_marker.exists():
            ready_marker.unlink()

        def _bg_reinstall():
            try:
                ok = _setup_venv(app_dir, requirements)
                _update_app_status(app_dir, "ready" if ok else "setup_failed")
            except Exception:
                _update_app_status(app_dir, "setup_failed")

        threading.Thread(target=_bg_reinstall, daemon=True).start()

    return {
        "success": True,
        "app_name": app_name,
        "version": meta["version"],
        "message": f"App '{app_name}' updated to v{meta['version']}",
    }


def delete_app(app_name: str) -> dict:
    """Delete an app and all its files."""
    app_dir = get_app_dir(app_name)

    if not app_dir.exists():
        return {"error": f"App '{app_name}' not found"}

    # Try to stop if running (import sandbox here to avoid circular import)
    try:
        from sandbox import stop_app as _stop_app, _running
        if app_name in _running:
            _stop_app(app_name)
    except ImportError:
        pass

    # Remove desktop shortcut
    _remove_shortcut(app_name)

    # Retry rmtree on Windows (locked files from just-stopped processes)
    for attempt in range(5):
        try:
            shutil.rmtree(app_dir)
            break
        except PermissionError:
            if attempt < 4:
                import time
                time.sleep(1)
            else:
                return {"error": f"Failed to delete app '{app_name}': files are locked. Try stopping the app first."}

    return {
        "success": True,
        "app_name": app_name,
        "message": f"App '{app_name}' deleted successfully",
    }


def _setup_venv(app_dir: Path, requirements: str) -> bool:
    """Create a virtual environment and install dependencies."""
    venv_dir = app_dir / "venv"
    ready_marker = app_dir / ".venv-ready"
    debug_log = app_dir / ".venv-setup.log"

    try:
        with open(debug_log, "a", encoding="utf-8") as log:
            log.write(f"[{datetime.now().isoformat()}] Starting _setup_venv\n")
            log.write(f"  sys.executable: {sys.executable}\n")
            log.write(f"  venv_dir: {venv_dir}\n")
            log.write(f"  requirements: {requirements!r}\n")
            log.flush()

            if not venv_dir.exists():
                result = subprocess.run(
                    [sys.executable, "-m", "venv", str(venv_dir)],
                    capture_output=True, timeout=120, check=False,
                    stdin=subprocess.DEVNULL,
                )
                log.write(f"  venv create: returncode={result.returncode}\n")
                if result.returncode != 0:
                    log.write(f"  venv stderr: {result.stderr.decode('utf-8', errors='replace')[:500]}\n")
                log.flush()

            if sys.platform == "win32":
                pip_path = str(venv_dir / "Scripts" / "pip")
            else:
                pip_path = str(venv_dir / "bin" / "pip")

            log.write(f"  pip_path: {pip_path}\n")
            log.write(f"  pip exists: {Path(pip_path).exists() or Path(pip_path + '.exe').exists()}\n")
            log.flush()

            if requirements and requirements.strip():
                result = subprocess.run(
                    [pip_path, "install", "-r", str(app_dir / "requirements.txt")],
                    capture_output=True, timeout=300, check=False,
                    stdin=subprocess.DEVNULL,
                )
                log.write(f"  pip install: returncode={result.returncode}\n")
                if result.returncode != 0:
                    log.write(f"  pip stderr: {result.stderr.decode('utf-8', errors='replace')[:500]}\n")
                log.flush()

            ready_marker.write_text("ok", encoding="utf-8")
            log.write(f"[{datetime.now().isoformat()}] _setup_venv completed OK\n")

        return True
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        try:
            with open(debug_log, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now().isoformat()}] _setup_venv FAILED: {type(e).__name__}: {e}\n")
        except Exception:
            pass
        return False


def _update_app_status(app_dir: Path, status: str):
    """Update the status field in app.json (thread-safe for single writer)."""
    app_json = app_dir / "app.json"
    try:
        meta = json.loads(app_json.read_text(encoding="utf-8"))
        meta["status"] = status
        meta["updated_at"] = datetime.now().isoformat()
        app_json.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except (json.JSONDecodeError, OSError):
        pass


def get_venv_python(app_dir: Path) -> Optional[str]:
    """Get the Python executable path inside the app's venv.

    Only returns a path when the venv is fully set up (dependencies installed).
    """
    ready_marker = app_dir / ".venv-ready"
    if not ready_marker.exists():
        return None

    venv_dir = app_dir / "venv"
    if sys.platform == "win32":
        python_path = venv_dir / "Scripts" / "python.exe"
    else:
        python_path = venv_dir / "bin" / "python"

    if python_path.exists():
        return str(python_path)
    return None


# ---------------------------------------------------------------------------
# Launcher & Desktop Shortcut
# ---------------------------------------------------------------------------

def _get_desktop_path() -> Path:
    """Get the user's desktop directory."""
    return Path.home() / "Desktop"


def _shortcut_filename(app_name: str, description: str) -> str:
    """Build a readable shortcut filename."""
    # Use first part of description (before ' - ') as display title
    title = description.split("-")[0].strip() if "-" in description else description
    title = title.strip() or _sanitize_name(app_name)
    if sys.platform == "win32":
        return f"KroWork - {title}.lnk"
    elif sys.platform == "darwin":
        return f"KroWork - {title}.command"
    else:
        return f"krowork-{_sanitize_name(title)}.desktop"


def _create_launcher(app_dir: Path, app_name: str, description: str) -> str:
    """Generate a launcher script inside the app directory.

    Returns the path to the launcher script.
    """
    title = description.split("-")[0].strip() if "-" in description else description
    title = title.strip() or app_name
    main_py = app_dir / "main.py"

    if sys.platform == "win32":
        python_exe = str((app_dir / "venv" / "Scripts" / "python.exe").resolve())
        launcher_path = app_dir / "launcher.bat"
        content = f"""@echo off
chcp 65001 >nul 2>&1
title {title}
echo ============================================
echo   {title}
echo   KroWork Local App
echo ============================================
echo.

set "APP_DIR={app_dir}"
set "PYTHON={python_exe}"
set "MAIN={main_py}"

:: Find free port
set "PORT=5000"
:check_port
netstat -ano 2>nul | findstr ":%PORT% " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    set /a PORT+=1
    if %PORT% gtr 9999 (
        echo [ERROR] No available port in range 5000-9999
        pause
        exit /b 1
    )
    goto check_port
)

set KROWORK_PORT=%PORT%
set KROWORK_APP_NAME={app_name}
echo Starting on port %PORT% ...
echo URL: http://127.0.0.1:%PORT%
echo.
echo Press Ctrl+C to stop the application.
echo.

:: Open browser after a short delay
ping -n 3 127.0.0.1 >nul 2>&1
start "" "http://127.0.0.1:%PORT%"

:: Run the Flask app
cd /d "%APP_DIR%"
"%PYTHON%" "%MAIN%"
pause
"""
    else:
        # macOS / Linux
        python_exe = str((app_dir / "venv" / "bin" / "python").resolve())
        if sys.platform == "darwin":
            launcher_path = app_dir / "launcher.command"
        else:
            launcher_path = app_dir / "launcher.sh"

        content = f"""#!/bin/bash
cd "{app_dir}"
export KROWORK_PORT=5000
export KROWORK_APP_NAME="{app_name}"
echo "============================================"
echo "  {title}"
echo "  KroWork Local App"
echo "============================================"
echo ""
echo "Starting..."
echo "URL: http://127.0.0.1:$KROWORK_PORT"
echo "Press Ctrl+C to stop."
echo ""
(sleep 2 && open "http://127.0.0.1:$KROWORK_PORT" 2>/dev/null || xdg-open "http://127.0.0.1:$KROWORK_PORT" 2>/dev/null) &
"{python_exe}" "{main_py}"
"""

    launcher_path.write_text(content, encoding="utf-8")

    # Make executable on Unix
    if sys.platform != "win32":
        os.chmod(launcher_path, 0o755)

    return str(launcher_path)


def _create_shortcut(app_dir: Path, app_name: str, description: str) -> Optional[str]:
    """Create a desktop shortcut that launches the app via its launcher script.

    Returns the shortcut path on success, None on failure.
    """
    desktop = _get_desktop_path()
    if not desktop.exists():
        return None

    launcher = app_dir / ("launcher.bat" if sys.platform == "win32" else
                           "launcher.command" if sys.platform == "darwin" else
                           "launcher.sh")
    if not launcher.exists():
        return None

    lnk_name = _shortcut_filename(app_name, description)
    lnk_path = desktop / lnk_name

    title = description.split("-")[0].strip() if "-" in description else description
    title = title.strip() or app_name

    # Generate personalized icon for this app
    icon_path = None
    try:
        icon_path = generate_icon_for_app(app_dir, app_name)
    except Exception:
        pass  # Non-critical: shortcut works without custom icon

    if sys.platform == "win32":
        # Use PowerShell to create .lnk via WScript.Shell COM (zero dependencies)
        icon_line = f"$s.IconLocation = '{icon_path}'" if icon_path else ""
        ps_script = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{str(lnk_path)}')
$s.TargetPath = '{str(launcher)}'
$s.WorkingDirectory = '{str(app_dir)}'
$s.Description = '{description}'
{icon_line}
$s.WindowStyle = 7
$s.Save()
'''
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, timeout=10, text=True,
                stdin=subprocess.DEVNULL,
            )
            if result.returncode == 0 and lnk_path.exists():
                return str(lnk_path)
        except Exception:
            pass

        # Fallback: copy .bat to desktop with a friendlier name
        try:
            fallback_name = f"KroWork - {title}.bat"
            fallback_path = desktop / fallback_name
            shutil.copy2(str(launcher), str(fallback_path))
            return str(fallback_path)
        except Exception:
            return None

    elif sys.platform == "darwin":
        # macOS: copy .command to desktop
        try:
            shutil.copy2(str(launcher), str(lnk_path))
            os.chmod(lnk_path, 0o755)
            return str(lnk_path)
        except Exception:
            return None

    else:
        # Linux: create .desktop file
        icon_line = f"Icon={icon_path}" if icon_path else ""
        desktop_content = f"""[Desktop Entry]
Type=Application
Name=KroWork - {title}
Comment={description}
Exec="{str(launcher)}"
Terminal=true
Categories=Utility;
{icon_line}
"""
        try:
            lnk_path.write_text(desktop_content, encoding="utf-8")
            os.chmod(lnk_path, 0o755)
            return str(lnk_path)
        except Exception:
            return None


def _remove_shortcut(app_name: str):
    """Remove desktop shortcut(s) for the given app."""
    desktop = _get_desktop_path()
    if not desktop.exists():
        return

    app_id = _sanitize_name(app_name)
    for entry in list(desktop.iterdir()):
        name_lower = entry.name.lower()
        if name_lower.startswith("krowork") and app_id in name_lower:
            try:
                entry.unlink()
            except OSError:
                pass


def create_shortcut_for_app(app_name: str) -> dict:
    """(Re-)create the desktop shortcut for an existing app.

    Can also be used to create shortcuts for apps that were created before
    the shortcut feature existed.
    """
    app_dir = get_app_dir(app_name)
    app_json = app_dir / "app.json"

    if not app_json.exists():
        return {"error": f"App '{app_name}' not found"}

    try:
        meta = json.loads(app_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"error": f"Failed to read app metadata: {e}"}

    description = meta.get("description", meta.get("name", app_name))

    # Ensure launcher exists
    _create_launcher(app_dir, app_name, description)

    # Remove old shortcut first
    _remove_shortcut(app_name)

    # Create new shortcut
    shortcut_path = _create_shortcut(app_dir, app_name, description)

    if shortcut_path:
        return {
            "success": True,
            "app_name": app_name,
            "shortcut": shortcut_path,
            "message": f"Desktop shortcut created: {shortcut_path}",
        }
    else:
        return {
            "success": True,
            "app_name": app_name,
            "shortcut": None,
            "message": f"Launcher created at {app_dir / 'launcher.bat'}, but desktop shortcut creation failed. You can run the launcher directly.",
        }
