"""
SQLite database layer for metrics storage and retrieval.

All queries use parameterised statements to prevent SQL injection.
Indexes are created on frequently-queried columns.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from linux_health_monitor.config import DB_PATH
from linux_health_monitor.models import AnomalyEvent, LogEntry, MetricSnapshot

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Raised when database operations fail."""
    pass


class HealthMonitorDB:
    """SQLite database manager for health monitoring metrics."""
    
    def __init__(self, db_path: Path = DB_PATH) -> None:
        """
        Initialize database connection and create tables if needed.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self) -> None:
        """Create database schema if it doesn't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create system_metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        collected_at TEXT NOT NULL,
                        cpu_percent REAL NOT NULL,
                        cpu_per_core TEXT NOT NULL,
                        load_avg_1 REAL NOT NULL,
                        load_avg_5 REAL NOT NULL,
                        load_avg_15 REAL NOT NULL,
                        memory_total INTEGER NOT NULL,
                        memory_used INTEGER NOT NULL,
                        memory_free INTEGER NOT NULL,
                        memory_percent REAL NOT NULL,
                        swap_used INTEGER NOT NULL,
                        swap_total INTEGER NOT NULL,
                        disk_partitions TEXT NOT NULL,
                        network_bytes_sent INTEGER NOT NULL,
                        network_bytes_recv INTEGER NOT NULL,
                        network_packets_sent INTEGER NOT NULL,
                        network_packets_recv INTEGER NOT NULL,
                        network_errin INTEGER NOT NULL,
                        network_errout INTEGER NOT NULL,
                        top_cpu_processes TEXT NOT NULL,
                        top_memory_processes TEXT NOT NULL
                    )
                """)
                
                # Create anomaly_events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS anomaly_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        collected_at TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        current_value REAL NOT NULL,
                        threshold REAL NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL
                    )
                """)
                
                # Create log_entries table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS log_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        collected_at TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        severity TEXT NOT NULL,
                        message TEXT NOT NULL,
                        source TEXT NOT NULL
                    )
                """)
                
                # Create indexes for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_system_metrics_collected_at 
                    ON system_metrics(collected_at)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_anomaly_events_collected_at 
                    ON anomaly_events(collected_at)
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_log_entries_collected_at 
                    ON log_entries(collected_at)
                """)
                
                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to initialize database: {e}")
    
    def insert_snapshot(self, snapshot: MetricSnapshot) -> int:
        """
        Insert a metric snapshot into the database.
        
        Args:
            snapshot: MetricSnapshot object to store.
        
        Returns:
            The row ID of the inserted record.
        
        Raises:
            DatabaseError: If insertion fails.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO system_metrics (
                        collected_at, cpu_percent, cpu_per_core, load_avg_1, load_avg_5,
                        load_avg_15, memory_total, memory_used, memory_free, memory_percent,
                        swap_used, swap_total, disk_partitions, network_bytes_sent,
                        network_bytes_recv, network_packets_sent, network_packets_recv,
                        network_errin, network_errout, top_cpu_processes, top_memory_processes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    snapshot.collected_at.isoformat(),
                    snapshot.cpu_percent,
                    json.dumps(snapshot.cpu_per_core),
                    snapshot.load_avg_1,
                    snapshot.load_avg_5,
                    snapshot.load_avg_15,
                    snapshot.memory_total,
                    snapshot.memory_used,
                    snapshot.memory_free,
                    snapshot.memory_percent,
                    snapshot.swap_used,
                    snapshot.swap_total,
                    json.dumps(snapshot.disk_partitions),
                    snapshot.network_bytes_sent,
                    snapshot.network_bytes_recv,
                    snapshot.network_packets_sent,
                    snapshot.network_packets_recv,
                    snapshot.network_errin,
                    snapshot.network_errout,
                    json.dumps([vars(p) for p in snapshot.top_cpu_processes]),
                    json.dumps([vars(p) for p in snapshot.top_memory_processes]),
                ))
                
                conn.commit()
                row_id = cursor.lastrowid
                logger.debug(f"Inserted snapshot with ID {row_id}")
                return row_id
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to insert snapshot: {e}")
    
    def insert_anomaly(self, anomaly: AnomalyEvent) -> int:
        """
        Insert an anomaly event into the database.
        
        Args:
            anomaly: AnomalyEvent object to store.
        
        Returns:
            The row ID of the inserted record.
        
        Raises:
            DatabaseError: If insertion fails.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO anomaly_events (
                        collected_at, metric_name, current_value, threshold, severity, message
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    anomaly.collected_at.isoformat(),
                    anomaly.metric_name,
                    anomaly.current_value,
                    anomaly.threshold,
                    anomaly.severity,
                    anomaly.message,
                ))
                
                conn.commit()
                logger.debug(f"Inserted anomaly event: {anomaly.metric_name}")
                return cursor.lastrowid
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to insert anomaly: {e}")
    
    def insert_log_entries(self, entries: List[LogEntry]) -> int:
        """
        Insert multiple log entries into the database.
        
        Args:
            entries: List of LogEntry objects to store.
        
        Returns:
            Number of inserted records.
        
        Raises:
            DatabaseError: If insertion fails.
        """
        if not entries:
            return 0
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for entry in entries:
                    cursor.execute("""
                        INSERT INTO log_entries (
                            collected_at, timestamp, severity, message, source
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        entry.collected_at.isoformat(),
                        entry.timestamp.isoformat(),
                        entry.severity,
                        entry.message,
                        entry.source,
                    ))
                
                conn.commit()
                logger.debug(f"Inserted {len(entries)} log entries")
                return len(entries)
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to insert log entries: {e}")
    
    def get_snapshots_by_range(
        self, start_time: datetime, end_time: datetime
    ) -> List[MetricSnapshot]:
        """
        Retrieve metric snapshots within a time range.
        
        Args:
            start_time: Start of time range (UTC).
            end_time: End of time range (UTC).
        
        Returns:
            List of MetricSnapshot objects.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM system_metrics
                    WHERE collected_at BETWEEN ? AND ?
                    ORDER BY collected_at ASC
                """, (start_time.isoformat(), end_time.isoformat()))
                
                rows = cursor.fetchall()
                snapshots = []
                
                for row in rows:
                    snapshot = MetricSnapshot(
                        collected_at=datetime.fromisoformat(row['collected_at']),
                        cpu_percent=row['cpu_percent'],
                        cpu_per_core=json.loads(row['cpu_per_core']),
                        load_avg_1=row['load_avg_1'],
                        load_avg_5=row['load_avg_5'],
                        load_avg_15=row['load_avg_15'],
                        memory_total=row['memory_total'],
                        memory_used=row['memory_used'],
                        memory_free=row['memory_free'],
                        memory_percent=row['memory_percent'],
                        swap_used=row['swap_used'],
                        swap_total=row['swap_total'],
                        disk_partitions=json.loads(row['disk_partitions']),
                        network_bytes_sent=row['network_bytes_sent'],
                        network_bytes_recv=row['network_bytes_recv'],
                        network_packets_sent=row['network_packets_sent'],
                        network_packets_recv=row['network_packets_recv'],
                        network_errin=row['network_errin'],
                        network_errout=row['network_errout'],
                    )
                    snapshots.append(snapshot)
                
                return snapshots
                
        except (sqlite3.Error, json.JSONDecodeError) as e:
            raise DatabaseError(f"Failed to retrieve snapshots: {e}")
    
    def get_recent_anomalies(self, limit: int = 50) -> List[AnomalyEvent]:
        """
        Retrieve recent anomaly events.
        
        Args:
            limit: Maximum number of anomalies to return.
        
        Returns:
            List of AnomalyEvent objects, most recent first.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM anomaly_events
                    ORDER BY collected_at DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                anomalies = []
                
                for row in rows:
                    anomaly = AnomalyEvent(
                        collected_at=datetime.fromisoformat(row['collected_at']),
                        metric_name=row['metric_name'],
                        current_value=row['current_value'],
                        threshold=row['threshold'],
                        severity=row['severity'],
                        message=row['message'],
                    )
                    anomalies.append(anomaly)
                
                return anomalies
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve anomalies: {e}")
    
    def get_recent_logs(self, limit: int = 50) -> List[LogEntry]:
        """
        Retrieve recent log entries.
        
        Args:
            limit: Maximum number of log entries to return.
        
        Returns:
            List of LogEntry objects, most recent first.
        
        Raises:
            DatabaseError: If query fails.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM log_entries
                    ORDER BY collected_at DESC
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                entries = []
                
                for row in rows:
                    entry = LogEntry(
                        collected_at=datetime.fromisoformat(row['collected_at']),
                        timestamp=datetime.fromisoformat(row['timestamp']),
                        severity=row['severity'],
                        message=row['message'],
                        source=row['source'],
                    )
                    entries.append(entry)
                
                return entries
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve log entries: {e}")
    
    def get_metric_values(self, metric_name: str, hours: int = 24) -> List[Tuple[datetime, float]]:
        """
        Retrieve time series data for a specific metric over the past N hours.
        
        Args:
            metric_name: Name of the metric (e.g., 'cpu_percent', 'memory_percent').
            hours: Number of hours of historical data to retrieve.
        
        Returns:
            List of (datetime, value) tuples.
        
        Raises:
            DatabaseError: If query fails or metric doesn't exist.
        """
        try:
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT collected_at, ? as metric_value FROM system_metrics
                    WHERE collected_at > ?
                    ORDER BY collected_at ASC
                """, (metric_name, cutoff_time))
                
                # We need to fetch the actual metric column
                cursor.execute(f"""
                    SELECT collected_at, {metric_name} as metric_value FROM system_metrics
                    WHERE collected_at > ?
                    ORDER BY collected_at ASC
                """, (cutoff_time,))
                
                rows = cursor.fetchall()
                return [(datetime.fromisoformat(row['collected_at']), row['metric_value']) for row in rows]
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to retrieve metric values: {e}")
    
    def clear_old_data(self, days_to_keep: int = 30) -> int:
        """
        Delete snapshots older than the specified number of days.
        
        Args:
            days_to_keep: Delete records older than this many days.
        
        Returns:
            Number of rows deleted.
        
        Raises:
            DatabaseError: If deletion fails.
        """
        try:
            cutoff_time = (datetime.utcnow() - timedelta(days=days_to_keep)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM system_metrics WHERE collected_at < ?
                """, (cutoff_time,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"Deleted {deleted_count} old metric records (older than {days_to_keep} days)")
                return deleted_count
                
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to clear old data: {e}")
