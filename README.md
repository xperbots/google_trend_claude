# Google Trends "Trending Now" Scraper

A robust Python scraper for extracting trending topics from Google Trends "Trending now" page using headless browser automation. This tool supports various filters, export formats, and both DOM scraping and official CSV export modes.

## 🎯 Key Features

- **🌍 Geographic Filtering**: Support for 100+ countries/regions
- **⏰ Time Windows**: Past 4 hours, 24 hours, 48 hours, or 7 days
- **📊 Category Filters**: All categories plus 19 specific categories (Sports, Entertainment, etc.)
- **🔄 Multiple Export Modes**: DOM scraping, CSV download, RSS feed support
- **📁 Output Formats**: JSON, CSV, Parquet
- **🤖 Browser Automation**: Playwright-based with anti-detection features
- **🔄 Retry Logic**: Robust error handling with exponential backoff
- **📸 Error Screenshots**: Automatic screenshot capture on failures
- **🎛️ CLI Interface**: Rich command-line interface with comprehensive options
- **📦 Programmatic API**: Can be used as a Python module for integration
- **🌐 Translation Support** (v2.0+): Automatic translation to any language with dual providers

## 🚀 Quick Start

### Installation

1. **Set up virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
playwright install chromium
```

3. **Verify installation**:
```bash
python test_basic.py
```

### Basic Usage

```bash
# Default: Vietnam, past 48 hours, games category, by search volume
python3 trends_trending_now.py

# UK, past 7 days, limit to 50 results
python trends_trending_now.py --geo="United Kingdom" --time-window=past_7_days --limit=50

# Sports category, active only, sorted by search volume, export as CSV
python trends_trending_now.py --category=sports --active-only --sort=search_volume --export-mode=export_csv

# Debug mode with headed browser and parquet output
python trends_trending_now.py --no-headless --format=parquet --log-level=DEBUG
```

## 📖 CLI Reference

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--geo` | string | "United States" | Geographic location (country/region name or code) |
| `--time-window` | enum | `past_24_hours` | Time window: `past_4_hours`, `past_24_hours`, `past_48_hours`, `past_7_days` |
| `--category` | enum | `all` | Category filter (see Categories section) |
| `--active-only` | flag | `false` | Show only active trends (exclude "Lasted" trends) |
| `--sort` | enum | `relevance` | Sort order: `title`, `search_volume`, `recency`, `relevance` |
| `--limit` | integer | None | Maximum number of trends to fetch |
| `--expand-breakdown` | flag | `false` | Expand trend breakdown for more related queries |
| `--export-mode` | enum | `scrape` | Export mode: `scrape`, `export_csv`, `export_rss` |
| `--headless` | flag | `true` | Run browser in headless mode |
| `--timeout` | integer | 30 | Page timeout in seconds |
| `--max-retries` | integer | 3 | Maximum retries for failed operations |
| `--lang` | string | None | Language setting (e.g., 'en-US', 'ja-JP') |
| `--proxy` | string | None | Proxy URL (e.g., 'http://proxy:8080') |
| `--out` | string | auto | Output file path |
| `--format` | enum | `json` | Output format: `json`, `csv`, `parquet` |
| `--log-level` | enum | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `--log-file` | string | None | Log file path |

### Categories

Available category filters:
- `all` - All categories
- `autos_and_vehicles` - Autos & Vehicles
- `beauty_and_fashion` - Beauty & Fashion
- `business_and_finance` - Business & Finance
- `climate` - Climate
- `entertainment` - Entertainment
- `food_and_drink` - Food & Drink
- `games` - Games
- `health` - Health
- `hobbies_and_leisure` - Hobbies & Leisure
- `jobs_and_education` - Jobs & Education
- `law_and_government` - Law & Government
- `other` - Other
- `pets_and_animals` - Pets & Animals
- `politics` - Politics
- `science` - Science
- `shopping` - Shopping
- `sports` - Sports
- `technology` - Technology
- `travel_and_transportation` - Travel & Transportation

## 🌐 Translation Feature (v2.0+)

The scraper can automatically translate trending topics from any language to your target language.

### Translation Providers

1. **Free Translation** (Default)
   - Uses Google Translate via deep-translator
   - No API key required
   - Supports automatic language detection

2. **GPT-5-nano Translation**
   - Advanced AI-powered translation
   - Requires API key
   - Better context understanding

### Translation Examples

```bash
# Translate Japanese trends to Chinese
python trends_trending_now.py --geo="Japan" --translate-to=zh

# Translate Korean trends to English
python trends_trending_now.py --geo="South Korea" --translate-to=en

# Use GPT-5-nano for translation (API key loaded from .env file)
python trends_trending_now.py --geo="France" --translate-to=zh --translation-provider=gpt-nano

# Or pass API key directly (overrides .env file)
python trends_trending_now.py --geo="Germany" --translate-to=zh --translation-provider=gpt-nano --gpt-api-key=YOUR_KEY
```

### Supported Languages

Common language codes:
- `zh` - Chinese
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `ja` - Japanese
- `ko` - Korean
- `pt` - Portuguese
- `ru` - Russian
- `ar` - Arabic
- `hi` - Hindi

## 🐍 Programmatic Usage

```python
import asyncio
from models import FetchParams, TimeWindow, Category, SortBy, ExportMode, OutputFormat, TranslationProvider
from trends_trending_now import run

# Create parameters
params = FetchParams(
    geo="Japan",
    time_window=TimeWindow.PAST_7_DAYS,
    category=Category.TECHNOLOGY,
    active_only=True,
    sort=SortBy.SEARCH_VOLUME,
    limit=20,
    headless=True,
    # Translation parameters (v2.0+)
    translation_target="zh",  # Translate to Chinese
    translation_provider=TranslationProvider.FREE
)

# Run scraper
trends = run(params)

# Process results
for trend in trends:
    print(f"{trend.title}: {trend.search_volume_text}")
```

## 📊 Data Schema

Each trend item contains the following fields:

```json
{
  "title": "example trend",
  "search_volume_text": "2M+",
  "search_volume_bucket": "2M_plus",
  "started_relative": "9 hours ago",
  "started_iso": "2025-09-05T13:30:00-07:00",
  "status": "Active",
  "top_related": ["related query 1", "related query 2"],
  "more_related_count": 285,
  "sparkline_svg_path": "M0,22L12,18...",
  "page_index": 1,
  "geo": "United States",
  "time_window": "past_24_hours",
  "category": "all",
  "active_only": false,
  "sort": "relevance",
  "retrieved_at": "2025-09-05T22:40:17-07:00",
  "source": "scrape"
}
```

## 🏗️ Project Structure

```
google_trend_claude/
├── trends_trending_now.py    # 🚀 Main CLI executable
├── models.py                 # 📊 Pydantic models and enums
├── scraper.py               # 🤖 Playwright automation and DOM parsing
├── exporter.py              # 📁 Export functionality (JSON/CSV/Parquet)
├── utils.py                 # 🔧 Utility functions and helpers
├── test_basic.py            # ✅ Basic functionality tests
├── requirements.txt         # 📦 Python dependencies
├── README.md               # 📖 This documentation
├── CLAUDE.md               # 🤖 Project context for AI assistant
├── ProjectIntro.md         # 📝 Original project specifications
├── out/                    # 📤 Output files directory
├── logs/                   # 📋 Logs and error screenshots
├── downloads/              # 💾 Downloaded CSV/RSS files
└── venv/                   # 🐍 Python virtual environment
```

### Core Files Description

| File | Purpose | Key Features |
|------|---------|--------------|
| `trends_trending_now.py` | Main CLI application | Full CLI interface, parameter validation |
| `simple_trends.py` | Quick Chinese viewer | Minimal CLI for fast Chinese output (v2.1) |
| `models.py` | Data models | Pydantic schemas, enums, type safety |
| `scraper.py` | Browser automation | Playwright integration, DOM parsing, geo fixes |
| `translator.py` | Translation engine | Dual providers, batch optimization, context (v2.0) |
| `exporter.py` | Data export | Multi-format export, CSV mapping |
| `utils.py` | Utility functions | Retry logic, screenshots, parsing |
| `test_basic.py` | Testing | Functionality verification |

## 🛠️ Technical Details

### Browser Automation
- **Playwright** with Chromium for robust web scraping
- Anti-detection measures (custom user agent, headers, timing)
- Automatic consent dialog handling
- Screenshot capture on errors

### Selector Strategy
- Uses stable selectors (ARIA labels, roles, text content)
- Avoids CSS classes that may change
- Fallback mechanisms for different page layouts

### Rate Limiting
- Random delays between actions (200-600ms)
- Configurable retry logic with exponential backoff
- Respects server response times

### Error Handling
- Comprehensive exception handling at each stage
- Automatic screenshot capture on failures
- Detailed error reporting with context
- Graceful fallbacks (CSV export → DOM scraping)

## 🔧 Development & Testing

### Running Tests
```bash
# Run basic functionality tests
python test_basic.py

# Test CLI help
python trends_trending_now.py --help

# Test with minimal data (safe test)
python trends_trending_now.py --limit=3 --headless=true --timeout=10
```

### Code Quality
```bash
# Format code (if black is installed)
black *.py

# Lint code (if flake8 is installed)  
flake8 *.py
```

### Project Size
The cleaned project contains only essential files:
- **6 core Python files** (~2,500 lines total)
- **Clean dependencies** (11 packages in requirements.txt)
- **No unused files** or directories
- **Comprehensive documentation**

## 🚨 Error Handling

The scraper includes comprehensive error handling:

1. **Network Issues**: Automatic retries with exponential backoff
2. **Element Not Found**: Fallback selectors and error screenshots  
3. **Export Failures**: Automatic fallback from CSV to DOM scraping
4. **Browser Crashes**: Graceful shutdown with error reporting

Error reports are saved to `logs/error_report.json` with details:
- Stage where error occurred
- Error message
- Screenshot path (if available)
- Timestamp

## 📄 Legal & Compliance

- **Read-only scraping** of publicly available data
- Respects robots.txt and rate limiting
- Uses official export features when available
- Complies with Google's Terms of Service
- For research and analysis purposes only

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if needed
5. Submit a pull request

## 📝 License

This project is for educational and research purposes. Please respect Google's Terms of Service and local laws regarding web scraping.

## 🐛 Troubleshooting

### Common Issues

**Permission Denied**
```bash
chmod +x trends_trending_now.py
```

**Browser Not Found**
```bash
playwright install chromium
```

**Module Import Errors**
```bash
pip install -r requirements.txt
```

**Consent Dialog Issues**
- Try running with `--no-headless` to see the browser
- Check logs for consent handling messages
- Manually accept consent once if needed

### Debug Mode

Run with debug logging to see detailed execution:
```bash
python trends_trending_now.py --log-level=DEBUG --no-headless
```

This will show:
- Browser actions and page navigation
- Element detection and interaction
- Data extraction process
- Export operations

## 📊 Project Summary

This Google Trends scraper is a **production-ready** solution built with modern Python practices:

### ✅ **What's Included**
- ✅ Complete CLI application with rich interface
- ✅ Robust browser automation with anti-detection
- ✅ Multiple export formats and modes
- ✅ Comprehensive error handling and recovery
- ✅ Type-safe code with Pydantic models
- ✅ Full documentation and examples
- ✅ Clean, maintainable codebase

### 🎯 **Use Cases**
- **Research**: Track trending topics by region/category
- **Marketing**: Monitor brand mentions and competitor trends
- **Journalism**: Identify breaking news and popular topics
- **Data Analysis**: Export trending data for further analysis
- **Automation**: Integrate into larger data pipelines

### 📈 **Performance**
- **Fast**: Parallel processing and efficient selectors
- **Reliable**: Retry logic and fallback mechanisms
- **Scalable**: Configurable limits and batch processing
- **Respectful**: Rate limiting and server-friendly delays

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Run with debug logging (`--log-level=DEBUG`)
3. Check `logs/` directory for error screenshots
4. Review the error report JSON for detailed diagnostics

**Ready to start scraping Google Trends!** 🚀