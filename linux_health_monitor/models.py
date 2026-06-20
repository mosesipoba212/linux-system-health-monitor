"""
Data classes for structured metric storage and analysis results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class ProcessInfo:
    """Information about a resource-consuming process."""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float


@dataclass
class MetricSnapshot:
    """Single point-in-time snapshot of all system metrics."""
    collected_at: datetime
    cpu_percent: float
    cpu_per_core: List[float]
    load_avg_1: float
    load_avg_5: float
    load_avg_15: float
    memory_total: int
    memory_used: int
    memory_free: int
    memory_percent: float
    swap_used: int
    swap_total: int
    disk_partitions: Dict[str, Dict[str, any]] = field(default_factory=dict)
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    network_packets_sent: int = 0
    network_packets_recv: int = 0
    network_errin: int = 0
    network_errout: int = 0
    top_cpu_processes: List[ProcessInfo] = field(default_factory=list)
    top_memory_processes: List[ProcessInfo] = field(default_factory=list)


@dataclass
class AnomalyEvent:
    """Detected anomaly or threshold breach."""
    collected_at: datetime
    metric_name: str
    current_value: float
    threshold: float
    severity: str  # "warning" or "critical"
    message: str


@dataclass
class LogEntry:
    """Parsed system log entry."""
    collected_at: datetime
    timestamp: datetime
    severity: str  # ERROR, WARNING, CRITICAL
    message: str
    source: str = "syslog"


@dataclass
class TrendReport:
    """Statistical analysis of metrics over a time range."""
    metric_name: str
    analysis_hours: int
    min_value: float
    max_value: float
    avg_value: float
    std_dev: float
    is_trending_up: bool
    trend_slope: float
    data_points: int
