#!/usr/bin/env python3
"""Render the profile's stats and streak cards as themed SVGs.

Runs in GitHub Actions (see .github/workflows/cards.yml) and writes
dist/stats-{dark,light}.svg and dist/streak-{dark,light}.svg, plus
.cards-data.json for scripts/wrap_snake.py (which frames the snk output).
Only the standard library is used. Fonts are embedded from scripts/fonts.json.
"""
import datetime as dt
import json
import math
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "dist")
DATA = os.environ.get("CARDS_DATA") or os.path.join(ROOT, ".cards-data.json")
LOGIN = os.environ.get("GH_LOGIN", "snooze26h")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

FONTS = json.load(open(os.path.join(HERE, "fonts.json"), encoding="utf-8"))

QUERY = """
query($login: String!) {
  user(login: $login) {
    createdAt
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


STREAK_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def gql(query, variables):
    if not TOKEN:
        sys.exit("GITHUB_TOKEN is not set")
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
    today = dt.datetime.now(dt.timezone.utc).date()
    st = streaks(all_days(u["createdAt"]), today)
    return {
        "streak": st,
        "created": u["createdAt"][:10],
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


def all_days(created):
    """从注册日逐年拉取贡献日历；GraphQL 单次查询最多覆盖一年，所以要切片。"""
    days, start = {}, dt.datetime.fromisoformat(created.replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    cur = start
    while cur < now:
        end = min(cur + dt.timedelta(days=365), now)
        cal = gql(STREAK_QUERY, {"login": LOGIN,
                                 "from": cur.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                 "to": end.strftime("%Y-%m-%dT%H:%M:%SZ")}
                  )["user"]["contributionsCollection"]["contributionCalendar"]
        for w in cal["weeks"]:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
        cur = end + dt.timedelta(seconds=1)
    return days


def streaks(days, today):
    """按 GitHub 惯例算连续天数：今天还没提交不算断签，从昨天续起。"""
    dates = sorted(days)
    total = sum(days.values())
    first = next((d for d in dates if days[d] > 0), None)
    longest = cur = 0
    lo_span = cu_span = None
    prev = None
    for d in dates:
        if days[d] > 0:
            dd = dt.date.fromisoformat(d)
            cur = cur + 1 if prev and (dd - prev).days == 1 else 1
            cu_span = (d if cur == 1 else cu_span[0], d)
            if cur > longest:
                longest, lo_span = cur, cu_span
            prev = dd
        else:
            prev = None
            cur = 0
    # 当前连续：末尾若是今天或昨天才算延续，否则归零
    tail = 0
    span_end = None
    probe = today
    if days.get(today.isoformat(), 0) == 0:
        probe = today - dt.timedelta(days=1)      # 今天还没结束，不算断
    while days.get(probe.isoformat(), 0) > 0:
        tail += 1
        span_end = span_end or probe
        probe -= dt.timedelta(days=1)
    cur_span = ((probe + dt.timedelta(days=1)).isoformat(), span_end.isoformat()) if tail else None
    return {"total": total, "first": first, "longest": longest,
            "longest_span": lo_span, "current": tail, "current_span": cur_span}


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


def lang_bar(p, d, bx0, bx1, by, gid):
    """语言占比条 + 图例，原本长在日历卡上，日历卡撤掉后移给蛇卡。"""
    bh = 8
    bw = bx1 - bx0
    segs, legend = [], []
    x = lx = bx0
    for i, (name, share) in enumerate(d["langs"]):
        w = bw * share
        col = p["langs"][i % len(p["langs"])]
        segs.append(f'<rect x="{x:.1f}" y="{by}" width="{max(w-2,0):.1f}" height="{bh}" fill="{col}"/>')
        x += w
        txt = f"{name} {share*100:.1f}%"
        legend.append(f'<circle cx="{lx+4}" cy="{by+26}" r="4" fill="{col}"/>'
                      f'<text x="{lx+14}" y="{by+30}" class="m" font-size="11" fill="{p["label"]}">{txt}</text>')
        lx += 14 + len(txt) * 6.6 + 22
    return (f'<clipPath id="bc{gid}"><rect x="{bx0}" y="{by}" width="{bw}" height="{bh}" rx="4"/></clipPath>'
            f'<g clip-path="url(#bc{gid})"><rect x="{bx0}" y="{by}" width="{bw}" height="{bh}" fill="{p["track"]}"/>'
            f'<g class="b">{"".join(segs)}</g></g>' + "".join(legend))


def streak_card(theme, d):
    """自绘连续贡献卡，替掉第三方 streak-stats 公共实例。"""
    p = PAL[theme]
    W, H = 445, 195
    st = d["streak"]

    def span(rng):
        if not rng:
            return "—"
        a, b = (dt.date.fromisoformat(x) for x in rng)
        f = lambda x: x.strftime("%b %d").replace(" 0", " ").lower()
        return f(a) if a == b else f"{f(a)} – {f(b)}"

    created = dt.date.fromisoformat(d["created"])
    cols = [
        (74, fmt(st["total"]), "total", "contributions",
         f'{created.strftime("%b %Y").lower()} – now'),
        (371, str(st["longest"]), "longest", "streak", span(st["longest_span"])),
    ]
    body = []
    for cx, val, l1, l2, sub_ in cols:
        body.append(f'<text x="{cx}" y="78" class="t" font-size="31" text-anchor="middle" fill="{p["value"]}">{val}</text>'
                    f'<text x="{cx}" y="100" class="m" font-size="11" text-anchor="middle" fill="{p["label"]}">{l1}</text>'
                    f'<text x="{cx}" y="115" class="m" font-size="11" text-anchor="middle" fill="{p["label"]}">{l2}</text>'
                    f'<text x="{cx}" y="140" class="m" font-size="9.5" text-anchor="middle" fill="{p["muted"]}">{sub_}</text>')
    # 中栏：当前连续天数套一个环，作为视觉重心
    cx, cy, r = 222, 88, 40
    circ = 2 * math.pi * r
    frac = min(st["current"] / max(st["longest"], 1), 1) if st["current"] else 0
    ring = (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{p["track"]}" stroke-width="7"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="url(#rgK)" stroke-width="7" stroke-linecap="round" '
            f'stroke-dasharray="{circ:.2f}" stroke-dashoffset="{circ*(1-frac):.2f}" transform="rotate(-90 {cx} {cy})">'
            f'<animate attributeName="stroke-dashoffset" from="{circ:.2f}" to="{circ*(1-frac):.2f}" dur="1.4s" fill="freeze" calcMode="spline" keySplines=".2 .8 .2 1"/></circle>'
            f'<text x="{cx}" y="{cy+11}" class="t" font-size="33" text-anchor="middle" fill="{p["value"]}">{st["current"]}</text>'
            f'<text x="{cx}" y="{cy+r+22}" class="m" font-size="11" text-anchor="middle" fill="{p["accent"]}">current streak</text>'
            f'<text x="{cx}" y="{cy+r+38}" class="m" font-size="9.5" text-anchor="middle" fill="{p["muted"]}">{span(st["current_span"])}</text>')
    div = "".join(f'<line x1="{x}" y1="58" x2="{x}" y2="150" stroke="{p["border"]}" stroke-width="1"/>'
                  for x in (148, 297))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="contribution streak of {LOGIN}">'
            + card_frame(p, W, H, "K")
            + f'<text x="34" y="37" class="t" font-size="19" fill="url(#tgK)">streak</text>'
            + f'<text x="{W-34}" y="37" class="m" font-size="11" text-anchor="end" fill="{p["muted"]}">since {created.strftime("%b %d, %Y").replace(" 0", " ")}</text>'
            + div + "".join(body) + ring + "</svg>")


def month_labels(p, d, cols, x0, bw, vb, y):
    """在蛇棋盘上方标月份——日历卡撤掉后，格子就没有时间参照了。"""
    vx, _, vw, _ = vb
    k = bw / vw                                   # viewBox → 卡片坐标的缩放比
    marks, last_month = [], None
    for wi, week in enumerate(d["weeks"][:len(cols)]):
        first = dt.date.fromisoformat(week[0][0])
        if first.month != last_month:
            marks.append((wi, first))
            last_month = first.month
    # 窗口起点多半落在月中，首月不足 3 周就不标，免得和下一个月挤在一起
    if len(marks) > 1 and marks[1][0] - marks[0][0] < 3:
        marks = marks[1:]
    out, last_x = [], -999
    for wi, first in marks:
        x = x0 + (cols[wi] - vx) * k
        if x - last_x >= 38 and wi < len(cols) - 2:
            out.append(f'<text x="{x:.1f}" y="{y}" class="m" font-size="11" fill="{p["muted"]}">'
                       f'{first.strftime("%b").lower()}</text>')
            last_x = x
    return "".join(out)


def snake_card(theme, d, inner, vb):
    """把 Platane/snk 的棋盘嵌进和其它卡同款的外框，并接上月份标签与语言条。"""
    p = PAL[theme]
    W = 1200
    x0 = 48
    bw = W - x0 * 2
    vx, vy, vw, vh = vb
    sh = bw * vh / vw                      # 等比缩放后的蛇高度
    sy = 72                                # 给月份标签留一行
    by = sy + sh + 14
    H = int(by + 46)
    cols = sorted({float(x) for x in re.findall(r'<rect class="c[^"]*" x="([-\d.]+)"', inner)})
    months = month_labels(p, d, cols, x0, bw, vb, sy - 8) if cols else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="contribution snake of {LOGIN}">'
            + card_frame(p, W, H, "N")
            + f'<g transform="translate(58 34)" fill="{p["accent"]}">{ICON["commit"]}</g>'
            + f'<text x="76" y="40" class="t" font-size="19" fill="url(#tgN)">contribution snake</text>'
            + f'<text x="{W-x0}" y="40" class="m" font-size="12" text-anchor="end" fill="{p["label"]}">'
              f'{fmt(d["total"])} contributions · {d["active_days"]} active days · last 12 months</text>'
            + months
            + f'<svg x="{x0}" y="{sy}" width="{bw}" height="{sh:.1f}" viewBox="{vx} {vy} {vw} {vh}">{inner}</svg>'
            + lang_bar(p, d, x0, W - x0, int(by), "N")
            + "</svg>")


def main():
    os.makedirs(OUT, exist_ok=True)
    d = collect()
    for theme in ("dark", "light"):
        for name, fn in (("stats", stats_card), ("streak", streak_card)):
            path = os.path.join(OUT, f"{name}-{theme}.svg")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(fn(theme, d))
            print(f"wrote {path} ({os.path.getsize(path)//1024} KB)")
    # 蛇卡要等 Platane/snk 跑完才能包，先把数据落盘给 wrap_snake.py
    with open(DATA, "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False)
    print(f"wrote {DATA}")
    print(json.dumps({k: v for k, v in d.items() if k != "weeks"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
