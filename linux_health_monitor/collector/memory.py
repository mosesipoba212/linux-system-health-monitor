"""
Memory metrics collection using psutil.
"""

import logging
from typing import Dict

import psutil

logger = logging.getLogger(__name__)


def get_memory_metrics() -> Dict[str, any]:
    """
    Collect RAM and swap memory usage metrics.
    
    Returns:
        Dict containing:
        - memory_total: int - total RAM in bytes
        - memory_used: int - used RAM in bytes
        - memory_free: int - free RAM in bytes
        - memory_percent: float - RAM usage percentage
        - swap_used: int - used swap in bytes
        - swap_total: int - total swap in bytes
    """
    try:
        virtual_mem = psutil.virtual_memory()
        swap_mem = psutil.swap_memory()
        
        return {
            "memory_total": virtual_mem.total,
            "memory_used": virtual_mem.used,
            "memory_free": virtual_mem.available,
            "memory_percent": virtual_mem.percent,
            "swap_used": swap_mem.used,
            "swap_total": swap_mem.total,
        }
    except Exception as e:
        logger.error(f"Error collecting memory metrics: {e}")
        raise
