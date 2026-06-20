"""
Main entry point for Linux System Health Monitor.

Command-line interface supporting three modes:
- --monitor: Continuous monitoring (default)
- --collect-once: Single collection cycle
- --report: Generate report from stored data
- --clear-old: Delete data older than retention period
- --dashboard: Run live dashboard with background collection
"""

import argparse
import logging
import sys
from pathlib import Path

from linux_health_monitor.config import (
    APP_NAME,
    COLLECTION_INTERVAL_SECONDS,
    DATA_RETENTION_DAYS,
    LOG_FORMAT,
    LOG_LEVEL,
    REPORT_OUTPUT_DIR,
    VERSION,
)
from linux_health_monitor.dashboard.app import run_dashboard
from linux_health_monitor.reporter.charts import generate_charts
from linux_health_monitor.reporter.csv_export import export_metrics_to_csv
from linux_health_monitor.reporter.summary import generate_summary_report
from linux_health_monitor.scheduler.runner import CollectionScheduler
from linux_health_monitor.storage.database import HealthMonitorDB, DatabaseError
from linux_health_monitor.system_info import get_startup_validation_summary


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        format=LOG_FORMAT,
        level=getattr(logging, LOG_LEVEL),
    )


def print_banner(interval_seconds: int = COLLECTION_INTERVAL_SECONDS) -> None:
    """Print application startup banner."""
    print(f"\n{'='*60}")
    print(f" {APP_NAME} v{VERSION}")
    print(f"{'='*60}")
    print(f" Collection Interval: {interval_seconds}s")
    print(f" Data Retention:      {DATA_RETENTION_DAYS} days")
    print(f" Report Output Dir:   {REPORT_OUTPUT_DIR}")
    print(f"{'='*60}\n")


def print_startup_validation_summary() -> None:
    """Print a concise startup health summary for live data sources."""
    summary = get_startup_validation_summary()
    if summary["verified"]:
        print("✅ All data sources verified live - no sample/mock data in use")
        return

    print("⚠️ Startup validation detected degraded sources:")
    for item in summary["degraded"]:
        print(f" - {item}")


def main() -> int:
    """
    Main entry point with command-line argument parsing.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    parser = argparse.ArgumentParser(
        description=f"{APP_NAME} - Monitor Linux system health and generate reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Run continuous monitoring
  python main.py --collect-once     # Single collection cycle
  python main.py --report           # Generate report from stored data
  python main.py --clear-old        # Delete data older than retention period
    python main.py --dashboard        # Run dashboard with background collector
        """
    )
    
    parser.add_argument('--version', action='version', version=f"{APP_NAME} {VERSION}")
    parser.add_argument(
        '--monitor',
        action='store_true',
        help='Run continuous monitoring loop (default)'
    )
    parser.add_argument(
        '--collect-once',
        action='store_true',
        help='Run one collection cycle and exit (for testing)'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate reports from stored data and exit'
    )
    parser.add_argument(
        '--clear-old',
        action='store_true',
        help=f'Delete data older than {DATA_RETENTION_DAYS} days and exit'
    )
    parser.add_argument(
        '--dashboard',
        action='store_true',
        help='Run live dashboard and background collection loop'
    )
    parser.add_argument(
        '--interval',
        type=int,
        help=(
            'Override collection interval in seconds for this run '
            f'(default: {COLLECTION_INTERVAL_SECONDS})'
        )
    )
    
    args = parser.parse_args()
    
    setup_logging()
    logger = logging.getLogger(__name__)
    
    interval_seconds = args.interval if args.interval is not None else COLLECTION_INTERVAL_SECONDS
    if interval_seconds <= 0:
        logger.error("--interval must be a positive integer")
        return 1

    print_banner(interval_seconds)
    
    try:
        db = HealthMonitorDB()
        
        if args.collect_once:
            print_startup_validation_summary()
            logger.info("Running single collection cycle...")
            scheduler = CollectionScheduler(interval_seconds)
            success = scheduler.run_once()
            return 0 if success else 1
        
        elif args.report:
            logger.info("Generating reports from stored data...")
            
            # Get latest snapshot for summary report
            from datetime import datetime, timedelta
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            snapshots = db.get_snapshots_by_range(start_time, end_time)
            
            if not snapshots:
                logger.error("No snapshots found in database for report generation")
                return 1
            
            latest = snapshots[-1]
            
            # Generate all reports
            report_path = generate_summary_report(db, latest)
            print(f"✓ Summary report: {report_path}")
            
            csv_path = export_metrics_to_csv(db, hours=24)
            print(f"✓ CSV export: {csv_path}")
            
            chart_paths = generate_charts(db, hours=24)
            for chart_path in chart_paths:
                print(f"✓ Chart: {chart_path}")
            
            logger.info("Report generation complete")
            return 0
        
        elif args.clear_old:
            logger.info(f"Clearing data older than {DATA_RETENTION_DAYS} days...")
            deleted = db.clear_old_data(DATA_RETENTION_DAYS)
            print(f"Deleted {deleted} old records")
            return 0

        elif args.dashboard:
            print_startup_validation_summary()
            logger.info("Starting dashboard mode...")
            run_dashboard(interval_seconds)
            return 0
        
        else:
            # Default: continuous monitoring
            print_startup_validation_summary()
            scheduler = CollectionScheduler(interval_seconds)
            scheduler.run_continuous()
            return 0
    
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
