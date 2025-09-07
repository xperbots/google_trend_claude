#!/usr/bin/env python3
"""
Simple Google Trends scraper that outputs only Chinese topic names.
Fast and minimal - perfect for quick trend monitoring.
"""

import asyncio
import os
import sys
import time
from typing import List

import typer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models import FetchParams, TimeWindow, Category, SortBy, ExportMode, OutputFormat, TranslationProvider
from scraper import run_scraper
from utils import setup_logging, ensure_directories


def print_chinese_topics(trends: List, geo: str):
    """Print a clean list of Chinese topic names."""
    print(f"\n📋 热门话题 ({geo}):")
    print("=" * 60)
    
    for i, trend in enumerate(trends, 1):
        if hasattr(trend, 'title_translated') and trend.title_translated:
            # Show both original and translated text
            print(f"{i:2d}. {trend.title} → {trend.title_translated}")
        else:
            print(f"{i:2d}. {trend.title}")
    
    print(f"\n✅ 共找到 {len(trends)} 个热门话题")


async def get_trending_topics(geo: str, time_window: str = "past_24_hours", limit: int = 20) -> List:
    """Quick function to get trending topics."""
    
    # Convert parameters
    time_window_enum = TimeWindow(time_window)
    
    # Always use GPT if API key exists, otherwise free translation
    translation_provider = TranslationProvider.GPT_NANO if os.getenv("OPENAI_API_KEY") else TranslationProvider.FREE
    
    params = FetchParams(
        geo=geo,
        time_window=time_window_enum,
        category=Category.ALL,
        active_only=False,
        sort=SortBy.RELEVANCE,
        limit=limit,
        expand_breakdown=False,
        export_mode=ExportMode.SCRAPE,
        headless=True,
        timeout=30,
        max_retries=3,
        translation_target="zh",  # Always translate to Chinese
        translation_provider=translation_provider
    )
    
    return await run_scraper(params)


def main(
    geo: str = typer.Argument("Japan", help="Country/region for trending topics"),
    time_window: str = typer.Option(
        "past_24_hours", 
        "--time",
        help="Time window: past_4_hours, past_24_hours, past_48_hours, past_7_days"
    ),
    limit: int = typer.Option(20, "--limit", help="Number of topics to fetch"),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed progress")
):
    """
    快速获取Google热门话题的中文列表
    
    Examples:
    
      # Japanese trends
      python simple_trends.py Japan
      
      # Korean trends from past week
      python simple_trends.py "South Korea" --time=past_7_days
      
      # US trends, limit to 10
      python simple_trends.py "United States" --limit=10
    """
    
    if not verbose:
        # Suppress logs for clean output
        setup_logging("ERROR")
    else:
        setup_logging("INFO")
        print(f"🔍 正在获取 {geo} 的热门话题...")
    
    try:
        start_time = time.time()
        
        # Get trends
        trends = asyncio.run(get_trending_topics(geo, time_window, limit))
        
        duration = time.time() - start_time
        
        if trends:
            print_chinese_topics(trends, geo)
            
            if verbose:
                provider = "GPT-4o-mini" if os.getenv("OPENAI_API_KEY") else "Google翻译"
                print(f"\n⏱️  用时: {duration:.1f}秒 | 翻译: {provider}")
        else:
            print(f"⚠️  未找到 {geo} 的热门话题")
            return 1
            
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
        return 130
    except Exception as e:
        if verbose:
            print(f"❌ 错误: {e}")
        else:
            print("❌ 获取热门话题失败，请使用 --verbose 查看详情")
        return 1


if __name__ == "__main__":
    # Ensure directories exist
    try:
        ensure_directories()
    except:
        pass  # Ignore errors in simple mode
    
    # Run CLI
    typer.run(main)