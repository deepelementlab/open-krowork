---
description: "Scrape web content, RSS feeds, or API data"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_scrape_page, mcp__krowork__krowork_scrape_elements, mcp__krowork__krowork_scrape_rss, mcp__krowork__krowork_scrape_table, mcp__krowork__krowork_scrape_api, mcp__krowork__krowork_monitor_page
---

# KroWork: Scrape

Scrape web pages, RSS feeds, API endpoints, or HTML tables.

## Workflow

### Step 1: Analyze Request

The user input `$ARGUMENTS` describes what to scrape. Determine the appropriate tool:

- **Full page content** → `krowork_scrape_page` (title, text, links)
- **Specific elements** → `krowork_scrape_elements` (CSS selector)
- **RSS/Atom feed** → `krowork_scrape_rss`
- **HTML table** → `krowork_scrape_table`
- **REST API** → `krowork_scrape_api`
- **Page monitoring** → `krowork_monitor_page` (detect changes)

### Step 2: Execute Scraping

Call the appropriate tool with the URL and parameters.

### Step 3: Present Results

Display the scraped data in a readable format:
- Summarize key findings
- Show data in tables for structured content
- Highlight important links or entries
- Note any errors or limitations

### Step 4: Suggest Next Steps

If the user wants to:
- **Save as an app**: Suggest `/krowork:create` to build an app using this data
- **Register as data source**: Suggest `/krowork:datasource` for repeated access
- **Monitor for changes**: Suggest using `krowork_monitor_page` on a schedule
