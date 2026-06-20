"""
Input validation for collected metrics before storage.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Raised when validation of collected metrics fails."""
    pass


def validate_cpu_metrics(cpu_data: Dict[str, Any]) -> bool:
    """
    Validate CPU metrics are within expected ranges.
    
    Args:
        cpu_data: Dict with cpu_percent, cpu_per_core, and load averages.
    
    Returns:
        True if all metrics are valid.
    
    Raises:
        ValidationError: If any metric fails validation.
    """
    required_keys = ['cpu_percent', 'cpu_per_core', 'load_avg_1', 'load_avg_5', 'load_avg_15']
    
    if not all(key in cpu_data for key in required_keys):
        raise ValidationError(f"Missing required CPU metric keys. Required: {required_keys}")
    
    cpu_percent = cpu_data['cpu_percent']
    if not isinstance(cpu_percent, (int, float)) or not 0 <= cpu_percent <= 100:
        raise ValidationError(f"Invalid CPU percent: {cpu_percent}. Must be 0-100.")
    
    cpu_per_core = cpu_data['cpu_per_core']
    if not isinstance(cpu_per_core, list):
        raise ValidationError(f"cpu_per_core must be a list, got {type(cpu_per_core)}")
    
    for core_usage in cpu_per_core:
        if not isinstance(core_usage, (int, float)) or not 0 <= core_usage <= 100:
            raise ValidationError(f"Invalid per-core CPU usage: {core_usage}")
    
    for key in ['load_avg_1', 'load_avg_5', 'load_avg_15']:
        value = cpu_data[key]
        if not isinstance(value, (int, float)) or value < 0:
            raise ValidationError(f"Invalid {key}: {value}. Must be non-negative.")
    
    return True


def validate_memory_metrics(mem_data: Dict[str, Any]) -> bool:
    """
    Validate memory metrics are within expected ranges.
    
    Args:
        mem_data: Dict with memory_total, memory_used, memory_percent, etc.
    
    Returns:
        True if all metrics are valid.
    
    Raises:
        ValidationError: If any metric fails validation.
    """
    required_keys = ['memory_total', 'memory_used', 'memory_free', 'memory_percent', 'swap_used', 'swap_total']
    
    if not all(key in mem_data for key in required_keys):
        raise ValidationError(f"Missing required memory metric keys. Required: {required_keys}")
    
    total = mem_data['memory_total']
    used = mem_data['memory_used']
    percent = mem_data['memory_percent']
    
    if not isinstance(total, int) or total <= 0:
        raise ValidationError(f"Invalid memory_total: {total}. Must be positive int.")
    
    if not isinstance(used, int) or used < 0 or used > total:
        raise ValidationError(f"Invalid memory_used: {used}. Must be 0 to {total}.")
    
    if not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
        raise ValidationError(f"Invalid memory_percent: {percent}. Must be 0-100.")
    
    return True


def validate_disk_metrics(disk_data: Dict[str, Dict[str, Any]]) -> bool:
    """
    Validate disk metrics for all partitions.
    
    Args:
        disk_data: Dict mapping mount points to partition stats.
    
    Returns:
        True if all metrics are valid.
    
    Raises:
        ValidationError: If any metric fails validation.
    """
    if not isinstance(disk_data, dict):
        raise ValidationError(f"disk_data must be a dict, got {type(disk_data)}")
    
    for mount_point, partition_data in disk_data.items():
        required_keys = ['total', 'used', 'free', 'percent']
        
        if not all(key in partition_data for key in required_keys):
            raise ValidationError(f"Missing keys for partition {mount_point}. Required: {required_keys}")
        
        total = partition_data['total']
        used = partition_data['used']
        percent = partition_data['percent']
        
        if not isinstance(total, int) or total <= 0:
            raise ValidationError(f"Invalid total for {mount_point}: {total}")
        
        if not isinstance(used, int) or used < 0 or used > total:
            raise ValidationError(f"Invalid used for {mount_point}: {used}")
        
        if not isinstance(percent, (int, float)) or not 0 <= percent <= 100:
            raise ValidationError(f"Invalid percent for {mount_point}: {percent}")
    
    return True


def validate_network_metrics(net_data: Dict[str, Any]) -> bool:
    """
    Validate network I/O metrics.
    
    Args:
        net_data: Dict with network bytes/packets sent/received and errors.
    
    Returns:
        True if all metrics are valid.
    
    Raises:
        ValidationError: If any metric fails validation.
    """
    required_keys = ['network_bytes_sent', 'network_bytes_recv', 'network_packets_sent', 
                     'network_packets_recv', 'network_errin', 'network_errout']
    
    if not all(key in net_data for key in required_keys):
        raise ValidationError(f"Missing required network metric keys. Required: {required_keys}")
    
    for key in required_keys:
        value = net_data[key]
        if not isinstance(value, int) or value < 0:
            raise ValidationError(f"Invalid {key}: {value}. Must be non-negative int.")
    
    return True


def validate_process_info(process_list: List[Dict[str, Any]]) -> bool:
    """
    Validate process information entries.
    
    Args:
        process_list: List of process dicts with pid, name, cpu_percent, memory_percent.
    
    Returns:
        True if all processes are valid.
    
    Raises:
        ValidationError: If any process data fails validation.
    """
    if not isinstance(process_list, list):
        raise ValidationError(f"process_list must be a list, got {type(process_list)}")
    
    for process in process_list:
        required_keys = ['pid', 'name', 'cpu_percent', 'memory_percent']
        
        if not all(key in process for key in required_keys):
            raise ValidationError(f"Process missing required keys: {required_keys}")
        
        pid = process['pid']
        if not isinstance(pid, int) or pid <= 0:
            raise ValidationError(f"Invalid PID: {pid}. Must be positive int.")
        
        name = process['name']
        if not isinstance(name, str) or not name:
            raise ValidationError(f"Invalid process name: {name}. Must be non-empty string.")
        
        for key in ['cpu_percent', 'memory_percent']:
            value = process[key]
            if not isinstance(value, (int, float)) or value < 0:
                raise ValidationError(f"Invalid {key}: {value}. Must be non-negative number.")
    
    return True
