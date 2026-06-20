"""
Time-series trend analysis over historical data.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import numpy as np

from linux_health_monitor.config import TREND_ANALYSIS_HOURS
from linux_health_monitor.models import TrendReport
from linux_health_monitor.storage.database import HealthMonitorDB

logger = logging.getLogger(__name__)


def analyze_trend(
    db: HealthMonitorDB,
    metric_name: str,
    hours: int = TREND_ANALYSIS_HOURS,
) -> Optional[TrendReport]:
    """
    Analyze trend of a metric over the specified time period.
    
    Calculates min, max, average, standard deviation and detects if the metric
    is trending upward using simple linear regression.
    
    Args:
        db: Database instance to query historical data.
        metric_name: Name of metric to analyze (e.g., 'cpu_percent', 'memory_percent').
        hours: Number of hours of historical data to analyze.
    
    Returns:
        TrendReport object with statistics, or None if insufficient data.
    """
    try:
        metric_data = db.get_metric_values(metric_name, hours=hours)
        
        if len(metric_data) < 2:
            logger.warning(f"Insufficient data for trend analysis of {metric_name}")
            return None
        
        values = np.array([value for _, value in metric_data])
        
        # Calculate statistics
        min_value = float(np.min(values))
        max_value = float(np.max(values))
        avg_value = float(np.mean(values))
        std_dev = float(np.std(values))
        
        # Detect upward trend using linear regression
        x = np.arange(len(values), dtype=float)
        y = values.astype(float)
        
        # Fit line: y = slope * x + intercept
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        
        # Determine if trending up (positive slope > 0.5% of average per data point)
        trend_threshold = avg_value * 0.005
        is_trending_up = slope > trend_threshold
        
        return TrendReport(
            metric_name=metric_name,
            analysis_hours=hours,
            min_value=min_value,
            max_value=max_value,
            avg_value=avg_value,
            std_dev=std_dev,
            is_trending_up=is_trending_up,
            trend_slope=slope,
            data_points=len(values),
        )
        
    except Exception as e:
        logger.error(f"Error analyzing trend for {metric_name}: {e}")
        return None


def analyze_multiple_trends(
    db: HealthMonitorDB,
    metrics: List[str],
    hours: int = TREND_ANALYSIS_HOURS,
) -> List[TrendReport]:
    """
    Analyze trends for multiple metrics.
    
    Args:
        db: Database instance to query historical data.
        metrics: List of metric names to analyze.
        hours: Number of hours of historical data to analyze.
    
    Returns:
        List of TrendReport objects for metrics with sufficient data.
    """
    trends = []
    
    for metric in metrics:
        trend = analyze_trend(db, metric, hours)
        if trend is not None:
            trends.append(trend)
    
    return trends
