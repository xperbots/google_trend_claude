"""
Export functionality for Google Trends Trending Now data.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from models import TrendItem, OutputFormat


logger = logging.getLogger(__name__)


class DataExporter:
    """Handle exporting trend data to various formats."""
    
    def __init__(self):
        pass
    
    def export_data(
        self,
        trends: List[TrendItem],
        output_path: str,
        format: OutputFormat
    ) -> bool:
        """
        Export trend data to specified format.
        
        Args:
            trends: List of trend items to export
            output_path: Output file path
            format: Output format
            
        Returns:
            True if export successful, False otherwise
        """
        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            
            if format == OutputFormat.JSON:
                return self._export_json(trends, output_path)
            elif format == OutputFormat.CSV:
                return self._export_csv(trends, output_path)
            elif format == OutputFormat.PARQUET:
                return self._export_parquet(trends, output_path)
            else:
                logger.error(f"Unsupported export format: {format}")
                return False
                
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return False
    
    def _export_json(self, trends: List[TrendItem], output_path: str) -> bool:
        """Export to JSON format."""
        try:
            # Convert to dict format
            data = [trend.model_dump() for trend in trends]
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"Exported {len(trends)} trends to JSON: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return False
    
    def _export_csv(self, trends: List[TrendItem], output_path: str) -> bool:
        """Export to CSV format."""
        try:
            # Convert to DataFrame
            df = self._trends_to_dataframe(trends)
            
            # Export to CSV
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            logger.info(f"Exported {len(trends)} trends to CSV: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False
    
    def _export_parquet(self, trends: List[TrendItem], output_path: str) -> bool:
        """Export to Parquet format."""
        try:
            # Convert to DataFrame
            df = self._trends_to_dataframe(trends)
            
            # Convert to PyArrow table and write Parquet
            table = pa.Table.from_pandas(df)
            pq.write_table(table, output_path)
            
            logger.info(f"Exported {len(trends)} trends to Parquet: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to Parquet: {e}")
            return False
    
    def _trends_to_dataframe(self, trends: List[TrendItem]) -> pd.DataFrame:
        """Convert trends to pandas DataFrame."""
        data = []
        
        for trend in trends:
            row = {
                'title': trend.title,
                'search_volume_text': trend.search_volume_text,
                'search_volume_bucket': trend.search_volume_bucket,
                'started_relative': trend.started_relative,
                'started_iso': trend.started_iso,
                'status': trend.status.value,
                'top_related': ';'.join(trend.top_related),  # Join list as string
                'more_related_count': trend.more_related_count,
                'sparkline_svg_path': trend.sparkline_svg_path,
                'page_index': trend.page_index,
                'geo': trend.geo,
                'time_window': trend.time_window.value,
                'category': trend.category.value,
                'active_only': trend.active_only,
                'sort': trend.sort.value,
                'retrieved_at': trend.retrieved_at.isoformat(),
                'source': trend.source
            }
            data.append(row)
        
        return pd.DataFrame(data)


def map_csv_to_trends(csv_path: str, params: Dict[str, Any]) -> List[TrendItem]:
    """
    Map official CSV export to TrendItem objects.
    
    Args:
        csv_path: Path to downloaded CSV file
        params: Fetch parameters for context
        
    Returns:
        List of TrendItem objects
    """
    try:
        df = pd.read_csv(csv_path)
        trends = []
        
        # CSV column mapping (may vary based on Google's export format)
        # This is a best-effort mapping based on typical CSV structure
        for index, row in df.iterrows():
            try:
                # Extract basic information (adjust based on actual CSV format)
                title = str(row.get('Title', row.get('Query', '')))
                search_volume_text = str(row.get('Search Volume', row.get('Searches', 'N/A')))
                
                # Create trend item with available data
                trend = TrendItem(
                    title=title,
                    search_volume_text=search_volume_text,
                    search_volume_bucket=_normalize_search_volume(search_volume_text),
                    started_relative=str(row.get('Started', 'Unknown')),
                    started_iso=None,  # Usually not in CSV
                    status=_parse_status(str(row.get('Status', 'Active'))),
                    top_related=_parse_related_queries(str(row.get('Related', ''))),
                    more_related_count=0,  # Usually not in CSV
                    sparkline_svg_path=None,  # Not in CSV
                    page_index=1,
                    geo=params.get('geo', 'Unknown'),
                    time_window=params.get('time_window', 'past_24_hours'),
                    category=params.get('category', 'all'),
                    active_only=params.get('active_only', False),
                    sort=params.get('sort', 'relevance'),
                    source='export_csv'
                )
                
                trends.append(trend)
                
            except Exception as e:
                logger.warning(f"Error processing CSV row {index}: {e}")
                continue
        
        logger.info(f"Mapped {len(trends)} trends from CSV: {csv_path}")
        return trends
        
    except Exception as e:
        logger.error(f"Error mapping CSV to trends: {e}")
        return []


def _normalize_search_volume(volume_text: str) -> str:
    """Normalize search volume text to bucket format."""
    if not volume_text or volume_text == 'N/A':
        return 'unknown'
    
    # Simple normalization
    normalized = volume_text.lower().replace('+', '_plus').replace(' ', '_')
    return normalized


def _parse_status(status_text: str) -> str:
    """Parse status text to standard format."""
    status_lower = status_text.lower().strip()
    if 'active' in status_lower:
        return 'Active'
    elif 'lasted' in status_lower:
        return 'Lasted'
    else:
        return 'Active'  # Default


def _parse_related_queries(related_text: str) -> List[str]:
    """Parse related queries from text."""
    if not related_text or related_text.lower() in ['nan', 'none', '']:
        return []
    
    # Split by common separators
    queries = []
    for separator in [';', ',', '|']:
        if separator in related_text:
            queries = [q.strip() for q in related_text.split(separator)]
            break
    
    if not queries:
        queries = [related_text.strip()]
    
    return [q for q in queries if q and q.lower() != 'nan']


def print_export_summary(
    trends: List[TrendItem],
    output_path: str,
    params: Dict[str, Any],
    duration: float
):
    """
    Print export summary to stdout.
    
    Args:
        trends: Exported trends
        output_path: Output file path
        params: Fetch parameters
        duration: Processing duration in seconds
    """
    print(f"\n=== Export Summary ===")
    print(f"Total trends exported: {len(trends)}")
    print(f"Output file: {output_path}")
    print(f"File size: {_format_file_size(output_path)}")
    print(f"Processing time: {duration:.2f}s")
    print(f"\nFilters applied:")
    print(f"  - Location: {params.get('geo', 'N/A')}")
    print(f"  - Time window: {params.get('time_window', 'N/A')}")
    print(f"  - Category: {params.get('category', 'N/A')}")
    print(f"  - Active only: {params.get('active_only', False)}")
    print(f"  - Sort by: {params.get('sort', 'N/A')}")
    print(f"  - Export mode: {params.get('export_mode', 'N/A')}")
    
    if trends:
        print(f"\nSample trends:")
        for i, trend in enumerate(trends[:3]):
            print(f"  {i+1}. {trend.title} ({trend.search_volume_text}, {trend.status})")


def _format_file_size(filepath: str) -> str:
    """Format file size in human readable format."""
    try:
        size = os.path.getsize(filepath)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    except:
        return "Unknown"