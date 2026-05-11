"""Open-KroWork Sandbox - Run apps in isolated subprocesses."""

import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Optional

from app_manager import get_app_dir, get_venv_python, app_exists, get_app


# Track running processes: app_name -> subprocess.Popen
_running: dict = {}


def _find_free_port(start: int = 5000, end: int = 9999) -> int:
    """Find an available port in the given range."""
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available port in range {start}-{end}")


def _wait_for_port(port: int, timeout: float = 15.0) -> bool:
    """Wait until a port is accepting connections."""
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


def start_app(app_name: str, port: Optional[int] = None) -> dict:
    """Start a KroWork app in a subprocess.

    Returns a dict with the URL and process info.
    """
    if not app_exists(app_name):
        return {"error": f"App '{app_name}' not found"}

    # Stop if already running
    if app_name in _running:
        stop_app(app_name)

    app_dir = get_app_dir(app_name)

    # Check if venv is ready (background setup might still be running)
    venv_python = get_venv_python(app_dir)
    if not venv_python:
        # Check app status to give a helpful error message
        app_info = get_app(app_name)
        status = app_info.get("status", "unknown")
        if status == "setting_up":
            return {
                "error": (
                    f"App '{app_name}' is still installing dependencies. "
                    f"Please wait a moment and try again."
                )
            }
        # venv missing but not setting up — try to create it synchronously
        # (edge case: app was created before background-setup fix)
        from app_manager import _setup_venv
        req_path = app_dir / "requirements.txt"
        req = req_path.read_text(encoding="utf-8") if req_path.exists() else "flask"
        _setup_venv(app_dir, req)
        venv_python = get_venv_python(app_dir)

    python = venv_python or sys.executable

    # Find a free port
    if port is None:
        port = _find_free_port()

    # Set environment for the child process
    env = os.environ.copy()
    env["KROWORK_APP_NAME"] = app_name
    env["KROWORK_APP_DIR"] = str(app_dir)
    env["KROWORK_PORT"] = str(port)
    env["FLASK_APP"] = "main.py"

    # Suppress Flask's Python warning about development server
    env["FLASK_ENV"] = "production"

    main_py = app_dir / "main.py"

    # Log file for capturing app output
    log_path = app_dir / "app.log"

    try:
        log_file = open(log_path, "w", encoding="utf-8")

        process = subprocess.Popen(
            [python, str(main_py)],
            cwd=str(app_dir),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
        )

        _running[app_name] = {
            "process": process,
            "port": port,
            "app_dir": str(app_dir),
            "log_file": log_file,
        }

        url = f"http://127.0.0.1:{port}"

        # Wait for the server to be ready
        ready = _wait_for_port(port, timeout=15)

        if not ready:
            # Check if process is still alive
            if process.poll() is not None:
                log_file.close()
                # Read log for error info
                error_output = log_path.read_text(encoding="utf-8")[-2000:]
                _running.pop(app_name, None)
                return {
                    "error": (
                        f"App '{app_name}' failed to start. "
                        f"Exit code: {process.poll()}. Output:\n{error_output}"
                    )
                }
            # Process alive but port not ready — still return success
            # (some apps may take longer to bind)

        # Try to open browser
        try:
            webbrowser.open(url)
        except Exception:
            pass

        status = "ready" if ready else "starting"

        return {
            "success": True,
            "app_name": app_name,
            "url": url,
            "port": port,
            "pid": process.pid,
            "status": status,
            "log_file": str(log_path),
            "message": f"App '{app_name}' started at {url}",
        }

    except Exception as e:
        return {"error": f"Failed to start app '{app_name}': {e}"}


def stop_app(app_name: str) -> dict:
    """Stop a running KroWork app."""
    if app_name not in _running:
        return {"error": f"App '{app_name}' is not running"}

    info = _running.pop(app_name)
    process = info["process"]
    log_file = info.get("log_file")

    try:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    except Exception:
        pass
    finally:
        if log_file:
            try:
                log_file.close()
            except Exception:
                pass

    return {
        "success": True,
        "app_name": app_name,
        "message": f"App '{app_name}' stopped",
    }


def get_app_status(app_name: str) -> dict:
    """Get the running status of an app."""
    if app_name not in _running:
        return {"app_name": app_name, "status": "stopped"}

    info = _running[app_name]
    process = info["process"]
    port = info["port"]

    # Check if process is still alive
    poll = process.poll()
    if poll is None:
        return {
            "app_name": app_name,
            "status": "running",
            "port": port,
            "url": f"http://127.0.0.1:{port}",
            "pid": process.pid,
        }
    else:
        # Process has exited, clean up
        log_file = info.get("log_file")
        if log_file:
            try:
                log_file.close()
            except Exception:
                pass
        _running.pop(app_name, None)
        return {
            "app_name": app_name,
            "status": "exited",
            "exit_code": poll,
        }


def get_app_log(app_name: str, tail: int = 50) -> dict:
    """Get the recent log output of a running app."""
    if app_name not in _running:
        return {"error": f"App '{app_name}' is not running"}

    info = _running[app_name]
    log_path = Path(info["app_dir"]) / "app.log"

    if not log_path.exists():
        return {"app_name": app_name, "log": ""}

    try:
        content = log_path.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        return {
            "app_name": app_name,
            "log": "\n".join(lines[-tail:]),
        }
    except Exception as e:
        return {"error": f"Failed to read log: {e}"}


def list_running_apps() -> dict:
    """List all currently running apps."""
    running = []
    stopped = []
    for name in list(_running.keys()):
        status = get_app_status(name)
        if status["status"] == "running":
            running.append(status)
        else:
            stopped.append(status)

    # Clean up stopped entries
    for s in stopped:
        _running.pop(s["app_name"], None)

    return {"running": running, "total": len(running)}
