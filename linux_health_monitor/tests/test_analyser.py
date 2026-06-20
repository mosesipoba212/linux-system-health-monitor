"""
Tests for analyzer modules.
"""

from datetime import datetime

import numpy as np
import pytest

from linux_health_monitor.analyser.anomaly import detect_anomalies
from linux_health_monitor.analyser.trends import analyze_trend
from linux_health_monitor.models import MetricSnapshot, ProcessInfo


class TestAnomalyDetector:
    """Test anomaly detection."""
    
    def test_detect_anomalies_cpu_threshold(self):
        """Test anomaly detection for CPU threshold breach."""
        snapshot = MetricSnapshot(
            collected_at=datetime.utcnow(),
            cpu_percent=90.0,  # Exceeds 85% threshold
            cpu_per_core=[85.0, 95.0],
            load_avg_1=2.0,
            load_avg_5=2.5,
            load_avg_15=3.0,
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
        
        anomalies = detect_anomalies(snapshot, cpu_threshold=85)
        
        # Should detect overall CPU and per-core anomalies
        assert len(anomalies) >= 1
        assert any('cpu_percent' in a.metric_name for a in anomalies)
    
    def test_detect_anomalies_memory_threshold(self):
        """Test anomaly detection for memory threshold breach."""
        snapshot = MetricSnapshot(
            collected_at=datetime.utcnow(),
            cpu_percent=50.0,
            cpu_per_core=[50.0, 50.0],
            load_avg_1=1.0,
            load_avg_5=1.5,
            load_avg_15=2.0,
            memory_total=16 * 1024**3,
            memory_used=15 * 1024**3,
            memory_free=1 * 1024**3,
            memory_percent=95.0,  # Exceeds 90% threshold
            swap_used=0,
            swap_total=0,
            disk_partitions={},
            top_cpu_processes=[],
            top_memory_processes=[],
        )
        
        anomalies = detect_anomalies(snapshot, memory_threshold=90)
        
        assert len(anomalies) >= 1
        assert any('memory_percent' in a.metric_name for a in anomalies)
    
    def test_detect_anomalies_disk_threshold(self):
        """Test anomaly detection for disk threshold breach."""
        snapshot = MetricSnapshot(
            collected_at=datetime.utcnow(),
            cpu_percent=50.0,
            cpu_per_core=[50.0, 50.0],
            load_avg_1=1.0,
            load_avg_5=1.5,
            load_avg_15=2.0,
            memory_total=16 * 1024**3,
            memory_used=8 * 1024**3,
            memory_free=8 * 1024**3,
            memory_percent=50.0,
            swap_used=0,
            swap_total=0,
            disk_partitions={
                '/': {
                    'total': 500 * 1024**3,
                    'used': 450 * 1024**3,
                    'free': 50 * 1024**3,
                    'percent': 90.0,  # Exceeds 80% threshold
                    'device': '/dev/sda1',
                    'fstype': 'ext4',
                }
            },
            top_cpu_processes=[],
            top_memory_processes=[],
        )
        
        anomalies = detect_anomalies(snapshot, disk_threshold=80)
        
        assert len(anomalies) >= 1
        assert any('disk_percent_/' in a.metric_name for a in anomalies)
    
    def test_detect_anomalies_no_breach(self):
        """Test no anomalies when all metrics are normal."""
        snapshot = MetricSnapshot(
            collected_at=datetime.utcnow(),
            cpu_percent=30.0,
            cpu_per_core=[30.0, 30.0],
            load_avg_1=1.0,
            load_avg_5=1.5,
            load_avg_15=2.0,
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
        
        anomalies = detect_anomalies(snapshot)
        
        assert len(anomalies) == 0
    
    def test_anomaly_severity_levels(self):
        """Test that anomalies have appropriate severity levels."""
        snapshot = MetricSnapshot(
            collected_at=datetime.utcnow(),
            cpu_percent=96.0,  # Critical level (>95%)
            cpu_per_core=[96.0],
            load_avg_1=2.0,
            load_avg_5=2.5,
            load_avg_15=3.0,
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
        
        anomalies = detect_anomalies(snapshot, cpu_threshold=85)
        
        critical_anomalies = [a for a in anomalies if a.severity == 'critical']
        assert len(critical_anomalies) > 0
