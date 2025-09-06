# Google Trends Scraper v1.0.0

## Overview
A robust Python-based Google Trends scraper that automates the extraction of trending topics from Google Trends "Trending Now" page using Playwright for browser automation.

## Key Features

### 🔍 Core Scraping Capabilities
- **Headless Browser Automation**: Uses Playwright to scrape Google Trends trending topics
- **Multiple Export Modes**: 
  - Direct DOM scraping
  - CSV export mode (with fallback)
  - RSS export mode (with fallback)
- **Pagination Support**: Automatically navigates through multiple pages of results
- **Error Handling**: Comprehensive error reporting with screenshot capture on failures

### 🎛️ Advanced Filtering Options
- **Geographic Location**: Filter trends by country/region
- **Time Windows**: Past 4 hours, 24 hours, 48 hours, or 7 days
- **Categories**: 20+ categories including Sports, Entertainment, Technology, etc.
- **Status Filtering**: Option to show only active trends
- **Sort Options**: By title, search volume, recency, or relevance

### 📊 Data Extraction
- **Trend Details**: Title, search volume, relative time, status (Active/Lasted)
- **Related Queries**: Extracts top related searches for each trend
- **Sparkline Data**: Captures SVG paths for trend visualization
- **Metadata**: Timestamps, geographic info, applied filters

### 💾 Export Formats
- **JSON**: Full structured data with all metadata
- **CSV**: Tabular format for spreadsheet analysis
- **Parquet**: Efficient columnar storage for big data processing

### 🛡️ Reliability Features
- **Retry Logic**: Configurable retries with exponential backoff
- **Random Delays**: Mimics human behavior to avoid detection
- **Proxy Support**: Optional proxy configuration
- **Multi-language Support**: Configurable browser locale settings

## Technical Stack
- **Language**: Python 3.8+
- **Browser Automation**: Playwright
- **CLI Framework**: Typer
- **Data Models**: Pydantic
- **Data Processing**: Pandas, PyArrow
- **Async Support**: Full async/await implementation

## Usage Examples

```bash
# Basic usage - US trends from past 24 hours
python trends_trending_now.py

# UK sports trends from past 7 days
python trends_trending_now.py --geo="United Kingdom" --category=sports --time-window=past_7_days

# Export as CSV with active trends only
python trends_trending_now.py --active-only --format=csv --export-mode=export_csv

# Debug mode with visible browser
python trends_trending_now.py --no-headless --log-level=DEBUG
```

## Project Structure
- `scraper.py`: Main scraping logic with browser automation
- `models.py`: Pydantic models and enums for type safety
- `exporter.py`: Data export functionality for multiple formats
- `utils.py`: Helper functions and utilities
- `trends_trending_now.py`: CLI entry point
- `test_basic.py`: Basic test suite

## Recent Outputs
Successfully scraped trending topics with comprehensive data extraction including search volumes (e.g., "200K+", "2M+"), related queries, and trend lifecycles.

---

🚀 Ready for production use with comprehensive error handling, logging, and configurable options.