"""Render a contribution graph using GitHub data and the Python standard library."""

import json
import math
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape


def main():
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=30)).replace(hour=0, minute=0, second=0, microsecond=0)
    login = os.environ.get("PROFILE_LOGIN", "petercorders")
    query = """
      query($login: String!, $from: DateTime!, $to: DateTime!) {
        user(login: $login) {
          contributionsCollection(from: $from, to: $to) {
            contributionCalendar {
              weeks { contributionDays { date contributionCount } }
            }
          }
        }
      }
    """
    request = Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {
            "login": login, "from": start.isoformat(), "to": now.isoformat()
        }}).encode(),
        headers={
            "Authorization": "Bearer " + os.environ["GH_TOKEN"],
            "Content-Type": "application/json",
            "User-Agent": "petercorders-profile-activity",
        },
    )
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("GitHub contribution query failed; retaining the previous graph")
    weeks = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    counts = {day["date"]: day["contributionCount"]
              for week in weeks for day in week["contributionDays"]}
    dates = [(start + timedelta(days=i)).date().isoformat() for i in range(31)]
    # Missing data must fail rather than silently drawing a zero contribution day.
    values = [counts[day] for day in dates]
    if any(not isinstance(value, int) or value < 0 for value in values):
        raise ValueError("Invalid contribution counts")

    left, right, top, bottom = 72, 1054, 116, 254
    ceiling = max(4, math.ceil(max(values) / 4) * 4)
    points = [(left + i * (right - left) / 30,
               bottom - value / ceiling * (bottom - top))
              for i, value in enumerate(values)]
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    total = sum(values)
    active = sum(value > 0 for value in values)
    svg = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="330" viewBox="0 0 1100 330" role="img" aria-labelledby="title description">
<title id="title">Activity / Last 31 days</title>
<desc id="description">{total} contributions across {active} active days, from {dates[0]} to {dates[-1]}. Daily counts: {', '.join(str(v) for v in values)}.</desc>
<defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#f9a522" stop-opacity=".28"/><stop offset="1" stop-color="#f9a522" stop-opacity=".015"/></linearGradient></defs>
<rect x="1" y="1" width="1098" height="328" rx="14" fill="#10131b" stroke="#2c2e37"/>
<g font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif">
<text x="36" y="43" fill="#f9a522" font-family="ui-monospace,Menlo,monospace" font-size="12" letter-spacing="2">~/ACTIVITY</text>
<text x="36" y="78" fill="#f1ede5" font-size="26" font-weight="600">A little progress, every day.</text>
<text x="1054" y="45" text-anchor="end" fill="#f9a522" font-size="28" font-weight="600">{total} contributions</text>
<text x="1054" y="72" text-anchor="end" fill="#8e8e9a" font-size="15">Last 31 days · {active} active days</text>''']
    for i in range(5):
        y = bottom - i * (bottom - top) / 4
        svg.append(f'<path d="M{left} {y}H{right}" stroke="#272a34" stroke-dasharray="3 6"/>')
        svg.append(f'<text x="54" y="{y+5}" text-anchor="end" fill="#7f808c" font-size="13">{int(ceiling*i/4)}</text>')
    svg.append(f'<polygon points="{left},{bottom} {line} {right},{bottom}" fill="url(#area)"/>')
    svg.append(f'<polyline points="{line}" fill="none" stroke="#f9a522" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>')
    for date, value, (x, y) in zip(dates, values, points):
        if value:
            svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="#ffd28a"><title>{escape(date)}: {value} contributions</title></circle>')
    for i in range(0, 31, 5):
        x = points[i][0]
        svg.append(f'<text x="{x:.1f}" y="280" text-anchor="middle" fill="#8e8e9a" font-size="13">{dates[i][5:]}</text>')
    svg.append(f'<text x="36" y="310" fill="#666976" font-size="12">GitHub contributions · {escape(dates[0])} — {escape(dates[-1])} · UTC</text>')
    svg.append('<text x="1054" y="310" text-anchor="end" fill="#666976" font-size="12">Updated daily</text></g></svg>')
    target = Path(__file__).resolve().parents[1] / "assets" / "activity.svg"
    # Build the entire output before replacing the previous usable graph.
    target.write_text("\n".join(svg), encoding="utf-8")
    print(f"Rendered {len(values)} days: {total} contributions, {active} active days")


if __name__ == "__main__":
    main()
