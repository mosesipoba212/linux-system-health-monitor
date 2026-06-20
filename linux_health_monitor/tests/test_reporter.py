"""
Tests for reporter modules.
"""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from linux_health_monitor.models import MetricSnapshot, ProcessInfo
from linux_health_monitor.reporter.csv_export import export_metrics_to_csv
from linux_health_monitor.reporter.summary import generate_summary_report


class TestSummaryReporter:
    """Test summary report generation."""
    
    def test_generate_summary_report_creates_file(self):
        """Test that summary report file is created."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Create mock database
            mock_db = MagicMock()
            mock_db.get_recent_anomalies.return_value = []
            mock_db.get_recent_logs.return_value = []
            
            # Create mock snapshot
            snapshot = MetricSnapshot(
                collected_at=datetime.utcnow(),
                cpu_percent=45.0,
                cpu_per_core=[45.0, 45.0],
                load_avg_1=1.5,
                load_avg_5=2.0,
                load_avg_15=2.5,
                memory_total=16 * 1024**3,
                memory_used=8 * 1024**3,
                memory_free=8 * 1024**3,
                memory_percent=50.0,
                swap_used=0,
                swap_total=0,
                disk_partitions={
                    '/': {
                        'total': 500 * 1024**3,
                        'used': 250 * 1024**3,
                        'free': 250 * 1024**3,
                        'percent': 50.0,
                        'device': '/dev/sda1',
                        'fstype': 'ext4',
                    }
                },
                top_cpu_processes=[],
                top_memory_processes=[],
            )
            
            with patch('linux_health_monitor.reporter.summary.analyze_multiple_trends', return_value=[]):
                report_path = generate_summary_report(mock_db, snapshot, output_dir)
            
            assert report_path.exists()
            assert report_path.suffix == '.txt'
            
            # Check report contains expected sections
            content = report_path.read_text()
            assert 'LINUX SYSTEM HEALTH MONITOR' in content
            assert 'CURRENT SYSTEM SNAPSHOT' in content
            assert 'DISK USAGE BY PARTITION' in content
            assert 'TOP PROCESSES' in content


class TestCSVExporter:
    """Test CSV export functionality."""
    
    def test_export_metrics_to_csv_creates_file(self):
        """Test that CSV export file is created."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Create mock database with snapshots
            mock_db = MagicMock()
            snapshot = MetricSnapshot(
                collected_at=datetime.utcnow(),
                cpu_percent=45.0,
                cpu_per_core=[45.0, 45.0],
                load_avg_1=1.5,
                load_avg_5=2.0,
                load_avg_15=2.5,
                memory_total=16 * 1024**3,
                memory_used=8 * 1024**3,
                memory_free=8 * 1024**3,
                memory_percent=50.0,
                swap_used=0,
                swap_total=0,
                disk_partitions={},
                top_cpu_processes=[],
                top_memory_processes=[],
            )
            mock_db.get_snapshots_by_range.return_value = [snapshot]
            
            csv_path = export_metrics_to_csv(mock_db, hours=24, output_dir=output_dir)
            
            assert csv_path.exists()
            assert csv_path.suffix == '.csv'
            
            # Check CSV contains expected headers
            content = csv_path.read_text()
            assert 'collected_at' in content
            assert 'cpu_percent' in content
            assert 'memory_percent' in content
    
    def test_export_metrics_handles_empty_database(self):
        """Test CSV export handles empty database gracefully."""
        with TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Create mock database with no snapshots
            mock_db = MagicMock()
            mock_db.get_snapshots_by_range.return_value = []
            
            csv_path = export_metrics_to_csv(mock_db, hours=24, output_dir=output_dir)
            
            # File should still be created even if empty
            assert isinstance(csv_path, Path)
