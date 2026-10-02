"""Refresh the profile's public stats. Stdlib only; run --check for a self-test."""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from html import escape
from pathlib import Path
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

USER = "aryagith"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "stats.svg"


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "aryagith-profile"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(f"https://api.github.com/{path}", headers=headers), timeout=30) as response:
        return json.load(response)


def render(repos, languages, prs, date):
    total = sum(languages.values())
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="300" viewBox="0 0 960 300" role="img" aria-labelledby="title desc">',
        '<title id="title">Public GitHub signals</title>',
        '<desc id="desc">Public repository and pull request counts, stars, and languages by source bytes. Forks and archived repositories are excluded from language totals.</desc>',
        '<rect width="960" height="300" rx="12" fill="#08090a"/>',
        '<g font-family="Consolas,monospace" xml:space="preserve">',
    ]

    def text(x, y, value, size=12, color="#e7e7e0"):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}">{escape(str(value))}</text>')

    text(32, 32, "ARYAGITH / PUBLIC SIGNALS", color="#a4b8ff")
    text(730, 32, f"SYNC / {date}", color="#a5a8a0")
    parts.append('<path d="M32 52H928 M32 154H928" stroke="#3a3d39"/>')
    original = [repo for repo in repos if not repo["fork"] and not repo["archived"]]
    metrics = [(len(repos), "PUBLIC REPOS"), (len(original), "ORIGINAL / ACTIVE"), (prs, "PUBLIC PULL REQUESTS"), (sum(repo["stargazers_count"] for repo in repos if not repo["fork"]), "STARS EARNED")]
    for index, (value, label) in enumerate(metrics):
        x = 32 + index * 232
        text(x, 108, f"{value:02d}", 38)
        text(x, 134, label, 11, "#a5a8a0")
    text(32, 181, "LANGUAGES / SOURCE BYTES", 11, "#a4b8ff")
    for index, (name, count) in enumerate(languages.most_common(6)):
        x, y = 32 + (index % 3) * 306, 211 + (index // 3) * 32
        percent = count / total * 100 if total else 0
        # ponytail: six-language summary; expand the card if more detail is useful.
        bar = "#" * max(1, round(percent / 10)) + "." * (10 - max(1, round(percent / 10)))
        text(x, y, f"{name[:15]:15} [{bar}] {percent:4.1f}%", 11)
    if not languages:
        text(32, 211, "No public source-language data yet.", color="#a5a8a0")
    text(32, 281, "PUBLIC DATA ONLY / FORKS + ARCHIVES EXCLUDED FROM LANGUAGE TOTALS", 9, "#a5a8a0")
    parts.extend(["</g>", "</svg>"])
    return "\n".join(parts) + "\n"


def check():
    repos = [{"fork": False, "archived": False, "stargazers_count": 3}, {"fork": True, "archived": False, "stargazers_count": 9}]
    svg = render(repos, Counter({"Python": 3, "C++": 1}), 7, "2026-10-02")
    ET.fromstring(svg)
    assert "75.0%" in svg and "25.0%" in svg and ">03</text>" in svg and ">01</text>" in svg
    assert "A&amp;B" in render([], Counter({"A&B": 1}), 0, "test")
    assert "No public source-language data" in render([], Counter(), 0, "test")
    print("Stats self-check passed.")


def main():
    repos = []
    page = 1
    while True:
        batch = api(f"users/{USER}/repos?type=owner&per_page=100&page={page}")
        repos.extend(repo for repo in batch if not repo["private"])
        if len(batch) < 100:
            break
        page += 1
    languages = Counter()
    for repo in repos:
        if not repo["fork"] and not repo["archived"]:
            languages.update(api(f"repos/{USER}/{quote(repo['name'], safe='')}/languages"))
    prs = api(f"search/issues?q={quote(f'author:{USER} type:pr is:public')}")
    if prs.get("incomplete_results"):
        raise RuntimeError("GitHub returned incomplete pull request totals; keeping the previous stats.")
    svg = render(repos, languages, prs["total_count"], datetime.now(timezone.utc).date().isoformat())
    ET.fromstring(svg)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".tmp")
    temporary.write_text(svg, encoding="utf-8")
    temporary.replace(OUTPUT)
    print(f"Updated {OUTPUT.name} from {len(repos)} public repositories.")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
