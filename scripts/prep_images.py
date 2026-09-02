#!/usr/bin/env python3
"""Prepare the portrait crops that gen_hero.py embeds into the banners.

Inputs (not tracked): the two CLANNAD frames.
Outputs: scripts/kyou.jpg (hero) and scripts/rain-{dark,light}.jpg (footer duotone).
Needs Pillow.  Run only when the source art changes.
"""
import os
import sys

from PIL import Image, ImageEnhance

HERE = os.path.dirname(os.path.abspath(__file__))


def duotone(img, shadow, highlight, gamma=1.0):
    """Map luminance onto a two-colour ramp."""
    g = img.convert("L")
    if gamma != 1.0:
        g = g.point(lambda v: int(255 * ((v / 255) ** gamma)))
    ramp = []
    for band in range(3):
        ramp += [int(shadow[band] + (highlight[band] - shadow[band]) * v / 255) for v in range(256)]
    return g.convert("RGB").point(ramp)


def main(rain_src, hero_src=None):
    rain = Image.open(rain_src).convert("RGB")
    # crop around the figure: she sits centre-left, face near the lower third
    box = (350, 130, 1820, 1030)
    crop = rain.crop(box)
    crop = ImageEnhance.Contrast(crop).enhance(1.12)
    variants = {
        # deep violet shadows, cool lavender highlights - matches the hero palette
        "rain-dark": ((11, 7, 24), (156, 133, 219), 1.35),
        "rain-light": ((70, 54, 120), (240, 234, 253), 0.82),
    }
    for name, (shadow, highlight, gamma) in variants.items():
        out = duotone(crop, shadow, highlight, gamma).resize((1240, 760), Image.LANCZOS)
        path = os.path.join(HERE, f"{name}.jpg")
        out.save(path, "JPEG", quality=82, optimize=True, subsampling=1)
        print(f"{path}: {os.path.getsize(path)//1024} KB")

    if hero_src:
        hero = Image.open(hero_src).convert("RGB").crop((60, 0, 1108, 872))
        path = os.path.join(HERE, "kyou.jpg")
        hero.save(path, "JPEG", quality=84, optimize=True, subsampling=1)
        print(f"{path}: {os.path.getsize(path)//1024} KB")


if __name__ == "__main__":
    main(*sys.argv[1:])
