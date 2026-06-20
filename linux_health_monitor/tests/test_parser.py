"""
Tests for parser modules.
"""

import pytest

from linux_health_monitor.parser.normaliser import normalize_snapshot
from linux_health_monitor.parser.validator import (
    ValidationError,
    validate_cpu_metrics,
    validate_disk_metrics,
    validate_memory_metrics,
    validate_network_metrics,
    validate_process_info,
)
from linux_health_monitor.models import ProcessInfo


class TestValidator:
    """Test input validation."""
    
    def test_validate_cpu_metrics_valid_data(self):
        """Test CPU validation with valid data."""
        valid_data = {
            'cpu_percent': 45.5,
            'cpu_per_core': [10.0, 20.0, 30.0],
            'load_avg_1': 1.5,
            'load_avg_5': 2.0,
            'load_avg_15': 2.5,
        }
        assert validate_cpu_metrics(valid_data) is True
    
    def test_validate_cpu_metrics_invalid_percent(self):
        """Test CPU validation rejects invalid percentage."""
        invalid_data = {
            'cpu_percent': 150.0,  # Out of range
            'cpu_per_core': [10.0, 20.0],
            'load_avg_1': 1.5,
            'load_avg_5': 2.0,
            'load_avg_15': 2.5,
        }
        with pytest.raises(ValidationError):
            validate_cpu_metrics(invalid_data)
    
    def test_validate_memory_metrics_valid_data(self):
        """Test memory validation with valid data."""
        valid_data = {
            'memory_total': 16 * 1024**3,
            'memory_used': 8 * 1024**3,
            'memory_free': 8 * 1024**3,
            'memory_percent': 50.0,
            'swap_used': 0,
            'swap_total': 4 * 1024**3,
        }
        assert validate_memory_metrics(valid_data) is True
    
    def test_validate_memory_metrics_invalid_used(self):
        """Test memory validation rejects used > total."""
        invalid_data = {
            'memory_total': 16 * 1024**3,
            'memory_used': 20 * 1024**3,  # More than total
            'memory_free': 0,
            'memory_percent': 50.0,
            'swap_used': 0,
            'swap_total': 4 * 1024**3,
        }
        with pytest.raises(ValidationError):
            validate_memory_metrics(invalid_data)
    
    def test_validate_disk_metrics_valid_data(self):
        """Test disk validation with valid data."""
        valid_data = {
            '/': {
                'total': 500 * 1024**3,
                'used': 250 * 1024**3,
                'free': 250 * 1024**3,
                'percent': 50.0,
            }
        }
        assert validate_disk_metrics(valid_data) is True
    
    def test_validate_network_metrics_valid_data(self):
        """Test network validation with valid data."""
        valid_data = {
            'network_bytes_sent': 1000000,
            'network_bytes_recv': 2000000,
            'network_packets_sent': 5000,
            'network_packets_recv': 6000,
            'network_errin': 0,
            'network_errout': 0,
        }
        assert validate_network_metrics(valid_data) is True
    
    def test_validate_process_info_valid_data(self):
        """Test process info validation with valid data."""
        valid_data = [
            {
                'pid': 1234,
                'name': 'python',
                'cpu_percent': 25.0,
                'memory_percent': 10.0,
            }
        ]
        assert validate_process_info(valid_data) is True
    
    def test_validate_process_info_invalid_pid(self):
        """Test process info validation rejects invalid PID."""
        invalid_data = [
            {
                'pid': -1,  # Invalid PID
                'name': 'python',
                'cpu_percent': 25.0,
                'memory_percent': 10.0,
            }
        ]
        with pytest.raises(ValidationError):
            validate_process_info(invalid_data)


class TestNormaliser:
    """Test data normalization."""
    
    def test_normalize_snapshot_creates_correct_schema(self):
        """Test that normalization produces correct MetricSnapshot."""
        cpu_data = {
            'cpu_percent': 45.5,
            'cpu_per_core': [10.0, 20.0],
            'load_avg_1': 1.5,
            'load_avg_5': 2.0,
            'load_avg_15': 2.5,
        }
        memory_data = {
            'memory_total': 16 * 1024**3,
            'memory_used': 8 * 1024**3,
            'memory_free': 8 * 1024**3,
            'memory_percent': 50.0,
            'swap_used': 0,
            'swap_total': 0,
        }
        disk_data = {
            '/': {
                'total': 500 * 1024**3,
                'used': 250 * 1024**3,
                'free': 250 * 1024**3,
                'percent': 50.0,
            }
        }
        network_data = {
            'network_bytes_sent': 1000000,
            'network_bytes_recv': 2000000,
            'network_packets_sent': 5000,
            'network_packets_recv': 6000,
            'network_errin': 0,
            'network_errout': 0,
        }
        processes_cpu = []
        processes_mem = []
        
        snapshot = normalize_snapshot(
            cpu_data, memory_data, disk_data, network_data,
            processes_cpu, processes_mem
        )
        
        assert snapshot.cpu_percent == 45.5
        assert snapshot.memory_percent == 50.0
        assert '/' in snapshot.disk_partitions
        assert snapshot.network_bytes_sent == 1000000
