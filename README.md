# Linux System Health Monitor

Live Linux, macOS, and Windows system health monitoring with anomaly detection, historical reporting, and an interactive Flask dashboard.

## Repository Overview

This repository contains the full project workspace for the system health monitor, including:

- the runnable Python application in `linux_health_monitor/`
- project summaries and planning documents at the repository root
- generated reports and charts under `linux_health_monitor/reports/`

The main application code and detailed usage guide live in:

- `linux_health_monitor/README.md`

## Quick Start

```bash
cd linux_health_monitor
pip install -r requirements.txt
python main.py --dashboard
```

Then open:

```text
http://localhost:5000
```

## Main Features

- Live CPU, memory, disk, network, and process monitoring
- Threshold-based anomaly detection
- SQLite-backed historical storage
- Live dashboard with a System Info panel
- Startup validation for live data sources
- Real system log ingestion when a readable source is available

## Important Paths

- Application code: `linux_health_monitor/`
- Detailed app documentation: `linux_health_monitor/README.md`
- Quick project notes: `QUICK_START.md`
- Project summary: `PROJECT_SUMMARY.md`
- Next steps: `NEXT_STEPS.md`

## Notes

This project is designed for persistent host or VM deployment rather than serverless execution.
