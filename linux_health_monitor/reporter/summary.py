"""
Generate plain-text summary reports of system health.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from linux_health_monitor.analyser.trends import analyze_multiple_trends
from linux_health_monitor.config import MAX_LOG_ENTRIES_IN_REPORT, REPORT_OUTPUT_DIR, VERSION
from linux_health_monitor.models import MetricSnapshot
from linux_health_monitor.storage.database import HealthMonitorDB

logger = logging.getLogger(__name__)


def generate_summary_report(
    db: HealthMonitorDB,
    latest_snapshot: MetricSnapshot,
    output_dir: Path = REPORT_OUTPUT_DIR,
) -> Path:
    """
    Generate a comprehensive plain-text summary report.
    
    Includes current metrics, active anomalies, 24-hour trends, top processes,
    and recent log errors.
    
    Args:
        db: Database instance to query historical data.
        latest_snapshot: Most recent metric snapshot.
        output_dir: Directory to save report file.
    
    Returns:
        Path to the generated report file.
    
    Raises:
        IOError: If report file cannot be written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = latest_snapshot.collected_at.strftime("%Y-%m-%d_%H-%M-%S")
    report_path = output_dir / f"report_{timestamp}.txt"
    
    try:
        with open(report_path, 'w') as f:
            # Header
            f.write("=" * 80 + "\n")
            f.write(f"LINUX SYSTEM HEALTH MONITOR - Report v{VERSION}\n")
            f.write("=" * 80 + "\n")
            f.write(f"Generated: {datetime.utcnow().isoformat()} UTC\n")
            f.write("\n")
            
            # Current System Snapshot
            f.write("CURRENT SYSTEM SNAPSHOT\n")
            f.write("-" * 80 + "\n")
            f.write(f"CPU Usage:              {latest_snapshot.cpu_percent:.1f}%\n")
            f.write(f"CPU Load Average:       1m={latest_snapshot.load_avg_1:.2f}, "
                   f"5m={latest_snapshot.load_avg_5:.2f}, "
                   f"15m={latest_snapshot.load_avg_15:.2f}\n")
            f.write(f"Memory Usage:           {latest_snapshot.memory_percent:.1f}% "
                   f"({_format_bytes(latest_snapshot.memory_used)}/{_format_bytes(latest_snapshot.memory_total)})\n")
            f.write(f"Swap Usage:             {_format_bytes(latest_snapshot.swap_used)}/{_format_bytes(latest_snapshot.swap_total)}\n")
            f.write("\n")
            
            # Disk Usage
            f.write("DISK USAGE BY PARTITION\n")
            f.write("-" * 80 + "\n")
            for mount_point, disk_info in latest_snapshot.disk_partitions.items():
                f.write(f"{mount_point:30} {disk_info['percent']:5.1f}% "
                       f"({_format_bytes(disk_info['used'])}/{_format_bytes(disk_info['total'])})\n")
            f.write("\n")
            
            # Top Processes
            f.write("TOP PROCESSES BY CPU\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'PID':>10} {'NAME':25} {'CPU %':>10} {'MEM %':>10}\n")
            f.write("-" * 80 + "\n")
            for proc in latest_snapshot.top_cpu_processes:
                f.write(f"{proc.pid:10d} {proc.name:25} {proc.cpu_percent:10.1f} {proc.memory_percent:10.1f}\n")
            f.write("\n")
            
            f.write("TOP PROCESSES BY MEMORY\n")
            f.write("-" * 80 + "\n")
            f.write(f"{'PID':>10} {'NAME':25} {'CPU %':>10} {'MEM %':>10}\n")
            f.write("-" * 80 + "\n")
            for proc in latest_snapshot.top_memory_processes:
                f.write(f"{proc.pid:10d} {proc.name:25} {proc.cpu_percent:10.1f} {proc.memory_percent:10.1f}\n")
            f.write("\n")
            
            # Recent Anomalies
            anomalies = db.get_recent_anomalies(limit=20)
            if anomalies:
                f.write("RECENT ANOMALIES\n")
                f.write("-" * 80 + "\n")
                for anomaly in anomalies:
                    f.write(f"[{anomaly.severity.upper()}] {anomaly.metric_name}: {anomaly.message}\n")
                f.write("\n")
            
            # Trends
            f.write("24-HOUR TRENDS\n")
            f.write("-" * 80 + "\n")
            trends = analyze_multiple_trends(
                db,
                ['cpu_percent', 'memory_percent'],
                hours=24
            )
            
            for trend in trends:
                trend_dir = "↑ UP" if trend.is_trending_up else "→ STABLE"
                f.write(f"{trend.metric_name:20} Min:{trend.min_value:6.1f} "
                       f"Max:{trend.max_value:6.1f} Avg:{trend.avg_value:6.1f} "
                       f"StdDev:{trend.std_dev:6.1f} [{trend_dir}]\n")
            f.write("\n")
            
            # Recent Log Errors
            log_entries = db.get_recent_logs(limit=MAX_LOG_ENTRIES_IN_REPORT)
            if log_entries:
                f.write("RECENT LOG ERRORS (Last 20)\n")
                f.write("-" * 80 + "\n")
                for entry in log_entries:
                    f.write(f"[{entry.severity}] {entry.timestamp.isoformat()}\n")
                    f.write(f"  {entry.message}\n")
                f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("End of Report\n")
        
        logger.info(f"Report generated: {report_path}")
        return report_path
        
    except IOError as e:
        logger.error(f"Failed to write report file: {e}")
        raise


def _format_bytes(bytes_value: int) -> str:
    """
    Format bytes into human-readable string.
    
    Args:
        bytes_value: Number of bytes.
    
    Returns:
        Formatted string (e.g., "4.2 GB").
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} PB"
