"""
Generate time-series charts using matplotlib.
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np

from linux_health_monitor.config import CHART_DPI, REPORT_OUTPUT_DIR
from linux_health_monitor.storage.database import HealthMonitorDB

logger = logging.getLogger(__name__)


def generate_charts(
    db: HealthMonitorDB,
    hours: int = 24,
    output_dir: Path = REPORT_OUTPUT_DIR,
) -> List[Path]:
    """
    Generate all system health charts and save as PNG files.
    
    Creates charts for:
    - CPU usage over time
    - Memory usage over time
    - Disk usage (latest snapshot)
    - Network I/O over time
    
    Args:
        db: Database instance to query metrics.
        hours: Number of hours of data to display in time-series charts.
        output_dir: Directory to save PNG files.
    
    Returns:
        List of paths to generated chart files.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []
    
    timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        snapshots = db.get_snapshots_by_range(start_time, end_time)
        
        if not snapshots:
            logger.warning(f"No snapshots found for chart generation in the last {hours} hours")
            return generated_files
        
        # Extract time series data
        timestamps = [s.collected_at for s in snapshots]
        cpu_data = [s.cpu_percent for s in snapshots]
        memory_data = [s.memory_percent for s in snapshots]
        network_sent = [s.network_bytes_sent for s in snapshots]
        network_recv = [s.network_bytes_recv for s in snapshots]
        
        # CPU chart
        cpu_path = _generate_cpu_chart(timestamps, cpu_data, output_dir, timestamp)
        if cpu_path:
            generated_files.append(cpu_path)
        
        # Memory chart
        memory_path = _generate_memory_chart(timestamps, memory_data, output_dir, timestamp)
        if memory_path:
            generated_files.append(memory_path)
        
        # Disk chart (latest snapshot)
        disk_path = _generate_disk_chart(snapshots[-1], output_dir, timestamp)
        if disk_path:
            generated_files.append(disk_path)
        
        # Network chart
        network_path = _generate_network_chart(timestamps, network_sent, network_recv, output_dir, timestamp)
        if network_path:
            generated_files.append(network_path)
        
        logger.info(f"Generated {len(generated_files)} charts")
        return generated_files
        
    except Exception as e:
        logger.error(f"Error generating charts: {e}")
        return generated_files


def _generate_cpu_chart(
    timestamps: List[datetime],
    cpu_data: List[float],
    output_dir: Path,
    timestamp: str,
) -> Path:
    """Generate CPU usage over time chart."""
    try:
        fig, ax = plt.subplots(figsize=(12, 6), dpi=CHART_DPI)
        
        ax.plot(timestamps, cpu_data, linewidth=2, color='#FF6B6B', label='CPU Usage')
        ax.axhline(y=85, color='orange', linestyle='--', linewidth=1, label='Warning Threshold (85%)')
        ax.axhline(y=95, color='red', linestyle='--', linewidth=1, label='Critical Threshold (95%)')
        
        ax.set_xlabel('Time')
        ax.set_ylabel('CPU Usage (%)')
        ax.set_title('CPU Usage Over Time (24 Hours)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_path = output_dir / f"chart_cpu_{timestamp}.png"
        fig.savefig(output_path)
        plt.close(fig)
        
        logger.info(f"CPU chart saved: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating CPU chart: {e}")
        return None


def _generate_memory_chart(
    timestamps: List[datetime],
    memory_data: List[float],
    output_dir: Path,
    timestamp: str,
) -> Path:
    """Generate memory usage over time chart."""
    try:
        fig, ax = plt.subplots(figsize=(12, 6), dpi=CHART_DPI)
        
        ax.plot(timestamps, memory_data, linewidth=2, color='#4ECDC4', label='Memory Usage')
        ax.axhline(y=90, color='orange', linestyle='--', linewidth=1, label='Warning Threshold (90%)')
        ax.axhline(y=95, color='red', linestyle='--', linewidth=1, label='Critical Threshold (95%)')
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Memory Usage (%)')
        ax.set_title('Memory Usage Over Time (24 Hours)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_path = output_dir / f"chart_memory_{timestamp}.png"
        fig.savefig(output_path)
        plt.close(fig)
        
        logger.info(f"Memory chart saved: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating memory chart: {e}")
        return None


def _generate_disk_chart(snapshot, output_dir: Path, timestamp: str) -> Path:
    """Generate disk usage bar chart for latest snapshot."""
    try:
        mount_points = list(snapshot.disk_partitions.keys())
        disk_percents = [snapshot.disk_partitions[mp]['percent'] for mp in mount_points]
        
        fig, ax = plt.subplots(figsize=(12, 6), dpi=CHART_DPI)
        
        colors = ['#2ECC71' if x < 80 else '#F39C12' if x < 95 else '#E74C3C' for x in disk_percents]
        ax.bar(mount_points, disk_percents, color=colors)
        ax.axhline(y=80, color='orange', linestyle='--', linewidth=1, label='Warning Threshold (80%)')
        ax.axhline(y=95, color='red', linestyle='--', linewidth=1, label='Critical Threshold (95%)')
        
        ax.set_xlabel('Mount Point')
        ax.set_ylabel('Disk Usage (%)')
        ax.set_title('Disk Usage by Partition (Latest)')
        ax.legend()
        ax.set_ylim(0, 105)
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        output_path = output_dir / f"chart_disk_{timestamp}.png"
        fig.savefig(output_path)
        plt.close(fig)
        
        logger.info(f"Disk chart saved: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating disk chart: {e}")
        return None


def _generate_network_chart(
    timestamps: List[datetime],
    network_sent: List[int],
    network_recv: List[int],
    output_dir: Path,
    timestamp: str,
) -> Path:
    """Generate network I/O over time chart."""
    try:
        fig, ax = plt.subplots(figsize=(12, 6), dpi=CHART_DPI)
        
        # Convert bytes to MB for better readability
        sent_mb = [b / (1024 * 1024) for b in network_sent]
        recv_mb = [b / (1024 * 1024) for b in network_recv]
        
        ax.plot(timestamps, sent_mb, linewidth=2, color='#3498DB', label='Bytes Sent', marker='o', markersize=3)
        ax.plot(timestamps, recv_mb, linewidth=2, color='#E74C3C', label='Bytes Received', marker='s', markersize=3)
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Data (MB)')
        ax.set_title('Network I/O Over Time (24 Hours)')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        output_path = output_dir / f"chart_network_{timestamp}.png"
        fig.savefig(output_path)
        plt.close(fig)
        
        logger.info(f"Network chart saved: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating network chart: {e}")
        return None
