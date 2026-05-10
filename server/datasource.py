"""Open-KroWork Data Source Integration - Unified interface for API/RSS/Web/Local data.

Provides a data source registry and helpers for fetching data from
REST APIs, RSS feeds, web pages, and local files.
"""

import csv
import io
import json
import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Data Source Registry
# ---------------------------------------------------------------------------

_REGISTRY_DIR = Path.home() / ".krowork" / "datasources"


def _ensure_registry_dir():
    _REGISTRY_DIR.mkdir(parents=True, exist_ok=True)


def _source_path(name: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in name.lower())
    return _REGISTRY_DIR / f"{safe}.json"


def register_source(name: str, source_type: str, config: dict) -> dict:
    """Register a new data source.

    Args:
        name: Human-readable name (e.g. "Hacker News")
        source_type: One of "rest_api", "rss", "web_scrape", "local_file", "sqlite"
        config: Source-specific configuration (url, method, headers, etc.)

    Returns:
        dict with the saved data source metadata
    """
    valid_types = {"rest_api", "rss", "web_scrape", "local_file", "sqlite"}
    if source_type not in valid_types:
        return {"error": f"Invalid source_type '{source_type}'. Must be one of {valid_types}"}

    _ensure_registry_dir()
    source = {
        "name": name,
        "type": source_type,
        "config": config,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _source_path(name).write_text(
        json.dumps(source, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return {"success": True, "source": source}


def list_sources() -> dict:
    """List all registered data sources."""
    _ensure_registry_dir()
    sources = []
    for f in sorted(_REGISTRY_DIR.glob("*.json")):
        try:
            sources.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return {"sources": sources, "total": len(sources)}


def get_source(name: str) -> dict:
    """Get a registered data source by name."""
    path = _source_path(name)
    if not path.exists():
        return {"error": f"Data source '{name}' not found"}
    return json.loads(path.read_text(encoding="utf-8"))


def delete_source(name: str) -> dict:
    """Delete a registered data source."""
    path = _source_path(name)
    if not path.exists():
        return {"error": f"Data source '{name}' not found"}
    path.unlink()
    return {"success": True, "name": name}


# ---------------------------------------------------------------------------
# Unified Fetch Interface
# ---------------------------------------------------------------------------

def fetch_data(source_name_or_config) -> dict:
    """Fetch data from a data source.

    Args:
        source_name_or_config: Either a registered source name (str)
            or a config dict with 'type' and 'config' keys.

    Returns:
        dict with 'source', 'fetched_at', and type-specific data fields
    """
    # Resolve config
    if isinstance(source_name_or_config, str):
        source = get_source(source_name_or_config)
        if "error" in source:
            return source
    elif isinstance(source_name_or_config, dict):
        source = source_name_or_config
    else:
        return {"error": "source_name_or_config must be a string name or dict config"}

    source_type = source.get("type", "")
    config = source.get("config", {})

    if source_type == "rest_api":
        return _fetch_rest_api(source, config)
    elif source_type == "rss":
        return _fetch_rss(source, config)
    elif source_type == "web_scrape":
        return _fetch_web_scrape(source, config)
    elif source_type == "local_file":
        return _fetch_local_file(source, config)
    elif source_type == "sqlite":
        return _fetch_sqlite(source, config)
    else:
        return {"error": f"Unsupported source type: {source_type}"}


# ---------------------------------------------------------------------------
# Type-Specific Fetchers
# ---------------------------------------------------------------------------

def _fetch_rest_api(source: dict, config: dict) -> dict:
    """Fetch data from a REST API."""
    import requests

    url = config.get("url", "")
    if not url:
        return {"error": "REST API source requires 'url' in config"}

    method = config.get("method", "GET").upper()
    headers = config.get("headers", {})
    params = config.get("params", {})
    body = config.get("body")
    timeout = config.get("timeout", 30)
    cache_ttl = config.get("cache_ttl", 0)

    # Check cache
    if cache_ttl > 0:
        cached = _get_cached(source["name"], cache_ttl)
        if cached:
            return cached

    session = requests.Session()
    session.headers.update(headers)

    try:
        if method == "GET":
            resp = session.get(url, params=params, timeout=timeout)
        elif method == "POST":
            resp = session.post(url, json=body, params=params, timeout=timeout)
        else:
            resp = session.request(method, url, json=body, params=params, timeout=timeout)

        resp.raise_for_status()

        # Try JSON parse
        try:
            data = resp.json()
        except ValueError:
            data = resp.text

        result = {
            "source": source.get("name", url),
            "type": "rest_api",
            "url": url,
            "status_code": resp.status_code,
            "data": data,
            "fetched_at": datetime.now().isoformat(),
        }

        if cache_ttl > 0:
            _set_cached(source["name"], result)

        return result

    except Exception as e:
        return {"error": f"REST API request failed: {e}"}


def _fetch_rss(source: dict, config: dict) -> dict:
    """Fetch data from an RSS/Atom feed."""
    from scraper import scrape_rss

    url = config.get("url", "")
    if not url:
        return {"error": "RSS source requires 'url' in config"}

    max_items = config.get("max_items", 20)
    result = scrape_rss(url, max_items=max_items)
    result["source"] = source.get("name", url)
    result["type"] = "rss"
    result["fetched_at"] = datetime.now().isoformat()
    return result


def _fetch_web_scrape(source: dict, config: dict) -> dict:
    """Fetch data by scraping a web page."""
    from scraper import fetch_page, extract_elements

    url = config.get("url", "")
    if not url:
        return {"error": "Web scrape source requires 'url' in config"}

    selector = config.get("selector", "")
    cache_ttl = config.get("cache_ttl", 300)

    if selector:
        result = extract_elements(url, selector)
    else:
        result = fetch_page(url, cache_ttl=cache_ttl)

    result["source"] = source.get("name", url)
    result["type"] = "web_scrape"
    result["fetched_at"] = datetime.now().isoformat()
    return result


def _fetch_local_file(source: dict, config: dict) -> dict:
    """Read data from a local file (CSV, JSON, TXT)."""
    file_path = config.get("file_path", "")
    if not file_path:
        return {"error": "Local file source requires 'file_path' in config"}

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    ext = path.suffix.lower()
    try:
        if ext == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
        elif ext == ".csv":
            data = _read_csv(path)
        elif ext in (".txt", ".md", ".log"):
            text = path.read_text(encoding="utf-8")
            max_lines = config.get("max_lines", 1000)
            lines = text.splitlines()[:max_lines]
            data = {"lines": lines, "total_lines": len(text.splitlines())}
        else:
            # Try reading as text
            data = path.read_text(encoding="utf-8")[:50000]

        return {
            "source": source.get("name", file_path),
            "type": "local_file",
            "file_path": str(path),
            "file_size": path.stat().st_size,
            "format": ext,
            "data": data,
            "fetched_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": f"Failed to read file: {e}"}


def _fetch_sqlite(source: dict, config: dict) -> dict:
    """Execute a query against a SQLite database."""
    db_path = config.get("db_path", "")
    query = config.get("query", "")
    if not db_path:
        return {"error": "SQLite source requires 'db_path' in config"}
    if not query:
        return {"error": "SQLite source requires 'query' in config"}

    path = Path(db_path)
    if not path.exists():
        return {"error": f"Database not found: {db_path}"}

    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()

        max_rows = config.get("max_rows", 1000)
        return {
            "source": source.get("name", db_path),
            "type": "sqlite",
            "columns": columns,
            "row_count": len(rows),
            "rows": rows[:max_rows],
            "fetched_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": f"SQLite query failed: {e}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_csv(path: Path, max_rows: int = 1000) -> dict:
    """Read a CSV file and return structured data."""
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        rows.append(dict(row))
    return {
        "columns": reader.fieldnames or [],
        "row_count": len(rows),
        "rows": rows,
    }


def _get_cached(name: str, ttl: int) -> Optional[dict]:
    """Get cached data if still fresh."""
    cache_dir = Path.home() / ".krowork" / "cache" / "datasource"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{_safe_cache_key(name)}.json"
    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < ttl:
            try:
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return None


def _set_cached(name: str, data: dict):
    """Save data to cache."""
    cache_dir = Path.home() / ".krowork" / "cache" / "datasource"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{_safe_cache_key(name)}.json"
    cache_file.write_text(
        json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8"
    )


def _safe_cache_key(name: str) -> str:
    import hashlib
    return hashlib.md5(name.encode()).hexdigest()[:12]
