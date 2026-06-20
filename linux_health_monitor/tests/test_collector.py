"""
Tests for collector modules.
"""

from unittest.mock import MagicMock, patch

import pytest

from linux_health_monitor.collector.cpu import get_cpu_metrics
from linux_health_monitor.collector.disk import get_disk_metrics
from linux_health_monitor.collector.memory import get_memory_metrics
from linux_health_monitor.collector.network import get_network_metrics
from linux_health_monitor.collector.processes import get_top_processes


class TestCPUCollector:
    """Test CPU metrics collection."""
    
    @patch('linux_health_monitor.collector.cpu.psutil.cpu_percent')
    @patch('linux_health_monitor.collector.cpu.psutil.getloadavg')
    def test_get_cpu_metrics_returns_correct_schema(self, mock_loadavg, mock_cpu_percent):
        """Test that CPU metrics return expected schema."""
        mock_cpu_percent.side_effect = [45.5, [10.0, 20.0, 30.0, 40.0]]
        mock_loadavg.return_value = (1.5, 2.0, 2.5)
        
        result = get_cpu_metrics()
        
        assert 'cpu_percent' in result
        assert 'cpu_per_core' in result
        assert 'load_avg_1' in result
        assert 'load_avg_5' in result
        assert 'load_avg_15' in result
        
        assert isinstance(result['cpu_percent'], (int, float))
        assert isinstance(result['cpu_per_core'], list)
        assert 0 <= result['cpu_percent'] <= 100


class TestMemoryCollector:
    """Test memory metrics collection."""
    
    @patch('linux_health_monitor.collector.memory.psutil.virtual_memory')
    @patch('linux_health_monitor.collector.memory.psutil.swap_memory')
    def test_get_memory_metrics_returns_correct_schema(self, mock_swap, mock_virtual):
        """Test that memory metrics return expected schema."""
        mock_virtual.return_value = MagicMock(
            total=16 * 1024**3,
            used=8 * 1024**3,
            available=8 * 1024**3,
            percent=50.0
        )
        mock_swap.return_value = MagicMock(
            total=4 * 1024**3,
            used=1 * 1024**3
        )
        
        result = get_memory_metrics()
        
        assert 'memory_total' in result
        assert 'memory_used' in result
        assert 'memory_free' in result
        assert 'memory_percent' in result
        assert 'swap_used' in result
        assert 'swap_total' in result
        
        assert isinstance(result['memory_total'], int)
        assert result['memory_total'] > 0


class TestDiskCollector:
    """Test disk metrics collection."""
    
    @patch('linux_health_monitor.collector.disk.psutil.disk_partitions')
    @patch('linux_health_monitor.collector.disk.psutil.disk_usage')
    def test_get_disk_metrics_returns_partition_data(self, mock_usage, mock_partitions):
        """Test that disk metrics return partition data."""
        mock_partition = MagicMock(
            device='/dev/sda1',
            mountpoint='/',
            fstype='ext4'
        )
        mock_partitions.return_value = [mock_partition]
        mock_usage.return_value = MagicMock(
            total=500 * 1024**3,
            used=250 * 1024**3,
            free=250 * 1024**3,
            percent=50.0
        )
        
        result = get_disk_metrics()
        
        assert isinstance(result, dict)
        assert '/' in result
        assert 'total' in result['/']
        assert 'used' in result['/']
        assert result['/']['percent'] == 50.0


class TestNetworkCollector:
    """Test network metrics collection."""
    
    @patch('linux_health_monitor.collector.network.psutil.net_io_counters')
    def test_get_network_metrics_returns_correct_schema(self, mock_counters):
        """Test that network metrics return expected schema."""
        mock_counters.return_value = MagicMock(
            bytes_sent=1000000,
            bytes_recv=2000000,
            packets_sent=5000,
            packets_recv=6000,
            errin=0,
            errout=0
        )
        
        result = get_network_metrics()
        
        assert 'network_bytes_sent' in result
        assert 'network_bytes_recv' in result
        assert 'network_packets_sent' in result
        assert 'network_packets_recv' in result
        assert 'network_errin' in result
        assert 'network_errout' in result
        
        assert isinstance(result['network_bytes_sent'], int)
        assert result['network_bytes_sent'] >= 0


class TestProcessCollector:
    """Test process metrics collection."""
    
    @patch('linux_health_monitor.collector.processes.psutil.process_iter')
    def test_get_top_processes_returns_lists(self, mock_process_iter):
        """Test that process collection returns top CPU and memory processes."""
        mock_proc = MagicMock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'test_process',
            'cpu_percent': 25.0,
            'memory_percent': 10.0
        }
        mock_process_iter.return_value = [mock_proc]
        
        top_cpu, top_mem = get_top_processes(limit=5)
        
        assert isinstance(top_cpu, list)
        assert isinstance(top_mem, list)
        assert len(top_cpu) <= 5
        assert len(top_mem) <= 5
