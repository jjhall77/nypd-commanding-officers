#!/usr/bin/env python3
"""
Scrape commanding officers from NYC.gov NYPD pages.

Covers three command types:
  - Precincts (78 commands)
  - Housing PSAs (9 commands)
  - Transit Districts (12 commands)

Each type has a landing page listing all commands. The scraper discovers
URLs from those landing pages, then visits each command page to extract
the CO rank and name.

Standalone repo version (July 2026) of pipeline/scrape_precinct_cos.py from
the NYPD panel project. Differences: writes a single commanding_officers.csv
in the repo root, omits the scraped_date column (git commit dates carry
timing, so diffs show only real CO changes), and exits non-zero if fewer than
90 of 99 commands parse — so a nyc.gov page redesign fails the workflow run
instead of silently clobbering the archive.

Usage:
    python scrape_cos.py
"""

import re
import time
import urllib.request
import urllib.error
import csv
from datetime import datetime

from pathlib import Path

BASE_URL = "https://www.nyc.gov"
OUT_DIR = Path(__file__).resolve().parent

COMMAND_SOURCES = [
    {
        "type": "precinct",
        "landing": f"{BASE_URL}/site/nypd/bureaus/patrol/precincts-landing.page",
        "link_pattern": r'/site/nypd/bureaus/patrol/precincts/[^"]+\.page',
    },
    {
        "type": "psa",
        "landing": f"{BASE_URL}/site/nypd/bureaus/transit-housing/housing.page",
        "link_pattern": r'/site/nypd/bureaus/transit-housing/police-service-area-[^"]+\.page',
    },
    {
        "type": "transit_district",
        "landing": f"{BASE_URL}/site/nypd/bureaus/transit-housing/transit.page",
        "link_pattern": r'/site/nypd/bureaus/transit-housing/transit-district-[^"]+\.page',
    },
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) research-bot/1.0"
}

CO_RANKS = [
    "Deputy Chief",
    "Assistant Chief",
    "Deputy Inspector",
    "Inspector",
    "Captain",
]


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean_text(s):
    s = s.replace("&nbsp;", " ")
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def get_command_urls(source):
    """Discover command page URLs from a landing page."""
    html = fetch(source["landing"])
    pattern = re.compile(
        r'<a\s+href="(' + source["link_pattern"] + r')"[^>]*>\s*([^<]+)</a>',
        re.IGNORECASE,
    )
    commands = []
    seen = set()
    for path, name in pattern.findall(html):
        name = name.strip()
        if path not in seen:
            seen.add(path)
            commands.append({
                "command": name,
                "command_type": source["type"],
                "url": BASE_URL + path,
            })
    return commands


def extract_co(html):
    """Extract CO rank and name from a command page."""
    m = re.search(
        r"Commanding\s+Officer:\s*</strong>\s*(.+?)(?:</p>|<br\s*/?>|<strong>)",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        text = clean_text(m.group(1))
        return parse_rank_name(text)

    m = re.search(
        r'<img\s+title="([^"]+)"[^>]*>.*?Commanding\s+Officer',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        return parse_rank_name(m.group(1).strip())

    return None, None


def parse_rank_name(text):
    for rank in CO_RANKS:
        if text.lower().startswith(rank.lower()):
            name = text[len(rank):].strip()
            return rank, name
    return None, text


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scrape_date = datetime.now().strftime("%Y-%m-%d")
    fieldnames = ["command", "command_type", "rank", "name", "url"]

    print(f"Scraping NYPD commanding officers — {scrape_date}")

    all_commands = []
    for source in COMMAND_SOURCES:
        commands = get_command_urls(source)
        print(f"  {source['type']:20s}  {len(commands)} commands found")
        all_commands.extend(commands)

    print(f"\nTotal: {len(all_commands)} commands\n")

    results = []
    errors = []

    for i, cmd in enumerate(all_commands):
        try:
            html = fetch(cmd["url"])
            rank, name = extract_co(html)

            if name:
                print(f"  {cmd['command']:30s}  {rank or '?':20s}  {name}")
            else:
                print(f"  {cmd['command']:30s}  ** could not parse **")
                errors.append(cmd["command"])

            results.append({
                "command": cmd["command"],
                "command_type": cmd["command_type"],
                "rank": rank or "",
                "name": name or "",
                "url": cmd["url"],
            })

            time.sleep(0.5)

        except Exception as e:
            print(f"  {cmd['command']:30s}  ERROR: {e}")
            errors.append(f"{cmd['command']}: {e}")
            results.append({
                "command": cmd["command"],
                "command_type": cmd["command_type"],
                "rank": "",
                "name": "",
                "url": cmd["url"],
            })

        if (i + 1) % 20 == 0:
            print(f"  ... {i + 1}/{len(all_commands)} done")

    # Single output file; git history carries the dates (scraped_date column
    # deliberately omitted so commits diff only on real CO changes)
    latest_path = OUT_DIR / "commanding_officers.csv"
    with open(latest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    n_ok = sum(1 for r in results if r["name"])
    print(f"\nDone: {n_ok}/{len(results)} parsed successfully")
    for ctype in ["precinct", "psa", "transit_district"]:
        ct = [r for r in results if r["command_type"] == ctype]
        ct_ok = sum(1 for r in ct if r["name"])
        print(f"  {ctype:20s}  {ct_ok}/{len(ct)}")
    if n_ok < 90:
        print(f"\nFATAL: only {n_ok}/99 parsed — page structure may have changed; not exiting 0")
        raise SystemExit(1)
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors[:10]:
            print(f"  - {e}")
    print(f"\nSaved to {out_path}")
    print(f"Latest: {latest_path}")


if __name__ == "__main__":
    main()
