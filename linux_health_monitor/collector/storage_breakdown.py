"""Read-only storage breakdown by category for dashboard display."""

from __future__ import annotations

import os
import platform
import plistlib
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

GAME_NAME_KEYWORDS = [
    "sims",
    "minecraft",
    "fortnite",
    "roblox",
    "league of legends",
    "valorant",
    "fifa",
    "call of duty",
]

NON_GAME_NAME_OVERRIDES = [
    "microsoft word",
    "microsoft excel",
    "microsoft powerpoint",
    "microsoft outlook",
    "microsoft teams",
    "microsoft onenote",
    "google chrome",
    "mozilla firefox",
    "firefox",
    "safari",
    "microsoft edge",
]

GAME_PLATFORM_FOLDER_NAMES_DARWIN = [
    "Steam",
    "Epic Games",
    "Epic",
    "Battle.net",
    "Riot Games",
    "EA",
    "Ubisoft Connect",
    "Ubisoft Game Launcher",
]

GAME_PLATFORM_FOLDER_NAMES_WINDOWS = [
    "Steam",
    "Epic Games",
    "Battle.net",
    "Riot Games",
    "EA Games",
    "Ubisoft Game Launcher",
]


def collect_storage_breakdown(disk_partitions: dict[str, dict[str, Any]], top_n: int = 5) -> dict[str, Any]:
    """Return category totals and top items for dashboard display."""
    home = Path.home()
    system_name = platform.system().lower()

    category_items: dict[str, list[dict[str, Any]]] = {key: [] for key in CATEGORY_ORDER}

    game_claimed_paths: set[str] = set()
    _collect_games(category_items["games"], home, system_name, game_claimed_paths)
    _collect_applications(category_items["applications"], home, system_name, game_claimed_paths)
    _collect_documents(category_items["documents"], home)
    _collect_media(category_items["media"], home)
    _collect_downloads(category_items["downloads"], home)

    used_total = int(sum(int(part.get("used", 0)) for part in disk_partitions.values()))

    # Global mutual-exclusivity pass: a path claimed by an earlier category
    # (games takes priority) is dropped from every later category.
    seen_paths: set[str] = set()
    category_totals: dict[str, int] = {}
    for key in CATEGORY_ORDER:
        if key == "system":
            continue
        deduped = []
        for item in _dedupe_items(category_items[key]):
            path = str(item["path"])
            if path in seen_paths:
                continue
            seen_paths.add(path)
            deduped.append(item)
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


def _collect_games(items: list[dict[str, Any]], home: Path, system_name: str, claimed_paths: set[str]) -> None:
    # Known game-launcher folders: anything installed under these is a game.
    for root in _game_platform_roots(home, system_name):
        if not _valid_dir(root):
            continue
        common = root / "steamapps" / "common"
        scan_root = common if _valid_dir(common) else root
        for child in _top_level_items(scan_root):
            size = _safe_dir_size(child)
            if size <= 0:
                continue
            items.append(_item_payload(child, size))
            claimed_paths.add(str(child))

    # Apps living directly in /Applications (or ~/Applications) are only
    # games if their name or OS-reported category says so.
    app_roots = _application_roots(home, system_name)
    for root in app_roots:
        if not _valid_dir(root):
            continue
        for item in _top_level_items(root):
            path_str = str(item)
            if path_str in claimed_paths:
                continue
            if not _is_game_app(item, system_name):
                continue
            size = _safe_dir_size(item)
            if size > 0:
                items.append(_item_payload(item, size))
                claimed_paths.add(path_str)


def _collect_applications(
    items: list[dict[str, Any]], home: Path, system_name: str, claimed_paths: set[str]
) -> None:
    for root in _application_roots(home, system_name):
        if not _valid_dir(root):
            continue
        for item in _top_level_items(root):
            if str(item) in claimed_paths:
                continue
            size = _safe_dir_size(item)
            if size > 0:
                items.append(_item_payload(item, size))


def _application_roots(home: Path, system_name: str) -> list[Path]:
    if system_name == "windows":
        return [
            Path(os.environ.get("ProgramFiles", "")),
            Path(os.environ.get("ProgramFiles(x86)", "")),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs",
        ]
    if system_name == "darwin":
        return [Path("/Applications"), home / "Applications"]
    return [Path("/opt"), Path("/usr/local"), home / ".local" / "share"]


def _game_platform_roots(home: Path, system_name: str) -> list[Path]:
    if system_name == "windows":
        bases = [Path(os.environ.get("ProgramFiles", "")), Path(os.environ.get("ProgramFiles(x86)", ""))]
        return [base / name for base in bases for name in GAME_PLATFORM_FOLDER_NAMES_WINDOWS if str(base)]
    if system_name == "darwin":
        support = home / "Library" / "Application Support"
        return [support / name for name in GAME_PLATFORM_FOLDER_NAMES_DARWIN]
    return [home / ".steam", home / ".local" / "share" / "Steam"]


def _is_game_app(path: Path, system_name: str) -> bool:
    name_lower = path.name.lower()
    if any(token in name_lower for token in NON_GAME_NAME_OVERRIDES):
        return False
    if any(token in name_lower for token in GAME_NAME_KEYWORDS):
        return True
    if system_name == "darwin":
        category = _macos_app_category(path)
        if category and "game" in category:
            return True
    return False


def _macos_app_category(app_path: Path) -> str:
    """Best-effort lookup of an app's OS-reported category/genre on macOS."""
    candidates = [app_path / "Contents" / "Info.plist"]

    wrapper_dir = app_path / "Wrapper"
    if _valid_dir(wrapper_dir):
        for child in _top_level_items(wrapper_dir):
            if child.suffix == ".app":
                candidates.append(child / "Info.plist")
        candidates.append(wrapper_dir / "iTunesMetadata.plist")

    for plist_path in candidates:
        if not plist_path.is_file():
            continue
        try:
            with open(plist_path, "rb") as fh:
                data = plistlib.load(fh)
        except Exception:
            continue

        category = str(data.get("LSApplicationCategoryType", "")).strip().lower()
        if category:
            return category

        genre = str(data.get("genre", "")).strip().lower()
        if genre:
            return genre

    return ""


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
