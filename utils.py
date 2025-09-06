"""
Utility functions for Google Trends Trending Now scraper.
"""

import asyncio
import logging
import os
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar, Union

from playwright.async_api import Page


logger = logging.getLogger(__name__)

T = TypeVar("T")


def setup_logging(level: str = "INFO", log_file: Optional[str] = None):
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=log_format,
        handlers=handlers
    )


async def retry_with_backoff(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    *args,
    **kwargs
) -> T:
    """
    Retry a function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        Result of the function
        
    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except exceptions as e:
            last_exception = e
            if attempt < max_retries:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay *= backoff_factor
            else:
                logger.error(f"All {max_retries + 1} attempts failed.")
                
    raise last_exception


def parse_search_volume(volume_text: str) -> str:
    """
    Parse search volume text into normalized bucket.
    
    Args:
        volume_text: Raw search volume text (e.g., "2M+", "500K+", "10K+")
        
    Returns:
        Normalized bucket string (e.g., "2M_plus", "500K_plus", "10K_plus")
    """
    # Remove spaces and convert to uppercase
    cleaned = volume_text.strip().upper()
    
    # Replace + with _plus
    bucket = cleaned.replace("+", "_PLUS")
    
    # Replace special characters with underscores
    bucket = re.sub(r"[^A-Z0-9_]", "_", bucket)
    
    # Remove multiple underscores
    bucket = re.sub(r"_+", "_", bucket)
    
    # Remove trailing underscores
    bucket = bucket.strip("_")
    
    return bucket.lower()


def parse_relative_time(relative_time: str) -> Optional[datetime]:
    """
    Parse relative time string to datetime.
    
    Args:
        relative_time: Relative time string (e.g., "9 hours ago", "2 days ago")
        
    Returns:
        Estimated datetime or None if parsing fails
    """
    try:
        # Normalize the input
        relative_time = relative_time.lower().strip()
        
        # Current time
        now = datetime.now()
        
        # Parse patterns like "X hours/minutes/days ago"
        patterns = [
            (r"(\d+)\s*minutes?\s*ago", lambda x: now - timedelta(minutes=int(x))),
            (r"(\d+)\s*hours?\s*ago", lambda x: now - timedelta(hours=int(x))),
            (r"(\d+)\s*days?\s*ago", lambda x: now - timedelta(days=int(x))),
            (r"(\d+)\s*weeks?\s*ago", lambda x: now - timedelta(weeks=int(x))),
        ]
        
        for pattern, calc_func in patterns:
            match = re.search(pattern, relative_time)
            if match:
                return calc_func(match.group(1))
        
        # Handle "just now" or similar
        if "just now" in relative_time or "now" in relative_time:
            return now
            
        logger.warning(f"Could not parse relative time: {relative_time}")
        return None
        
    except Exception as e:
        logger.error(f"Error parsing relative time '{relative_time}': {e}")
        return None


def extract_more_count(text: str) -> int:
    """
    Extract count from "+ N more" text.
    
    Args:
        text: Text containing "+ N more" pattern
        
    Returns:
        Extracted count or 0 if not found
    """
    try:
        # Look for patterns like "+ 285 more", "+285 more", etc.
        match = re.search(r"\+\s*(\d+)\s*more", text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 0
    except Exception as e:
        logger.error(f"Error extracting more count from '{text}': {e}")
        return 0


async def random_delay(min_ms: int = 200, max_ms: int = 600):
    """
    Add random delay between actions.
    
    Args:
        min_ms: Minimum delay in milliseconds
        max_ms: Maximum delay in milliseconds
    """
    delay = random.randint(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)


async def take_screenshot(
    page: Page, 
    name: str = "error",
    directory: str = "./logs"
) -> str:
    """
    Take a screenshot of the current page.
    
    Args:
        page: Playwright page object
        name: Screenshot name prefix
        directory: Directory to save screenshots
        
    Returns:
        Path to saved screenshot
    """
    try:
        os.makedirs(directory, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = os.path.join(directory, filename)
        
        await page.screenshot(path=filepath, full_page=True)
        logger.info(f"Screenshot saved: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")
        return ""


async def handle_consent_dialog(page: Page, timeout: int = 5000):
    """
    Handle Google consent/privacy dialog if present.
    
    Args:
        page: Playwright page object
        timeout: Timeout in milliseconds
    """
    try:
        # Common consent button texts
        consent_texts = [
            "I agree",
            "Accept all",
            "Agree",
            "Accept",
            "Got it",
            "Continue"
        ]
        
        for text in consent_texts:
            try:
                consent_button = page.get_by_role("button", name=text)
                if await consent_button.is_visible(timeout=timeout):
                    logger.info(f"Found consent button: {text}")
                    await consent_button.click()
                    await random_delay()
                    return
            except:
                continue
                
    except Exception as e:
        logger.debug(f"No consent dialog found or error handling it: {e}")


def ensure_directories():
    """Ensure required directories exist."""
    directories = ["./out", "./logs"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


def get_geo_code(location: str) -> str:
    """
    Get standardized geo code from location name.
    
    Args:
        location: Location name (e.g., "United States", "US")
        
    Returns:
        Standardized location name or code
    """
    # Common mappings
    geo_mappings = {
        "us": "United States",
        "usa": "United States",
        "uk": "United Kingdom",
        "gb": "United Kingdom",
        "jp": "Japan",
        "de": "Germany",
        "fr": "France",
        "ca": "Canada",
        "au": "Australia",
        "in": "India",
        "br": "Brazil",
        "mx": "Mexico",
        "es": "Spain",
        "it": "Italy",
        "kr": "South Korea",
        "nl": "Netherlands",
        "se": "Sweden",
        "no": "Norway",
        "dk": "Denmark",
        "fi": "Finland",
    }
    
    # Check if it's a known code
    location_lower = location.lower()
    if location_lower in geo_mappings:
        return geo_mappings[location_lower]
    
    # Otherwise return as-is (assume it's already a full name)
    return location


class DownloadHandler:
    """Handle file downloads from the browser."""
    
    def __init__(self, download_dir: str = "./downloads"):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        
    async def wait_for_download(
        self,
        page: Page,
        action: Callable,
        timeout: int = 30000
    ) -> Optional[str]:
        """
        Wait for a download to complete after performing an action.
        
        Args:
            page: Playwright page object
            action: Async function that triggers the download
            timeout: Timeout in milliseconds
            
        Returns:
            Path to downloaded file or None
        """
        try:
            # Start waiting for download before clicking
            async with page.expect_download(timeout=timeout) as download_info:
                await action()
                
            download = await download_info.value
            
            # Save the download
            filename = download.suggested_filename
            filepath = os.path.join(self.download_dir, filename)
            await download.save_as(filepath)
            
            logger.info(f"Downloaded file: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None