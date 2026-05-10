---
description: "Summarize, analyze, or translate web content using AI"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_preprocess_content, mcp__krowork__krowork_scrape_page, mcp__krowork__krowork_scrape_rss, mcp__krowork__krowork_scrape_elements
---

# KroWork: Summarize

Fetch web content and use Claude's AI capabilities to summarize, analyze, or translate it.

## How It Works

This skill combines KroWork's web scraping with Claude's AI abilities:
1. **KroWork** handles content fetching and preprocessing (cleaning, deduplication, extraction)
2. **Claude** handles the AI part (summarization, analysis, translation)

No external LLM API is needed — Claude IS the AI engine.

## Workflow

### Step 1: Understand the Request

The user input `$ARGUMENTS` may contain:
- A URL to summarize
- A description of what analysis they want (summarize, key points, translate, compare, etc.)
- Multiple URLs to compare

Determine the action:
- **Summarize**: "帮我总结这篇文章" → Provide a concise summary
- **Key points**: "这篇文章的重点是什么" → Extract and list key takeaways
- **Translate**: "翻译成中文/英文" → Translate the content
- **Analyze**: "分析这个产品的优缺点" → Deep analysis
- **Compare**: "对比这两个页面" → Compare multiple sources
- **Monitor + Summarize**: "每天帮我总结这个网站的更新" → Set up monitoring

### Step 2: Fetch and Preprocess Content

Use `krowork_preprocess_content` to get clean, structured content:

- `url`: The target URL
- `max_length`: Adjust based on need (default 8000, increase for deep analysis)

This returns:
- `title`: Page title
- `description`: Meta description
- `key_points`: Headings extracted from the page
- `clean_text`: Noise-free main content
- `stats`: Content statistics

For RSS feeds, use `krowork_scrape_rss` instead.

### Step 3: Apply AI Analysis

Using the preprocessed content, apply Claude's AI capabilities:

- **For summaries**: Read the `clean_text` and produce a structured summary
- **For analysis**: Combine `key_points` with `clean_text` for deeper insights
- **For translation**: Translate the `clean_text` to the requested language
- **For comparison**: Fetch multiple URLs, then compare side by side

### Step 4: Present Results

Format the AI output clearly:
- Use headers and bullet points for readability
- Include the source URL
- Note the content date if available
- Highlight key findings

### Step 5: Suggest Follow-up

- "Create a monitoring app" → `/krowork:create`
- "Track this page for changes" → `krowork_monitor_page`
- "Save as data source" → `/krowork:datasource`

## Tips for Best Results

- For long articles, increase `max_length` to get more content
- For news sites, use `krowork_scrape_rss` for structured feed data
- For comparison, fetch all URLs first, then analyze together
- The `key_points` from preprocessing help Claude focus on the right sections
