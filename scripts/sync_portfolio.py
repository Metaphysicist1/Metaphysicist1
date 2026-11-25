#!/usr/bin/env python3
"""Refresh the GitHub profile from a revision-pinned ultra-portfolio snapshot.

Install scripts/requirements.txt, then run python3 scripts/sync_portfolio.py.
Use --offline to regenerate from the checked-in snapshot without network access.
The dashboard art is drawn by scripts/board.py.
"""
import argparse
import hashlib
import io
import json
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image

from board import fetch_github_snapshot, render as render_board

ROOT = Path(__file__).resolve().parents[1]
REPO = "Metaphysicist1/ultra-portfolio"


def fetch(url):
    with urlopen(Request(url, headers={"User-Agent": "Edgar-Portfolio-Sync"}), timeout=30) as response:
        return response.read()


def render(data):
    github_path = ROOT / "data/github.json"
    if not github_path.exists():
        fetch_github_snapshot()
    render_board(data, json.loads(github_path.read_text()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if not args.offline:
        revision = json.loads(fetch(f"https://api.github.com/repos/{REPO}/commits/main"))["sha"]
        raw = f"https://raw.githubusercontent.com/{REPO}/{revision}/public"
        payload = fetch(f"{raw}/data/life.json")
        data = json.loads(payload)
        (ROOT / "data").mkdir(exist_ok=True)
        (ROOT / "assets").mkdir(exist_ok=True)
        # Fetch and validate before replacing checked-in content.
        images = {key: fetch(f"{raw}/{next(e for e in data['entries'] if e['id'] == key)['image']}")
                  for key in ("paperclaw", "wortweg")}
        for content in images.values():
            Image.open(io.BytesIO(content)).verify()
        (ROOT / "data/life.json").write_bytes(payload)
        (ROOT / "data/source.json").write_text(json.dumps({
            "repository": REPO, "revision": revision, "path": "public/data/life.json",
            "sha256": hashlib.sha256(payload).hexdigest()
        }, indent=2) + "\n")
        for key, content in images.items():
            (ROOT / f"assets/{key}.jpg").write_bytes(content)
        try:
            fetch_github_snapshot()
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, KeyError) as error:
            print(f"Kept the existing GitHub snapshot ({error}).")
    render(json.loads((ROOT / "data/life.json").read_text()))
    print("Updated README.md from the portfolio snapshot.")


if __name__ == "__main__":
    main()
