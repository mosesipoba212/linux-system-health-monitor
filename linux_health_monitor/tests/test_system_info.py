"""Tests for system info and live source detection."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

from linux_health_monitor.system_info import get_system_info, resolve_log_source


def test_get_system_info_has_expected_keys() -> None:
    info = get_system_info()

    assert "platform" in info
    assert "operating_system" in info
    assert "hostname" in info
    assert "python_version" in info
    assert "cpu_architecture" in info
    assert "physical_cores" in info
    assert "logical_cores" in info
    assert "total_ram_gb" in info
    assert "log_source" in info


@patch("linux_health_monitor.system_info.platform.system", return_value="Darwin")
@patch("linux_health_monitor.system_info.platform.release", return_value="24.3.0")
@patch("linux_health_monitor.system_info.platform.version", return_value="Darwin Kernel Version")
@patch("linux_health_monitor.system_info.platform.node", return_value="mac-demo")
@patch("linux_health_monitor.system_info.platform.python_version", return_value="3.14.4")
@patch("linux_health_monitor.system_info.platform.machine", return_value="arm64")
@patch("linux_health_monitor.system_info.platform.processor", return_value="Apple M2")
@patch("linux_health_monitor.system_info.psutil.cpu_count", side_effect=[8, 8])
@patch("linux_health_monitor.system_info.psutil.virtual_memory")
def test_macos_branch(
    mock_virtual_memory,
    mock_cpu_count,
    mock_processor,
    mock_machine,
    mock_python_version,
    mock_node,
    mock_version,
    mock_release,
    mock_system,
) -> None:
    mock_virtual_memory.return_value = SimpleNamespace(total=16 * 1024**3)

    info = get_system_info()

    assert info["platform"] == "macOS"
    assert info["operating_system"].startswith("macOS")
    assert info["hostname"] == "mac-demo"
    assert info["cpu_architecture"] == "Apple Silicon (arm64)"
    assert info["physical_cores"] == "8"
    assert info["logical_cores"] == "8"
    assert info["total_ram_gb"] == "16.00 GB"
    assert info["log_source"]["platform"] == "macOS"


@patch("linux_health_monitor.system_info.platform.system", return_value="Linux")
@patch("linux_health_monitor.system_info.platform.release", return_value="6.8.0")
@patch("linux_health_monitor.system_info.platform.version", return_value="#1 SMP")
@patch("linux_health_monitor.system_info.platform.node", return_value="linux-demo")
@patch("linux_health_monitor.system_info.platform.python_version", return_value="3.14.4")
@patch("linux_health_monitor.system_info.platform.machine", return_value="x86_64")
@patch("linux_health_monitor.system_info.platform.processor", return_value="")
@patch("linux_health_monitor.system_info.psutil.cpu_count", side_effect=[4, 8])
@patch("linux_health_monitor.system_info.psutil.virtual_memory")
@patch("linux_health_monitor.system_info.platform.freedesktop_os_release", return_value={"PRETTY_NAME": "Ubuntu 22.04.4 LTS"})
def test_linux_branch(
    mock_os_release,
    mock_virtual_memory,
    mock_cpu_count,
    mock_processor,
    mock_machine,
    mock_python_version,
    mock_node,
    mock_version,
    mock_release,
    mock_system,
) -> None:
    mock_virtual_memory.return_value = SimpleNamespace(total=32 * 1024**3)

    info = get_system_info()

    assert info["platform"] == "Linux"
    assert info["operating_system"] == "Ubuntu 22.04.4 LTS"
    assert info["hostname"] == "linux-demo"
    assert info["cpu_architecture"] == "x86_64"
    assert info["physical_cores"] == "4"
    assert info["logical_cores"] == "8"
    assert info["total_ram_gb"] == "32.00 GB"
    assert info["log_source"]["platform"] == "Linux"


@patch("linux_health_monitor.system_info.platform.system", return_value="Windows")
@patch("linux_health_monitor.system_info.platform.release", return_value="11")
@patch("linux_health_monitor.system_info.platform.version", return_value="10.0.22631")
@patch("linux_health_monitor.system_info.platform.node", return_value="windows-demo")
@patch("linux_health_monitor.system_info.platform.python_version", return_value="3.14.4")
@patch("linux_health_monitor.system_info.platform.machine", return_value="AMD64")
@patch("linux_health_monitor.system_info.platform.processor", return_value="Intel64 Family 6 Model 158 Stepping 10")
@patch("linux_health_monitor.system_info.psutil.cpu_count", side_effect=[8, 16])
@patch("linux_health_monitor.system_info.psutil.virtual_memory")
def test_windows_branch_with_event_log_module(
    mock_virtual_memory,
    mock_cpu_count,
    mock_processor,
    mock_machine,
    mock_python_version,
    mock_node,
    mock_version,
    mock_release,
    mock_system,
) -> None:
    mock_virtual_memory.return_value = SimpleNamespace(total=64 * 1024**3)
    original_module = sys.modules.get("win32evtlog")
    sys.modules["win32evtlog"] = SimpleNamespace()
    try:
        info = get_system_info()
        log_source = resolve_log_source()
    finally:
        if original_module is None:
            sys.modules.pop("win32evtlog", None)
        else:
            sys.modules["win32evtlog"] = original_module

    assert info["platform"] == "Windows"
    assert info["operating_system"].startswith("Windows")
    assert info["hostname"] == "windows-demo"
    assert info["cpu_architecture"] == "AMD64"
    assert info["physical_cores"] == "8"
    assert info["logical_cores"] == "16"
    assert info["total_ram_gb"] == "64.00 GB"
    assert log_source["platform"] == "Windows"
    assert log_source["available"] is True
