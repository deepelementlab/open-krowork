"""Open-KroWork App Export/Import - Package apps for sharing.

Supports exporting an app as a .krowork zip archive and importing
apps from such archives, enabling team sharing without environment setup.
"""

import json
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from app_manager import get_app_dir, get_apps_dir, app_exists, _sanitize_name


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_app(app_name: str, output_path: str = None) -> dict:
    """Export a KroWork app as a .krowork zip archive.

    The archive contains:
      - manifest.json  (metadata for sharing)
      - app.json       (app metadata)
      - main.py        (backend code)
      - requirements.txt
      - templates/index.html
      - (optional) static/ assets

    The venv/ and data/ directories are excluded (recipients rebuild venv).

    Args:
        app_name: Name of the app to export
        output_path: Optional output file path. Defaults to Desktop.

    Returns:
        dict with export_path on success, or error
    """
    app_dir = get_app_dir(app_name)
    if not app_dir.exists() or not (app_dir / "app.json").exists():
        return {"error": f"App '{app_name}' not found"}

    # Load metadata
    meta = json.loads((app_dir / "app.json").read_text(encoding="utf-8"))

    # Determine output path
    if output_path:
        out = Path(output_path)
    else:
        desktop = Path.home() / "Desktop"
        out_dir = desktop if desktop.exists() else Path.cwd()
        safe_name = _sanitize_name(app_name)
        out = out_dir / f"{safe_name}.krowork"

    # Build manifest
    manifest = {
        "format": "krowork-app-package",
        "version": "1.0",
        "exported_at": datetime.now().isoformat(),
        "app_name": meta.get("name", app_name),
        "app_id": meta.get("id", _sanitize_name(app_name)),
        "description": meta.get("description", ""),
        "app_version": meta.get("version", "1.0.0"),
    }

    try:
        with zipfile.ZipFile(str(out), "w", zipfile.ZIP_DEFLATED) as zf:
            # Write manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))

            # Write app metadata
            zf.write(str(app_dir / "app.json"), "app.json")

            # Write main code
            main_py = app_dir / "main.py"
            if main_py.exists():
                zf.write(str(main_py), "main.py")

            # Write requirements
            req = app_dir / "requirements.txt"
            if req.exists():
                zf.write(str(req), "requirements.txt")

            # Write HTML template
            html = app_dir / "templates" / "index.html"
            if html.exists():
                zf.write(str(html), "templates/index.html")

            # Write static assets if any
            static_dir = app_dir / "static"
            if static_dir.exists():
                for f in static_dir.rglob("*"):
                    if f.is_file():
                        arcname = f"static/{f.relative_to(static_dir)}"
                        zf.write(str(f), arcname)

            # Write config if present
            config_file = app_dir / "config.json"
            if config_file.exists():
                zf.write(str(config_file), "config.json")

        return {
            "success": True,
            "app_name": app_name,
            "export_path": str(out),
            "file_size": out.stat().st_size,
            "message": f"App '{app_name}' exported to {out}",
        }

    except Exception as e:
        return {"error": f"Export failed: {e}"}


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_app(krowork_path: str, new_name: str = None) -> dict:
    """Import a KroWork app from a .krowork archive.

    Creates a new app from the archive, installs dependencies,
    and creates a desktop shortcut.

    Args:
        krowork_path: Path to the .krowork zip file
        new_name: Optional rename for the imported app

    Returns:
        dict with app info on success, or error
    """
    archive = Path(krowork_path)
    if not archive.exists():
        return {"error": f"Archive not found: {krowork_path}"}

    try:
        with zipfile.ZipFile(str(archive), "r") as zf:
            names = zf.namelist()

            # Validate manifest
            if "manifest.json" not in names:
                return {"error": "Invalid .krowork archive: missing manifest.json"}

            manifest = json.loads(zf.read("manifest.json"))
            if manifest.get("format") != "krowork-app-package":
                return {"error": "Invalid .krowork archive: bad manifest format"}

            # Determine app name
            app_name = new_name or manifest.get("app_name", archive.stem)

            # Check if already exists
            app_dir = get_app_dir(app_name)
            if app_dir.exists():
                return {"error": f"App '{app_name}' already exists. Use a different name."}

            # Create directory structure
            app_dir.mkdir(parents=True, exist_ok=True)
            (app_dir / "templates").mkdir(exist_ok=True)
            (app_dir / "data").mkdir(exist_ok=True)

            # Extract files
            for name in names:
                # Skip directories
                if name.endswith("/"):
                    continue
                # Security: prevent path traversal
                if ".." in name or name.startswith("/"):
                    continue

                target = app_dir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))

            # Install dependencies
            req_file = app_dir / "requirements.txt"
            if req_file.exists():
                from app_manager import _setup_venv
                _setup_venv(app_dir, req_file.read_text(encoding="utf-8"))
            else:
                from app_manager import _setup_venv
                (req_file).write_text("flask", encoding="utf-8")
                _setup_venv(app_dir, "flask")

            # Update app.json metadata
            app_json_path = app_dir / "app.json"
            if app_json_path.exists():
                meta = json.loads(app_json_path.read_text(encoding="utf-8"))
                meta["id"] = _sanitize_name(app_name)
                meta["name"] = app_name
                meta["status"] = "imported"
                meta["updated_at"] = datetime.now().isoformat()
                meta["imported_from"] = str(archive)
                app_json_path.write_text(
                    json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
                )

            # Create launcher and shortcut
            from app_manager import _create_launcher, _create_shortcut
            description = manifest.get("description", app_name)
            _create_launcher(app_dir, app_name, description)
            shortcut_path = _create_shortcut(app_dir, app_name, description)

            return {
                "success": True,
                "app_name": app_name,
                "app_id": _sanitize_name(app_name),
                "app_dir": str(app_dir),
                "imported_from": str(archive),
                "original_name": manifest.get("app_name", ""),
                "original_version": manifest.get("app_version", ""),
                "shortcut": shortcut_path,
                "message": f"App '{app_name}' imported successfully",
            }

    except zipfile.BadZipFile:
        return {"error": "Invalid archive: not a valid zip file"}
    except Exception as e:
        # Clean up on failure
        app_dir = get_app_dir(new_name or krowork_path)
        if app_dir.exists():
            shutil.rmtree(app_dir, ignore_errors=True)
        return {"error": f"Import failed: {e}"}


def list_exported(path: str = None) -> dict:
    """List .krowork files in a directory (default: Desktop)."""
    search_dir = Path(path) if path else (Path.home() / "Desktop")
    if not search_dir.exists():
        return {"archives": [], "total": 0}

    archives = []
    for f in search_dir.glob("*.krowork"):
        try:
            with zipfile.ZipFile(str(f), "r") as zf:
                if "manifest.json" in zf.namelist():
                    manifest = json.loads(zf.read("manifest.json"))
                    archives.append({
                        "path": str(f),
                        "name": manifest.get("app_name", f.stem),
                        "version": manifest.get("app_version", ""),
                        "description": manifest.get("description", ""),
                        "file_size": f.stat().st_size,
                    })
        except (zipfile.BadZipFile, json.JSONDecodeError):
            pass

    return {"archives": archives, "total": len(archives)}
