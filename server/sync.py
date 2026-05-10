"""Open-KroWork Cross-Device Sync - Sync apps via user-owned cloud folders.

Design principle: Data stays in the user's control. We sync .krowork packages
to a user-specified folder (e.g., OneDrive/KroWork, Dropbox/Apps/KroWork,
or a WebDAV mount point). No KroWork cloud service needed.

Sync workflow:
  1. User configures sync target: a folder path (could be cloud-synced)
  2. push: Export local apps as .krowork files to the target folder
  3. pull: Import new/updated .krowork files from the target folder
  4. status: Show what's changed since last sync
  5. Incremental: Only transfer apps that changed (based on version + hash)
"""

import hashlib
import json
import os
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from app_manager import get_apps_dir, get_app_dir, app_exists, _sanitize_name


# ---------------------------------------------------------------------------
# Sync Configuration
# ---------------------------------------------------------------------------

SYNC_CONFIG_DIR = Path.home() / ".krowork" / "sync"
SYNC_CONFIG_FILE = SYNC_CONFIG_DIR / "config.json"


def _ensure_config_dir():
    SYNC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def configure_sync(target_dir: str, device_name: str = "") -> dict:
    """Configure the sync target directory.

    Args:
        target_dir: Path to sync folder (e.g., OneDrive/KroWork, Dropbox/Apps/KroWork)
        device_name: Optional name for this device (for conflict resolution)

    Returns:
        dict with config info
    """
    target = Path(target_dir)
    if not target.exists():
        try:
            target.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return {"error": f"Cannot create sync directory: {e}"}

    # Verify writable
    test_file = target / ".krowork_sync_test"
    try:
        test_file.write_text("sync-test", encoding="utf-8")
        test_file.unlink()
    except OSError as e:
        return {"error": f"Sync directory is not writable: {e}"}

    _ensure_config_dir()

    # Auto-detect device name
    if not device_name:
        import platform
        device_name = platform.node() or "unknown"

    config = {
        "target_dir": str(target.resolve()),
        "device_name": device_name,
        "configured_at": datetime.now().isoformat(),
        "last_sync_at": None,
        "last_push_at": None,
        "last_pull_at": None,
    }

    SYNC_CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Create sync metadata directory in target
    meta_dir = target / ".krowork_meta"
    meta_dir.mkdir(exist_ok=True)

    return {
        "success": True,
        "target_dir": str(target.resolve()),
        "device_name": device_name,
        "message": f"Sync configured: {target}",
    }


def get_sync_config() -> dict:
    """Get current sync configuration."""
    if not SYNC_CONFIG_FILE.exists():
        return {"configured": False}
    return {
        "configured": True,
        **json.loads(SYNC_CONFIG_FILE.read_text(encoding="utf-8")),
    }


def disable_sync() -> dict:
    """Disable sync (keep config file for reference)."""
    if SYNC_CONFIG_FILE.exists():
        config = json.loads(SYNC_CONFIG_FILE.read_text(encoding="utf-8"))
        config["enabled"] = False
        config["disabled_at"] = datetime.now().isoformat()
        SYNC_CONFIG_FILE.write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return {"success": True, "message": "Sync disabled"}


# ---------------------------------------------------------------------------
# Sync Operations
# ---------------------------------------------------------------------------

def sync_push(force: bool = False) -> dict:
    """Push all local apps to the sync target.

    Exports each app as a .krowork package. Only exports apps that have
    changed since the last push (unless force=True).

    Args:
        force: Push all apps regardless of changes

    Returns:
        dict with push results
    """
    config = get_sync_config()
    if not config.get("configured"):
        return {"error": "Sync not configured. Use configure_sync() first."}

    target = Path(config["target_dir"])
    if not target.exists():
        return {"error": f"Sync target not found: {target}"}

    from app_manager import list_apps
    apps_result = list_apps()
    apps = apps_result.get("apps", [])

    if not apps:
        return {"pushed": 0, "message": "No apps to push"}

    # Load sync metadata
    meta = _load_sync_meta(target)
    pushed = []
    skipped = []

    for app_info in apps:
        app_name = app_info["name"]
        app_version = app_info.get("version", "1.0.0")

        # Check if app changed since last push
        safe_name = _sanitize_name(app_name)
        remote_key = f"{safe_name}.krowork"
        last_meta = meta.get("pushed", {}).get(safe_name, {})

        if not force and last_meta.get("version") == app_version:
            # Also check content hash
            current_hash = _app_content_hash(app_name)
            if current_hash == last_meta.get("hash"):
                skipped.append(app_name)
                continue

        # Export the app
        from app_export import export_app
        export_result = export_app(app_name, str(target / remote_key))

        if export_result.get("success"):
            current_hash = _app_content_hash(app_name)
            meta.setdefault("pushed", {})[safe_name] = {
                "version": app_version,
                "hash": current_hash,
                "pushed_at": datetime.now().isoformat(),
                "device": config.get("device_name", ""),
            }
            pushed.append({
                "name": app_name,
                "version": app_version,
                "file": remote_key,
            })
        else:
            skipped.append(f"{app_name} (error: {export_result.get('error', 'unknown')})")

    # Save metadata
    _save_sync_meta(target, meta)

    # Update config timestamps
    config["last_push_at"] = datetime.now().isoformat()
    config["last_sync_at"] = datetime.now().isoformat()
    SYNC_CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "success": True,
        "pushed": pushed,
        "pushed_count": len(pushed),
        "skipped_count": len(skipped),
        "skipped": skipped,
        "target_dir": str(target),
        "synced_at": config["last_sync_at"],
    }


def sync_pull(overwrite: bool = False) -> dict:
    """Pull new/updated apps from the sync target.

    Imports .krowork packages that are new or have a newer version
    than the local copy.

    Args:
        overwrite: Overwrite existing apps even if versions match

    Returns:
        dict with pull results
    """
    config = get_sync_config()
    if not config.get("configured"):
        return {"error": "Sync not configured. Use configure_sync() first."}

    target = Path(config["target_dir"])
    if not target.exists():
        return {"error": f"Sync target not found: {target}"}

    # Find all .krowork files in target
    archives = list(target.glob("*.krowork"))
    if not archives:
        return {"pulled": 0, "message": "No .krowork files found in sync target"}

    meta = _load_sync_meta(target)
    pulled = []
    skipped = []
    conflicts = []

    for archive_path in archives:
        try:
            manifest = _read_manifest(archive_path)
            if not manifest:
                skipped.append(f"{archive_path.name} (invalid archive)")
                continue

            app_name = manifest.get("app_name", archive_path.stem)
            remote_version = manifest.get("app_version", "0.0.0")
            safe_name = manifest.get("app_id", _sanitize_name(app_name))

            # Check if already locally installed
            if app_exists(app_name):
                from app_manager import get_app
                local_info = get_app(app_name)
                local_version = local_info.get("version", "0.0.0")

                # Compare versions
                if not overwrite and _version_gte(local_version, remote_version):
                    skipped.append(f"{app_name} (local v{local_version} >= remote v{remote_version})")
                    continue

                # Potential conflict: local has changes too
                last_pull = meta.get("pulled", {}).get(safe_name, {})
                if not overwrite and last_pull.get("version") != local_version:
                    # Local was modified since last pull
                    conflicts.append({
                        "app_name": app_name,
                        "local_version": local_version,
                        "remote_version": remote_version,
                        "message": "Local app was modified. Use overwrite=True to force.",
                    })
                    continue

            # Import the app
            from app_export import import_app
            import_result = import_app(str(archive_path))

            if import_result.get("success"):
                meta.setdefault("pulled", {})[safe_name] = {
                    "version": remote_version,
                    "pulled_at": datetime.now().isoformat(),
                    "device": config.get("device_name", ""),
                }
                pulled.append({
                    "name": app_name,
                    "version": remote_version,
                    "source": archive_path.name,
                })
            else:
                skipped.append(f"{app_name} ({import_result.get('error', 'import failed')})")

        except Exception as e:
            skipped.append(f"{archive_path.name} ({e})")

    _save_sync_meta(target, meta)

    config["last_pull_at"] = datetime.now().isoformat()
    config["last_sync_at"] = datetime.now().isoformat()
    SYNC_CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    return {
        "success": True,
        "pulled": pulled,
        "pulled_count": len(pulled),
        "skipped": skipped,
        "skipped_count": len(skipped),
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "target_dir": str(target),
        "synced_at": config["last_sync_at"],
    }


def sync_status() -> dict:
    """Check sync status: what needs to be pushed/pulled.

    Returns:
        dict with local_apps, remote_apps, to_push, to_pull, conflicts
    """
    config = get_sync_config()
    if not config.get("configured"):
        return {"error": "Sync not configured"}

    target = Path(config["target_dir"])
    if not target.exists():
        return {"error": f"Sync target not found: {target}"}

    # Get local apps
    from app_manager import list_apps
    local_apps = {}
    for app in list_apps().get("apps", []):
        local_apps[app["name"]] = {
            "version": app.get("version", "0.0.0"),
            "updated_at": app.get("updated_at", ""),
        }

    # Get remote apps
    remote_apps = {}
    for archive_path in target.glob("*.krowork"):
        manifest = _read_manifest(archive_path)
        if manifest:
            name = manifest.get("app_name", archive_path.stem)
            remote_apps[name] = {
                "version": manifest.get("app_version", "0.0.0"),
                "file": archive_path.name,
                "exported_at": manifest.get("exported_at", ""),
            }

    # Compute diffs
    to_push = []
    to_pull = []
    conflicts = []

    # Apps only local → push
    for name, info in local_apps.items():
        if name not in remote_apps:
            to_push.append({"name": name, "version": info["version"], "reason": "new local app"})
        else:
            local_v = info["version"]
            remote_v = remote_apps[name]["version"]
            if _version_gt(local_v, remote_v):
                to_push.append({"name": name, "version": local_v, "reason": f"local newer ({local_v} > {remote_v})"})
            elif _version_gt(remote_v, local_v):
                to_pull.append({"name": name, "version": remote_v, "reason": f"remote newer ({remote_v} > {local_v})"})
            else:
                # Same version, check hash
                local_hash = _app_content_hash(name)
                meta = _load_sync_meta(target)
                pushed_hash = meta.get("pushed", {}).get(_sanitize_name(name), {}).get("hash", "")
                if pushed_hash and local_hash != pushed_hash:
                    conflicts.append({"name": name, "version": local_v, "reason": "content changed but same version"})

    # Apps only remote → pull
    for name, info in remote_apps.items():
        if name not in local_apps:
            to_pull.append({"name": name, "version": info["version"], "reason": "new remote app"})

    return {
        "configured": True,
        "target_dir": str(target),
        "device_name": config.get("device_name", ""),
        "last_sync_at": config.get("last_sync_at"),
        "local_count": len(local_apps),
        "remote_count": len(remote_apps),
        "to_push": to_push,
        "to_push_count": len(to_push),
        "to_pull": to_pull,
        "to_pull_count": len(to_pull),
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
    }


def sync_list_remote() -> dict:
    """List all apps available in the sync target."""
    config = get_sync_config()
    if not config.get("configured"):
        return {"error": "Sync not configured"}

    target = Path(config["target_dir"])
    if not target.exists():
        return {"error": f"Sync target not found: {target}"}

    apps = []
    for archive_path in sorted(target.glob("*.krowork")):
        manifest = _read_manifest(archive_path)
        if manifest:
            apps.append({
                "name": manifest.get("app_name", archive_path.stem),
                "version": manifest.get("app_version", ""),
                "description": manifest.get("description", ""),
                "exported_at": manifest.get("exported_at", ""),
                "file_size": archive_path.stat().st_size,
                "file": archive_path.name,
            })

    return {"remote_apps": apps, "total": len(apps), "target_dir": str(target)}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_sync_meta(target: Path) -> dict:
    """Load sync metadata from the target directory."""
    meta_file = target / ".krowork_meta" / "sync_meta.json"
    if meta_file.exists():
        try:
            return json.loads(meta_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_sync_meta(target: Path, meta: dict):
    """Save sync metadata to the target directory."""
    meta_dir = target / ".krowork_meta"
    meta_dir.mkdir(exist_ok=True)
    (meta_dir / "sync_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _read_manifest(archive_path: Path) -> Optional[dict]:
    """Read manifest.json from a .krowork archive."""
    try:
        with zipfile.ZipFile(str(archive_path), "r") as zf:
            if "manifest.json" in zf.namelist():
                return json.loads(zf.read("manifest.json"))
    except (zipfile.BadZipFile, json.JSONDecodeError, OSError):
        pass
    return None


def _app_content_hash(app_name: str) -> str:
    """Compute a content hash for an app (for change detection)."""
    app_dir = get_app_dir(app_name)
    hasher = hashlib.md5()
    for file_name in ["app.json", "main.py", "requirements.txt"]:
        fp = app_dir / file_name
        if fp.exists():
            hasher.update(fp.read_bytes())
    html = app_dir / "templates" / "index.html"
    if html.exists():
        hasher.update(html.read_bytes())
    return hasher.hexdigest()[:12]


def _version_parse(v: str) -> list:
    """Parse a version string like '1.2.3' into [1, 2, 3]."""
    try:
        return [int(x) for x in v.split(".")]
    except (ValueError, AttributeError):
        return [0]


def _version_gt(a: str, b: str) -> bool:
    """Check if version a > b."""
    return _version_parse(a) > _version_parse(b)


def _version_gte(a: str, b: str) -> bool:
    """Check if version a >= b."""
    return _version_parse(a) >= _version_parse(b)
