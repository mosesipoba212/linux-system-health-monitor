# Linux System Health Monitor & Automated Reporting Pipeline

A production-style Python application for live system monitoring, anomaly detection, historical reporting, and a browser dashboard.

## What it does

- Collects CPU, memory, disk, network, and process metrics from live `psutil` calls.
- Detects threshold-based anomalies for CPU, memory, and disk usage.
- Stores historical snapshots, anomalies, and log entries in SQLite.
- Exposes a Flask dashboard with live charts and a System Info panel.
- Reads live system logs when a source is available.
- Prints a startup validation summary so you can confirm whether the deployment is using live data sources.

## Requirements

- Python 3.8 or newer
- `psutil`
- `Flask`
- `plotly`
- Optional on Windows: `pywin32` for Windows Event Log access

## Quick Start

```bash
cd linux_health_monitor
pip install -r requirements.txt
```

## Run the monitor

### Continuous monitoring

```bash
python main.py
```

or explicitly:

```bash
python main.py --monitor
```

### Collect once

```bash
python main.py --collect-once
```

### Start the dashboard

```bash
python main.py --dashboard --interval 5
```

Open the dashboard at:

```text
http://localhost:5000
```

## Dashboard

The dashboard shows:

- CPU usage
- Memory usage
- Disk usage by partition
- Network I/O history
- Top CPU and memory processes
- Active anomalies
- Recent log errors
- Live System Info with hostname, OS, Python version, CPU architecture, core counts, RAM, and log source

If no live log source is available, the UI shows an explicit unavailable state instead of sample entries.

## Live data behavior

- CPU, memory, disk, network, and process values are collected at request time for the dashboard.
- Log data comes from a readable system log source when available.
- Startup validation prints whether the app has live data sources available.
- No sample log file is used by the live dashboard path.

## Configuration

Key settings live in `config.py`:

```python
COLLECTION_INTERVAL_SECONDS = 60
DATA_RETENTION_DAYS = 30
CPU_THRESHOLD = 85
MEMORY_THRESHOLD = 90
DISK_THRESHOLD = 80
TOP_PROCESSES_COUNT = 5
TREND_ANALYSIS_HOURS = 24
CHART_DPI = 150
```

## Project layout

```text
linux_health_monitor/
├── main.py
├── config.py
├── system_info.py
├── collector/
├── analyser/
├── dashboard/
├── parser/
├── reporter/
├── scheduler/
├── storage/
└── tests/
```

## Tests

Run the test suite with:

```bash
pytest tests/
```

A focused test for the new System Info behavior is available at:

```bash
pytest linux_health_monitor/tests/test_system_info.py -q
```

## Troubleshooting

- If log access fails, check whether your current OS exposes a readable system log source.
- On Windows, install `pywin32` to enable Event Log reading.
- If you see database locking issues, make sure only one monitor instance is running.

## Notes

This project is intended for a persistent host, VM, or self-hosted deployment. It is not designed as a serverless workload.
