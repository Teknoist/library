# Exocad Library Hub

Static GitHub Pages catalogue for library, software and public Telegram file links.

## Data sources

- `links.txt` is converted to `files.json` with `python convert.py`.
- `hex.json` stores Base64-encoded software URLs.
- `scripts/sync_telegram_public.py` updates `telegram.json` from the configured public Telegram channels. It retains previously indexed message IDs, so a bounded crawl cannot remove older records.

## Local preview

Run `python -m http.server 8000` in the repository root, then open `http://localhost:8000`.

## Automation

GitHub Actions rebuilds `files.json` after `links.txt` changes and syncs Telegram data every six hours. The workflows use pinned action revisions and serialise runs to avoid competing commits.

Telegram sync settings can be changed with `TG_CHANNELS`, `TG_PAGES`, `TG_DELAY`, and `TG_ALLOWED_EXTENSIONS` environment variables.
