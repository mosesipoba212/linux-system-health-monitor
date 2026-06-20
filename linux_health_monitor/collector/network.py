"""
Network I/O metrics collection using psutil.
"""

import logging
from typing import Dict

import psutil

logger = logging.getLogger(__name__)


def get_network_metrics() -> Dict[str, any]:
    """
    Collect network I/O statistics including bytes and packets sent/received.
    
    Returns:
        Dict containing:
        - network_bytes_sent: int - cumulative bytes sent since boot
        - network_bytes_recv: int - cumulative bytes received since boot
        - network_packets_sent: int - cumulative packets sent since boot
        - network_packets_recv: int - cumulative packets received since boot
        - network_errin: int - cumulative inbound errors
        - network_errout: int - cumulative outbound errors
    """
    try:
        net_io = psutil.net_io_counters()
        
        return {
            "network_bytes_sent": net_io.bytes_sent,
            "network_bytes_recv": net_io.bytes_recv,
            "network_packets_sent": net_io.packets_sent,
            "network_packets_recv": net_io.packets_recv,
            "network_errin": net_io.errin,
            "network_errout": net_io.errout,
        }
    except Exception as e:
        logger.error(f"Error collecting network metrics: {e}")
        raise
