"""System information and live data-source helpers."""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path
from typing import Any

import psutil

from linux_health_monitor.config import WINDOWS_EVENT_LOG_SOURCES

logger = logging.getLogger(__name__)


def get_system_info() -> dict[str, Any]:
    """Collect deployment-safe system information for the dashboard."""
    os_name = _safe_call(platform.system)
    os_release = _safe_call(platform.release)
    os_version = _safe_call(platform.version)
    hostname = _safe_call(platform.node)
    python_version = _safe_call(platform.python_version)
    architecture = _resolve_architecture()
    physical_cores = _safe_int(lambda: psutil.cpu_count(logical=False))
    logical_cores = _safe_int(lambda: psutil.cpu_count(logical=True))
    total_ram_gb = _safe_ram_gb()
    log_source = resolve_log_source()

    return {
        "platform": _platform_tag(os_name),
        "operating_system": _format_operating_system(os_name, os_release),
        "os_details": os_version,
        "os_name": os_name,
        "os_release": os_release,
        "os_version": os_version,
        "hostname": hostname,
        "python_version": python_version,
        "cpu_architecture": architecture,
        "physical_cores": physical_cores,
        "logical_cores": logical_cores,
        "total_ram_gb": total_ram_gb,
        "log_source": log_source,
    }


def resolve_log_source() -> dict[str, Any]:
    """Resolve the current system log source without using fallback data."""
    system_name = _safe_call(platform.system)
    system_name_lower = system_name.lower() if isinstance(system_name, str) else ""

    if system_name_lower == "windows":
        try:
            import win32evtlog  # type: ignore  # noqa: F401
        except ImportError:
            return {
                "available": False,
                "platform": "Windows",
                "kind": "windows_event_log",
                "label": "No accessible system log on this device",
                "value": "Unavailable",
                "reason": "pywin32 is not installed",
            }

        return {
            "available": True,
            "platform": "Windows",
            "kind": "windows_event_log",
            "label": "Windows Event Log",
            "value": ", ".join(WINDOWS_EVENT_LOG_SOURCES),
            "reason": None,
        }

    candidates: list[Path]
    if system_name_lower == "darwin":
        candidates = [Path("/var/log/system.log")]
    elif system_name_lower == "linux":
        candidates = [Path("/var/log/syslog"), Path("/var/log/messages")]
    else:
        candidates = [Path("/var/log/syslog"), Path("/var/log/system.log"), Path("/var/log/messages")]

    for path in candidates:
        if path.exists() and os.access(path, os.R_OK):
            return {
                "available": True,
                "platform": _platform_tag(system_name),
                "kind": "file",
                "label": "Real system log",
                "value": str(path),
                "reason": None,
            }

    return {
        "available": False,
        "platform": _platform_tag(system_name),
        "kind": "none",
        "label": "No accessible system log on this device",
        "value": "Unavailable",
        "reason": "No readable local system log path was found",
    }


def get_startup_validation_summary() -> dict[str, Any]:
    """Build a concise startup validation summary for CLI and dashboard modes."""
    system_info = get_system_info()
    degraded: list[str] = []

    for key in ("os_name", "os_release", "os_version", "hostname", "python_version", "cpu_architecture"):
        if system_info.get(key) in (None, "", "Unavailable"):
            degraded.append(f"{key.replace('_', ' ').title()} unavailable")

    if system_info.get("physical_cores") in (None, "Unavailable"):
        degraded.append("Physical core count unavailable")
    if system_info.get("logical_cores") in (None, "Unavailable"):
        degraded.append("Logical core count unavailable")
    if system_info.get("total_ram_gb") in (None, "Unavailable"):
        degraded.append("Total RAM unavailable")

    log_source = system_info["log_source"]
    if not log_source.get("available"):
        degraded.append(log_source.get("label", "System log unavailable"))

    verified = not degraded
    return {
        "verified": verified,
        "degraded": degraded,
        "system_info": system_info,
    }


def _resolve_architecture() -> str:
    machine = _safe_call(platform.machine)
    processor = _safe_call(platform.processor)

    if machine:
        if machine == "arm64" and _safe_call(platform.system).lower() == "darwin":
            return "Apple Silicon (arm64)"
        return str(machine)

    if processor:
        return str(processor)

    return "Unavailable"


def _safe_ram_gb() -> str:
    try:
        total = psutil.virtual_memory().total
        return f"{total / (1024 ** 3):.2f} GB"
    except Exception:
        return "Unavailable"


def _platform_tag(system_name: Any) -> str:
    system_name_text = str(system_name).lower()
    if system_name_text == "darwin":
        return "macOS"
    if system_name_text == "windows":
        return "Windows"
    if system_name_text == "linux":
        return "Linux"
    return "Unknown"


def _format_operating_system(system_name: Any, release: Any) -> str:
    platform_tag = _platform_tag(system_name)
    release_text = str(release)

    if platform_tag == "macOS":
        return f"macOS {release_text}" if release_text != "Unavailable" else "macOS"

    if platform_tag == "Windows":
        return f"Windows {release_text}" if release_text != "Unavailable" else "Windows"

    if platform_tag == "Linux":
        try:
            os_release = platform.freedesktop_os_release()
            pretty_name = os_release.get("PRETTY_NAME")
            if pretty_name:
                return str(pretty_name)
        except Exception:
            pass

        return f"Linux {release_text}" if release_text != "Unavailable" else "Linux"

    return "Unavailable"


def _safe_call(func: Any) -> str:
    try:
        result = func()
        if result in (None, ""):
            return "Unavailable"
        return str(result)
    except Exception:
        return "Unavailable"


def _safe_int(func: Any) -> str:
    try:
        result = func()
        if result is None:
            return "Unavailable"
        return str(int(result))
    except Exception:
        return "Unavailable"
