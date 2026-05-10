---
description: "Manage data sources for API, RSS, web scraping, files, and databases"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_register_datasource, mcp__krowork__krowork_list_datasources, mcp__krowork__krowork_fetch_datasource, mcp__krowork__krowork_delete_datasource
---

# KroWork: Data Sources

Register, manage, and fetch data from external data sources.

## Workflow

### Step 1: Understand Data Need

The user input `$ARGUMENTS` describes the data source they want to set up. Determine:

- **Source type**: REST API, RSS feed, web scraping, local file, or SQLite database
- **Configuration**: URL, authentication, headers, query parameters
- **Purpose**: One-time fetch or repeated use

### Step 2: Register Data Source

If the user wants a persistent data source, use `krowork_register_datasource`:

- `name`: Human-readable name (e.g., "Hacker News")
- `source_type`: One of: rest_api, rss, web_scrape, local_file, sqlite
- `config`: Source-specific configuration

### Step 3: Fetch Data

Use `krowork_fetch_datasource` with the registered name to retrieve data.

### Step 4: Present Results

Show the fetched data in a readable format and suggest how to use it:
- Create an app with this data source
- Set up monitoring/scheduling
- Export the data

## Supported Source Types

| Type | Config Keys |
|------|-------------|
| rest_api | url, method, headers, params, body, cache_ttl |
| rss | url, max_items |
| web_scrape | url, selector, cache_ttl |
| local_file | file_path, max_lines |
| sqlite | db_path, query, max_rows |
