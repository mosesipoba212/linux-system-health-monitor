"""
Disk usage metrics collection using psutil.
"""

import logging
from typing import Dict

import psutil

logger = logging.getLogger(__name__)


def get_disk_metrics() -> Dict[str, Dict[str, any]]:
    """
    Collect disk usage metrics for all mounted partitions.
    
    Returns:
        Dict mapping mount points to partition stats:
        Each partition contains:
        - total: int - total disk space in bytes
        - used: int - used disk space in bytes
        - free: int - free disk space in bytes
        - percent: float - usage percentage
    """
    try:
        disk_partitions = {}
        
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_partitions[partition.mountpoint] = {
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                    "device": partition.device,
                    "fstype": partition.fstype,
                }
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot access partition {partition.mountpoint}: {e}")
                continue
        
        return disk_partitions
    except Exception as e:
        logger.error(f"Error collecting disk metrics: {e}")
        raise
