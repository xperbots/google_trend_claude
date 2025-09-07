"""
Pydantic models and enums for Google Trends Trending Now scraper.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class TimeWindow(str, Enum):
    """Time window options for trending searches."""
    PAST_4_HOURS = "past_4_hours"
    PAST_24_HOURS = "past_24_hours"
    PAST_48_HOURS = "past_48_hours"
    PAST_7_DAYS = "past_7_days"
    
    def to_display_text(self) -> str:
        """Convert to display text shown on the page."""
        mapping = {
            self.PAST_4_HOURS: "Past 4 hours",
            self.PAST_24_HOURS: "Past 24 hours",
            self.PAST_48_HOURS: "Past 48 hours",
            self.PAST_7_DAYS: "Past 7 days"
        }
        return mapping[self]


class Category(str, Enum):
    """Category options for trending searches."""
    ALL = "all"
    AUTOS_AND_VEHICLES = "autos_and_vehicles"
    BEAUTY_AND_FASHION = "beauty_and_fashion"
    BUSINESS_AND_FINANCE = "business_and_finance"
    CLIMATE = "climate"
    ENTERTAINMENT = "entertainment"
    FOOD_AND_DRINK = "food_and_drink"
    GAMES = "games"
    HEALTH = "health"
    HOBBIES_AND_LEISURE = "hobbies_and_leisure"
    JOBS_AND_EDUCATION = "jobs_and_education"
    LAW_AND_GOVERNMENT = "law_and_government"
    OTHER = "other"
    PETS_AND_ANIMALS = "pets_and_animals"
    POLITICS = "politics"
    SCIENCE = "science"
    SHOPPING = "shopping"
    SPORTS = "sports"
    TECHNOLOGY = "technology"
    TRAVEL_AND_TRANSPORTATION = "travel_and_transportation"
    
    def to_display_text(self) -> str:
        """Convert to display text shown on the page."""
        if self == self.ALL:
            return "All categories"
        # Convert snake_case to Title Case
        return self.value.replace("_", " ").title()


class SortBy(str, Enum):
    """Sort options for trending searches."""
    TITLE = "title"
    SEARCH_VOLUME = "search_volume"
    RECENCY = "recency"
    RELEVANCE = "relevance"
    
    def to_display_text(self) -> str:
        """Convert to display text shown on the page."""
        mapping = {
            self.TITLE: "By title",
            self.SEARCH_VOLUME: "By search volume",
            self.RECENCY: "By recency",
            self.RELEVANCE: "By relevance"
        }
        return mapping[self]


class ExportMode(str, Enum):
    """Export mode options."""
    SCRAPE = "scrape"
    EXPORT_CSV = "export_csv"
    EXPORT_RSS = "export_rss"


class OutputFormat(str, Enum):
    """Output file format options."""
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"


class TrendStatus(str, Enum):
    """Trend status options."""
    ACTIVE = "Active"
    LASTED = "Lasted"


class TranslationProvider(str, Enum):
    """Translation provider options."""
    FREE = "free"
    GPT_NANO = "gpt-nano"


class TrendItem(BaseModel):
    """Model for a single trending search item."""
    title: str = Field(description="The trending search title/keyword")
    search_volume_text: str = Field(description="Search volume as displayed (e.g., '2M+')")
    search_volume_bucket: str = Field(description="Normalized search volume bucket (e.g., '2M_plus')")
    started_relative: str = Field(description="When the trend started in relative time (e.g., '9 hours ago')")
    started_iso: Optional[str] = Field(None, description="When the trend started in ISO format")
    status: TrendStatus = Field(description="Trend status (Active or Lasted)")
    top_related: List[str] = Field(default_factory=list, description="Top related search queries")
    more_related_count: int = Field(0, description="Number of additional related queries (from '+ N more')")
    sparkline_svg_path: Optional[str] = Field(None, description="SVG path data for trend sparkline")
    page_index: int = Field(1, description="Page number where this trend was found")
    
    # Context fields
    geo: str = Field(description="Geographic location")
    time_window: TimeWindow = Field(description="Time window setting")
    category: Category = Field(description="Category filter")
    active_only: bool = Field(False, description="Whether only active trends were shown")
    sort: SortBy = Field(description="Sort order")
    retrieved_at: datetime = Field(default_factory=datetime.now, description="When the data was retrieved")
    
    # Optional source field for export mode
    source: Optional[str] = Field("scrape", description="Data source (scrape, export_csv, export_rss)")
    
    # Translation fields
    title_translated: Optional[str] = Field(None, description="Translated title")
    related_translated: Optional[List[str]] = Field(None, description="Translated related queries")
    
    # Trend breakdown fields (rich context for better translation)
    trend_category: Optional[str] = Field(None, description="Actual category extracted from Google Trends page")
    breakdown_description: Optional[str] = Field(None, description="Google's explanation of what this trend represents")
    query_variants: Optional[List[str]] = Field(None, description="Related search query variants from breakdown")
    trend_context: Optional[str] = Field(None, description="Rich context about the trend's meaning and background")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class FetchParams(BaseModel):
    """Parameters for fetching trending searches."""
    geo: str = Field("Vietnam", description="Geographic location")
    time_window: TimeWindow = Field(TimeWindow.PAST_48_HOURS, description="Time window")
    category: Category = Field(Category.GAMES, description="Category filter")
    active_only: bool = Field(False, description="Show only active trends")
    sort: SortBy = Field(SortBy.SEARCH_VOLUME, description="Sort order")
    
    # Scraping control
    limit: Optional[int] = Field(None, description="Maximum number of trends to fetch")
    expand_breakdown: bool = Field(False, description="Expand trend breakdown for more related queries")
    export_mode: ExportMode = Field(ExportMode.SCRAPE, description="Export mode")
    headless: bool = Field(True, description="Run browser in headless mode")
    timeout: int = Field(30, description="Page timeout in seconds")
    max_retries: int = Field(3, description="Maximum number of retries")
    lang: Optional[str] = Field(None, description="Language setting (e.g., 'en-US')")
    proxy: Optional[str] = Field(None, description="Proxy URL")
    
    # Output
    out: Optional[str] = Field(None, description="Output file path")
    format: OutputFormat = Field(OutputFormat.JSON, description="Output file format")
    
    # Translation
    translation_target: Optional[str] = Field(None, description="Target language for translation (e.g., 'zh' for Chinese)")
    translation_provider: TranslationProvider = Field(TranslationProvider.FREE, description="Translation provider")
    gpt_api_key: Optional[str] = Field(None, description="API key for GPT-5-nano (if using GPT provider)")
    
    def get_output_path(self) -> str:
        """Generate output file path if not specified."""
        if self.out:
            return self.out
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        geo_safe = self.geo.lower().replace(" ", "_")
        extension = self.format.value
        
        return f"./out/trending_{geo_safe}_{timestamp}.{extension}"


class ErrorReport(BaseModel):
    """Model for error reporting."""
    stage: str = Field(description="Stage where error occurred")
    message: str = Field(description="Error message")
    screenshot_path: Optional[str] = Field(None, description="Path to error screenshot")
    timestamp: datetime = Field(default_factory=datetime.now, description="When error occurred")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }