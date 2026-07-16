#!/usr/bin/env python3
"""Build telegram.json from public Telegram channel file messages.

Reads public preview pages like https://t.me/s/DentalCADCAMLibrary.
It only indexes file/document cards whose visible filename ends with an allowed extension.
Files are not downloaded or rehosted; download_url points to the Telegram message.
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "telegram.json"
META = ROOT / "telegram_meta.json"
DEFAULT_CHANNELS = "DentalCADCAMLibrary,ExoCADCAMLibrary"
CHANNELS_RAW = os.getenv("TG_CHANNELS") or os.getenv("TG_CHANNEL") or DEFAULT_CHANNELS
CHANNELS = [
    channel.strip().lstrip("@").removeprefix("https://t.me/").removeprefix("t.me/")
    for channel in CHANNELS_RAW.split(",")
    if channel.strip()
]
PAGES = int(os.getenv("TG_PAGES", "25"))
DELAY = float(os.getenv("TG_DELAY", "0.6"))
ALLOWED = {
    x.strip().lower()
    for x in os.getenv(
        "TG_ALLOWED_EXTENSIONS",
        ".zip,.7z,.rar,.stl,.obj,.ply,.dme,.xml,.library,.implant",
    ).split(",")
    if x.strip()
}


def clean_name(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def has_allowed_extension(name: str) -> bool:
    lower = name.lower()
    return any(lower.endswith(ext) for ext in ALLOWED)


def message_id_from_post(post: str) -> int | None:
    if not post or "/" not in post:
        return None
    try:
        return int(post.rsplit("/", 1)[1])
    except ValueError:
        return None


def fetch(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 library-sync/1.0"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.text


def parse_page(html: str, channel: str, base_url: str) -> tuple[list[dict], str | None, int]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[dict] = []
    messages = soup.select(".tgme_widget_message")

    for msg in messages:
        post = msg.get("data-post", "")
        mid = message_id_from_post(post)
        if mid is None:
            continue

        title_el = msg.select_one(".tgme_widget_message_document_title")
        if not title_el:
            continue

        file_name = clean_name(title_el.get_text(" "))
        if not file_name or not has_allowed_extension(file_name):
            continue

        date_el = msg.select_one("time[datetime]")
        date = date_el.get("datetime", "") if date_el else ""
        items.append(
            {
                "name": file_name,
                "download_url": f"https://t.me/{channel}/{mid}",
                "source": "telegram",
                "channel": channel,
                "channel_url": f"https://t.me/{channel}",
                "file_name": file_name,
                "message_id": mid,
                "date": date,
            }
        )

    more = soup.select_one("a.tme_messages_more")
    next_url = urljoin(base_url, more.get("href")) if more and more.get("href") else None
    return items, next_url, len(messages)


def main() -> int:
    by_message: dict[tuple[str, int], dict] = {}
    scanned_messages = 0
    fetched_pages = 0

    for channel in CHANNELS:
        base_url = f"https://t.me/s/{channel}"
        url = base_url

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

    data = sorted(
        by_message.values(),
        key=lambda x: (x["name"].casefold(), x["channel"].casefold(), x["message_id"]),
    )
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    META.write_text(
        json.dumps(
            {
                "source": "telegram_public_preview",
                "channels": [f"https://t.me/{channel}" for channel in CHANNELS],
                "pages": fetched_pages,
                "scanned_messages": scanned_messages,
                "items": len(data),
                "allowed_extensions": sorted(ALLOWED),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Indexed {len(data)} Telegram file messages from "
        f"{len(CHANNELS)} channels and {fetched_pages} pages"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
