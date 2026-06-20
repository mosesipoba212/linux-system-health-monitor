"""
Export system metrics to CSV format.
"""

import csv
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from linux_health_monitor.config import REPORT_OUTPUT_DIR
from linux_health_monitor.storage.database import HealthMonitorDB

logger = logging.getLogger(__name__)


def export_metrics_to_csv(
    db: HealthMonitorDB,
    hours: int = 24,
    output_dir: Path = REPORT_OUTPUT_DIR,
) -> Path:
    """
    Export system metrics from the last N hours to a CSV file.
    
    Args:
        db: Database instance to query metrics.
        hours: Number of hours of data to export (default: 24).
        output_dir: Directory to save CSV file.
    
    Returns:
        Path to the generated CSV file.
    
    Raises:
        IOError: If CSV file cannot be written.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours)
    
    csv_path = output_dir / f"metrics_{end_time.strftime('%Y-%m-%d')}.csv"
    
    try:
        snapshots = db.get_snapshots_by_range(start_time, end_time)
        
        if not snapshots:
            logger.warning(f"No snapshots found for export in the last {hours} hours")
            return csv_path
        
        with open(csv_path, 'w', newline='') as f:
            fieldnames = [
                'collected_at',
                'cpu_percent',
                'cpu_cores_count',
                'load_avg_1',
                'load_avg_5',
                'load_avg_15',
                'memory_total',
                'memory_used',
                'memory_free',
                'memory_percent',
                'swap_used',
                'swap_total',
                'network_bytes_sent',
                'network_bytes_recv',
                'network_packets_sent',
                'network_packets_recv',
            ]
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for snapshot in snapshots:
                writer.writerow({
                    'collected_at': snapshot.collected_at.isoformat(),
                    'cpu_percent': f"{snapshot.cpu_percent:.2f}",
                    'cpu_cores_count': len(snapshot.cpu_per_core),
                    'load_avg_1': f"{snapshot.load_avg_1:.2f}",
                    'load_avg_5': f"{snapshot.load_avg_5:.2f}",
                    'load_avg_15': f"{snapshot.load_avg_15:.2f}",
                    'memory_total': snapshot.memory_total,
                    'memory_used': snapshot.memory_used,
                    'memory_free': snapshot.memory_free,
                    'memory_percent': f"{snapshot.memory_percent:.2f}",
                    'swap_used': snapshot.swap_used,
                    'swap_total': snapshot.swap_total,
                    'network_bytes_sent': snapshot.network_bytes_sent,
                    'network_bytes_recv': snapshot.network_bytes_recv,
                    'network_packets_sent': snapshot.network_packets_sent,
                    'network_packets_recv': snapshot.network_packets_recv,
                })
        
        logger.info(f"Exported {len(snapshots)} snapshots to {csv_path}")
        return csv_path
        
    except IOError as e:
        logger.error(f"Failed to write CSV file: {e}")
        raise
