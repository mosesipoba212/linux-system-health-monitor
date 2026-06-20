"""
Collection loop scheduler - runs on configurable interval.
"""

import logging
import time
from pathlib import Path

from linux_health_monitor.analyser.anomaly import detect_anomalies
from linux_health_monitor.collector.cpu import get_cpu_metrics
from linux_health_monitor.collector.disk import get_disk_metrics
from linux_health_monitor.collector.logs import parse_syslog
from linux_health_monitor.collector.memory import get_memory_metrics
from linux_health_monitor.collector.network import get_network_metrics
from linux_health_monitor.collector.processes import get_top_processes
from linux_health_monitor.config import (
    COLLECTION_INTERVAL_SECONDS,
    DATA_RETENTION_DAYS,
    TOP_PROCESSES_COUNT,
)
from linux_health_monitor.parser.normaliser import normalize_snapshot
from linux_health_monitor.parser.validator import (
    ValidationError,
    validate_cpu_metrics,
    validate_disk_metrics,
    validate_memory_metrics,
    validate_network_metrics,
    validate_process_info,
)
from linux_health_monitor.storage.database import HealthMonitorDB
from linux_health_monitor.system_info import resolve_log_source

logger = logging.getLogger(__name__)


class CollectionScheduler:
    """Manages the collection loop and data processing pipeline."""
    
    def __init__(self, interval_seconds: int = COLLECTION_INTERVAL_SECONDS) -> None:
        """
        Initialize the scheduler.
        
        Args:
            interval_seconds: Collection interval in seconds.
        """
        self.interval = interval_seconds
        self.db = HealthMonitorDB()
        self.running = False
        self.log_source_info = resolve_log_source()
        self.log_source_path = self._resolve_log_source_path()
    
    def run_once(self) -> bool:
        """
        Run a single collection cycle.
        
        Collects metrics, validates, stores, and analyzes.
        
        Returns:
            True if successful, False if any step failed.
        """
        cycle_start = time.time()
        
        try:
            logger.info("Starting collection cycle...")
            
            # Collect metrics
            cpu_data = get_cpu_metrics()
            validate_cpu_metrics(cpu_data)
            logger.debug("CPU metrics collected and validated")
            
            memory_data = get_memory_metrics()
            validate_memory_metrics(memory_data)
            logger.debug("Memory metrics collected and validated")
            
            disk_data = get_disk_metrics()
            validate_disk_metrics(disk_data)
            logger.debug("Disk metrics collected and validated")
            
            network_data = get_network_metrics()
            validate_network_metrics(network_data)
            logger.debug("Network metrics collected and validated")
            
            top_cpu_processes, top_memory_processes = get_top_processes(TOP_PROCESSES_COUNT)
            process_data = [
                vars(p) for p in (top_cpu_processes + top_memory_processes)
            ]
            validate_process_info(process_data)
            logger.debug("Process metrics collected and validated")
            
            # Normalize data
            snapshot = normalize_snapshot(
                cpu_data, memory_data, disk_data, network_data,
                top_cpu_processes, top_memory_processes
            )
            logger.debug("Snapshot normalized")
            
            # Store snapshot
            snapshot_id = self.db.insert_snapshot(snapshot)
            logger.debug(f"Snapshot stored with ID {snapshot_id}")
            
            # Detect anomalies
            anomalies = detect_anomalies(snapshot)
            for anomaly in anomalies:
                self.db.insert_anomaly(anomaly)
                logger.warning(f"Anomaly detected: {anomaly.message}")
            
            # Parse and store logs
            log_entries = []
            if self.log_source_info.get("available"):
                log_entries = parse_syslog(self.log_source_path)
            if log_entries:
                self.db.insert_log_entries(log_entries[-10:])  # Store only recent 10
            
            cycle_time = time.time() - cycle_start
            logger.info(f"Collection cycle completed in {cycle_time:.2f}s "
                       f"({len(anomalies)} anomalies detected)")
            
            return True
            
        except ValidationError as e:
            logger.error(f"Validation error during collection: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during collection cycle: {e}")
            return False
    
    def run_continuous(self) -> None:
        """
        Run the collection loop continuously at the configured interval.
        
        Handles KeyboardInterrupt gracefully for shutdown.
        Logs cleanup of old data periodically.
        """
        self.running = True
        cycle_count = 0
        cleanup_interval = 24  # Clean old data every N cycles
        
        logger.info(f"Starting continuous monitoring (interval: {self.interval}s)")
        
        try:
            while self.running:
                cycle_count += 1
                
                self.run_once()
                
                # Periodic cleanup
                if cycle_count % cleanup_interval == 0:
                    try:
                        deleted = self.db.clear_old_data(DATA_RETENTION_DAYS)
                        logger.info(f"Cleaned up {deleted} old records")
                    except Exception as e:
                        logger.error(f"Cleanup failed: {e}")
                
                # Sleep until next cycle
                time.sleep(self.interval)
        
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            self.running = False
        except Exception as e:
            logger.error(f"Fatal error in collection loop: {e}")
            self.running = False

    def _resolve_log_source_path(self) -> Path:
        """Choose the preferred live log source path, if one exists."""
        label = self.log_source_info.get("label", "System log unavailable")
        value = self.log_source_info.get("value", "Unavailable")

        if self.log_source_info.get("available") and self.log_source_info.get("kind") == "file":
            logger.info(f"Reading live system log from: {value}")
            return Path(str(value))

        if self.log_source_info.get("available") and self.log_source_info.get("kind") == "windows_event_log":
            logger.info(f"Reading live system log from: {label} ({value})")
            return Path(".")

        logger.warning(f"{label}: {self.log_source_info.get('reason', 'Unavailable')}")
        return Path(".")
