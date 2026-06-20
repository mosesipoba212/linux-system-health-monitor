"""
System log parser - extract ERROR, WARNING, CRITICAL entries from syslog.
"""

import logging
import os
import platform
import re
from datetime import datetime
from pathlib import Path
from typing import List

from linux_health_monitor.config import WINDOWS_EVENT_LOG_MAX_ENTRIES, WINDOWS_EVENT_LOG_SOURCES
from linux_health_monitor.models import LogEntry

logger = logging.getLogger(__name__)
_WINDOWS_HINT_LOGGED = False


def parse_syslog(log_file_path: Path) -> List[LogEntry]:
    """
    Parse system logs and extract ERROR, WARNING, and CRITICAL entries.
    
    Expected format: standard syslog format with timestamp and severity levels.
    
    Args:
        log_file_path: Path to the log file to parse.
    
    Returns:
        List of LogEntry objects matching ERROR, WARNING, or CRITICAL severity.
    """
    if platform.system() == "Windows":
        return _parse_windows_event_logs()

    entries: List[LogEntry] = []
    severity_pattern = re.compile(r'\b(ERROR|CRITICAL|WARNING)\b', re.IGNORECASE)
    
    try:
        if not log_file_path.exists() or not log_file_path.is_file() or not os.access(log_file_path, os.R_OK):
            logger.warning(f"No accessible system log on this device: {log_file_path}")
            return entries
        
        with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if not line.strip():
                    continue
                
                match = severity_pattern.search(line)
                if not match:
                    continue
                
                severity = match.group(1).upper()
                
                try:
                    parsed_entry = LogEntry(
                        collected_at=datetime.utcnow(),
                        timestamp=_parse_syslog_timestamp(line),
                        severity=severity,
                        message=line.strip(),
                        source="syslog"
                    )
                    entries.append(parsed_entry)
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Skipping malformed log line: {line.strip()[:80]}")
                    continue
        
        return entries
        
    except Exception as e:
        logger.error(f"Error parsing syslog file {log_file_path}: {e}")
        raise


def _parse_windows_event_logs() -> List[LogEntry]:
    """Read recent Windows event log entries."""
    try:
        import win32evtlog  # type: ignore
    except ImportError:
        global _WINDOWS_HINT_LOGGED
        if not _WINDOWS_HINT_LOGGED:
            logger.warning(
                "Windows Event Log support requires `pip install pywin32`; "
                "no system log entries can be read until it is installed."
            )
            _WINDOWS_HINT_LOGGED = True
        return []

    entries: List[LogEntry] = []
    severity_map = {
        win32evtlog.EVENTLOG_ERROR_TYPE: "ERROR",
        win32evtlog.EVENTLOG_WARNING_TYPE: "WARNING",
        win32evtlog.EVENTLOG_AUDIT_FAILURE: "CRITICAL",
    }

    for source in WINDOWS_EVENT_LOG_SOURCES:
        handle = None
        try:
            handle = win32evtlog.OpenEventLog(None, source)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

            while len(entries) < WINDOWS_EVENT_LOG_MAX_ENTRIES:
                events = win32evtlog.ReadEventLog(handle, flags, 0)
                if not events:
                    break

                for event in events:
                    severity = severity_map.get(event.EventType)
                    if severity is None:
                        continue

                    message = _build_windows_event_message(event, source)
                    entries.append(
                        LogEntry(
                            collected_at=datetime.utcnow(),
                            timestamp=_parse_windows_event_timestamp(event),
                            severity=severity,
                            message=message,
                            source=f"windows_event:{source}",
                        )
                    )

                    if len(entries) >= WINDOWS_EVENT_LOG_MAX_ENTRIES:
                        break

                if len(entries) >= WINDOWS_EVENT_LOG_MAX_ENTRIES:
                    break

        except Exception as e:
            logger.warning(f"Failed reading Windows Event Log source '{source}': {e}")
        finally:
            if handle is not None:
                try:
                    win32evtlog.CloseEventLog(handle)
                except Exception:
                    pass

    if entries:
        entries.sort(key=lambda item: item.timestamp)
        return entries

    return []


def _parse_file_entries(log_file_path: Path) -> List[LogEntry]:
    """Parse log entries from a file path using syslog-like severity matching."""
    entries: List[LogEntry] = []
    severity_pattern = re.compile(r'\b(ERROR|CRITICAL|WARNING)\b', re.IGNORECASE)

    if not log_file_path.exists():
        logger.warning(f"Log file not found: {log_file_path}")
        return entries

    with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as handle:
        for line in handle:
            if not line.strip():
                continue

            match = severity_pattern.search(line)
            if not match:
                continue

            severity = match.group(1).upper()
            entries.append(
                LogEntry(
                    collected_at=datetime.utcnow(),
                    timestamp=_parse_syslog_timestamp(line),
                    severity=severity,
                    message=line.strip(),
                    source="syslog",
                )
            )

    return entries


def _parse_windows_event_timestamp(event: object) -> datetime:
    """Extract an event timestamp robustly across pywin32 versions."""
    timestamp = getattr(event, "TimeGenerated", None)
    if timestamp is None:
        return datetime.utcnow()

    if isinstance(timestamp, datetime):
        return timestamp

    if hasattr(timestamp, "timestamp"):
        try:
            return datetime.fromtimestamp(timestamp.timestamp())
        except Exception:
            return datetime.utcnow()

    return datetime.utcnow()


def _build_windows_event_message(event: object, source: str) -> str:
    """Build a concise normalized message for a Windows event log record."""
    event_id = getattr(event, "EventID", 0)
    inserts = getattr(event, "StringInserts", None)
    rendered = " | ".join(str(item) for item in inserts) if inserts else "No detail"
    return f"[{source}] EventID={event_id}: {rendered}"


def _parse_syslog_timestamp(line: str) -> datetime:
    """
    Extract and parse timestamp from syslog line.
    
    Attempts to parse standard syslog format: "Mon DD HH:MM:SS"
    Falls back to current UTC time if parsing fails.
    
    Args:
        line: Raw syslog line.
    
    Returns:
        Parsed datetime in UTC.
    """
    try:
        # Try standard syslog format: "Mon DD HH:MM:SS"
        timestamp_str = ' '.join(line.split()[:3])
        parsed = datetime.strptime(timestamp_str, "%b %d %H:%M:%S")
        
        # Add current year (syslog doesn't include year)
        parsed = parsed.replace(year=datetime.utcnow().year)
        return parsed
    except (ValueError, IndexError):
        # Fall back to current UTC time
        return datetime.utcnow()
