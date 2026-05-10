"""Open-KroWork Task Scheduler - Schedule apps to run automatically.

Supports OS-level scheduled tasks:
  - Windows: Task Scheduler via schtasks
  - macOS: launchd via plist files
  - Linux: cron via crontab

Tasks are registered in ~/.krowork/schedules/ for management.
"""

import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from app_manager import get_app_dir, app_exists, _sanitize_name, get_venv_python


# ---------------------------------------------------------------------------
# Schedule Registry
# ---------------------------------------------------------------------------

_SCHEDULES_DIR = Path.home() / ".krowork" / "schedules"


def _ensure_schedules_dir():
    _SCHEDULES_DIR.mkdir(parents=True, exist_ok=True)


def _schedule_path(name: str) -> Path:
    safe = _sanitize_name(name)
    return _SCHEDULES_DIR / f"{safe}.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_schedule(app_name: str, schedule_type: str = "daily",
                    time_str: str = "08:00", days: list = None,
                    command: str = None) -> dict:
    """Create a scheduled task for a KroWork app.

    Args:
        app_name: Name of the app to schedule
        schedule_type: "daily", "weekly", "interval", "once"
        time_str: Time in HH:MM format (for daily/weekly/once)
        days: List of weekday names for weekly (e.g. ["monday", "friday"])
        command: Optional shell command override. Defaults to running the app.
                 For "interval" type, this is the interval in minutes.

    Returns:
        dict with schedule info on success
    """
    if not app_exists(app_name):
        return {"error": f"App '{app_name}' not found"}

    app_dir = get_app_dir(app_name)
    python_exe = get_venv_python(app_dir)
    if not python_exe:
        return {"error": f"App '{app_name}' venv not found. Run the app first."}

    main_py = app_dir / "main.py"
    if not main_py.exists():
        return {"error": f"App '{app_name}' main.py not found"}

    # Build schedule config
    schedule_id = _sanitize_name(f"schedule-{app_name}")
    config = {
        "schedule_id": schedule_id,
        "app_name": app_name,
        "app_dir": str(app_dir),
        "schedule_type": schedule_type,
        "time": time_str,
        "days": days or [],
        "command": command,
        "created_at": datetime.now().isoformat(),
        "status": "active",
    }

    # Create OS-level scheduled task
    if platform.system() == "Windows":
        result = _create_windows_task(config, python_exe, str(main_py), app_dir)
    elif platform.system() == "Darwin":
        result = _create_macos_task(config, python_exe, str(main_py), app_dir)
    else:
        result = _create_linux_task(config, python_exe, str(main_py), app_dir)

    if "error" in result:
        return result

    # Save schedule registry
    _ensure_schedules_dir()
    _schedule_path(app_name).write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "success": True,
        "schedule_id": schedule_id,
        "app_name": app_name,
        "schedule_type": schedule_type,
        "time": time_str,
        "message": f"Scheduled '{app_name}' ({schedule_type} at {time_str})",
    }


def delete_schedule(app_name: str) -> dict:
    """Remove a scheduled task for an app."""
    spath = _schedule_path(app_name)
    if not spath.exists():
        return {"error": f"No schedule found for '{app_name}'"}

    config = json.loads(spath.read_text(encoding="utf-8"))

    # Remove OS-level task
    if platform.system() == "Windows":
        _delete_windows_task(config.get("schedule_id", ""))
    elif platform.system() == "Darwin":
        _delete_macos_task(config.get("schedule_id", ""))
    else:
        _delete_linux_task(config.get("schedule_id", ""))

    spath.unlink()
    return {"success": True, "app_name": app_name, "message": f"Schedule for '{app_name}' removed"}


def list_schedules() -> dict:
    """List all scheduled tasks."""
    _ensure_schedules_dir()
    schedules = []
    for f in sorted(_SCHEDULES_DIR.glob("*.json")):
        try:
            schedules.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return {"schedules": schedules, "total": len(schedules)}


def get_schedule(app_name: str) -> dict:
    """Get schedule info for a specific app."""
    spath = _schedule_path(app_name)
    if not spath.exists():
        return {"error": f"No schedule found for '{app_name}'"}
    return json.loads(spath.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Windows Task Scheduler
# ---------------------------------------------------------------------------

def _create_windows_task(config: dict, python_exe: str, main_py: str,
                         app_dir: Path) -> dict:
    """Create a Windows scheduled task using schtasks."""
    task_name = f"KroWork_{config['schedule_id']}"
    schedule_type = config["schedule_type"]
    time_str = config.get("time", "08:00")

    # Build the command to run
    run_cmd = f'"{python_exe}" "{main_py}"'

    # Determine schedule flags
    if schedule_type == "daily":
        schedule_flag = f'/SC DAILY /ST {time_str}'
    elif schedule_type == "weekly":
        days_str = ",".join(config.get("days", ["MON"]))
        schedule_flag = f'/SC WEEKLY /D {days_str} /ST {time_str}'
    elif schedule_type == "interval":
        interval = config.get("command", "30")
        schedule_flag = f'/SC MINUTE /MO {interval}'
    elif schedule_type == "once":
        schedule_flag = f'/SC ONCE /ST {time_str}'
    else:
        return {"error": f"Unsupported schedule type: {schedule_type}"}

    cmd = (
        f'schtasks /Create /TN "{task_name}" /TR "{run_cmd}" '
        f'{schedule_flag} /F'
    )

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=15, shell=True
        )
        if result.returncode != 0:
            return {"error": f"schtasks failed: {result.stderr.strip()}"}
        return {"os_task": task_name}
    except Exception as e:
        return {"error": f"Failed to create Windows task: {e}"}


def _delete_windows_task(task_name: str):
    """Remove a Windows scheduled task."""
    if not task_name:
        return
    full_name = f"KroWork_{task_name}"
    subprocess.run(
        f'schtasks /Delete /TN "{full_name}" /F',
        capture_output=True, timeout=10, shell=True
    )


# ---------------------------------------------------------------------------
# macOS launchd
# ---------------------------------------------------------------------------

def _create_macos_task(config: dict, python_exe: str, main_py: str,
                        app_dir: Path) -> dict:
    """Create a macOS launchd plist."""
    task_id = config["schedule_id"]
    plist_name = f"com.krowork.{task_id}.plist"
    plist_path = Path.home() / "Library" / "LaunchAgents" / plist_name

    # Build plist
    label = f"com.krowork.{task_id}"
    program_args = [python_exe, main_py]
    working_dir = str(app_dir)

    # Determine start interval or calendar
    schedule_type = config["schedule_type"]
    if schedule_type == "interval":
        interval_mins = int(config.get("command", "30"))
        start_interval = interval_mins * 60
        calendar_dict = None
    else:
        start_interval = None
        hour, minute = config.get("time", "08:00").split(":")
        weekday_map = {"monday": 1, "tuesday": 2, "wednesday": 3,
                       "thursday": 4, "friday": 5, "saturday": 6, "sunday": 7}
        days = config.get("days", [])
        weekday = weekday_map.get(days[0].lower(), 1) if days else None

        calendar_dict = {"Hour": int(hour), "Minute": int(minute)}
        if schedule_type == "weekly" and weekday:
            calendar_dict["Weekday"] = weekday

    # Write plist
    plist_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">',
        '<plist version="1.0"><dict>',
        f'<key>Label</key><string>{label}</string>',
        '<key>ProgramArguments</key><array>',
    ]
    for arg in program_args:
        plist_parts.append(f'<string>{arg}</string>')
    plist_parts.append('</array>')
    plist_parts.append(f'<key>WorkingDirectory</key><string>{working_dir}</string>')

    if start_interval:
        plist_parts.append(
            f'<key>StartInterval</key><integer>{start_interval}</integer>'
        )
    if calendar_dict:
        plist_parts.append('<key>StartCalendarInterval</key><dict>')
        for k, v in calendar_dict.items():
            plist_parts.append(f'<key>{k}</key><integer>{v}</integer>')
        plist_parts.append('</dict>')

    plist_parts.append('</dict></plist>')

    try:
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text("\n".join(plist_parts), encoding="utf-8")
        subprocess.run(["launchctl", "load", str(plist_path)],
                       capture_output=True, timeout=10)
        return {"os_task": plist_name}
    except Exception as e:
        return {"error": f"Failed to create macOS task: {e}"}


def _delete_macos_task(task_name: str):
    """Remove a macOS launchd task."""
    if not task_name:
        return
    plist_name = f"com.krowork.{task_name}.plist"
    plist_path = Path.home() / "Library" / "LaunchAgents" / plist_name
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)],
                       capture_output=True, timeout=10)
        plist_path.unlink()


# ---------------------------------------------------------------------------
# Linux cron
# ---------------------------------------------------------------------------

def _create_linux_task(config: dict, python_exe: str, main_py: str,
                        app_dir: Path) -> dict:
    """Create a Linux cron job."""
    schedule_type = config["schedule_type"]
    time_str = config.get("time", "08:00")
    hour, minute = time_str.split(":")

    if schedule_type == "interval":
        interval = config.get("command", "30")
        cron_expr = f"*/{interval} * * * *"
    elif schedule_type == "daily":
        cron_expr = f"{minute} {hour} * * *"
    elif schedule_type == "weekly":
        day_map = {"monday": "1", "tuesday": "2", "wednesday": "3",
                   "thursday": "4", "friday": "5", "saturday": "6", "sunday": "0"}
        days = config.get("days", ["monday"])
        dow = ",".join(day_map.get(d.lower(), "1") for d in days)
        cron_expr = f"{minute} {hour} * * {dow}"
    elif schedule_type == "once":
        # Cron doesn't support one-shot, use at instead or just schedule daily
        cron_expr = f"{minute} {hour} * * *"
    else:
        return {"error": f"Unsupported schedule type: {schedule_type}"}

    task_marker = f"KROWORK_{config['schedule_id'].upper()}"
    cron_line = f'{cron_expr} cd {app_dir} && {python_exe} {main_py}  # {task_marker}'

    try:
        # Read existing crontab
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        existing = result.stdout if result.returncode == 0 else ""

        # Remove old entry for this task
        lines = [l for l in existing.splitlines()
                 if task_marker not in l and l.strip()]

        # Add new entry
        lines.append(cron_line)
        new_cron = "\n".join(lines) + "\n"

        # Write back
        proc = subprocess.run(["crontab", "-"], input=new_cron,
                              capture_output=True, text=True, timeout=10)
        if proc.returncode != 0:
            return {"error": f"crontab update failed: {proc.stderr}"}

        return {"os_task": task_marker}
    except FileNotFoundError:
        return {"error": "crontab not available on this system"}
    except Exception as e:
        return {"error": f"Failed to create cron job: {e}"}


def _delete_linux_task(task_name: str):
    """Remove a Linux cron job."""
    if not task_name:
        return
    task_marker = f"KROWORK_{task_name.upper()}"
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        if result.returncode != 0:
            return
        lines = [l for l in result.stdout.splitlines()
                 if task_marker not in l]
        new_cron = "\n".join(lines) + "\n" if lines else ""
        subprocess.run(["crontab", "-"], input=new_cron,
                       capture_output=True, text=True, timeout=10)
    except Exception:
        pass
