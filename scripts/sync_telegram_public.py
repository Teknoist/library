#!/usr/bin/env python3
"""Build telegram.json from public Telegram channel file messages.

Reads the public preview page at https://t.me/s/DentalCADCAMLibrary.
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
CHANNEL = os.getenv("TG_CHANNEL", "DentalCADCAMLibrary").strip().lstrip("@")
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
BASE = f"https://t.me/s/{CHANNEL}"


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


def parse_page(html: str) -> tuple[list[dict], str | None, int]:
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
                "download_url": f"https://t.me/{CHANNEL}/{mid}",
                "source": "telegram",
                "file_name": file_name,
                "message_id": mid,
                "date": date,
            }
        )

    more = soup.select_one("a.tme_messages_more")
    next_url = urljoin(BASE, more.get("href")) if more and more.get("href") else None
    return items, next_url, len(messages)


def main() -> int:
    url = BASE
    by_id: dict[int, dict] = {}
    scanned_messages = 0
    fetched_pages = 0

    for _ in range(PAGES):
        html = fetch(url)
        fetched_pages += 1
        items, next_url, message_count = parse_page(html)
        scanned_messages += message_count
        for item in items:
            by_id[item["message_id"]] = item
        if not next_url or next_url == url:
            break
        url = next_url
        time.sleep(DELAY)

    data = sorted(by_id.values(), key=lambda x: (x["name"].casefold(), x["message_id"]))
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    META.write_text(
        json.dumps(
            {
                "source": "telegram_public_preview",
                "channel": f"https://t.me/{CHANNEL}",
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
    print(f"Indexed {len(data)} Telegram file messages from {fetched_pages} pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
