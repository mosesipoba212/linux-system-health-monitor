"""
Data normalization - convert raw collected data into standardized MetricSnapshot format.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

from linux_health_monitor.models import MetricSnapshot, ProcessInfo

logger = logging.getLogger(__name__)


def normalize_snapshot(
    cpu_data: Dict[str, Any],
    memory_data: Dict[str, Any],
    disk_data: Dict[str, Dict[str, Any]],
    network_data: Dict[str, Any],
    top_cpu_processes: List[ProcessInfo],
    top_memory_processes: List[ProcessInfo],
) -> MetricSnapshot:
    """
    Normalize raw collected data into a standardized MetricSnapshot dataclass.
    
    All timestamps are normalized to ISO 8601 UTC format during storage.
    
    Args:
        cpu_data: Raw CPU metrics dict.
        memory_data: Raw memory metrics dict.
        disk_data: Raw disk metrics dict.
        network_data: Raw network metrics dict.
        top_cpu_processes: List of top CPU-consuming processes.
        top_memory_processes: List of top memory-consuming processes.
    
    Returns:
        MetricSnapshot object with all metrics in standardized format.
    """
    return MetricSnapshot(
        collected_at=datetime.utcnow(),
        cpu_percent=float(cpu_data['cpu_percent']),
        cpu_per_core=[float(x) for x in cpu_data['cpu_per_core']],
        load_avg_1=float(cpu_data['load_avg_1']),
        load_avg_5=float(cpu_data['load_avg_5']),
        load_avg_15=float(cpu_data['load_avg_15']),
        memory_total=int(memory_data['memory_total']),
        memory_used=int(memory_data['memory_used']),
        memory_free=int(memory_data['memory_free']),
        memory_percent=float(memory_data['memory_percent']),
        swap_used=int(memory_data['swap_used']),
        swap_total=int(memory_data['swap_total']),
        disk_partitions={k: _normalize_disk_partition(v) for k, v in disk_data.items()},
        network_bytes_sent=int(network_data['network_bytes_sent']),
        network_bytes_recv=int(network_data['network_bytes_recv']),
        network_packets_sent=int(network_data['network_packets_sent']),
        network_packets_recv=int(network_data['network_packets_recv']),
        network_errin=int(network_data['network_errin']),
        network_errout=int(network_data['network_errout']),
        top_cpu_processes=top_cpu_processes,
        top_memory_processes=top_memory_processes,
    )


def _normalize_disk_partition(partition_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single disk partition's data.
    
    Args:
        partition_data: Raw partition stats dict.
    
    Returns:
        Normalized partition dict with consistent types.
    """
    return {
        "total": int(partition_data['total']),
        "used": int(partition_data['used']),
        "free": int(partition_data['free']),
        "percent": float(partition_data['percent']),
        "device": str(partition_data.get('device', 'unknown')),
        "fstype": str(partition_data.get('fstype', 'unknown')),
    }
