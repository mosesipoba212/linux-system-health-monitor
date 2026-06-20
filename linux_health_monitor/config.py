"""
Global configuration for the Linux System Health Monitor.

All configurable parameters are defined here for easy maintenance.
Thresholds, paths, and intervals can be adjusted without modifying source code.
"""

from pathlib import Path
from typing import Final

# Project metadata
VERSION: Final[str] = "1.0.0"
APP_NAME: Final[str] = "Linux Health Monitor"

# Paths - all use pathlib.Path for cross-platform compatibility
BASE_DIR: Final[Path] = Path(__file__).parent
DB_PATH: Final[Path] = BASE_DIR / "data" / "health_monitor.db"
REPORT_OUTPUT_DIR: Final[Path] = BASE_DIR / "reports"
LOGS_DIR: Final[Path] = BASE_DIR / "logs"
WINDOWS_EVENT_LOG_SOURCES: Final[tuple[str, ...]] = ("System", "Application")
WINDOWS_EVENT_LOG_MAX_ENTRIES: Final[int] = 200

# Collection settings
COLLECTION_INTERVAL_SECONDS: Final[int] = 60
DATA_RETENTION_DAYS: Final[int] = 30
TOP_PROCESSES_COUNT: Final[int] = 5

# Anomaly detection thresholds (percentages)
CPU_THRESHOLD: Final[int] = 85
MEMORY_THRESHOLD: Final[int] = 90
DISK_THRESHOLD: Final[int] = 80

# Analysis settings
TREND_ANALYSIS_HOURS: Final[int] = 24

# Reporting settings
CHART_DPI: Final[int] = 150
MAX_LOG_ENTRIES_IN_REPORT: Final[int] = 20

# Logging configuration
LOG_FORMAT: Final[str] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_LEVEL: Final[str] = "INFO"
