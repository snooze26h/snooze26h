#!/usr/bin/env python3
"""Render the profile's stats card and contribution calendar as themed SVGs.

Runs in GitHub Actions (see .github/workflows/cards.yml) and writes
dist/stats-{dark,light}.svg and dist/calendar-{dark,light}.svg.
Only the standard library is used. Fonts are embedded from scripts/fonts.json.
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dist")
LOGIN = os.environ.get("GH_LOGIN", "snooze26h")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
if not TOKEN:
    sys.exit("GITHUB_TOKEN is not set")

FONTS = json.load(open(os.path.join(HERE, "fonts.json"), encoding="utf-8"))

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json",
                 "User-Agent": "profile-cards"})
    res = json.load(urllib.request.urlopen(req, timeout=60))
    if res.get("errors"):
        sys.exit(json.dumps(res["errors"], indent=2))
    return res["data"]


def collect():
    u = gql(QUERY, {"login": LOGIN})["user"]
    repos = u["repositories"]["nodes"]
    skip = {"XSLT", "Makefile", "DTrace", "HTML", "Shell", "Batchfile", "CMake"}
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            if e["node"]["name"] in skip:
                continue
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    total_lang = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    cc = u["contributionsCollection"]
    weeks = [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]]
             for w in cc["contributionCalendar"]["weeks"]]
    days = [d for w in weeks for d in w]
    return {
        "stars": sum(r["stargazerCount"] for r in repos),
        "repos": u["repositories"]["totalCount"],
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "contributed_to": cc["totalRepositoriesWithContributedCommits"],
        "followers": u["followers"]["totalCount"],
        "total": cc["contributionCalendar"]["totalContributions"],
        "active_days": sum(1 for _, c in days if c > 0),
        "days_count": len(days),
        "weeks": weeks,
        "langs": [(n, s / total_lang) for n, s in top],
    }


PAL = {
    "dark": dict(
        bg0="#1a1033", bg1="#120b22", border="#3b2a6b",
        title="#f5f3ff", label="#a99cd0", value="#f5f3ff", muted="#8b7fb8",
        accent="#a78bfa", accent2="#4ade80", track="#2a1d4d",
        levels=["#2a1d52", "#4c3390", "#6d4fc2", "#9d7bd8", "#d9ccff"],
        langs=["#c4b5fd", "#a78bfa", "#8b5cf6", "#4ade80", "#f0abfc", "#6d4fc2"],
        grad0="#ffffff", grad1="#a78bfa"),
    "light": dict(
        bg0="#fbf9ff", bg1="#f1ecff", border="#ddd0fb",
        title="#3b0d8a", label="#6b5aa6", value="#3b0d8a", muted="#8b7fb8",
        accent="#7c3aed", accent2="#22c55e", track="#e6dcfb",
        levels=["#e6ddfb", "#c9b6f7", "#a98df0", "#8560e3", "#5b2fc9"],
        langs=["#7c3aed", "#a78bfa", "#c4b5fd", "#22c55e", "#e879f9", "#4c1d95"],
        grad0="#3b0d8a", grad1="#9333ea"),
}


def fontface(key):
    f = FONTS[key]
    return ("@font-face{font-family:'%s';font-style:%s;font-weight:%s;"
            "src:url(data:font/woff2;base64,%s) format('woff2');}\n"
            % (f["family"], f["style"], f["weight"], f["b64"]))


CSS = (fontface("outfit") + fontface("jbmono") +
       ".t{font-family:'Outfit',sans-serif;font-weight:800}"
       ".m{font-family:'JetBrains Mono',monospace;font-weight:500}"
       "@keyframes pop{from{opacity:0;transform:scale(.55)}to{opacity:1;transform:scale(1)}}"
       ".c{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.2,.8,.2,1) both}"
       "@keyframes bar{from{transform:scaleX(0)}to{transform:scaleX(1)}}"
       ".b{transform-origin:left;animation:bar 1.2s cubic-bezier(.2,.8,.2,1) .2s both}")

ICON = {
    "star": '<path d="M0,-6.5 L1.9,-2 L6.5,-1.7 L2.9,1.4 L4,6 L0,3.5 L-4,6 L-2.9,1.4 L-6.5,-1.7 L-1.9,-2 Z"/>',
    "commit": '<circle r="3.2" fill="none" stroke-width="1.8"/><path d="M-7.5,0 H-3.2 M3.2,0 H7.5" stroke-width="1.8"/>',
    "pr": ('<circle cx="-4" cy="-4.2" r="2.1" fill="none" stroke-width="1.6"/>'
           '<circle cx="-4" cy="4.6" r="2.1" fill="none" stroke-width="1.6"/>'
           '<circle cx="4.6" cy="4.6" r="2.1" fill="none" stroke-width="1.6"/>'
           '<path d="M-4,-2.1 V2.5 M4.6,2.5 V-0.8 Q4.6,-4.2 1.2,-4.2 H-0.6" fill="none" stroke-width="1.6"/>'),
    "issue": '<circle r="6" fill="none" stroke-width="1.8"/><circle r="1.7"/>',
    "repo": '<path d="M-5,-6.5 H5 V6.5 H-3.4 Q-5,6.5 -5,4.9 Z M-5,3.3 H5" fill="none" stroke-width="1.6"/>',
}


def fmt(n):
    return f"{n/1000:.1f}k" if n >= 10000 else f"{n:,}"


def card_frame(p, w, h, gid):
    return (f'<defs><style><![CDATA[{CSS}]]></style>'
            f'<linearGradient id="bg{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{p["bg0"]}"/><stop offset="1" stop-color="{p["bg1"]}"/></linearGradient>'
            f'<linearGradient id="tg{gid}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{p["grad0"]}"/><stop offset="1" stop-color="{p["grad1"]}"/></linearGradient>'
            f'<linearGradient id="rg{gid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{p["accent"]}"/><stop offset="1" stop-color="{p["accent2"]}"/></linearGradient>'
            f'</defs>'
            f'<rect x="0.75" y="0.75" width="{w-1.5}" height="{h-1.5}" rx="16" fill="url(#bg{gid})" stroke="{p["border"]}" stroke-width="1.5"/>')


def stats_card(theme, d):
    p = PAL[theme]
    W, H = 445, 195
    rows = [("star", "stars", d["stars"]), ("commit", "commits", d["commits"]),
            ("pr", "pull requests", d["prs"]), ("issue", "issues", d["issues"]),
            ("repo", "repos", d["repos"])]
    body = []
    for i, (ic, label, val) in enumerate(rows):
        y = 70 + i * 26
        body.append(f'<g transform="translate(34 {y-4.5})" fill="{p["accent"]}" stroke="{p["accent"]}" stroke-linecap="round" stroke-linejoin="round">{ICON[ic]}</g>')
        body.append(f'<text x="52" y="{y}" class="m" font-size="13" fill="{p["label"]}">{label}</text>')
        body.append(f'<text x="252" y="{y}" class="t" font-size="15" text-anchor="end" fill="{p["value"]}">{fmt(val)}</text>')
    # ring: share of active days in the last 12 months
    cx, cy, r = 352, 104, 50
    circ = 2 * math.pi * r
    frac = d["active_days"] / max(d["days_count"], 1)
    ring = (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{p["track"]}" stroke-width="9"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#rgS)" stroke-width="9" stroke-linecap="round" '
            f'stroke-dasharray="{circ:.2f}" stroke-dashoffset="{circ*(1-frac):.2f}" transform="rotate(-90 {cx} {cy})">'
            f'<animate attributeName="stroke-dashoffset" from="{circ:.2f}" to="{circ*(1-frac):.2f}" dur="1.4s" fill="freeze" calcMode="spline" keySplines=".2 .8 .2 1"/></circle>'
            f'<text x="{cx}" y="{cy+6}" class="t" font-size="27" text-anchor="middle" fill="{p["value"]}">{fmt(d["total"])}</text>'
            f'<text x="{cx}" y="{cy+24}" class="m" font-size="10" text-anchor="middle" fill="{p["muted"]}">contributions</text>'
            f'<text x="{cx}" y="{cy+r+26}" class="m" font-size="10.5" text-anchor="middle" fill="{p["muted"]}">last 12 months</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="github stats of {LOGIN}">'
            + card_frame(p, W, H, "S")
            + f'<g transform="translate(34 31)" fill="{p["accent"]}">{ICON["star"]}</g>'
            + f'<text x="52" y="37" class="t" font-size="19" fill="url(#tgS)">{LOGIN}</text>'
            + f'<text x="252" y="37" class="m" font-size="11" text-anchor="end" fill="{p["muted"]}">github stats</text>'
            + "".join(body) + ring + "</svg>")


def calendar_card(theme, d):
    p = PAL[theme]
    W, H = 1200, 280
    x0, y0, cell, gap = 48, 78, 16, 4
    step = cell + gap
    weeks = d["weeks"]
    mx = max((c for w in weeks for _, c in w), default=0)

    def level(c):
        if c <= 0:
            return 0
        if mx <= 4:
            return min(c, 4)
        return min(4, 1 + int(3 * (c - 1) / max(mx - 1, 1) + 1e-9) if c < mx else 4)

    cells, labels = [], []
    last_month, last_label_x = None, -999
    for wi, week in enumerate(weeks):
        x = x0 + wi * step
        first = dt.date.fromisoformat(week[0][0])
        if first.month != last_month:
            if x - last_label_x >= 3 * step and wi < len(weeks) - 2:
                labels.append(f'<text x="{x}" y="{y0-12}" class="m" font-size="11" fill="{p["muted"]}">{first.strftime("%b").lower()}</text>')
                last_label_x = x
            last_month = first.month
        for date, count in week:
            di = dt.date.fromisoformat(date).weekday()  # mon=0 … sun=6
            di = (di + 1) % 7  # sun=0 … sat=6, like github
            y = y0 + di * step
            cells.append(f'<rect class="c" x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3.5" fill="{p["levels"][level(count)]}" style="animation-delay:{wi*0.018:.3f}s"><title>{date}: {count}</title></rect>')
    # language bar
    by, bh, bx0, bx1 = 238, 8, x0, W - x0
    bw = bx1 - bx0
    segs, legend = [], []
    x = bx0
    lx = bx0
    for i, (name, share) in enumerate(d["langs"]):
        w = bw * share
        col = p["langs"][i % len(p["langs"])]
        segs.append(f'<rect x="{x:.1f}" y="{by}" width="{max(w-2,0):.1f}" height="{bh}" fill="{col}"/>')
        x += w
        txt = f"{name} {share*100:.1f}%"
        legend.append(f'<circle cx="{lx+4}" cy="{by+26}" r="4" fill="{col}"/>'
                      f'<text x="{lx+14}" y="{by+30}" class="m" font-size="11" fill="{p["label"]}">{txt}</text>')
        lx += 14 + len(txt) * 6.6 + 22
    bar = (f'<clipPath id="bc"><rect x="{bx0}" y="{by}" width="{bw}" height="{bh}" rx="4"/></clipPath>'
           f'<g clip-path="url(#bc)"><rect x="{bx0}" y="{by}" width="{bw}" height="{bh}" fill="{p["track"]}"/>'
           f'<g class="b">{"".join(segs)}</g></g>' + "".join(legend))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="contribution calendar of {LOGIN}">'
            + card_frame(p, W, H, "C")
            + f'<g transform="translate(58 34)" fill="{p["accent"]}">{ICON["star"]}</g>'
            + f'<text x="76" y="40" class="t" font-size="19" fill="url(#tgC)">contributions</text>'
            + f'<text x="{W-x0}" y="40" class="m" font-size="12" text-anchor="end" fill="{p["label"]}">{fmt(d["total"])} contributions · {d["active_days"]} active days · last 12 months</text>'
            + "".join(labels) + "".join(cells) + bar + "</svg>")


def main():
    os.makedirs(OUT, exist_ok=True)
    d = collect()
    for theme in ("dark", "light"):
        for name, fn in (("stats", stats_card), ("calendar", calendar_card)):
            path = os.path.join(OUT, f"{name}-{theme}.svg")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(fn(theme, d))
            print(f"wrote {path} ({os.path.getsize(path)//1024} KB)")
    print(json.dumps({k: v for k, v in d.items() if k != "weeks"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
