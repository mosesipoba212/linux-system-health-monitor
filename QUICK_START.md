# Quick Start Guide

## Installation

```bash
cd linux_health_monitor
pip3 install -r requirements.txt
```

## Run Modes

### 1. Continuous Monitoring (Default)
```bash
python3 main.py
```
Runs forever, collecting metrics every 60 seconds. Press CTRL+C to stop.

### 2. Single Collection Cycle
```bash
python3 main.py --collect-once
```
Perfect for testing, cron jobs, or CI/CD pipelines.

### 3. Generate Reports
```bash
python3 main.py --report
```
Creates:
- `reports/report_YYYY-MM-DD_HH-MM-SS.txt` - Full summary
- `reports/metrics_YYYY-MM-DD.csv` - 24-hour metrics
- `reports/chart_cpu_*.png` - CPU chart
- `reports/chart_memory_*.png` - Memory chart
- `reports/chart_disk_*.png` - Disk chart
- `reports/chart_network_*.png` - Network chart

### 4. Clean Old Data
```bash
python3 main.py --clear-old
```
Deletes records older than 30 days (configurable).

## Run Tests

```bash
pytest tests/ -v
```

## Configuration

Edit `config.py` to customize:

```python
COLLECTION_INTERVAL_SECONDS = 60      # How often to collect
DATA_RETENTION_DAYS = 30              # How long to keep data
CPU_THRESHOLD = 85                    # Anomaly threshold %
MEMORY_THRESHOLD = 90                 # Anomaly threshold %
DISK_THRESHOLD = 80                   # Anomaly threshold %
CHART_DPI = 150                       # Chart resolution
```

## File Locations

- **Database:** `data/health_monitor.db` (SQLite)
- **Reports:** `reports/` (text, CSV, PNG)
- **Logs:** `logs/` (output directory)
- **Config:** `config.py` (all settings)

## Example Cron Job

Collect once every 5 minutes:

```bash
*/5 * * * * cd /path/to/linux_health_monitor && python3 main.py --collect-once
```

Generate reports daily at 2 AM:

```bash
0 2 * * * cd /path/to/linux_health_monitor && python3 main.py --report
```

## Output Examples

### Summary Report
```
================================================================================
LINUX SYSTEM HEALTH MONITOR - Report v1.0.0
================================================================================
Generated: 2024-01-15T10:30:45 UTC

CURRENT SYSTEM SNAPSHOT
CPU Usage:              45.3%
Memory Usage:           50.1% (8.0 GB/16.0 GB)
Swap Usage:             0.0 B/4.0 GB

TOP PROCESSES BY CPU
   PID NAME                  CPU %       MEM %
 12345 python              25.5       10.2
```

### CSV Export
```
collected_at,cpu_percent,memory_percent,network_bytes_sent,...
2024-01-15T10:00:00,45.2,50.1,1000000,...
2024-01-15T10:01:00,48.5,51.2,2000000,...
```

## Architecture

```
[Collector] → [Parser] → [Storage] → [Analyser] → [Reporter]
   (Raw)        (Valid)     (DB)      (Anomalies)  (Reports)
```

## Module Quick Reference

| Module | Purpose | Key Functions |
|--------|---------|---|
| collector/ | Gather metrics | get_cpu_metrics(), get_memory_metrics() |
| parser/ | Validate & normalize | validate_cpu_metrics(), normalize_snapshot() |
| storage/ | Database layer | insert_snapshot(), get_snapshots_by_range() |
| analyser/ | Detect & analyze | detect_anomalies(), analyze_trend() |
| reporter/ | Generate output | generate_summary_report(), export_metrics_to_csv() |
| scheduler/ | Run loop | CollectionScheduler.run_once(), run_continuous() |

## Troubleshooting

**Permission errors?**
```bash
sudo python3 main.py
```

**ModuleNotFoundError?**
```bash
pip3 install -r requirements.txt
```

**Database locked?**
- Ensure only one instance is running
- Stop any stuck processes: `pkill -f "python3 main.py"`

**No syslog data?**
- Check `/var/log/syslog` exists
- Edit `config.py` to set custom `SYSTEM_LOG_FILE`

**Charts not generating?**
- Ensure matplotlib is installed: `pip3 install matplotlib`
- Check disk space in `reports/` directory

## Key Metrics Explained

- **CPU %:** Overall system CPU usage (0-100%)
- **Load Average:** Number of processes waiting for CPU (1/5/15 min)
- **Memory %:** Used RAM as percentage of total
- **Disk %:** Used space as percentage per partition
- **Network Bytes:** Cumulative since system boot

## Anomaly Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| CPU | 85% | 95% | Check process list, review trends |
| Memory | 90% | 95% | May cause system slowdown |
| Disk | 80% | 95% | Clean up files or add storage |

---

For detailed documentation, see `README.md`
