#!/usr/bin/env python3
"""
Google Trends Trending Now scraper.

This script scrapes trending topics from Google Trends "Trending now" page
using headless browser automation with configurable filters and export options.
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import List, Optional

import typer
from typing_extensions import Annotated

from models import (
    FetchParams, TrendItem, TimeWindow, Category, SortBy, 
    ExportMode, OutputFormat, ErrorReport
)
from scraper import run_scraper
from exporter import DataExporter, print_export_summary
from utils import setup_logging, ensure_directories


app = typer.Typer(
    name="trends-trending-now",
    help="Google Trends Trending Now scraper with headless browser automation",
    add_completion=False
)


@app.command()
def main(
    geo: str = typer.Option(
        "United States",
        "--geo",
        help="Geographic location (country/region name or code)"
    ),
    time_window: str = typer.Option(
        "past_24_hours",
        "--time-window",
        help="Time window: past_4_hours, past_24_hours, past_48_hours, past_7_days"
    ),
    category: str = typer.Option(
        "all",
        "--category", 
        help="Category: all, sports, entertainment, etc."
    ),
    active_only: bool = typer.Option(
        False,
        "--active-only",
        help="Show only active trends (exclude 'Lasted' trends)"
    ),
    sort: str = typer.Option(
        "relevance",
        "--sort",
        help="Sort: title, search_volume, recency, relevance"
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        help="Maximum number of trends to fetch (default: all available)"
    ),
    expand_breakdown: bool = typer.Option(
        False,
        "--expand-breakdown",
        help="Expand trend breakdown to get more related queries"
    ),
    export_mode: str = typer.Option(
        "scrape",
        "--export-mode",
        help="Export mode: scrape, export_csv, export_rss"
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode"
    ),
    timeout: int = typer.Option(
        30,
        "--timeout",
        help="Page timeout in seconds"
    ),
    max_retries: int = typer.Option(
        3,
        "--max-retries", 
        help="Maximum number of retries for failed operations"
    ),
    lang: Optional[str] = typer.Option(
        None,
        "--lang",
        help="Language setting (e.g., 'en-US', 'ja-JP')"
    ),
    proxy: Optional[str] = typer.Option(
        None,
        "--proxy",
        help="Proxy URL (e.g., 'http://proxy:8080')"
    ),
    out: Optional[str] = typer.Option(
        None,
        "--out",
        help="Output file path (default: auto-generated)"
    ),
    format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json, csv, parquet"
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    ),
    log_file: Optional[str] = typer.Option(
        None,
        "--log-file",
        help="Log file path (default: logs only to stdout)"
    )
):
    """
    Scrape Google Trends "Trending now" page with specified filters.
    
    Examples:
    
      # Default: US, past 24 hours, all categories, by relevance
      python trends_trending_now.py
      
      # UK, past 7 days, limit to 50 results
      python trends_trending_now.py --geo="United Kingdom" --time-window=past_7_days --limit=50
      
      # Sports category, active only, sorted by search volume, export as CSV
      python trends_trending_now.py --category=sports --active-only --sort=search_volume --export-mode=export_csv
      
      # Debug mode with headed browser and parquet output
      python trends_trending_now.py --no-headless --format=parquet --log-level=DEBUG
    """
    
    # Setup logging
    setup_logging(log_level, log_file)
    
    # Ensure output directories exist
    ensure_directories()
    
    # Convert string parameters to enums
    try:
        time_window_enum = TimeWindow(time_window)
        category_enum = Category(category)
        sort_enum = SortBy(sort)
        export_mode_enum = ExportMode(export_mode)
        format_enum = OutputFormat(format)
    except ValueError as e:
        print(f"❌ Invalid parameter value: {e}")
        return 1
    
    # Create fetch parameters
    params = FetchParams(
        geo=geo,
        time_window=time_window_enum,
        category=category_enum,
        active_only=active_only,
        sort=sort_enum,
        limit=limit,
        expand_breakdown=expand_breakdown,
        export_mode=export_mode_enum,
        headless=headless,
        timeout=timeout,
        max_retries=max_retries,
        lang=lang,
        proxy=proxy,
        out=out,
        format=format_enum
    )
    
    # Run the scraper
    try:
        print(f"Starting Google Trends scraper...")
        print(f"Target: {geo}, {time_window_enum.to_display_text()}")
        print(f"Filters: {category_enum.to_display_text()}, {sort_enum.to_display_text()}")
        print(f"Mode: {'Headless' if headless else 'Headed'} browser\n")
        
        start_time = time.time()
        
        # Run scraping
        trends = asyncio.run(run_main_scraping(params))
        
        duration = time.time() - start_time
        
        # Export results
        if trends:
            output_path = params.get_output_path()
            exporter = DataExporter()
            
            success = exporter.export_data(trends, output_path, params.format)
            
            if success:
                # Print summary
                print_export_summary(
                    trends, 
                    output_path, 
                    params.model_dump(), 
                    duration
                )
                print(f"\n✅ Successfully exported {len(trends)} trends to {output_path}")
                return 0
            else:
                print(f"\n❌ Failed to export data")
                return 1
        else:
            print(f"\n⚠️  No trends found with the specified filters")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⚠️  Scraping interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        
        # Create error report
        error_report = ErrorReport(
            stage="main_execution",
            message=str(e),
            screenshot_path=None
        )
        
        # Save error report
        error_path = "./logs/error_report.json"
        try:
            with open(error_path, 'w') as f:
                f.write(error_report.model_dump_json(indent=2))
            print(f"Error report saved to: {error_path}")
        except:
            pass
            
        return 1


async def run_main_scraping(params: FetchParams) -> List[TrendItem]:
    """
    Main scraping function that can be called programmatically.
    
    Args:
        params: Fetch parameters
        
    Returns:
        List of TrendItem objects
    """
    return await run_scraper(params)


def run(params: FetchParams) -> List[TrendItem]:
    """
    Synchronous wrapper for programmatic usage.
    
    Args:
        params: Fetch parameters
        
    Returns:
        List of TrendItem objects
    """
    return asyncio.run(run_main_scraping(params))


if __name__ == "__main__":
    # Handle missing directories
    try:
        ensure_directories()
    except Exception as e:
        print(f"Error creating directories: {e}")
        sys.exit(1)
    
    # Run the CLI app
    try:
        app()
    except Exception as e:
        print(f"Critical error: {e}")
        sys.exit(1)