"""Flask dashboard for live system health metrics."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Any

from flask import Flask, jsonify, render_template

from linux_health_monitor.analyser.anomaly import detect_anomalies
from linux_health_monitor.collector.cpu import get_cpu_metrics
from linux_health_monitor.collector.disk import get_disk_metrics
from linux_health_monitor.collector.logs import parse_syslog
from linux_health_monitor.collector.memory import get_memory_metrics
from linux_health_monitor.collector.network import get_network_metrics
from linux_health_monitor.collector.processes import get_top_processes
from linux_health_monitor.collector.storage_breakdown import collect_storage_breakdown
from linux_health_monitor.config import DB_PATH
from linux_health_monitor.models import MetricSnapshot, ProcessInfo
from linux_health_monitor.parser.normaliser import normalize_snapshot
from linux_health_monitor.parser.validator import (
    validate_cpu_metrics,
    validate_disk_metrics,
    validate_memory_metrics,
    validate_network_metrics,
    validate_process_info,
)
from linux_health_monitor.scheduler.runner import CollectionScheduler
from linux_health_monitor.storage.database import HealthMonitorDB
from linux_health_monitor.system_info import get_system_info

logger = logging.getLogger(__name__)

STORAGE_BREAKDOWN_CACHE_TTL_SECONDS = 300

_storage_state_lock = threading.Lock()
_storage_cache: dict[str, Any] = {
    "payload": None,
    "cached_at": None,
}


def create_app(interval_seconds: int = 5) -> Flask:
    """Create and configure the Flask dashboard app."""
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.route("/")
    def index() -> str:
        return render_template("index.html", interval_seconds=interval_seconds)

    @app.route("/api/latest")
    def latest() -> Any:
        payload = _build_dashboard_payload(interval_seconds)
        return jsonify(payload)

    @app.route("/api/system-info")
    def system_info() -> Any:
        return jsonify(get_system_info())

    return app


def run_dashboard(interval_seconds: int = 5) -> None:
    """Start continuous collection in a background thread and run dashboard server."""
    scheduler = CollectionScheduler(interval_seconds)
    worker = threading.Thread(target=scheduler.run_continuous, daemon=True, name="collector-thread")
    worker.start()

    app = create_app(interval_seconds)
    logger.info("Dashboard available at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


def _build_dashboard_payload(interval_seconds: int) -> dict[str, Any]:
    system_info = get_system_info()
    try:
        snapshot = _collect_live_snapshot()
    except Exception as exc:
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "has_data": False,
            "message": f"Unable to collect live metrics: {exc}",
            "system_info": system_info,
        }

    anomalies = detect_anomalies(snapshot)
    active_anomalies = [
        {
            "metric": item.metric_name,
            "severity": item.severity,
            "message": item.message,
        }
        for item in anomalies
    ]

    db = HealthMonitorDB()
    log_source = system_info["log_source"]
    if log_source.get("available"):
        recent_logs = _dedupe_recent_logs(db.get_recent_logs(limit=200), limit=10)
        recent_logs_message = ""
    else:
        recent_logs = []
        recent_logs_message = "No accessible system log on this device"

    history = _get_network_history(limit=30)

    disk_items = []
    for mount_point, partition in snapshot.disk_partitions.items():
        disk_items.append(
            {
                "mount": mount_point,
                "usage_percent": float(partition.get("percent", 0.0)),
                "used": int(partition.get("used", 0)),
                "total": int(partition.get("total", 0)),
            }
        )
    disk_items = _filter_and_label_disk_items(disk_items)

    top_cpu = [
        {
            "pid": proc.pid,
            "name": proc.name,
            "cpu_percent": proc.cpu_percent,
            "memory_percent": proc.memory_percent,
        }
        for proc in snapshot.top_cpu_processes[:5]
    ]
    top_memory = [
        {
            "pid": proc.pid,
            "name": proc.name,
            "cpu_percent": proc.cpu_percent,
            "memory_percent": proc.memory_percent,
        }
        for proc in snapshot.top_memory_processes[:5]
    ]

    cutoff = datetime.utcnow() - timedelta(seconds=max(10, interval_seconds * 3))
    active_recent = [
        item
        for item in db.get_recent_anomalies(limit=100)
        if item.collected_at >= cutoff
    ]

    # Keep "current" anomalies strongly tied to the latest snapshot and merge in recent entries.
    recent_anomaly_messages = {
        item.message: {
            "metric": item.metric_name,
            "severity": item.severity,
            "message": item.message,
        }
        for item in active_recent
    }
    for item in active_anomalies:
        recent_anomaly_messages[item["message"]] = item

    storage_breakdown = _build_storage_breakdown_payload(snapshot.disk_partitions)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "has_data": True,
        "latest_collected_at": snapshot.collected_at.isoformat(),
        "system_info": system_info,
        "cpu_percent": snapshot.cpu_percent,
        "memory_percent": snapshot.memory_percent,
        "disk_usage": disk_items,
        "disk_chart_note": "Showing top partitions by usage. System/snapshot volumes hidden for clarity.",
        "storage_breakdown": storage_breakdown,
        "network": history,
        "top_cpu_processes": top_cpu,
        "top_memory_processes": top_memory,
        "active_anomalies": list(recent_anomaly_messages.values()),
        "recent_logs_message": recent_logs_message,
        "recent_logs": [
            {
                "timestamp": entry.timestamp.isoformat(),
                "severity": entry.severity,
                "source": entry.source,
                "message": entry.message,
            }
            for entry in recent_logs
        ],
    }


def _collect_live_snapshot() -> MetricSnapshot:
    """Collect a fresh snapshot directly from psutil-backed collectors."""
    cpu_data = get_cpu_metrics()
    validate_cpu_metrics(cpu_data)

    memory_data = get_memory_metrics()
    validate_memory_metrics(memory_data)

    disk_data = get_disk_metrics()
    validate_disk_metrics(disk_data)

    network_data = get_network_metrics()
    validate_network_metrics(network_data)

    top_cpu_processes, top_memory_processes = get_top_processes(5)
    process_data = [vars(proc) for proc in (top_cpu_processes + top_memory_processes)]
    validate_process_info(process_data)

    return normalize_snapshot(
        cpu_data,
        memory_data,
        disk_data,
        network_data,
        top_cpu_processes,
        top_memory_processes,
    )


def _dedupe_recent_logs(entries: list[Any], limit: int = 10) -> list[Any]:
    """Remove repeated entries with the same message in the same minute and keep newest first."""
    # Sort by the event timestamp (not collected_at) so display reflects real log recency.
    sorted_entries = sorted(entries, key=lambda item: item.timestamp, reverse=True)
    deduped: list[Any] = []
    seen: set[tuple[str, str]] = set()

    for entry in sorted_entries:
        minute_key = _extract_event_minute(entry)
        message_key = _normalize_log_message_for_dedupe(entry.message)
        key = (message_key, minute_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
        if len(deduped) >= limit:
            break

    return deduped


def _extract_event_minute(entry: Any) -> str:
    """Extract event minute from the raw log line, falling back to parsed timestamp."""
    text = str(entry.message)

    iso_match = re.match(r"^(\d{4}-\d{2}-\d{2})[T\s](\d{2}:\d{2})", text)
    if iso_match:
        return f"{iso_match.group(1)}T{iso_match.group(2)}"

    # Typical syslog prefix: "Jun 20 09:21:42 ..."
    syslog_match = re.match(r"^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2})(?::\d{2})", text)
    if syslog_match:
        return f"{entry.timestamp.year}-{syslog_match.group(1)}"

    return entry.timestamp.strftime("%Y-%m-%dT%H:%M")


def _normalize_log_message_for_dedupe(message: str) -> str:
    """Strip timestamp prefixes so dedupe is based on semantic message text."""
    text = message.strip()

    # Remove common leading timestamp forms.
    text = re.sub(r"^\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\s+", "", text)
    text = re.sub(r"^[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+", "", text)

    # Prefer the part from the first severity keyword to reduce host/service noise.
    severity_match = re.search(r"\b(CRITICAL|ERROR|WARNING)\b.*", text, re.IGNORECASE)
    if severity_match:
        return severity_match.group(0).lower()

    return text.lower()


def _get_latest_snapshot_row() -> dict[str, Any] | None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM system_metrics ORDER BY collected_at DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None


def _get_network_history(limit: int = 30) -> dict[str, list[Any]]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT collected_at, network_bytes_sent, network_bytes_recv
            FROM system_metrics
            ORDER BY collected_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = list(reversed(cursor.fetchall()))

    return {
        "timestamps": [row["collected_at"] for row in rows],
        "bytes_sent": [row["network_bytes_sent"] for row in rows],
        "bytes_recv": [row["network_bytes_recv"] for row in rows],
    }


def _snapshot_from_row(row: dict[str, Any]) -> MetricSnapshot:
    return MetricSnapshot(
        collected_at=datetime.fromisoformat(row["collected_at"]),
        cpu_percent=row["cpu_percent"],
        cpu_per_core=json.loads(row["cpu_per_core"]),
        load_avg_1=row["load_avg_1"],
        load_avg_5=row["load_avg_5"],
        load_avg_15=row["load_avg_15"],
        memory_total=row["memory_total"],
        memory_used=row["memory_used"],
        memory_free=row["memory_free"],
        memory_percent=row["memory_percent"],
        swap_used=row["swap_used"],
        swap_total=row["swap_total"],
        disk_partitions=json.loads(row["disk_partitions"]),
        network_bytes_sent=row["network_bytes_sent"],
        network_bytes_recv=row["network_bytes_recv"],
        network_packets_sent=row["network_packets_sent"],
        network_packets_recv=row["network_packets_recv"],
        network_errin=row["network_errin"],
        network_errout=row["network_errout"],
        top_cpu_processes=[
            ProcessInfo(**item) for item in json.loads(row["top_cpu_processes"])
        ],
        top_memory_processes=[
            ProcessInfo(**item) for item in json.loads(row["top_memory_processes"])
        ],
    )


def _filter_and_label_disk_items(items: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    """Filter noisy system/internal volumes and provide short labels for display."""
    filtered: list[dict[str, Any]] = []

    for item in items:
        mount = str(item.get("mount", "")).strip()
        usage = float(item.get("usage_percent", 0.0))
        if not mount:
            continue

        is_root = mount == "/"
        if not is_root and usage <= 0:
            continue
        if not is_root and _is_internal_mount(mount):
            continue

        enriched = dict(item)
        enriched["label"] = _derive_mount_label(mount)
        filtered.append(enriched)

    # Keep best entry per display label so aliases like update/mnt1 do not clutter the chart.
    by_label: dict[str, dict[str, Any]] = {}
    for item in filtered:
        label = str(item.get("label", item.get("mount", "")))
        existing = by_label.get(label)
        if existing is None or float(item.get("usage_percent", 0.0)) > float(existing.get("usage_percent", 0.0)):
            by_label[label] = item

    result = list(by_label.values())
    # Keep most relevant partitions first by fullness.
    result.sort(key=lambda part: float(part.get("usage_percent", 0.0)), reverse=True)
    return result[:limit]


def _is_internal_mount(mount: str) -> bool:
    """Return True for mounts that are typically internal/noisy system volumes."""
    lowered = mount.lower()
    blocked_tokens = ("preboot", "vm", "xarts", "hardware", "recovery", "snapshot")
    if any(token in lowered for token in blocked_tokens):
        return True

    parts = [segment for segment in mount.split("/") if segment]
    if not parts:
        return False

    for segment in parts:
        if _looks_like_uuid_or_hash(segment):
            return True

    return False


def _looks_like_uuid_or_hash(text: str) -> bool:
    """Heuristic for UUID/hash-style path segments that are not user-friendly labels."""
    candidate = text.strip()
    if len(candidate) < 16:
        return False

    compact = candidate.replace("-", "")
    if re.fullmatch(r"[0-9a-fA-F]+", compact):
        return True

    return bool(re.fullmatch(r"[A-Za-z0-9_-]{24,}", candidate))


def _derive_mount_label(mount: str) -> str:
    """Produce short human-readable labels for chart x-axis."""
    if mount == "/":
        return "Root (/)"

    lowered = mount.lower()
    if "/system/volumes/update/" in lowered:
        return "Update"
    if "/system/volumes/data" in lowered:
        return "Data"
    if "/system/volumes/" in lowered:
        return "System"

    parts = [segment for segment in mount.split("/") if segment]
    if not parts:
        return mount

    last = parts[-1]
    cleaned = last.replace("_", " ").strip()
    if not cleaned:
        return mount

    if cleaned.isupper() or cleaned.islower():
        cleaned = cleaned.title()

    return cleaned


def _build_storage_breakdown_payload(disk_partitions: dict[str, dict[str, Any]], force_refresh: bool = False) -> dict[str, Any]:
    breakdown = _ensure_storage_breakdown_cache(disk_partitions=disk_partitions, force_refresh=force_refresh)
    with _storage_state_lock:
        cached_at = _storage_cache.get("cached_at")

    cache_age_seconds: int | None = None
    if isinstance(cached_at, datetime):
        cache_age_seconds = max(int((datetime.utcnow() - cached_at).total_seconds()), 0)

    return {
        **breakdown,
        "cache_ttl_seconds": STORAGE_BREAKDOWN_CACHE_TTL_SECONDS,
        "cache_age_seconds": cache_age_seconds,
    }


def _ensure_storage_breakdown_cache(disk_partitions: dict[str, dict[str, Any]], force_refresh: bool = False) -> dict[str, Any]:
    with _storage_state_lock:
        cached_payload = _storage_cache.get("payload")
        cached_at = _storage_cache.get("cached_at")
        cache_is_fresh = (
            cached_payload is not None
            and isinstance(cached_at, datetime)
            and (datetime.utcnow() - cached_at) < timedelta(seconds=STORAGE_BREAKDOWN_CACHE_TTL_SECONDS)
        )
        if cache_is_fresh and not force_refresh:
            return dict(_storage_cache["payload"])

    breakdown = collect_storage_breakdown(disk_partitions)
    breakdown["generated_at"] = datetime.utcnow().isoformat()

    with _storage_state_lock:
        _storage_cache["payload"] = breakdown
        _storage_cache["cached_at"] = datetime.utcnow()

    return dict(breakdown)
