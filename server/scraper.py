"""Open-KroWork Web Scraper - Lightweight web scraping via requests + BeautifulSoup4.

Provides scraping capabilities that can be used by generated apps
or called directly through MCP tools.
"""

import json
import os
import re
import hashlib
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse


def _get_session():
    """Get a requests session with proper headers."""
    import requests
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    return session


def fetch_page(url: str, timeout: int = 30, cache_ttl: int = 300) -> dict:
    """Fetch a web page and return its content with metadata.

    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        cache_ttl: Cache time-to-live in seconds (0 to disable)

    Returns:
        dict with url, status, title, text, html, links, headers
    """
    import requests
    from bs4 import BeautifulSoup

    # Check cache
    cache_dir = Path.home() / ".krowork" / "cache" / "scraper"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_file = cache_dir / f"{cache_key}.json"

    if cache_ttl > 0 and cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < cache_ttl:
            return json.loads(cache_file.read_text(encoding="utf-8"))

    session = _get_session()
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()

    # Detect encoding
    if not resp.encoding or resp.encoding == "ISO-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Extract title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Extract clean text
    # Remove script/style tags
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)

    # Extract links
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(url, href)
        link_text = a.get_text(strip=True)
        if full_url.startswith("http"):
            links.append({"url": full_url, "text": link_text})

    # Extract meta description
    meta_desc = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        meta_desc = meta["content"]

    result = {
        "url": url,
        "status": resp.status_code,
        "title": title,
        "description": meta_desc,
        "text": text[:50000],  # Limit text size
        "html_length": len(html),
        "links": links[:200],  # Limit links
        "content_type": resp.headers.get("Content-Type", ""),
    }

    # Save cache
    if cache_ttl > 0:
        cache_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")

    return result


def extract_elements(url: str, selector: str, base_url: str = None,
                     timeout: int = 30) -> dict:
    """Extract specific elements from a web page using CSS selectors.

    Args:
        url: URL to fetch
        selector: CSS selector (e.g., "h2 a", ".article-title", "#content")
        base_url: Base URL for resolving relative links
        timeout: Request timeout

    Returns:
        dict with url, selector, count, elements (list of {text, attributes})
    """
    from bs4 import BeautifulSoup

    session = _get_session()
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()

    if not resp.encoding or resp.encoding == "ISO-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    elements = []

    for el in soup.select(selector):
        item = {"text": el.get_text(strip=True)}
        if el.name == "a" and el.get("href"):
            item["url"] = urljoin(base_url or url, el["href"])
        for attr in ["src", "href", "alt", "title", "class", "id", "data-src"]:
            val = el.get(attr)
            if val:
                if attr in ("src", "href"):
                    item[attr] = urljoin(base_url or url, val)
                else:
                    item[attr] = val
        elements.append(item)

    return {
        "url": url,
        "selector": selector,
        "count": len(elements),
        "elements": elements[:500],
    }


def scrape_rss(url: str, max_items: int = 20, timeout: int = 30) -> dict:
    """Parse an RSS or Atom feed.

    Args:
        url: RSS/Atom feed URL
        max_items: Maximum items to return
        timeout: Request timeout

    Returns:
        dict with title, description, link, items (list of feed entries)
    """
    import xml.etree.ElementTree as ET

    session = _get_session()
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)

    # Detect RSS vs Atom
    items = []
    feed_title = ""
    feed_desc = ""
    feed_link = url

    if root.tag.endswith("rss") or root.tag == "rss":
        # RSS 2.0
        channel = root.find("channel")
        if channel is not None:
            feed_title = (channel.findtext("title") or "").strip()
            feed_desc = (channel.findtext("description") or "").strip()
            feed_link = (channel.findtext("link") or url).strip()
            for item in channel.findall("item")[:max_items]:
                items.append({
                    "title": (item.findtext("title") or "").strip(),
                    "link": (item.findtext("link") or "").strip(),
                    "description": (item.findtext("description") or "").strip(),
                    "pub_date": (item.findtext("pubDate") or "").strip(),
                    "author": (item.findtext("author") or item.findtext("dc:creator", "") or "").strip(),
                })
    elif root.tag.endswith("feed") or root.tag == "feed":
        # Atom
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        feed_title = (root.findtext("atom:title", "", ns) or "").strip()
        feed_desc = (root.findtext("atom:subtitle", "", ns) or "").strip()
        link_el = root.find("atom:link", ns)
        if link_el is not None and link_el.get("href"):
            feed_link = link_el["href"]
        for entry in root.findall("atom:entry", ns)[:max_items]:
            link = ""
            link_el = entry.find("atom:link", ns)
            if link_el is not None:
                link = link_el.get("href", "")
            items.append({
                "title": (entry.findtext("atom:title", "", ns) or "").strip(),
                "link": link,
                "description": (entry.findtext("atom:summary", "", ns) or "").strip(),
                "pub_date": (entry.findtext("atom:published", "", ns) or
                             entry.findtext("atom:updated", "", ns) or "").strip(),
                "author": "",
            })

    return {
        "url": url,
        "title": feed_title,
        "description": feed_desc,
        "link": feed_link,
        "item_count": len(items),
        "items": items,
    }


def scrape_table(url: str, table_index: int = 0, timeout: int = 30) -> dict:
    """Extract data from an HTML table on a web page.

    Args:
        url: URL containing the table
        table_index: Which table to extract (0-based)
        timeout: Request timeout

    Returns:
        dict with url, headers (list), rows (list of lists)
    """
    from bs4 import BeautifulSoup

    session = _get_session()
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    tables = soup.find_all("table")

    if table_index >= len(tables):
        return {"error": f"Table index {table_index} not found. Found {len(tables)} tables."}

    table = tables[table_index]
    headers = []
    rows = []

    # Extract headers
    thead = table.find("thead")
    if thead:
        for th in thead.find_all(["th", "td"]):
            headers.append(th.get_text(strip=True))

    # If no thead, try first tr
    if not headers:
        first_tr = table.find("tr")
        if first_tr:
            for th in first_tr.find_all("th"):
                headers.append(th.get_text(strip=True))

    # Extract rows
    tbody = table.find("tbody") or table
    for tr in tbody.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        row = [cell.get_text(strip=True) for cell in cells]
        # Skip header row if it was in tbody
        if row == headers:
            continue
        rows.append(row)

    return {
        "url": url,
        "table_index": table_index,
        "headers": headers,
        "row_count": len(rows),
        "rows": rows[:500],
    }


def scrape_multi_page(base_url: str, link_selector: str, content_selector: str,
                      max_pages: int = 5, delay: float = 1.0,
                      timeout: int = 30) -> dict:
    """Scrape multiple pages: fetch a listing page, follow links, extract content.

    Args:
        base_url: Starting URL (listing page)
        link_selector: CSS selector for links to follow
        content_selector: CSS selector for content on detail pages
        max_pages: Maximum number of detail pages to scrape
        delay: Delay between requests in seconds
        timeout: Request timeout

    Returns:
        dict with base_url, pages_scraped, results (list of {url, title, content})
    """
    # Get links from listing page
    links_result = extract_elements(base_url, link_selector, timeout=timeout)
    links = [el["url"] for el in links_result["elements"] if "url" in el][:max_pages]

    results = []
    session = _get_session()

    for i, page_url in enumerate(links):
        if i > 0 and delay > 0:
            time.sleep(delay)

        try:
            resp = session.get(page_url, timeout=timeout)
            resp.raise_for_status()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            title = (soup.title.string or "").strip() if soup.title else ""
            elements = soup.select(content_selector)
            content = "\n".join(el.get_text(strip=True) for el in elements)

            results.append({
                "url": page_url,
                "title": title,
                "content": content[:10000],
            })
        except Exception as e:
            results.append({"url": page_url, "error": str(e)})

    return {
        "base_url": base_url,
        "pages_scraped": len(results),
        "results": results,
    }


def extract_text_from_pdf(file_path: str) -> dict:
    """Extract text content from a PDF file.

    Args:
        file_path: Path to the PDF file

    Returns:
        dict with file_path, page_count, text
    """
    try:
        import PyPDF2
    except ImportError:
        return {"error": "PyPDF2 not installed. Run: pip install PyPDF2"}

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    text_parts = []
    page_count = 0
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        page_count = len(reader.pages)
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")

    return {
        "file_path": str(path),
        "page_count": page_count,
        "text": "\n".join(text_parts)[:50000],
    }


# ---------------------------------------------------------------------------
# Advanced Scraping (Phase 4)
# ---------------------------------------------------------------------------

def scrape_paginated(base_url: str, next_selector: str, content_selector: str,
                     max_pages: int = 5, delay: float = 1.0,
                     timeout: int = 30) -> dict:
    """Scrape a paginated website by following 'next page' links.

    Args:
        base_url: Starting URL
        next_selector: CSS selector for the 'next page' link
        content_selector: CSS selector for content to extract on each page
        max_pages: Maximum pages to scrape
        delay: Delay between requests in seconds
        timeout: Request timeout

    Returns:
        dict with base_url, pages_scraped, results
    """
    session = _get_session()
    results = []
    current_url = base_url

    for page_num in range(max_pages):
        try:
            resp = session.get(current_url, timeout=timeout)
            resp.raise_for_status()

            if not resp.encoding or resp.encoding == "ISO-8859-1":
                resp.encoding = resp.apparent_encoding or "utf-8"

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract content
            elements = soup.select(content_selector)
            page_content = []
            for el in elements:
                item = {"text": el.get_text(strip=True)}
                if el.name == "a" and el.get("href"):
                    item["url"] = urljoin(current_url, el["href"])
                page_content.append(item)

            results.append({
                "page_url": current_url,
                "page_number": page_num + 1,
                "content_count": len(page_content),
                "content": page_content[:100],
            })

            # Find next page link
            next_link = None
            next_el = soup.select_one(next_selector)
            if next_el:
                if next_el.name == "a" and next_el.get("href"):
                    next_link = urljoin(current_url, next_el["href"])
                elif next_el.name != "a":
                    a_in_next = next_el.find("a", href=True)
                    if a_in_next:
                        next_link = urljoin(current_url, a_in_next["href"])

            if not next_link or next_link == current_url:
                break

            current_url = next_link

            if page_num < max_pages - 1 and delay > 0:
                time.sleep(delay)

        except Exception as e:
            results.append({"page_url": current_url, "error": str(e)})
            break

    return {
        "base_url": base_url,
        "pages_scraped": len(results),
        "results": results,
    }


def scrape_with_auth(url: str, selector: str, auth_type: str = "cookie",
                      auth_value: str = "", extra_headers: dict = None,
                      timeout: int = 30) -> dict:
    """Scrape a page that requires authentication.

    Args:
        url: URL to scrape
        selector: CSS selector for content extraction
        auth_type: "cookie", "header", or "basic"
        auth_value: Cookie string, header value, or "user:pass" for basic auth
        extra_headers: Additional headers dict
        timeout: Request timeout

    Returns:
        dict with url, count, elements
    """
    import requests
    from bs4 import BeautifulSoup

    session = _get_session()

    # Apply authentication
    if auth_type == "cookie" and auth_value:
        for pair in auth_value.split(";"):
            if "=" in pair:
                k, v = pair.strip().split("=", 1)
                session.cookies.set(k, v)
    elif auth_type == "header" and auth_value:
        if ":" in auth_value:
            k, v = auth_value.split(":", 1)
            session.headers[k.strip()] = v.strip()
    elif auth_type == "basic" and auth_value:
        from requests.auth import HTTPBasicAuth
        if ":" in auth_value:
            user, pwd = auth_value.split(":", 1)
            session.auth = HTTPBasicAuth(user, pwd)

    if extra_headers:
        session.headers.update(extra_headers)

    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    elements = []
    for el in soup.select(selector):
        item = {"text": el.get_text(strip=True)}
        if el.name == "a" and el.get("href"):
            item["url"] = urljoin(url, el["href"])
        elements.append(item)

    return {
        "url": url,
        "count": len(elements),
        "elements": elements[:200],
    }


def scrape_api(url: str, method: str = "GET", body: dict = None,
                headers: dict = None, params: dict = None,
                json_path: str = "", timeout: int = 30) -> dict:
    """Scrape a REST API endpoint and return structured JSON data.

    Args:
        url: API endpoint URL
        method: HTTP method
        body: Request body (for POST/PUT)
        headers: Custom headers
        params: Query parameters
        json_path: Dot-notation path to extract from response (e.g., "data.items")
        timeout: Request timeout

    Returns:
        dict with url, status, data
    """
    import requests

    session = _get_session()
    if headers:
        session.headers.update(headers)

    if method.upper() == "GET":
        resp = session.get(url, params=params, timeout=timeout)
    elif method.upper() == "POST":
        resp = session.post(url, json=body, params=params, timeout=timeout)
    else:
        resp = session.request(method, url, json=body, params=params, timeout=timeout)

    resp.raise_for_status()

    try:
        data = resp.json()
    except ValueError:
        return {"url": url, "status": resp.status_code, "data": resp.text[:50000]}

    # Extract nested data by path
    if json_path:
        for key in json_path.split("."):
            if isinstance(data, dict):
                data = data.get(key, {})
            elif isinstance(data, list) and key.isdigit():
                data = data[int(key)] if int(key) < len(data) else None
            else:
                break

    return {
        "url": url,
        "status": resp.status_code,
        "data": data,
    }


def monitor_page(url: str, selector: str, cache_ttl: int = 0,
                 timeout: int = 30) -> dict:
    """Check if a web page's content has changed since last check.

    Args:
        url: URL to monitor
        selector: CSS selector for the content to track
        cache_ttl: Set > 0 to use cache (skip check if fresh)
        timeout: Request timeout

    Returns:
        dict with url, content_hash, current_text, changed (bool)
    """
    import hashlib

    # Load previous hash
    cache_dir = Path.home() / ".krowork" / "cache" / "monitor"
    cache_dir.mkdir(parents=True, exist_ok=True)
    hash_file = cache_dir / (hashlib.md5(url.encode()).hexdigest() + ".json")
    previous_hash = ""
    if hash_file.exists():
        try:
            previous_hash = json.loads(hash_file.read_text(encoding="utf-8")).get("hash", "")
        except (json.JSONDecodeError, OSError):
            pass

    result = extract_elements(url, selector, timeout=timeout)
    if "error" in result:
        return result

    # Combine all element texts
    current_text = " ".join(el.get("text", "") for el in result.get("elements", []))
    current_hash = hashlib.md5(current_text.encode()).hexdigest()
    changed = current_hash != previous_hash

    # Save current hash
    hash_file.write_text(
        json.dumps({"hash": current_hash, "checked_at": time.time()}),
        encoding="utf-8"
    )

    return {
        "url": url,
        "selector": selector,
        "changed": changed,
        "content_hash": current_hash,
        "current_text": current_text[:5000],
        "element_count": result.get("count", 0),
    }


# ---------------------------------------------------------------------------
# Content Preprocessing (for AI consumption)
# ---------------------------------------------------------------------------

def preprocess_content(url: str, max_length: int = 8000, timeout: int = 30) -> dict:
    """Fetch a web page and preprocess its content for AI summarization.

    Extracts clean text, removes noise (ads, nav, footers), deduplicates
    lines, and returns a structured summary-ready format.

    The caller (Claude) can then use its own AI capabilities to produce
    summaries, analyses, or translations.

    Args:
        url: URL to fetch and preprocess
        max_length: Maximum text length to return (default 8000 chars)
        timeout: Request timeout

    Returns:
        dict with url, title, description, key_points, clean_text, stats
    """
    import requests
    from bs4 import BeautifulSoup

    session = _get_session()
    resp = session.get(url, timeout=timeout)
    resp.raise_for_status()

    if not resp.encoding or resp.encoding == "ISO-8859-1":
        resp.encoding = resp.apparent_encoding or "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Meta description
    meta_desc = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        meta_desc = meta["content"].strip()

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "aside", "iframe", "noscript", "form", "svg"]):
        tag.decompose()

    # Remove ads (common patterns)
    for el in soup.find_all(attrs={"class": re.compile(r"ad[s_]?|banner|popup|modal|cookie", re.I)}):
        el.decompose()
    for el in soup.find_all(attrs={"id": re.compile(r"ad[s_]?|banner|popup|sidebar", re.I)}):
        el.decompose()

    # Extract headings as key points
    key_points = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text and len(text) < 200:
            key_points.append(text)
    key_points = key_points[:20]

    # Extract main content: prefer <article>, <main>, or largest text block
    main_content = ""
    for selector in ["article", "main", "[role='main']", ".content", ".post", ".article"]:
        container = soup.select_one(selector)
        if container:
            main_content = container.get_text(separator="\n", strip=True)
            if len(main_content) > 200:
                break

    if not main_content or len(main_content) < 200:
        main_content = soup.get_text(separator="\n", strip=True)

    # Clean up: remove excessive blank lines and deduplicate
    lines = main_content.splitlines()
    seen = set()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            clean_lines.append(stripped)

    clean_text = "\n".join(clean_lines)[:max_length]

    # Extract links with context
    links = []
    for a in soup.find_all("a", href=True):
        href = urljoin(url, a["href"])
        text = a.get_text(strip=True)[:100]
        if text and href.startswith("http") and len(links) < 15:
            links.append({"text": text, "url": href})

    # Compute content stats
    word_count = len(clean_text.split())
    char_count = len(clean_text)

    return {
        "url": url,
        "title": title,
        "description": meta_desc,
        "key_points": key_points,
        "clean_text": clean_text,
        "links": links,
        "stats": {
            "char_count": char_count,
            "word_count": word_count,
            "heading_count": len(key_points),
            "link_count": len(links),
            "original_html_length": len(resp.text),
        },
    }
