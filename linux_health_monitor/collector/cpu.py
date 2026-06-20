"""
CPU metrics collection using psutil.
"""

import logging
from typing import Dict, List

import psutil

logger = logging.getLogger(__name__)


def get_cpu_metrics() -> Dict[str, any]:
    """
    Collect CPU usage metrics including overall %, per-core usage, and load averages.
    
    Returns:
        Dict containing:
        - cpu_percent: float - overall CPU usage percentage
        - cpu_per_core: List[float] - per-core CPU usage percentages
        - load_avg_1: float - 1-minute load average
        - load_avg_5: float - 5-minute load average
        - load_avg_15: float - 15-minute load average
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        load_avg = psutil.getloadavg()
        
        return {
            "cpu_percent": cpu_percent,
            "cpu_per_core": cpu_per_core,
            "load_avg_1": load_avg[0],
            "load_avg_5": load_avg[1],
            "load_avg_15": load_avg[2],
        }
    except Exception as e:
        logger.error(f"Error collecting CPU metrics: {e}")
        raise
