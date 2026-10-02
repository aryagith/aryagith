"""Refresh the text profile's public stats. Stdlib only; run --check to test."""

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen

USER = "aryagith"
ROOT = Path(__file__).resolve().parents[1]
START, END = "<!-- PROFILE:START -->", "<!-- PROFILE:END -->"


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "aryagith-profile"}
    if token := os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(f"https://api.github.com/{path}", headers=headers), timeout=30) as response:
        return json.load(response)


def render(repos, languages, prs, date, portrait):
    original = [repo for repo in repos if not repo["fork"] and not repo["archived"]]
    stars = sum(repo["stargazers_count"] for repo in repos if not repo["fork"])
    info = [
        "arya gosavi", "aryagith@github", "------------------------------------------", "",
        "School ....... York University", "Location ..... Toronto, CA",
        "Focus ........ AI / full-stack / systems", "",
        "Languages .... Python, CUDA, C#",
        "               TypeScript, JavaScript", "",
        "-- GitHub --------------------------------", "",
        f"Public repos . {len(repos)}", f"Original ..... {len(original)} active repositories",
        f"Pull requests  {prs} public", f"Stars ........ {stars}", "",
        "-- Source bytes --------------------------",
    ]
    total = sum(languages.values())
    info.extend(f"{name[:24]:24} {count / total:>6.1%}" for name, count in languages.most_common(6) if total)
    if not total:
        info.append("No language data yet.")
    info.extend(["", f"Updated ...... {date}"])
    width = max(map(len, portrait), default=0)
    rows = [f"{portrait[i] if i < len(portrait) else '':<{width}}    {info[i] if i < len(info) else ''}".rstrip() for i in range(max(len(portrait), len(info)))]
    return "```text\n" + "\n".join(rows) + "\n```"


def replace_profile(readme, profile):
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(START) > readme.index(END):
        raise ValueError("Expected one ordered pair of profile markers; leaving README unchanged.")
    before, rest = readme.split(START)
    _, after = rest.split(END)
    return before + START + "\n" + profile + "\n" + END + after


def check():
    repos = [{"fork": False, "archived": False, "stargazers_count": 3}, {"fork": True, "archived": False, "stargazers_count": 9}]
    profile = render(repos, Counter({"Python": 3, "C++": 1}), 7, "2026-10-02", [" .#", "@@ "])
    assert "75.0%" in profile and "25.0%" in profile and "Stars ........ 3" in profile
    assert "Public repos . 2" in profile and "Original ..... 1 active" in profile
    readme = f"intro\n{START}\nold\n{END}\nprojects\n"
    updated = replace_profile(readme, profile)
    assert updated.startswith("intro\n") and updated.endswith("\nprojects\n") and "old" not in updated
    assert replace_profile(updated, profile) == updated
    assert "No language data yet" in render([], Counter(), 0, "test", [])
    try:
        replace_profile("missing markers", profile)
    except ValueError:
        pass
    else:
        raise AssertionError("Missing markers must fail before writing.")
    print("Text profile self-check passed.")


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
        raise RuntimeError("Incomplete pull request totals; keeping the previous stats.")
    portrait = (ROOT / "assets/portrait.txt").read_text(encoding="utf-8").splitlines()
    profile = render(repos, languages, prs["total_count"], datetime.now(timezone.utc).date().isoformat(), portrait)
    output = ROOT / "README.md"
    updated = replace_profile(output.read_text(encoding="utf-8"), profile)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(updated, encoding="utf-8")
    temporary.replace(output)
    print(f"Updated README from {len(repos)} public repositories.")


if __name__ == "__main__":
    check() if "--check" in sys.argv else main()
