"""Draw the profile dashboard from the portfolio log and a GitHub snapshot.

Numbers on the board come from data/github.json. Project names and links come
from data/life.json. Jupyter notebooks are left out of the language bar because
their byte count is mostly saved output, not code.
"""

import html
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "assets" / "board"

INK = "#e6edf3"
MUTED = "#8b949e"
PANEL = "#161b22"
INSET = "#0d1117"
GREEN = "#3ddc97"
AMBER = "#ffb020"
CYAN = "#3ee0ff"
CORAL = "#ff7a59"

CARDS = [
    ("paperclaw", "571", "parks checked against Sentinel-2", GREEN),
    ("wortweg", "der·die·das", "one German word, every day", AMBER),
    ("clipvault", "no cloud", "clipboard history for GNOME", CORAL),
    ("pneunet", "Cloud Run", "pneumonia detection from X-rays", CYAN),
    ("supply-agent", "LangGraph", "supply chain, on Google Cloud", "#7ee787"),
    ("neuro-timer", "focus", "work protocols, desktop and web", "#d2a8ff"),
]

PRODUCT_IDS = [
    "paperclaw", "wortweg", "flat-bot", "clipvault", "concierge",
    "supply-agent", "neuro-timer", "clustar", "pneunet", "coverbot", "stamo",
]

ALSO = ["coverbot", "stamo", "clustar", "concierge", "flat-bot"]

LINKS = [
    ("Portfolio", "https://www.edgarabasov.website", GREEN),
    ("LinkedIn", "https://www.linkedin.com/in/edgar-abasov/", CYAN),
    ("X", "https://x.com/AbasovEdgar", INK),
    ("Email", "mailto:edgarabasov1@gmail.com", AMBER),
]


def esc(value):
    return html.escape(str(value), quote=True)


def fetch_github_snapshot():
    """Refresh data/github.json from the public profile. Needs the gh CLI."""
    query = """
    query {
      user(login: "Metaphysicist1") {
        followers { totalCount }
        publicRepositories: repositories(ownerAffiliations: OWNER, privacy: PUBLIC) { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
          totalCount
          nodes {
            languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
              edges { size node { name color } }
            }
          }
        }
        createdAt
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { contributionCount date weekday } }
          }
        }
      }
    }
    """
    raw = subprocess.check_output(["gh", "api", "graphql", "-f", f"query={query}"], text=True)
    user = json.loads(raw)["data"]["user"]
    calendar = user["contributionsCollection"]["contributionCalendar"]
    sizes, colors = {}, {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name == "Jupyter Notebook":
                continue
            sizes[name] = sizes.get(name, 0) + edge["size"]
            colors[name] = edge["node"]["color"]
    total = sum(sizes.values()) or 1
    ranked = sorted(sizes.items(), key=lambda item: -item[1])
    top, other = ranked[:5], ranked[5:]
    languages = [
        {"name": name, "color": colors[name], "bytes": size, "pct": round(100 * size / total, 1)}
        for name, size in top
    ]
    if other:
        other_bytes = sum(size for _, size in other)
        languages.append({
            "name": "Other",
            "color": "#4a5560",
            "bytes": other_bytes,
            "pct": round(100 * other_bytes / total, 1),
        })
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]
    peak = max(days, key=lambda day: day["contributionCount"])
    snapshot = {
        "login": "Metaphysicist1",
        "followers": user["followers"]["totalCount"],
        "public_repos": user["publicRepositories"]["totalCount"],
        "created_at": user["createdAt"],
        "total_contributions": calendar["totalContributions"],
        "from": days[0]["date"],
        "to": days[-1]["date"],
        "peak": {"date": peak["date"], "count": peak["contributionCount"]},
        "weeks": calendar["weeks"],
        "languages": languages,
        "languages_note": "Jupyter Notebook excluded; notebook files are mostly saved output.",
    }
    path = ROOT / "data" / "github.json"
    path.write_text(json.dumps(snapshot, indent=2) + "\n")
    return snapshot


def _panel(width, height, radius=24):
    return f'<rect width="{width}" height="{height}" rx="{radius}" fill="{PANEL}"/>'


def _text(x, y, content, size, fill, weight="700", anchor="start"):
    return (
        f'<text x="{x}" y="{y}" fill="{fill}" font-family="Arial, Helvetica, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{esc(content)}</text>'
    )


def _identity():
    body = (
        _panel(680, 156)
        + _text(32, 84, "Edgar Abasov", 58, INK)
        + _text(32, 124, "AI engineer  ·  Berlin  ·  stamo.AI", 22, MUTED, "400")
    )
    return _doc(680, 156, body, "Edgar Abasov, AI engineer in Berlin, co-founder at stamo.AI.")


def _meter(figure, label, color):
    body = (
        _panel(210, 112, 18)
        + _text(18, 62, figure, 36, color)
        + _text(18, 90, label, 16, MUTED, "400")
    )
    return _doc(210, 112, body, f"{figure} {label}")


def _meters(github):
    year = github["created_at"][:4]
    return [
        ("year", f'{github["total_contributions"]:,}', "this year", GREEN),
        ("repos", str(github["public_repos"]), "repositories", CYAN),
        ("followers", str(github["followers"]), "followers", AMBER),
        ("joined", year, "joined", CORAL),
    ]


def _languages(github):
    width, bar_h = 880, 32
    offset = 0
    segments = []
    for language in github["languages"]:
        segment = width * language["pct"] / 100
        segments.append(
            f'<rect x="{offset:.1f}" y="0" width="{max(segment, 0):.1f}" height="{bar_h}" fill="{language["color"]}"/>'
        )
        offset += segment
    body = (
        f'<clipPath id="langbar"><rect width="{width}" height="{bar_h}" rx="16"/></clipPath>'
        + f'<g clip-path="url(#langbar)">{"".join(segments)}</g>'
    )
    title = "Languages in code, notebooks excluded. " + ", ".join(
        f'{item["name"]} {item["pct"]:.0f} percent' for item in github["languages"]
    )
    return _doc(width, bar_h, body, title)


def _cube(x, y, size, height, colors):
    top, left, right = colors
    s = size
    top_pts = f"{x},{y - height} {x + s},{y + s / 2 - height} {x},{y + s - height} {x - s},{y + s / 2 - height}"
    left_pts = f"{x - s},{y + s / 2 - height} {x},{y + s - height} {x},{y + s} {x - s},{y + s / 2}"
    right_pts = f"{x + s},{y + s / 2 - height} {x},{y + s - height} {x},{y + s} {x + s},{y + s / 2}"
    return (
        f'<polygon points="{left_pts}" fill="{left}"/>'
        f'<polygon points="{right_pts}" fill="{right}"/>'
        f'<polygon points="{top_pts}" fill="{top}"/>'
    )


def _calendar(github):
    weeks = github["weeks"]
    peak = max(day["contributionCount"] for week in weeks for day in week["contributionDays"]) or 1
    size = 8
    cubes = []
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            count = day["contributionCount"]
            x = (week_index - day["weekday"]) * size
            y = (week_index + day["weekday"]) * (size / 2)
            if count <= 0:
                height, colors = 2, ("#243140", "#1c2836", "#16202c")
            else:
                span = math.log1p(count) / math.log1p(peak)
                height = 5 + int(26 * span)
                if span < 0.45:
                    colors = ("#1f9d6a", "#14724c", "#0e5438")
                elif span < 0.78:
                    colors = ("#3ddc97", "#1ea36c", "#146b48")
                else:
                    colors = ("#ffe56a", "#d9a406", "#8f6c00")
            cubes.append((y, x, _cube(x, y, size, height, colors)))
    cubes.sort()
    xs, ys = [], []
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            xs.append((week_index - day["weekday"]) * size)
            ys.append((week_index + day["weekday"]) * (size / 2))
    min_x, max_x = min(xs) - size, max(xs) + size
    min_y, max_y = min(ys) - 32, max(ys) + size + 8
    target_w, target_h = 740, 300
    scale = min(target_w / (max_x - min_x), target_h / (max_y - min_y))
    chart_y = 88 + (target_h - (max_y - min_y) * scale) / 2
    chart = (
        f'<g transform="translate(24 {chart_y:.1f}) scale({scale:.4f}) '
        f'translate({-min_x:.1f} {-min_y:.1f})">{"".join(cube for _, _, cube in cubes)}</g>'
    )
    start = _pretty(github["from"])
    end = _pretty(github["to"])
    city = _doc(
        800,
        420,
        _panel(800, 420) + _text(24, 36, "A year of commits", 22, INK) + _text(24, 62, f"{start}  –  {end}", 16, MUTED, "400") + chart,
        (
            f'{github["total_contributions"]:,} contributions from {start} to {end}. '
            f'Tallest day is {github["peak"]["date"]} with {github["peak"]["count"]} contributions.'
        ),
    )
    totals = [0] * 7
    for week in weeks:
        for day in week["contributionDays"]:
            totals[day["weekday"]] += day["contributionCount"]
    names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    busiest = max(totals)
    bars = []
    for index, (name, total) in enumerate(zip(names, totals)):
        y = 64 + index * 46
        width = max(12, int(150 * total / busiest))
        color = AMBER if total == busiest else GREEN
        bars.append(
            _text(20, y + 16, name, 16, MUTED, "400")
            + f'<rect x="68" y="{y}" width="150" height="22" rx="11" fill="{INSET}"/>'
            + f'<rect x="68" y="{y}" width="{width}" height="22" rx="11" fill="{color}"/>'
            + _text(300, y + 16, f"{total:,}", 16, INK, "700", "end")
        )
    weekday = _doc(
        320,
        400,
        _panel(320, 400) + _text(20, 36, "By weekday", 20, INK) + "".join(bars),
        "Contributions by weekday. Monday is the busiest.",
    )
    return city, weekday


def _shipped(data):
    entries = {entry["id"]: entry for entry in data["entries"]}
    counts = {}
    for key in PRODUCT_IDS:
        year = entries[key]["date"][:4]
        counts[year] = counts.get(year, 0) + 1
    years = sorted(counts)
    colors = [CYAN, AMBER, GREEN, CORAL]
    peak = max(counts.values())
    cards = []
    for index, year in enumerate(years):
        count = counts[year]
        color = colors[index % len(colors)]
        bar = max(18, int(180 * count / peak))
        body = (
            _panel(240, 132, 20)
            + _text(20, 68, str(count), 44, color)
            + _text(20, 98, f"shipped · {year}", 16, MUTED, "400")
            + f'<rect x="20" y="108" width="{bar}" height="10" rx="5" fill="{color}"/>'
        )
        cards.append((year, count, _doc(240, 132, body, f"{count} products shipped in {year}")))
    return cards


def _card(entry, figure, line, color):
    year = entry.get("date", "")[:4]
    body = (
        _panel(400, 210, 22)
        + f'<circle cx="36" cy="40" r="7" fill="{color}"/>'
        + _text(364, 46, year, 16, MUTED, "400", "end")
        + _text(28, 118, figure, 40, color)
        + _text(28, 158, entry["title"], 22, INK)
        + _text(28, 186, line, 16, MUTED, "400")
    )
    alt = f'{entry["title"]}. {entry.get("text") or line}'
    return _doc(400, 210, body, alt)


def _pill(label, color):
    body = (
        f'<rect width="168" height="48" rx="24" fill="{PANEL}"/>'
        + f'<circle cx="28" cy="24" r="6" fill="{color}"/>'
        + _text(44, 30, label, 16, INK, "700")
    )
    return _doc(168, 48, body, label)


def _also_pill(label):
    width = max(148, 18 + len(label) * 9)
    body = (
        f'<rect width="{width}" height="44" rx="22" fill="{PANEL}"/>'
        + _text(width / 2, 28, label, 15, INK, "700", "middle")
    )
    return _doc(width, 44, body, label), width


def _doc(width, height, body, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f"<title>{esc(title)}</title>{body}</svg>\n"
    )


def _pretty(iso):
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    year, month, day = iso.split("-")
    return f"{int(day)} {months[int(month) - 1]} {year}"


def _img(src, alt, width=None):
    size = f' width="{width}"' if width else ""
    return f'<img{size} src="{esc(src)}" alt="{esc(alt)}" />'


def _linked(url, src, alt, width=None):
    return f'<a href="{esc(url)}">{_img(src, alt, width)}</a>'


def render(data, github):
    BOARD.mkdir(parents=True, exist_ok=True)
    entries = {entry["id"]: entry for entry in data["entries"]}
    (BOARD / "identity.svg").write_text(_identity())
    for key, figure, label, color in _meters(github):
        (BOARD / f"meter-{key}.svg").write_text(_meter(figure, label, color))
    (BOARD / "languages.svg").write_text(_languages(github))
    city, weekday = _calendar(github)
    (BOARD / "city.svg").write_text(city)
    (BOARD / "weekday.svg").write_text(weekday)
    years = _shipped(data)
    for year, count, svg in years:
        (BOARD / f"year-{year}.svg").write_text(svg)
    for key, figure, line, color in CARDS:
        (BOARD / f"card-{key}.svg").write_text(_card(entries[key], figure, line, color))
    for label, _url, color in LINKS:
        (BOARD / f"link-{label.lower()}.svg").write_text(_pill(label, color))
    for key in ALSO:
        svg, _width = _also_pill(entries[key]["title"])
        (BOARD / f"also-{key}.svg").write_text(svg)

    languages = ", ".join(f'{item["name"]} {item["pct"]} percent' for item in github["languages"])
    cards = "\n  ".join(
        _linked(entries[key]["url"], f"assets/board/card-{key}.svg", entries[key].get("text") or entries[key]["title"], 280)
        for key, *_rest in CARDS
    )
    links = "\n  ".join(
        _linked(url, f"assets/board/link-{label.lower()}.svg", label, 148)
        for label, url, _color in LINKS
    )
    also = "\n  ".join(
        _linked(entries[key]["url"], f"assets/board/also-{key}.svg", entries[key]["title"])
        for key in ALSO
        if entries[key].get("url")
    )
    text_projects = "\n".join(
        f'- [{entries[key]["title"]}]({entries[key]["url"]}) — {entries[key]["text"]}'
        for key, *_rest in CARDS
        if entries[key].get("text")
    )
    meters = "\n  ".join(
        _img(f"assets/board/meter-{key}.svg", f"{figure} {label}", 168)
        for key, figure, label, _color in _meters(github)
    )
    year_cards = "\n  ".join(
        _img(f"assets/board/year-{year}.svg", f"{count} products shipped in {year}", 200)
        for year, count, _svg in years
    )
    legend = " · ".join(f'{item["name"]} {item["pct"]:.0f}%' for item in github["languages"])
    readme = f'''<!-- Generated by scripts/sync_portfolio.py from data/life.json and data/github.json. -->

<p align="center">
  {_img("assets/board/identity.svg", "Edgar Abasov, AI engineer in Berlin, co-founder at stamo.AI.", 520)}
</p>

<p align="center">
  {meters}
</p>

<p align="center">
  {_img("assets/board/languages.svg", legend + ". Notebook files left out.", 720)}
  <br>
  {legend}
  <br>
  Notebook files left out.
</p>

<p align="center">
  {links}
</p>

<p align="center">
  {_img("assets/board/city.svg", f'{github["total_contributions"]:,} contributions from {_pretty(github["from"])} to {_pretty(github["to"])}. Peak day {github["peak"]["date"]} with {github["peak"]["count"]} contributions.', 520)}
  {_img("assets/board/weekday.svg", "Contributions by weekday. Monday is the busiest.", 260)}
</p>

<p align="center">
  {year_cards}
</p>

<p align="center">
  {cards}
</p>

<p align="center">
  {also}
</p>

<p align="center">
  {_linked(entries["paperclaw"]["url"], "assets/paperclaw.jpg", entries["paperclaw"]["text"], 430)}
  {_linked(entries["wortweg"]["url"], "assets/wortweg.jpg", entries["wortweg"]["text"], 430)}
</p>

<p align="center">
  <a href="https://skillicons.dev">{_img("https://skillicons.dev/icons?i=py,pytorch,fastapi,docker,gcp,linux,git,bash,postgres,html,css,js&perline=6", "Python, PyTorch, FastAPI, Docker, Google Cloud, Linux, Git, Bash, Postgres, HTML, CSS and JavaScript.")}</a>
</p>

<p align="center">
  {_linked("https://github.com/Metaphysicist1", "https://streak-stats.demolab.com?user=Metaphysicist1&hide_border=true&background=0D1117&ring=3DDC97&fire=FFB020&currStreakNum=E6EDF3&sideNums=E6EDF3&currStreakLabel=8B949E&sideLabels=8B949E&dates=8B949E&stroke=161B22&border_radius=16", "Live contribution streak for Metaphysicist1.", 495)}
</p>

<p align="center">
  {_img("https://github-readme-activity-graph.vercel.app/graph?username=Metaphysicist1&bg_color=0d1117&color=8b949e&line=3ddc97&point=ffb020&area=true&hide_border=true&radius=16&custom_title=Contributions%20over%20the%20year", "Contribution activity over the past year.", 880)}
</p>

<details>
<summary>The same work, as text</summary>

{text_projects}

</details>
'''
    (ROOT / "README.md").write_text(readme)
    _write_preview()


def _write_preview():
    readme = (ROOT / "README.md").read_text()
    body = readme.split("\n", 2)[-1]
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Edgar Abasov — profile preview</title>
<style>
  body {{ margin: 0; background: #0d1117; color: #e6edf3; font: 16px/1.5 Arial, Helvetica, sans-serif; }}
  main {{ max-width: 920px; margin: 0 auto; padding: 28px 16px 80px; }}
  img {{ max-width: 100%; height: auto; }}
  p {{ text-align: center; }}
  a {{ color: #3ddc97; }}
  summary {{ cursor: pointer; }}
</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""
    (ROOT / "preview.html").write_text(page)


if __name__ == "__main__":
    snapshot = json.loads((ROOT / "data/github.json").read_text()) if (ROOT / "data/github.json").exists() else fetch_github_snapshot()
    life = json.loads((ROOT / "data/life.json").read_text())
    render(life, snapshot)
    print("Wrote assets/board, README.md and preview.html")
