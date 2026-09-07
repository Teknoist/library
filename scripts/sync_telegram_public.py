#!/usr/bin/env python3
"""Build telegram.json from public Telegram channel file messages."""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "telegram.json"
META = ROOT / "telegram_meta.json"
DEFAULT_CHANNELS = "DentalCADCAMLibrary,ExoCADCAMLibrary"
ALLOWED = {
    extension.strip().lower()
    for extension in os.getenv("TG_ALLOWED_EXTENSIONS", ".zip,.7z,.rar,.stl,.obj,.ply,.dme,.xml,.library,.implant").split(",")
    if extension.strip().startswith(".")
}


def positive_int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def non_negative_float(name: str, default: float) -> float:
    value = float(os.getenv(name, str(default)))
    if value < 0:
        raise ValueError(f"{name} must not be negative")
    return value


def normalize_channel(value: str) -> str:
    value = value.strip().lstrip("@")
    if value.startswith(("https://", "http://")):
        parsed = urlparse(value)
        if parsed.hostname not in {"t.me", "www.t.me"}:
            raise ValueError(f"Unsupported Telegram host: {parsed.hostname}")
        value = parsed.path.strip("/").removeprefix("s/")
    if not re.fullmatch(r"[A-Za-z0-9_]{5,64}", value):
        raise ValueError(f"Invalid Telegram channel: {value!r}")
    return value


CHANNELS = [normalize_channel(channel) for channel in (os.getenv("TG_CHANNELS") or os.getenv("TG_CHANNEL") or DEFAULT_CHANNELS).split(",") if channel.strip()]
PAGES = positive_int("TG_PAGES", 25)
DELAY = non_negative_float("TG_DELAY", 0.6)


def clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def has_allowed_extension(name: str) -> bool:
    return any(name.lower().endswith(extension) for extension in ALLOWED)


def message_id_from_post(post: str) -> int | None:
    try:
        return int(post.rsplit("/", 1)[1])
    except (AttributeError, IndexError, ValueError):
        return None


def fetch(url: str, attempts: int = 3) -> str:
    headers = {"User-Agent": "Mozilla/5.0 library-sync/1.1"}
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, headers=headers, timeout=(10, 30))
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            if attempt == attempts:
                raise
            time.sleep(attempt)
    raise RuntimeError("Unreachable")


def valid_next_url(url: str | None, channel: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.netloc == "t.me" and parsed.path == f"/s/{channel}"


def parse_page(html: str, channel: str, base_url: str) -> tuple[list[dict], str | None, int]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    messages = soup.select(".tgme_widget_message")
    for message in messages:
        message_id = message_id_from_post(message.get("data-post", ""))
        title = message.select_one(".tgme_widget_message_document_title")
        if message_id is None or not title:
            continue
        file_name = clean_name(title.get_text(" "))
        if not file_name or not has_allowed_extension(file_name):
            continue
        date = (message.select_one("time[datetime]") or {}).get("datetime", "")
        items.append({
            "name": file_name,
            "download_url": f"https://t.me/{channel}/{message_id}",
            "source": "telegram",
            "channel": channel,
            "channel_url": f"https://t.me/{channel}",
            "file_name": file_name,
            "message_id": message_id,
            "date": date,
        })
    more = soup.select_one("a.tme_messages_more")
    next_url = urljoin(base_url, more["href"]) if more and more.get("href") else None
    return items, next_url if valid_next_url(next_url, channel) else None, len(messages)


def existing_items() -> dict[tuple[str, int], dict]:
    if not OUT.exists():
        return {}
    try:
        raw_items = json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read existing {OUT.name}: {error}") from error
    if not isinstance(raw_items, list):
        raise RuntimeError(f"Existing {OUT.name} is not a list")
    items: dict[tuple[str, int], dict] = {}
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        channel, message_id = item.get("channel"), item.get("message_id")
        if isinstance(channel, str) and isinstance(message_id, int):
            items[(channel, message_id)] = item
    return items


def atomic_write(path: Path, data: object) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        json.dump(data, temp, ensure_ascii=False, indent=2)
        temp.write("\n")
        temp_path = Path(temp.name)
    os.replace(temp_path, path)


def main() -> int:
    if not CHANNELS or not ALLOWED:
        raise ValueError("At least one channel and one allowed extension are required")
    by_message = existing_items()
    scanned_messages = fetched_pages = 0
    errors: dict[str, str] = {}
    succeeded: list[str] = []
    for channel in CHANNELS:
        url = base_url = f"https://t.me/s/{channel}"
        try:
            for _ in range(PAGES):
                html = fetch(url)
                fetched_pages += 1
                items, next_url, message_count = parse_page(html, channel, base_url)
                scanned_messages += message_count
                for item in items:
                    by_message[(channel, item["message_id"])] = item
                if not next_url or next_url == url:
                    break
                url = next_url
                time.sleep(DELAY)
            succeeded.append(channel)
        except requests.RequestException as error:
            errors[channel] = str(error)
            print(f"Warning: {channel} could not be synced: {error}", file=sys.stderr)
    if not succeeded:
        print("No channel could be synced; existing files were left untouched.", file=sys.stderr)
        return 1
    data = sorted(by_message.values(), key=lambda item: (item["name"].casefold(), item["channel"].casefold(), item["message_id"]))
    atomic_write(OUT, data)
    atomic_write(META, {
        "source": "telegram_public_preview",
        "channels": [f"https://t.me/{channel}" for channel in CHANNELS],
        "synced_channels": [f"https://t.me/{channel}" for channel in succeeded],
        "failed_channels": errors,
        "pages": fetched_pages,
        "scanned_messages": scanned_messages,
        "items": len(data),
        "allowed_extensions": sorted(ALLOWED),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    print(f"Indexed {len(data)} Telegram file messages from {len(succeeded)} channel(s) and {fetched_pages} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
