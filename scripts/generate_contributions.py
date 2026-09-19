"""Render the account-wide GitHub contribution calendar without external services."""
import datetime as dt
import html
import json
import math
import os
from pathlib import Path
import subprocess

QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""


def render(calendar, login):
    weeks = calendar["weeks"]
    values = [sum(day["contributionCount"] for day in week["contributionDays"]) for week in weeks]
    if not values:
        raise ValueError("GitHub returned an empty contribution calendar")
    ceiling = max(5, math.ceil(max(values) / 5) * 5)
    left, top, width, height, baseline = 42, 18, 930, 198, 216
    points = [(left + i * width / max(1, len(values) - 1), baseline - value * height / ceiling) for i, value in enumerate(values)]
    line = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in points)
    area = line + f" L{points[-1][0]:.2f},{baseline} L{left},{baseline} Z"
    start = weeks[0]["contributionDays"][0]["date"]
    end = weeks[-1]["contributionDays"][-1]["date"]
    description = f"{login}: {calendar['totalContributions']} GitHub contributions across all repositories, {start} to {end}. Each point is a weekly total, not commits alone."
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="250" viewBox="0 0 1000 250" role="img" aria-labelledby="title desc">', '<title id="title">GitHub contribution graph</title>', f'<desc id="desc">{html.escape(description)}</desc>', '<rect width="1000" height="250" rx="6" fill="#0d1117"/>', '<g font-family="Segoe UI,Arial,sans-serif" font-size="11" fill="#8b949e">']
    for step in range(6):
        y = baseline - step * height / 5
        svg.append(f'<path d="M{left},{y:.2f} H972" stroke="#21262d" fill="none"/>')
        svg.append(f'<text x="34" y="{y + 4:.2f}" text-anchor="end">{ceiling * step // 5}</text>')
    previous_month = None
    for i, week in enumerate(weeks):
        date = dt.date.fromisoformat(week["contributionDays"][0]["date"])
        month = (date.year, date.month)
        if month != previous_month and 20 < points[i][0] - left < width - 20:
            svg.append(f'<text x="{points[i][0]:.2f}" y="238" text-anchor="middle">{date:%m/%y}</text>')
        previous_month = month
    svg.extend(['</g>', f'<path d="{area}" fill="#39d353" fill-opacity="0.22"/>', f'<path d="{line}" stroke="#39d353" stroke-width="2.5" stroke-linejoin="round" fill="none"/>', '</svg>'])
    return "\n".join(svg) + "\n"


def main():
    login = os.environ.get("PROFILE_USERNAME", "Havkz")
    result = subprocess.run(["gh", "api", "graphql", "-f", f"query={QUERY}", "-f", f"login={login}"], check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    target = Path(__file__).resolve().parents[1] / "assets" / "contributions.svg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(calendar, login), encoding="utf-8", newline="\n")
    print(f"Rendered {calendar['totalContributions']} account-wide contributions to {target}")


if __name__ == "__main__":
    main()
