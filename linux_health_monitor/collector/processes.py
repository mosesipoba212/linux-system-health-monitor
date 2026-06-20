"""
Process monitoring - collect top resource-consuming processes.
"""

import logging
from typing import List

import psutil

from linux_health_monitor.models import ProcessInfo

logger = logging.getLogger(__name__)


def get_top_processes(limit: int = 5) -> tuple[List[ProcessInfo], List[ProcessInfo]]:
    """
    Collect the top N processes by CPU and memory usage.
    
    Args:
        limit: Maximum number of top processes to return for each category.
    
    Returns:
        Tuple of (top_cpu_processes, top_memory_processes).
        Each list contains ProcessInfo objects sorted by usage descending.
    """
    try:
        processes_with_stats = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']

                # Skip kernel/system entries that fail downstream validation.
                if not isinstance(pid, int) or pid <= 0:
                    continue
                if not isinstance(name, str) or not name.strip():
                    continue

                processes_with_stats.append({
                    "pid": pid,
                    "name": name,
                    "cpu_percent": proc.info['cpu_percent'] or 0.0,
                    "memory_percent": proc.info['memory_percent'] or 0.0,
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage and get top N
        top_cpu = sorted(
            processes_with_stats,
            key=lambda x: x['cpu_percent'],
            reverse=True
        )[:limit]
        
        # Sort by memory usage and get top N
        top_memory = sorted(
            processes_with_stats,
            key=lambda x: x['memory_percent'],
            reverse=True
        )[:limit]
        
        cpu_process_objs = [
            ProcessInfo(
                pid=p['pid'],
                name=p['name'],
                cpu_percent=p['cpu_percent'],
                memory_percent=p['memory_percent']
            )
            for p in top_cpu
        ]
        
        memory_process_objs = [
            ProcessInfo(
                pid=p['pid'],
                name=p['name'],
                cpu_percent=p['cpu_percent'],
                memory_percent=p['memory_percent']
            )
            for p in top_memory
        ]
        
        return cpu_process_objs, memory_process_objs
        
    except Exception as e:
        logger.error(f"Error collecting process metrics: {e}")
        raise
