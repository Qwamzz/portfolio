"""Render the social share card and the touch icons.

Run once whenever the name or focus line changes:

    python tools/make_share_images.py <fonts-dir>

<fonts-dir> must contain TTF files for the site's fonts:
    bricolage-700.ttf   Bricolage Grotesque, optical size 96, weight 700
    geistmono-500.ttf   Geist Mono, weight 500

Fetch them from Google Fonts (any CSS2 URL requested without a browser user
agent returns .ttf links). Pillow is only needed here, not by the site.
"""

import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")

PAPER = (243, 242, 237)
INK = (14, 14, 15)
SIGNAL = (200, 240, 49)
MUTED = (163, 161, 155)

NAME = ["Nii Yartey", "Gidiglo"]
EYEBROW = "CLOUD  /  SECURITY  /  DATA ENGINEERING"
TICKER = ["AZ-305", "AZ-400", "AZ-500", "SC-200", "AZ-700", "AI-102", "AZ-104", "KCNA", "ISO 27001"]
FOOTER = "ACCRA, GHANA"


def tracked(draw, xy, text, font, fill, tracking):
    """Draw text with letter spacing, which Pillow has no option for."""
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill)
        x += draw.textlength(char, font=font) + tracking
    return x


def share_card(fonts):
    width, height = 1200, 630
    img = Image.new("RGB", (width, height), INK)
    d = ImageDraw.Draw(img)

    display = ImageFont.truetype(os.path.join(fonts, "bricolage-700.ttf"), 132)
    mono = ImageFont.truetype(os.path.join(fonts, "geistmono-500.ttf"), 22)
    mono_small = ImageFont.truetype(os.path.join(fonts, "geistmono-500.ttf"), 20)

    pad = 72
    # Eyebrow with the signal square, as on the site.
    d.rectangle((pad, pad + 6, pad + 12, pad + 18), fill=SIGNAL)
    tracked(d, (pad + 28, pad), EYEBROW, mono, MUTED, 2.2)

    # Name, tightly tracked like the hero.
    y = pad + 70
    for line in NAME:
        tracked(d, (pad - 4, y), line, display, PAPER, -4.5)
        y += 128

    # Location, bottom right of the name block.
    loc_w = d.textlength(FOOTER, font=mono_small) + len(FOOTER) * 2
    tracked(d, (width - pad - loc_w, height - 96 - 52), FOOTER, mono_small, MUTED, 2)

    # Signal band with exam codes.
    band_top = height - 96
    d.rectangle((0, band_top, width, height), fill=SIGNAL)
    # Only as many codes as fit inside the margins - never clip one.
    x = pad
    for code in TICKER:
        w = sum(d.textlength(ch, font=mono) + 2.4 for ch in code)
        if x + w > width - pad:
            break
        tracked(d, (x, band_top + 36), code, mono, INK, 2.4)
        x += w + 44

    out = os.path.join(IMG, "og.png")
    img.save(out, optimize=True)
    return out


def icon(fonts, size, name):
    img = Image.new("RGB", (size, size), INK)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(os.path.join(fonts, "bricolage-700.ttf"), int(size * 0.44))
    text = "NY"
    tracking = -size * 0.02
    w = sum(d.textlength(c, font=font) for c in text) + tracking * (len(text) - 1)
    bbox = d.textbbox((0, 0), text, font=font)
    h = bbox[3] - bbox[1]
    tracked(d, ((size - w) / 2, (size - h) / 2 - bbox[1]), text, font, SIGNAL, tracking)
    out = os.path.join(IMG, name)
    img.save(out, optimize=True)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    fonts_dir = sys.argv[1]
    for path in (share_card(fonts_dir),
                 icon(fonts_dir, 180, "apple-touch-icon.png"),
                 icon(fonts_dir, 32, "favicon-32.png")):
        print("wrote", os.path.relpath(path, ROOT), os.path.getsize(path), "bytes")
