"""Build files.json from the exported links list without publishing partial data."""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "links.txt"
OUTPUT = ROOT / "files.json"
LINE_PATTERN = re.compile(r"^Exported\s+(.*?):\s+(https?://\S+)\s*$", re.MULTILINE)


def display_name(value: str) -> str:
    """Return a filename for either POSIX or Windows-style export paths."""
    name = PurePosixPath(value.strip().replace("\\", "/")).name
    return name.removesuffix(".zip") if name.lower().endswith(".zip") else name


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def atomic_write_json(path: Path, data: list[dict[str, str]]) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temp:
        json.dump(data, temp, ensure_ascii=False, indent=2)
        temp.write("\n")
        temp_path = Path(temp.name)
    os.replace(temp_path, path)


def main() -> int:
    matches = LINE_PATTERN.findall(INPUT.read_text(encoding="utf-8"))
    data = [
        {"name": display_name(full_path), "download_url": url.strip()}
        for full_path, url in matches
        if display_name(full_path) and is_http_url(url.strip())
    ]
    if not data:
        raise ValueError("No valid exported links found; files.json was left unchanged.")
    names = [item["name"] for item in data]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate filenames found; files.json was left unchanged.")
    atomic_write_json(OUTPUT, data)
    print(f"Wrote {len(data)} records to {OUTPUT.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
