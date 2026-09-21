#!/usr/bin/env python3
"""Frame the Platane/snk output in the same card chrome as the other cards.

Runs after the snk step (see .github/workflows/cards.yml): reads the raw
dist/snake-{dark,light}.svg, wraps each in a bordered card carrying the
title, the contribution summary and the language bar, then writes it back.
Reads .cards-data.json produced by gen_cards.py, so no API call of its own.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import gen_cards as g  # noqa: E402  绘图函数与调色板的唯一来源

OUT = g.OUT
DATA = g.DATA


def split_svg(svg):
    """拆出 snk 根元素的 viewBox 与内部内容，供嵌套 <svg> 使用。"""
    m = re.match(r'\s*<svg\b([^>]*)>(.*)</svg>\s*\Z', svg, re.S)
    if not m:
        raise SystemExit("unexpected snk output: no single root <svg>")
    attrs, inner = m.group(1), m.group(2)
    vb = re.search(r'viewBox="([-\d.\s]+)"', attrs)
    if not vb:
        raise SystemExit("unexpected snk output: no viewBox")
    nums = [float(v) for v in vb.group(1).split()]
    if len(nums) != 4:
        raise SystemExit(f"unexpected viewBox: {vb.group(1)!r}")
    # snk 在棋盘下方还画了一条自己的进度条，会和卡片底部的语言条撞在一起；
    # 把 viewBox 收到棋盘底边，多出来的部分由嵌套 <svg> 自动裁掉
    ys = [float(y) for y in re.findall(r'<rect class="c[^"]*"[^>]*\sy="([-\d.]+)"', inner)]
    if ys:
        cell = 12.0
        nums[3] = max(ys) + cell + 6 - nums[1]
    return nums, inner


def main():
    if not os.path.exists(DATA):
        raise SystemExit(f"{DATA} not found — run gen_cards.py first")
    with open(DATA, encoding="utf-8") as fh:
        d = json.load(fh)

    for theme in ("dark", "light"):
        path = os.path.join(OUT, f"snake-{theme}.svg")
        if not os.path.exists(path):
            raise SystemExit(f"{path} not found — did the snk step run?")
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        if "contribution snake of" in raw[:400]:
            print(f"skipped {path} (already framed)")
            continue
        vb, inner = split_svg(raw)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(g.snake_card(theme, d, inner, vb))
        print(f"framed {path} ({os.path.getsize(path)//1024} KB)")


if __name__ == "__main__":
    main()
