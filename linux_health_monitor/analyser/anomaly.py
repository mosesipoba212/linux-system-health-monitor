"""
Threshold-based anomaly detection.
"""

import logging
from typing import List

from linux_health_monitor.config import CPU_THRESHOLD, DISK_THRESHOLD, MEMORY_THRESHOLD
from linux_health_monitor.models import AnomalyEvent, MetricSnapshot

logger = logging.getLogger(__name__)


def detect_anomalies(
    snapshot: MetricSnapshot,
    cpu_threshold: float = CPU_THRESHOLD,
    memory_threshold: float = MEMORY_THRESHOLD,
    disk_threshold: float = DISK_THRESHOLD,
) -> List[AnomalyEvent]:
    """
    Detect anomalies in a metric snapshot by comparing against configurable thresholds.
    
    Args:
        snapshot: MetricSnapshot to analyze.
        cpu_threshold: CPU usage threshold percentage.
        memory_threshold: Memory usage threshold percentage.
        disk_threshold: Disk usage threshold percentage.
    
    Returns:
        List of AnomalyEvent objects for any breached thresholds.
    """
    anomalies: List[AnomalyEvent] = []
    
    # Check CPU
    if snapshot.cpu_percent > cpu_threshold:
        severity = "critical" if snapshot.cpu_percent > 95 else "warning"
        anomalies.append(AnomalyEvent(
            collected_at=snapshot.collected_at,
            metric_name="cpu_percent",
            current_value=snapshot.cpu_percent,
            threshold=cpu_threshold,
            severity=severity,
            message=f"CPU usage {snapshot.cpu_percent:.1f}% exceeds threshold {cpu_threshold}%",
        ))
        logger.warning(f"CPU anomaly detected: {snapshot.cpu_percent:.1f}%")
    
    # Check per-core CPU
    for i, core_usage in enumerate(snapshot.cpu_per_core):
        if core_usage > cpu_threshold:
            severity = "critical" if core_usage > 95 else "warning"
            anomalies.append(AnomalyEvent(
                collected_at=snapshot.collected_at,
                metric_name=f"cpu_core_{i}",
                current_value=core_usage,
                threshold=cpu_threshold,
                severity=severity,
                message=f"CPU core {i} usage {core_usage:.1f}% exceeds threshold {cpu_threshold}%",
            ))
    
    # Check Memory
    if snapshot.memory_percent > memory_threshold:
        severity = "critical" if snapshot.memory_percent > 95 else "warning"
        anomalies.append(AnomalyEvent(
            collected_at=snapshot.collected_at,
            metric_name="memory_percent",
            current_value=snapshot.memory_percent,
            threshold=memory_threshold,
            severity=severity,
            message=f"Memory usage {snapshot.memory_percent:.1f}% exceeds threshold {memory_threshold}%",
        ))
        logger.warning(f"Memory anomaly detected: {snapshot.memory_percent:.1f}%")
    
    # Check Disk per partition
    for mount_point, partition in snapshot.disk_partitions.items():
        disk_percent = partition['percent']
        if disk_percent > disk_threshold:
            severity = "critical" if disk_percent > 95 else "warning"
            anomalies.append(AnomalyEvent(
                collected_at=snapshot.collected_at,
                metric_name=f"disk_percent_{mount_point}",
                current_value=disk_percent,
                threshold=disk_threshold,
                severity=severity,
                message=f"Disk {mount_point} usage {disk_percent:.1f}% exceeds threshold {disk_threshold}%",
            ))
            logger.warning(f"Disk anomaly detected on {mount_point}: {disk_percent:.1f}%")
    
    return anomalies
