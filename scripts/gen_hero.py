#!/usr/bin/env python3
"""Regenerate assets/hero-*.svg, divider-*.svg and footer-*.svg.

Usage:  python scripts/gen_hero.py      (needs fontTools + brotli for text measuring)
Fonts come from scripts/fonts.json (Google Fonts subsets), the portrait from scripts/kyou.jpg.
"""
import json, base64, io, os, random
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "assets")
os.makedirs(OUT, exist_ok=True)
fonts = json.load(open(os.path.join(HERE, "fonts.json")))
img_b64 = base64.b64encode(open(os.path.join(HERE, "kyou.jpg"), "rb").read()).decode()

_ttf = {}
def ttf(key):
    if key not in _ttf:
        _ttf[key] = TTFont(io.BytesIO(base64.b64decode(fonts[key]["b64"])))
    return _ttf[key]

def width(key, text, size, fallback=None, letter_spacing=0.0):
    f = ttf(key); cmap = f.getBestCmap(); hmtx = f["hmtx"]; upem = f["head"].unitsPerEm
    total = 0.0
    for ch in text:
        g = cmap.get(ord(ch))
        if g is not None:
            total += hmtx[g][0] / upem * size
        elif fallback:
            fb = ttf(fallback); g2 = fb.getBestCmap().get(ord(ch))
            total += (fb["hmtx"][g2][0] / fb["head"].unitsPerEm * size) if g2 else size
        else:
            total += size * 0.6
        total += letter_spacing
    return total

def fontface(key):
    f = fonts[key]
    return ("@font-face{font-family:'%s';font-style:%s;font-weight:%s;"
            "src:url(data:font/woff2;base64,%s) format('woff2');}\n"
            % (f["family"], f["style"], f["weight"], f["b64"]))

PAL = {
 "dark": dict(
   bg0="#100a22", bg1="#1a1036", bg2="#0d1520",
   blob1="#7c3aed", blob2="#c084fc", blob3="#22c55e", blob4="#a78bfa",
   blob1o=".55", blob2o=".30", blob3o=".22", blob4o=".28",
   name0="#ffffff", name1="#dcd0ff", name2="#a78bfa", nameGlow="#7c3aed", glowO=".7",
   over="#a78bfa", tag="#ede9fe", cn="#b9a7ea",
   pillStroke="#8b6ce8", pillFill="#7c3aed", pillFillO=".16", pillText="#e2d9ff",
   bokeh="#ffffff", bokehO="1", spark="#ffffff",
   border="#c4b5fd", borderO=".22", grainO=".045", cursor="#a78bfa", imgBottom=".28",
   footText="#e9ddff", footSub="#b9a7ea", footMono="#8b7fb8"),
 "light": dict(
   bg0="#fbf9ff", bg1="#f2ecff", bg2="#eef6ef",
   blob1="#c4b5fd", blob2="#f5d0fe", blob3="#a7f3c0", blob4="#ddd6fe",
   blob1o=".75", blob2o=".55", blob3o=".55", blob4o=".9",
   name0="#3b0d8a", name1="#6d28d9", name2="#a21caf", nameGlow="#c4b5fd", glowO=".55",
   over="#7c3aed", tag="#4c1d95", cn="#6b5aa6",
   pillStroke="#a78bfa", pillFill="#7c3aed", pillFillO=".08", pillText="#5b21b6",
   bokeh="#c4b5fd", bokehO=".8", spark="#8b5cf6",
   border="#7c3aed", borderO=".18", grainO=".03", cursor="#7c3aed", imgBottom=".45",
   footText="#3b0d8a", footSub="#6b5aa6", footMono="#8b7fb8"),
}

def star(s):
    k = s * 0.22
    return f"M0,{-s:.1f} L{k:.1f},{-k:.1f} L{s:.1f},0 L{k:.1f},{k:.1f} L0,{s:.1f} L{-k:.1f},{k:.1f} L{-s:.1f},0 L{-k:.1f},{-k:.1f} Z"

W, H = 1200, 480
IMG_W, IMG_H = 1048, 872
img_w = IMG_W * H / IMG_H
img_x = W - img_w

BASE_CSS = """
.over{font-family:'JetBrains Mono',monospace;font-weight:500;font-size:14px;letter-spacing:2.5px}
.name{font-family:'Outfit',sans-serif;font-weight:800;font-size:92px;letter-spacing:-2px}
.tag{font-family:'Instrument Serif',serif;font-style:italic;font-size:33px}
.cn{font-family:'Noto Serif SC',serif;font-weight:600;font-size:18px;letter-spacing:1.5px}
.pill{font-family:'JetBrains Mono','Noto Sans SC',monospace;font-weight:500;font-size:13px}
.foot-cn{font-family:'Noto Serif SC',serif;font-weight:600;font-size:22px;letter-spacing:2px}
.foot-en{font-family:'Instrument Serif',serif;font-style:italic;font-size:21px}
"""

def bokeh(p, seed=7, n=16):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        cx = rnd.uniform(20, 1180); cy = rnd.uniform(20, 460)
        r = rnd.uniform(5, 24); o = rnd.uniform(0.10, 0.42) * float(p["bokehO"])
        dy = -rnd.uniform(18, 48); dur = rnd.uniform(9, 19); beg = -rnd.uniform(0, 12)
        out.append(
            f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.1f}" opacity="{o:.2f}">'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {dy:.0f};0 0" '
            f'dur="{dur:.1f}s" begin="{beg:.1f}s" repeatCount="indefinite"/></circle>')
    return "\n".join(out)

SPARKS = [(688,74,9,3.1,0.0),(1118,108,12,2.6,0.8),(1046,36,7,3.6,1.5),(1152,326,8,2.9,0.4),(704,404,7,3.3,2.1),(862,48,6,2.4,1.1),(1180,220,5,3.8,0.6)]
def sparkles(p):
    out = []
    for (x, y, s, dur, beg) in SPARKS:
        out.append(
            f'<g transform="translate({x} {y})"><path d="{star(s)}" fill="{p["spark"]}">'
            f'<animate attributeName="opacity" values="0.15;1;0.15" dur="{dur}s" begin="{beg}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="scale" values="0.7;1.15;0.7" dur="{dur}s" begin="{beg}s" repeatCount="indefinite"/>'
            f'</path></g>')
    return "\n".join(out)

PILLS = ["北京交通大学 · 本科", "GNN", "agent memory", "sitzfleisch"]
def pills(p, x0=72, y0=356):
    out = []; x = x0
    for t in PILLS:
        tw = width("jbmono", t, 13, fallback="notosans")
        w = tw + 28
        out.append(
            f'<rect x="{x:.1f}" y="{y0}" width="{w:.1f}" height="28" rx="14" fill="{p["pillFill"]}" fill-opacity="{p["pillFillO"]}" '
            f'stroke="{p["pillStroke"]}" stroke-opacity=".75" stroke-width="1"/>'
            f'<text x="{x+14:.1f}" y="{y0+18.5}" class="pill" fill="{p["pillText"]}">{t}</text>')
        x += w + 10
    return "\n".join(out)

def hero(theme):
    p = PAL[theme]
    css = "".join(fontface(k) for k in ("outfit","iserif","jbmono","notoserif","notosans")) + BASE_CSS
    name_w = width("outfit", "snooze26h", 92, letter_spacing=-2)
    cursor_x = 72 + name_w + 12
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="snooze26h — the day starts when you sit down">
<title>snooze26h — the day starts when you sit down</title>
<defs>
<style><![CDATA[{css}]]></style>
<clipPath id="card"><rect x="0" y="0" width="{W}" height="{H}" rx="28" ry="28"/></clipPath>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="{p['bg0']}"/><stop offset=".55" stop-color="{p['bg1']}"/><stop offset="1" stop-color="{p['bg2']}"/>
</linearGradient>
<linearGradient id="nameGrad" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{p['name0']}"/><stop offset=".6" stop-color="{p['name1']}"/><stop offset="1" stop-color="{p['name2']}"/>
</linearGradient>
<linearGradient id="fadeH" gradientUnits="userSpaceOnUse" x1="{img_x:.1f}" y1="0" x2="{img_x+200:.1f}" y2="0">
  <stop offset="0" stop-color="#000"/><stop offset="1" stop-color="#fff"/>
</linearGradient>
<linearGradient id="fadeV" gradientUnits="userSpaceOnUse" x1="0" y1="320" x2="0" y2="{H}">
  <stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="{p['imgBottom']}"/>
</linearGradient>
<mask id="mV"><rect x="{img_x:.1f}" y="0" width="{img_w:.1f}" height="{H}" fill="url(#fadeV)"/></mask>
<mask id="mImg"><g mask="url(#mV)"><rect x="{img_x:.1f}" y="0" width="{img_w:.1f}" height="{H}" fill="url(#fadeH)"/></g></mask>
<filter id="blur70" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="70"/></filter>
<filter id="blur9" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="9"/></filter>
<filter id="blur18" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="18"/></filter>
<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter>
</defs>
<g clip-path="url(#card)">
<rect width="{W}" height="{H}" fill="url(#bg)"/>
<g filter="url(#blur70)">
<ellipse cx="230" cy="430" rx="430" ry="210" fill="{p['blob1']}" opacity="{p['blob1o']}"><animate attributeName="cx" values="230;320;230" dur="17s" repeatCount="indefinite"/></ellipse>
<ellipse cx="540" cy="30" rx="330" ry="150" fill="{p['blob2']}" opacity="{p['blob2o']}"><animate attributeName="cy" values="30;80;30" dur="21s" repeatCount="indefinite"/></ellipse>
<ellipse cx="1090" cy="480" rx="290" ry="130" fill="{p['blob3']}" opacity="{p['blob3o']}"/>
<ellipse cx="730" cy="240" rx="200" ry="230" fill="{p['blob4']}" opacity="{p['blob4o']}"><animate attributeName="rx" values="200;250;200" dur="14s" repeatCount="indefinite"/></ellipse>
</g>
<g filter="url(#blur9)" fill="{p['bokeh']}">
{bokeh(p)}
</g>
<image href="data:image/jpeg;base64,{img_b64}" x="{img_x:.1f}" y="0" width="{img_w:.1f}" height="{H}" preserveAspectRatio="xMidYMid slice" mask="url(#mImg)"/>
{sparkles(p)}
<rect width="{W}" height="{H}" filter="url(#grain)" opacity="{p['grainO']}"/>
<text x="72" y="118" class="over" fill="{p['over']}">hi there, i'm</text>
<text x="72" y="222" class="name" fill="{p['nameGlow']}" opacity="{p['glowO']}" filter="url(#blur18)">snooze26h</text>
<text x="72" y="222" class="name" fill="url(#nameGrad)">snooze26h</text>
<rect x="{cursor_x:.1f}" y="160" width="7" height="64" rx="2" fill="{p['cursor']}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" dur="1.1s" repeatCount="indefinite"/></rect>
<text x="72" y="282" class="tag" fill="{p['tag']}">the day starts when you sit down.</text>
<text x="72" y="318" class="cn" fill="{p['cn']}">一天从坐下那一刻开始。</text>
{pills(p)}
<rect x="1" y="1" width="{W-2}" height="{H-2}" rx="27" fill="none" stroke="{p['border']}" stroke-opacity="{p['borderO']}" stroke-width="1.5"/>
</g>
</svg>
'''

def divider(theme):
    p = PAL[theme]
    c1 = "#a78bfa" if theme == "dark" else "#7c3aed"
    c2 = "#4ade80" if theme == "dark" else "#22c55e"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 28" width="1200" height="28">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{c1}" stop-opacity="0"/><stop offset=".5" stop-color="{c1}" stop-opacity=".9"/><stop offset="1" stop-color="{c2}" stop-opacity="0"/></linearGradient>
</defs>
<line x1="60" y1="14" x2="1140" y2="14" stroke="url(#g)" stroke-width="1.5"/>
<g transform="translate(600 14)"><path d="{star(7)}" fill="{c1}"><animateTransform attributeName="transform" type="rotate" values="0;90" dur="6s" repeatCount="indefinite"/></path></g>
</svg>
'''

def footer(theme):
    p = PAL[theme]
    css = "".join(fontface(k) for k in ("iserif","jbmono","notoserif")) + BASE_CSS
    FW, FH = 1200, 170
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {FW} {FH}" width="{FW}" height="{FH}" role="img" aria-label="私人笔记留过程，公开文字留结论">
<defs>
<style><![CDATA[{css}]]></style>
<clipPath id="card"><rect x="0" y="0" width="{FW}" height="{FH}" rx="28" ry="28"/></clipPath>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{p['bg2']}"/><stop offset=".5" stop-color="{p['bg1']}"/><stop offset="1" stop-color="{p['bg0']}"/></linearGradient>
<filter id="blur60" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="60"/></filter>
<filter id="grain" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/></filter>
</defs>
<g clip-path="url(#card)">
<rect width="{FW}" height="{FH}" fill="url(#bg)"/>
<g filter="url(#blur60)">
<ellipse cx="180" cy="190" rx="360" ry="120" fill="{p['blob1']}" opacity="{p['blob1o']}"><animate attributeName="cx" values="180;260;180" dur="18s" repeatCount="indefinite"/></ellipse>
<ellipse cx="1040" cy="190" rx="300" ry="110" fill="{p['blob3']}" opacity="{p['blob3o']}"/>
<ellipse cx="640" cy="-40" rx="320" ry="110" fill="{p['blob2']}" opacity="{p['blob2o']}"><animate attributeName="cx" values="640;560;640" dur="22s" repeatCount="indefinite"/></ellipse>
</g>
<rect width="{FW}" height="{FH}" filter="url(#grain)" opacity="{p['grainO']}"/>
<g transform="translate(600 40)"><path d="{star(8)}" fill="{p['spark']}" opacity=".9"><animate attributeName="opacity" values="0.3;1;0.3" dur="3s" repeatCount="indefinite"/></path></g>
<text x="600" y="86" text-anchor="middle" class="foot-cn" fill="{p['footText']}">私人笔记留过程，公开文字留结论</text>
<text x="600" y="120" text-anchor="middle" class="foot-en" fill="{p['footSub']}">private notes keep the process, public words keep the conclusions.</text>
<text x="600" y="150" text-anchor="middle" class="over" fill="{p['footMono']}">snooze26h  ·  beijing jiaotong university</text>
<rect x="1" y="1" width="{FW-2}" height="{FH-2}" rx="27" fill="none" stroke="{p['border']}" stroke-opacity="{p['borderO']}" stroke-width="1.5"/>
</g>
</svg>
'''

for theme in ("dark", "light"):
    for name, fn in (("hero", hero), ("divider", divider), ("footer", footer)):
        path = os.path.join(OUT, f"{name}-{theme}.svg")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(fn(theme))
        print(f"{path}: {os.path.getsize(path)/1024:.0f} KB")
