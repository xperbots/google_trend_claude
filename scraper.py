"""
Google Trends Trending Now scraper using Playwright.
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from models import (
    TrendItem, FetchParams, ErrorReport, TrendStatus, 
    TimeWindow, Category, SortBy, ExportMode
)
from utils import (
    retry_with_backoff, random_delay, take_screenshot, 
    handle_consent_dialog, parse_search_volume, 
    parse_relative_time, extract_more_count, 
    get_geo_code, DownloadHandler
)


logger = logging.getLogger(__name__)


class GoogleTrendsScraper:
    """Main scraper class for Google Trends Trending Now page."""
    
    def __init__(self, params: FetchParams):
        self.params = params
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.download_handler = DownloadHandler()
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start_browser()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_browser()
        
    async def start_browser(self):
        """Start browser with specified configuration."""
        try:
            playwright = await async_playwright().start()
            
            # Browser launch args
            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
            
            if self.params.proxy:
                # Playwright proxy format
                proxy = {"server": self.params.proxy}
            else:
                proxy = None
            
            self.browser = await playwright.chromium.launch(
                headless=self.params.headless,
                args=launch_args,
                proxy=proxy
            )
            
            # Create context with realistic settings
            user_agent = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36")
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=user_agent,
                locale=self.params.lang or 'en-US',
                timezone_id='America/New_York'
            )
            
            # Set extra headers
            await self.context.set_extra_http_headers({
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
            
            self.page = await self.context.new_page()
            
            logger.info("Browser started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
            
    async def close_browser(self):
        """Close browser and cleanup."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
            
    async def scrape_trends(self) -> List[TrendItem]:
        """
        Main method to scrape trending topics.
        
        Returns:
            List of TrendItem objects
        """
        try:
            if not self.page:
                raise RuntimeError("Browser not started")
            
            # Navigate to trending page
            await self._navigate_to_trending_page()
            
            # Handle consent dialog if present
            await handle_consent_dialog(self.page)
            
            # Apply filters
            await self._apply_filters()
            
            # Check if CSV export mode is requested
            if self.params.export_mode == ExportMode.EXPORT_CSV:
                return await self._export_csv_mode()
            elif self.params.export_mode == ExportMode.EXPORT_RSS:
                return await self._export_rss_mode()
            
            # Default DOM scraping mode
            trends = []
            page_index = 1
            
            while True:
                logger.info(f"Scraping page {page_index}")
                
                # Wait for trends to load
                await self._wait_for_trends_load()
                
                # Extract trends from current page
                page_trends = await self._extract_page_trends(page_index)
                trends.extend(page_trends)
                
                logger.info(f"Extracted {len(page_trends)} trends from page {page_index}")
                
                # Check if we should continue
                if (self.params.limit and len(trends) >= self.params.limit) or \
                   not await self._go_to_next_page():
                    break
                    
                page_index += 1
                await random_delay()
            
            # Limit results if specified
            if self.params.limit:
                trends = trends[:self.params.limit]
            
            logger.info(f"Total trends scraped: {len(trends)}")
            return trends
            
        except Exception as e:
            await take_screenshot(self.page, "scraping_error")
            logger.error(f"Error scraping trends: {e}")
            raise
            
    async def _export_csv_mode(self) -> List[TrendItem]:
        """Handle CSV export mode."""
        try:
            logger.info("Using CSV export mode")
            
            # Look for Export button
            export_button = self.page.get_by_text("Export")
            if not await export_button.is_visible():
                logger.warning("Export button not found, falling back to DOM scraping")
                return await self._fallback_to_dom_scraping()
            
            await export_button.click()
            await random_delay()
            
            # Look for CSV download option
            csv_option = self.page.get_by_text("Download CSV")
            if not await csv_option.is_visible():
                logger.warning("CSV download option not found, falling back to DOM scraping")
                return await self._fallback_to_dom_scraping()
            
            # Download CSV
            csv_path = await self.download_handler.wait_for_download(
                self.page,
                lambda: csv_option.click(),
                timeout=30000
            )
            
            if not csv_path:
                logger.warning("CSV download failed, falling back to DOM scraping")
                return await self._fallback_to_dom_scraping()
            
            # Parse CSV and convert to TrendItems
            from exporter import map_csv_to_trends
            trends = map_csv_to_trends(csv_path, self.params.model_dump())
            
            logger.info(f"Successfully imported {len(trends)} trends from CSV")
            return trends
            
        except Exception as e:
            logger.error(f"CSV export mode failed: {e}")
            logger.info("Falling back to DOM scraping")
            return await self._fallback_to_dom_scraping()
            
    async def _export_rss_mode(self) -> List[TrendItem]:
        """Handle RSS export mode."""
        try:
            logger.info("Using RSS export mode")
            
            # Look for Export button
            export_button = self.page.get_by_text("Export")
            if not await export_button.is_visible():
                logger.warning("Export button not found, falling back to DOM scraping")
                return await self._fallback_to_dom_scraping()
            
            await export_button.click()
            await random_delay()
            
            # Look for RSS option
            rss_option = self.page.get_by_text("RSS")
            if not await rss_option.is_visible():
                logger.warning("RSS option not found, falling back to DOM scraping")
                return await self._fallback_to_dom_scraping()
            
            # Get RSS URL
            rss_url = await rss_option.get_attribute("href")
            if not rss_url:
                logger.warning("RSS URL not found, falling back to DOM scraping")
                return await self._fallback_to_dom_scraping()
            
            # Fetch and parse RSS (would need additional implementation)
            logger.warning("RSS parsing not fully implemented, falling back to DOM scraping")
            return await self._fallback_to_dom_scraping()
            
        except Exception as e:
            logger.error(f"RSS export mode failed: {e}")
            logger.info("Falling back to DOM scraping")
            return await self._fallback_to_dom_scraping()
            
    async def _fallback_to_dom_scraping(self) -> List[TrendItem]:
        """Fallback to DOM scraping when export modes fail."""
        logger.info("Using DOM scraping fallback")
        
        # Reset to scrape mode and re-run
        original_mode = self.params.export_mode
        self.params.export_mode = ExportMode.SCRAPE
        
        try:
            # Navigate back to trending page to reset state
            await self._navigate_to_trending_page()
            await self._apply_filters()
            
            # Run DOM scraping
            trends = []
            page_index = 1
            
            while True:
                await self._wait_for_trends_load()
                page_trends = await self._extract_page_trends(page_index)
                trends.extend(page_trends)
                
                if (self.params.limit and len(trends) >= self.params.limit) or \
                   not await self._go_to_next_page():
                    break
                    
                page_index += 1
                await random_delay()
            
            if self.params.limit:
                trends = trends[:self.params.limit]
                
            return trends
            
        finally:
            # Restore original mode
            self.params.export_mode = original_mode
            
    async def _navigate_to_trending_page(self):
        """Navigate to Google Trends trending page."""
        url = "https://trends.google.com/trending"
        
        await retry_with_backoff(
            self.page.goto,
            max_retries=self.params.max_retries,
            url=url,
            wait_until="networkidle",
            timeout=self.params.timeout * 1000
        )
        
        logger.info(f"Navigated to: {url}")
        await random_delay()
        
    async def _apply_filters(self):
        """Apply all specified filters to the page."""
        try:
            # Wait for trending data to be available - look for table content
            await self.page.wait_for_selector(
                'tr, table',
                timeout=15000
            )
            await random_delay(2000, 3000)  # Give page time to fully load
            
            # Check if we need to change filters from defaults
            needs_filter_changes = (
                self.params.geo != "United States" or
                self.params.time_window.value != "past_24_hours" or
                self.params.category.value != "all" or
                self.params.active_only or
                self.params.sort.value != "relevance"
            )
            
            if needs_filter_changes:
                logger.info("Applying custom filters...")
                
                # Apply location filter
                if self.params.geo != "United States":
                    await self._set_location()
                
                # Apply time window filter  
                if self.params.time_window.value != "past_24_hours":
                    await self._set_time_window()
                
                # Apply category filter
                if self.params.category.value != "all":
                    await self._set_category()
                
                # Apply trend status filter (active only)
                if self.params.active_only:
                    await self._set_active_only()
                
                # Apply sort filter
                if self.params.sort.value != "relevance":
                    await self._set_sort()
                
                # Wait for results to update
                await random_delay(1000, 2000)
            else:
                logger.info("Using default filters, no changes needed")
            
            logger.info("Filters applied successfully")
            
        except Exception as e:
            await take_screenshot(self.page, "filter_error")
            logger.error(f"Error applying filters: {e}")
            raise
            
    async def _set_location(self):
        """Set geographic location filter."""
        try:
            # Click on location selector
            location_button = self.page.get_by_text("Select location")
            await location_button.click()
            await random_delay()
            
            # Search for location
            search_box = self.page.locator('input[type="text"]').first
            await search_box.fill(get_geo_code(self.params.geo))
            await random_delay()
            
            # Click on matching result
            location_option = self.page.get_by_text(self.params.geo).first
            await location_option.click()
            await random_delay()
            
            logger.info(f"Set location to: {self.params.geo}")
            
        except Exception as e:
            logger.warning(f"Could not set location to {self.params.geo}: {e}")
            
    async def _set_time_window(self):
        """Set time window filter."""
        try:
            # Click on time window selector
            time_button = self.page.get_by_text("Past 24 hours")
            await time_button.click()
            await random_delay()
            
            # Click on desired time window
            target_text = self.params.time_window.to_display_text()
            time_option = self.page.get_by_text(target_text)
            await time_option.click()
            await random_delay()
            
            logger.info(f"Set time window to: {target_text}")
            
        except Exception as e:
            logger.warning(f"Could not set time window: {e}")
            
    async def _set_category(self):
        """Set category filter."""
        try:
            # Click on category selector
            category_button = self.page.get_by_text("All categories")
            await category_button.click()
            await random_delay()
            
            # Click on desired category
            if self.params.category != Category.ALL:
                target_text = self.params.category.to_display_text()
                category_option = self.page.get_by_text(target_text)
                await category_option.click()
                await random_delay()
            
            logger.info(f"Set category to: {self.params.category.to_display_text()}")
            
        except Exception as e:
            logger.warning(f"Could not set category: {e}")
            
    async def _set_active_only(self):
        """Set active only filter."""
        try:
            # Click on trend status selector
            status_button = self.page.get_by_text("All trends")
            await status_button.click()
            await random_delay()
            
            # Check "Show active trends only"
            active_checkbox = self.page.get_by_text("Show active trends only")
            await active_checkbox.click()
            await random_delay()
            
            logger.info("Set to show active trends only")
            
        except Exception as e:
            logger.warning(f"Could not set active only filter: {e}")
            
    async def _set_sort(self):
        """Set sort order."""
        try:
            # Click on sort selector
            sort_button = self.page.get_by_text("By relevance")
            await sort_button.click()
            await random_delay()
            
            # Click on desired sort option
            target_text = self.params.sort.to_display_text()
            sort_option = self.page.get_by_text(target_text)
            await sort_option.click()
            await random_delay()
            
            logger.info(f"Set sort to: {target_text}")
            
        except Exception as e:
            logger.warning(f"Could not set sort order: {e}")
            
    async def _wait_for_trends_load(self):
        """Wait for trends list to load."""
        try:
            # Wait for trend items to be visible - look for the actual trending topics
            await self.page.wait_for_selector(
                'text="Search volume"',  # This appears in the header
                timeout=15000,
                state="visible"
            )
            await random_delay()
        except Exception as e:
            logger.warning(f"Timeout waiting for trends to load: {e}")
            
    async def _extract_page_trends(self, page_index: int) -> List[TrendItem]:
        """Extract trends from the current page."""
        trends = []
        
        try:
            # Wait a bit more for data to stabilize
            await random_delay(2000, 3000)
            
            # Look for trend rows - they appear to be in a table-like structure
            # Based on screenshot, trending topics are in rows under the "Trends" section
            trend_elements = await self.page.query_selector_all('tr')
            
            logger.info(f"Found {len(trend_elements)} potential trend elements")
            
            for i, element in enumerate(trend_elements):
                try:
                    # Get text content for debugging
                    text_content = await element.inner_text() if element else ""
                    logger.debug(f"Element {i}: {text_content[:100]}...")  # Debug log
                    
                    # Skip header rows or empty rows
                    if not text_content or "Trends" in text_content or "Search volume" in text_content:
                        continue
                    
                    # Skip very short content that's likely not a trend
                    if len(text_content.strip()) < 10:
                        continue
                        
                    trend = await self._extract_single_trend(element, page_index)
                    if trend:
                        trends.append(trend)
                        logger.info(f"Extracted trend: {trend.title}")
                        
                        # Expand breakdown if requested
                        if self.params.expand_breakdown:
                            await self._expand_trend_breakdown(element, trend)
                            
                except Exception as e:
                    logger.warning(f"Error extracting trend {i}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting trends from page: {e}")
            
        return trends
        
    async def _extract_single_trend(
        self, 
        item_element, 
        page_index: int
    ) -> Optional[TrendItem]:
        """Extract data from a single trend item."""
        try:
            # Get all text content from the row to parse
            row_text = await item_element.inner_text()
            if not row_text or len(row_text.strip()) < 3:
                return None
            
            # Parse the text content directly since it's well-structured
            lines = [line.strip() for line in row_text.split('\n') if line.strip()]
            
            # Need at least a few lines for a valid trend
            if len(lines) < 4:
                return None
                
            # Extract title (usually first meaningful line)
            title = lines[0] if lines else "Unknown"
            
            # Find search volume (looks like "2M+", "100K+", etc.)
            volume_text = "N/A"
            for line in lines:
                if '+' in line and any(char.isdigit() for char in line):
                    if 'K+' in line or 'M+' in line or any(x in line for x in ['1,000%', '400%', '500%']):
                        if not any(x in line for x in ['1,000%', '400%', '500%', '800%', '700%', '900%']):
                            volume_text = line
                            break
            
            # Find time (looks like "X hours ago", "X minutes ago")
            relative_time = "Unknown"
            for line in lines:
                if 'ago' in line.lower():
                    relative_time = line
                    break
            
            # Extract status from the row text
            status = TrendStatus.ACTIVE  # Default, can be refined based on actual data
            if "Active" in row_text:
                status = TrendStatus.ACTIVE
            elif "Lasted" in row_text:
                status = TrendStatus.LASTED
            
            # Extract related queries - they appear after the main data
            related_queries = []
            more_count = 0
            
            # Look for related query terms (usually appear after time)
            collecting_related = False
            for line in lines:
                # Skip system text and main data
                if any(skip in line for skip in ['arrow_upward', '1,000%', 'trending_up', 'Active', 'ago']):
                    collecting_related = True
                    continue
                
                if collecting_related and line and len(line) > 1:
                    # Check if it's a "+ N more" line
                    if '+ ' in line and ('more' in line or line.endswith('...')):
                        more_count = extract_more_count(line)
                    else:
                        # It's likely a related query
                        related_queries.append(line.strip())
            
            # Clean up related queries (remove very short ones and duplicates)
            related_queries = [q for q in related_queries if len(q) > 2]
            related_queries = list(dict.fromkeys(related_queries))  # Remove duplicates
            
            # Limit to reasonable number
            related_queries = related_queries[:5]
            
            # Extract sparkline path if available
            sparkline_path = None
            svg_element = await item_element.query_selector('svg path')
            if svg_element:
                sparkline_path = await svg_element.get_attribute('d')
            
            # Skip if we don't have essential data
            if not title or title == "Unknown" or len(title) < 2:
                return None
            
            # Create TrendItem
            trend = TrendItem(
                title=title,
                search_volume_text=volume_text,
                search_volume_bucket=parse_search_volume(volume_text),
                started_relative=relative_time,
                started_iso=parse_relative_time(relative_time).isoformat() if parse_relative_time(relative_time) else None,
                status=status,
                top_related=related_queries,
                more_related_count=more_count,
                sparkline_svg_path=sparkline_path,
                page_index=page_index,
                geo=self.params.geo,
                time_window=self.params.time_window,
                category=self.params.category,
                active_only=self.params.active_only,
                sort=self.params.sort,
                retrieved_at=datetime.now()
            )
            
            return trend
            
        except Exception as e:
            logger.warning(f"Error extracting single trend: {e}")
            return None
            
    async def _expand_trend_breakdown(self, item_element, trend: TrendItem):
        """Expand trend breakdown to get more related queries."""
        try:
            # Look for expand button/link
            expand_element = await item_element.query_selector('span:has-text("more")')
            if expand_element:
                await expand_element.click()
                await random_delay()
                
                # Extract additional related queries from expanded view
                # This would need to be implemented based on actual page structure
                # when the breakdown is expanded
                
                # Close the expanded view
                close_button = await self.page.query_selector('[aria-label="Close"]')
                if close_button:
                    await close_button.click()
                    await random_delay()
                    
        except Exception as e:
            logger.warning(f"Error expanding trend breakdown: {e}")
            
    async def _go_to_next_page(self) -> bool:
        """Go to next page if available."""
        try:
            # Look for next page button
            next_button = self.page.get_by_role("button", name="arrow_forward_ios")
            
            if await next_button.is_visible() and await next_button.is_enabled():
                await next_button.click()
                await random_delay(500, 1000)
                
                # Wait for new content to load
                await self._wait_for_trends_load()
                return True
            else:
                logger.info("No more pages available")
                return False
                
        except Exception as e:
            logger.warning(f"Error navigating to next page: {e}")
            return False


async def run_scraper(params: FetchParams) -> List[TrendItem]:
    """
    Main function to run the scraper.
    
    Args:
        params: Scraping parameters
        
    Returns:
        List of scraped trends
    """
    async with GoogleTrendsScraper(params) as scraper:
        return await scraper.scrape_trends()