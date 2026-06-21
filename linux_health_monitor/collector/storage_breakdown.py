"""Read-only storage breakdown by category for dashboard display."""

from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any

CATEGORY_ORDER = [
    "games",
    "applications",
    "documents",
    "media",
    "downloads",
    "system",
]

CATEGORY_LABELS = {
    "games": "Games",
    "applications": "Applications/Programs",
    "documents": "Documents",
    "media": "Photos, Videos & Media",
    "downloads": "Downloads",
    "system": "System/OS",
}


def collect_storage_breakdown(disk_partitions: dict[str, dict[str, Any]], top_n: int = 5) -> dict[str, Any]:
    """Return category totals and top items for dashboard display."""
    home = Path.home()
    system_name = platform.system().lower()

    category_items: dict[str, list[dict[str, Any]]] = {key: [] for key in CATEGORY_ORDER}

    _collect_games(category_items["games"], home, system_name)
    _collect_applications(category_items["applications"], home, system_name)
    _collect_documents(category_items["documents"], home)
    _collect_media(category_items["media"], home)
    _collect_downloads(category_items["downloads"], home)

    used_total = int(sum(int(part.get("used", 0)) for part in disk_partitions.values()))

    category_totals: dict[str, int] = {}
    for key in CATEGORY_ORDER:
        if key == "system":
            continue
        deduped = _dedupe_items(category_items[key])
        category_items[key] = deduped
        category_totals[key] = int(sum(item["size_bytes"] for item in deduped))

    non_system_total = int(sum(category_totals.values()))
    system_total = max(used_total - non_system_total, 0)
    category_totals["system"] = system_total
    category_items["system"] = []

    categories_payload = []
    for key in CATEGORY_ORDER:
        items = sorted(category_items.get(key, []), key=lambda item: int(item["size_bytes"]), reverse=True)[:top_n]
        categories_payload.append(
            {
                "key": key,
                "label": CATEGORY_LABELS[key],
                "total_size_bytes": int(category_totals.get(key, 0)),
                "top_items": [
                    {
                        "name": item["name"],
                        "path": item["path"],
                        "size_bytes": int(item["size_bytes"]),
                    }
                    for item in items
                ],
            }
        )

    return {
        "generated_at": None,
        "total_used_bytes": used_total,
        "categories": categories_payload,
    }


def _collect_games(items: list[dict[str, Any]], home: Path, system_name: str) -> None:
    if system_name == "windows":
        roots = [
            Path(os.environ.get("ProgramFiles", "")) / "Steam",
            Path(os.environ.get("ProgramFiles", "")) / "Epic Games",
            Path(os.environ.get("ProgramFiles", "")) / "Battle.net",
            Path(os.environ.get("ProgramFiles", "")) / "WindowsApps",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Steam",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Epic Games",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "Battle.net",
            Path(os.environ.get("ProgramFiles(x86)", "")) / "WindowsApps",
        ]
    elif system_name == "darwin":
        roots = [Path("/Applications"), home / "Applications"]
    else:
        roots = [home / ".steam", home / ".local" / "share" / "Steam"]

    for root in roots:
        if not _valid_dir(root):
            continue
        if system_name == "darwin":
            # On macOS, treat large application bundles as likely game installs.
            for item in _top_level_items(root):
                size = _safe_dir_size(item)
                if size >= 1024**3:
                    items.append(_item_payload(item, size))
            continue

        size = _safe_dir_size(root)
        if size > 0:
            items.append(_item_payload(root, size))
        for child in _top_level_items(root):
            child_size = _safe_dir_size(child)
            if child_size > 0:
                items.append(_item_payload(child, child_size))


def _collect_applications(items: list[dict[str, Any]], home: Path, system_name: str) -> None:
    if system_name == "windows":
        roots = [
            Path(os.environ.get("ProgramFiles", "")),
            Path(os.environ.get("ProgramFiles(x86)", "")),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
        ]
    elif system_name == "darwin":
        roots = [Path("/Applications"), home / "Applications"]
    else:
        roots = [Path("/opt"), Path("/usr/local"), home / ".local" / "share"]

    for root in roots:
        if not _valid_dir(root):
            continue
        for item in _top_level_items(root):
            size = _safe_dir_size(item)
            if size > 0:
                items.append(_item_payload(item, size))


def _collect_documents(items: list[dict[str, Any]], home: Path) -> None:
    documents = home / "Documents"
    if not _valid_dir(documents):
        return
    for item in _top_level_items(documents):
        size = _safe_dir_size(item)
        if size > 0:
            items.append(_item_payload(item, size))


def _collect_media(items: list[dict[str, Any]], home: Path) -> None:
    roots = [home / "Pictures", home / "Photos", home / "Movies", home / "Videos", home / "Music"]
    for root in roots:
        if not _valid_dir(root):
            continue
        for item in _top_level_items(root):
            size = _safe_dir_size(item)
            if size > 0:
                items.append(_item_payload(item, size))


def _collect_downloads(items: list[dict[str, Any]], home: Path) -> None:
    downloads = home / "Downloads"
    if not _valid_dir(downloads):
        return
    for item in _top_level_items(downloads):
        size = _safe_dir_size(item)
        if size > 0:
            items.append(_item_payload(item, size))


def _valid_dir(path: Path) -> bool:
    return bool(str(path)) and path.exists() and path.is_dir()


def _top_level_items(root: Path) -> list[Path]:
    try:
        children = [child for child in root.iterdir() if not child.name.startswith(".")]
    except (OSError, PermissionError):
        return []
    return children


def _safe_dir_size(path: Path) -> int:
    try:
        if path.is_file():
            return int(path.stat().st_size)
        total = 0
        for dirpath, _, filenames in os.walk(path, onerror=lambda _err: None):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                try:
                    total += int(file_path.stat().st_size)
                except (OSError, PermissionError):
                    continue
        return total
    except (OSError, PermissionError):
        return 0


def _item_payload(path: Path, size: int) -> dict[str, Any]:
    return {
        "name": path.name or str(path),
        "path": str(path),
        "size_bytes": int(size),
    }


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for item in items:
        path = str(item.get("path", ""))
        if not path or path in seen:
            continue
        seen.add(path)
        result.append(item)
    return result
