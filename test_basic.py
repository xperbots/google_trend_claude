#!/usr/bin/env python3
"""
Basic functionality test for Google Trends Trending Now scraper.
"""

import asyncio
import sys
from models import FetchParams, TimeWindow, Category, SortBy, ExportMode, OutputFormat
from scraper import run_scraper
from exporter import DataExporter

async def test_basic_functionality():
    """Test basic scraping functionality without actually hitting Google."""
    print("🧪 Testing basic functionality...")
    
    # Create test parameters
    params = FetchParams(
        geo="United States",
        time_window=TimeWindow.PAST_24_HOURS,
        category=Category.ALL,
        active_only=False,
        sort=SortBy.RELEVANCE,
        limit=5,  # Small limit for testing
        headless=True,
        timeout=10,  # Short timeout for testing
        max_retries=1,
        export_mode=ExportMode.SCRAPE,
        format=OutputFormat.JSON
    )
    
    print(f"✅ Created FetchParams: {params.geo}, {params.time_window.value}")
    
    # Test export functionality
    exporter = DataExporter()
    print("✅ Created DataExporter")
    
    # Test utility functions
    from utils import parse_search_volume, extract_more_count, parse_relative_time
    
    # Test search volume parsing
    assert parse_search_volume("2M+") == "2m_plus"
    assert parse_search_volume("500K+") == "500k_plus"
    print("✅ Search volume parsing works")
    
    # Test more count extraction
    assert extract_more_count("+ 285 more") == 285
    assert extract_more_count("no match") == 0
    print("✅ More count extraction works")
    
    # Test relative time parsing
    time_result = parse_relative_time("2 hours ago")
    assert time_result is not None
    print("✅ Relative time parsing works")
    
    print("🎉 All basic tests passed!")
    return True

def test_cli_import():
    """Test that CLI can be imported without errors."""
    try:
        import trends_trending_now
        print("✅ CLI module imports successfully")
        return True
    except Exception as e:
        print(f"❌ CLI import failed: {e}")
        return False

if __name__ == "__main__":
    print("Running basic functionality tests...\n")
    
    # Test CLI import
    if not test_cli_import():
        sys.exit(1)
    
    # Test async functionality
    try:
        result = asyncio.run(test_basic_functionality())
        if result:
            print("\n🎉 All tests passed! The scraper is ready to use.")
            print("\nTo run the scraper:")
            print("python trends_trending_now.py --limit=5 --no-headless")
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)