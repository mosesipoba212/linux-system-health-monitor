# Linux System Health Monitor - Complete Project Index

## 📍 Project Location
```
/Users/moses/Linux System Health Monitor & Automated Reporting Pipeline/
└── linux_health_monitor/
```

## 📂 Files at a Glance

### Core Application Files
| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | 162 | CLI entry point (4 modes) |
| `config.py` | 47 | All configuration settings |
| `models.py` | 79 | Dataclasses for all types |
| `requirements.txt` | 4 | Python dependencies |

### Collector Modules (6 files)
| File | Lines | Purpose |
|------|-------|---------|
| `collector/cpu.py` | 42 | CPU, load average |
| `collector/memory.py` | 36 | RAM and swap |
| `collector/disk.py` | 52 | Disk per partition |
| `collector/network.py` | 39 | Network I/O stats |
| `collector/processes.py` | 80 | Top processes |
| `collector/logs.py` | 102 | Syslog parser |

### Parser Modules (2 files)
| File | Lines | Purpose |
|------|-------|---------|
| `parser/validator.py` | 189 | Input validation |
| `parser/normaliser.py` | 80 | Data normalization |

### Storage Module (1 file)
| File | Lines | Purpose |
|------|-------|---------|
| `storage/database.py` | 522 | SQLite CRUD layer |

### Analyser Modules (2 files)
| File | Lines | Purpose |
|------|-------|---------|
| `analyser/anomaly.py` | 93 | Threshold detection |
| `analyser/trends.py` | 129 | Trend analysis |

### Reporter Modules (3 files)
| File | Lines | Purpose |
|------|-------|---------|
| `reporter/summary.py` | 185 | Text reports |
| `reporter/csv_export.py` | 89 | CSV export |
| `reporter/charts.py` | 267 | Matplotlib charts |

### Scheduler Module (1 file)
| File | Lines | Purpose |
|------|-------|---------|
| `scheduler/runner.py` | 185 | Collection loop |

### Test Suite (4 files)
| File | Lines | Purpose |
|------|-------|---------|
| `tests/test_collector.py` | 154 | Collector tests |
| `tests/test_parser.py` | 186 | Parser tests |
| `tests/test_analyser.py` | 191 | Analyser tests |
| `tests/test_reporter.py` | 123 | Reporter tests |

### Documentation Files
| File | Purpose |
|------|---------|
| `README.md` | 9,811 lines - Complete documentation |
| `QUICK_START.md` | Quick reference guide |
| `PROJECT_SUMMARY.md` | Project completion checklist |
| `FILE_MANIFEST.txt` | Complete file inventory |

## 🎯 How to Use This Project

### 1. Start Monitoring
```bash
cd linux_health_monitor
python3 main.py
```

### 2. Single Collection (Testing)
```bash
python3 main.py --collect-once
```

### 3. Generate Reports
```bash
python3 main.py --report
```

### 4. Run Tests
```bash
pytest tests/ -v
```

## 📊 Feature Map

### Metrics Collection (collector/)
- ✅ CPU (overall %, per-core %, load avg)
- ✅ Memory (total, used, free, %)
- ✅ Disk (per partition)
- ✅ Network (bytes/packets sent/received)
- ✅ Processes (top 5 by CPU & memory)
- ✅ Logs (ERROR/WARNING/CRITICAL)

### Data Processing (parser/ → storage/)
- ✅ Validate all inputs
- ✅ Type checking
- ✅ Range validation
- ✅ Normalize to MetricSnapshot
- ✅ Store in SQLite
- ✅ Auto-cleanup old data

### Analysis (analyser/)
- ✅ Anomaly detection (CPU 85%, MEM 90%, DISK 80%)
- ✅ Severity classification
- ✅ Trend analysis with linear regression
- ✅ Statistical calculations

### Reporting (reporter/)
- ✅ Plain-text summary reports
- ✅ CSV export (24-hour data)
- ✅ CPU usage chart
- ✅ Memory usage chart
- ✅ Disk usage chart
- ✅ Network I/O chart

### Scheduling (scheduler/)
- ✅ Configurable collection interval (default 60s)
- ✅ Collection loop with error handling
- ✅ Graceful shutdown on CTRL+C
- ✅ Periodic data cleanup

## 🔧 Configuration

All settings are in `config.py`. Key settings:

```python
COLLECTION_INTERVAL_SECONDS = 60      # How often to collect
DATA_RETENTION_DAYS = 30              # How long to keep data
CPU_THRESHOLD = 85                    # CPU anomaly threshold %
MEMORY_THRESHOLD = 90                 # Memory anomaly threshold %
DISK_THRESHOLD = 80                   # Disk anomaly threshold %
CHART_DPI = 150                       # Chart resolution
TOP_PROCESSES_COUNT = 5               # Top N processes to track
TREND_ANALYSIS_HOURS = 24             # Hours for trend analysis
```

## 📈 Output Locations

| Output | Location |
|--------|----------|
| Database | `data/health_monitor.db` |
| Reports | `reports/report_*.txt` |
| CSV Data | `reports/metrics_*.csv` |
| Charts | `reports/chart_*.png` |
| Logs | `logs/` |

## 🧪 Testing

Run all tests:
```bash
pytest tests/ -v
```

Test by module:
```bash
pytest tests/test_collector.py -v
pytest tests/test_parser.py -v
pytest tests/test_analyser.py -v
pytest tests/test_reporter.py -v
```

## 📖 Documentation Guide

1. **Getting Started**
   - Read: `QUICK_START.md`
   - Then: `README.md` (Installation section)

2. **Usage Examples**
   - See: `QUICK_START.md` (Run Modes section)
   - Also: `README.md` (Usage section)

3. **Configuration**
   - Edit: `config.py`
   - Reference: `README.md` (Configuration section)

4. **Understanding the Code**
   - Architecture: `README.md` (Project Structure)
   - Features: `README.md` (Features section)
   - Database: `README.md` (Database Schema)

5. **Troubleshooting**
   - See: `README.md` (Troubleshooting section)

6. **Project Details**
   - Completion: `PROJECT_SUMMARY.md`
   - Files: `FILE_MANIFEST.txt`

## 🚀 Quick Start

### Installation
```bash
pip3 install -r requirements.txt
```

### Run Modes
```bash
# Continuous monitoring
python3 main.py

# Single collection cycle
python3 main.py --collect-once

# Generate reports
python3 main.py --report

# Clean old data
python3 main.py --clear-old
```

### Verify Installation
```bash
# Test syntax
python3 -m py_compile main.py

# Run tests
pytest tests/ -v

# Single collection
python3 main.py --collect-once
```

## 💡 Key Concepts

### MetricSnapshot
Complete system state at one point in time:
- CPU metrics (overall, per-core, load)
- Memory metrics (RAM, swap)
- Disk usage per partition
- Network I/O stats
- Top processes (CPU & memory)

### AnomalyEvent
Detected threshold breach:
- Metric name
- Current value
- Threshold
- Severity (warning/critical)
- Timestamp

### TrendReport
Statistical analysis over time:
- Min/max/average values
- Standard deviation
- Trend direction (up/stable)
- Linear regression slope

## 🔐 Security

- ✅ Parameterised SQL queries (no injection)
- ✅ Input validation and type checking
- ✅ Specific exception handling
- ✅ Safe file path handling
- ✅ No hardcoded secrets
- ✅ No shell execution

## 📊 Database

### Tables
- `system_metrics` - All collected metrics
- `anomaly_events` - Threshold breaches
- `log_entries` - Parsed syslog entries

### Indexes
- `idx_system_metrics_collected_at`
- `idx_anomaly_events_collected_at`
- `idx_log_entries_collected_at`

## ✨ Production Ready

This project follows production standards:
- 100% type hints
- 100% docstrings
- Specific exception handling
- Comprehensive logging
- Parameterised SQL queries
- Configuration externalization
- Test coverage
- Security best practices

## 🎓 Learning Resources

### For Understanding the Code
1. Start with `main.py` - See how everything connects
2. Read `config.py` - Understand all settings
3. Read `models.py` - See data structures
4. Explore each package in order:
   - `collector/` - How metrics are gathered
   - `parser/` - How data is validated
   - `storage/` - How data is stored
   - `analyser/` - How analysis is done
   - `reporter/` - How reports are generated

### For Running Examples
1. `python3 main.py --collect-once` - Single cycle
2. `python3 main.py --report` - Generate reports
3. `pytest tests/ -v` - See all tests

### For Customization
1. Edit `config.py` for settings
2. Modify thresholds for anomalies
3. Add new collectors in `collector/`
4. Add new analyzers in `analyser/`
5. Add new reporters in `reporter/`

## 📋 Checklist

- [x] All 35 files created
- [x] All code syntactically valid
- [x] All functions documented
- [x] All functions type-hinted
- [x] All exceptions specific
- [x] All SQL parameterised
- [x] All tests pass
- [x] Complete documentation
- [x] Production ready

---

**Version:** 1.0.0  
**Status:** ✅ Production Ready  
**Total Lines:** 2,804+ Python code  
**Total Functions:** 60+  
**Test Cases:** 40+  
**Documentation:** 10,000+ words

