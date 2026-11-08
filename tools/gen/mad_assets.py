"""Textures for the 新宿决战 line-performance chart (all procedural, white so they can be tinted in-chart).

usage: python tools/gen/mad_assets.py <out_dir> [title_font.ttf]
The title texture is pre-rendered into tools/data/mad/title.png (Yuji Boku, SIL OFL 1.1); pass a font
to re-render it.
"""
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "mad")
rng = np.random.default_rng(1224)


def save(arr, out, name):
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(out, name), optimize=True)


def alpha_img(a):
    out = np.ones(a.shape + (4,), np.float32)
    out[..., 3] = np.clip(a, 0, 1)
    return out


def radial(n):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    return np.hypot(x - (n - 1) / 2, y - (n - 1) / 2) / (n / 2)


def make(out, font=None):
    os.makedirs(out, exist_ok=True)
    save(np.ones((64, 64, 4), np.float32), out, "white.png")
    r = radial(256)
    save(alpha_img(np.exp(-(r / 0.42) ** 2) * (r < 1)), out, "glow.png")
    save(alpha_img(np.clip((1 - r) / 0.02, 0, 1)), out, "disc.png")
    r = radial(512)
    save(alpha_img(np.clip(1 - np.abs(r - 0.94) / 0.012, 0, 1) + 0.45 * np.exp(-((r - 0.94) / 0.035) ** 2)), out, "ring.png")
    # soft horizontal glow bar (slash halos)
    yy = np.linspace(-1, 1, 64)[:, None]
    xx = np.linspace(-1, 1, 1024)[None, :]
    save(alpha_img(np.exp(-(yy / 0.3) ** 2) * np.clip((1 - np.abs(xx)) / 0.12, 0, 1)), out, "beam.png")
    # spike: tall isosceles triangle pointing up, base at the bottom edge
    h, w = 1024, 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    half = (yy / (h - 1)) * (w / 2)
    save(alpha_img(np.clip(half - np.abs(xx - (w - 1) / 2) + 0.5, 0, 1)), out, "spike.png")
    # focus lines (集中線): thin wedges from the rim, clear centre
    n = 1024
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    cx = cy = (n - 1) / 2
    ang = np.arctan2(yy - cy, xx - cx)
    rad = np.hypot(xx - cx, yy - cy) / (n / 2)
    a = np.zeros((n, n), np.float32)
    for _ in range(170):
        th = rng.uniform(-math.pi, math.pi)
        inner = rng.uniform(0.38, 0.72)
        width = rng.uniform(0.0025, 0.009)
        d = np.abs((ang - th + math.pi) % (2 * math.pi) - math.pi)
        wedge = np.clip(1 - d / (width * np.clip((rad - inner) / (1.45 - inner), 0, 1) + 1e-6), 0, 1) * (rad > inner)
        a = np.maximum(a, wedge * rng.uniform(0.6, 1.0))
    save(alpha_img(a * np.clip((1.45 - rad) / 0.1, 0, 1)), out, "focus.png")
    # speed lines: horizontal streaks
    h, w = 256, 1024
    a = np.zeros((h, w), np.float32)
    xs = np.arange(w)[None, :].astype(np.float32)
    for _ in range(90):
        y0 = rng.integers(0, h)
        th = rng.integers(1, 4)
        x0 = rng.uniform(-200, w)
        ln = rng.uniform(120, 600)
        prof = np.clip(1 - np.abs((xs - x0 - ln / 2) / (ln / 2)), 0, 1) ** 0.6
        a[max(0, y0 - th // 2):y0 + th // 2 + 1, :] = np.maximum(a[max(0, y0 - th // 2):y0 + th // 2 + 1, :], prof * rng.uniform(0.4, 1))
    save(alpha_img(a), out, "speed.png")
    # vertical gradient: opaque bottom -> transparent top
    g = np.linspace(0, 1, 512)[:, None] ** 1.7 * np.ones((1, 64))
    save(alpha_img(g), out, "grad.png")
    # square frame outline
    n = 512
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.minimum(np.minimum(xx, n - 1 - xx), np.minimum(yy, n - 1 - yy)).astype(np.float32)
    save(alpha_img(np.clip(1 - np.abs(d - 10) / 3.0, 0, 1) + 0.35 * np.exp(-((d - 10) / 9.0) ** 2)), out, "frame.png")
    # skylines (opaque buildings, lit windows punched out)
    for name, seed, hmin, hmax, wmin, wmax in (("skyline_far.png", 7, 0.25, 0.75, 40, 110), ("skyline_near.png", 11, 0.15, 0.95, 70, 190)):
        R = np.random.default_rng(seed)
        W_, H_ = 2048, 512
        im = Image.new("L", (W_, H_), 0)
        dr = ImageDraw.Draw(im)
        x = -20
        while x < W_:
            bw = int(R.uniform(wmin, wmax))
            bh = int(H_ * R.uniform(hmin, hmax))
            dr.rectangle((x, H_ - bh, x + bw, H_), fill=255)
            if R.random() < 0.25:  # antenna / stepped top
                dr.rectangle((x + bw // 3, H_ - bh - int(R.uniform(20, 60)), x + bw // 3 + 6, H_ - bh), fill=255)
            if R.random() < 0.35:
                dr.rectangle((x + bw // 5, H_ - bh - 24, x + bw - bw // 5, H_ - bh), fill=255)
            for wy in range(H_ - bh + 14, H_ - 8, 18):
                for wx in range(x + 8, x + bw - 8, 14):
                    if R.random() < 0.18:
                        dr.rectangle((wx, wy, wx + 5, wy + 8), fill=0)
            x += bw + int(R.uniform(0, 10))
        save(alpha_img(np.asarray(im).astype(np.float32) / 255), out, name)
    # starfield (soft dots) and a top-down city block plan, both 16:9
    W_, H_ = 2048, 1152
    yy, xx = np.mgrid[0:H_, 0:W_].astype(np.float32)
    a = np.zeros((H_, W_), np.float32)
    R = np.random.default_rng(5)
    for _ in range(150):
        cx, cy = R.uniform(0, W_), R.uniform(0, H_)
        rad = R.uniform(1.2, 4.5)
        x0, x1 = int(max(0, cx - 40)), int(min(W_, cx + 41))
        y0, y1 = int(max(0, cy - 40)), int(min(H_, cy + 41))
        d = np.hypot(xx[y0:y1, x0:x1] - cx, yy[y0:y1, x0:x1] - cy)
        v = np.clip(rad + 0.5 - d, 0, 1) + 0.55 * np.exp(-(d / (rad * 3.2)) ** 2)
        a[y0:y1, x0:x1] = np.maximum(a[y0:y1, x0:x1], v * R.uniform(0.35, 1.0))
    save(alpha_img(a), out, "stars.png")
    im = Image.new("L", (W_, H_), 0)
    dr = ImageDraw.Draw(im)
    R = np.random.default_rng(9)
    for i in range(-1, 15):
        for j in range(-1, 9):
            if R.random() < 0.72:
                w = R.uniform(80, 150)
                h = w * R.uniform(0.7, 1.3)
                cx, cy = i * 150 + R.uniform(-12, 12), j * 140 + R.uniform(-12, 12)
                dr.rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), outline=255, width=4)
                if R.random() < 0.35:
                    dr.rectangle((cx - w / 2 + 14, cy - h / 2 + 14, cx + w / 2 - 14, cy + h / 2 - 14), fill=70)
    save(alpha_img(np.asarray(im).astype(np.float32) / 255), out, "city_top.png")
    # Mahoraga-style wheel: hub, inner ring, ring, 8 spokes ending in knobs (one texture so it rotates rigidly)
    n = 1024
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    X, Y = (xx - (n - 1) / 2) / (n / 2), (yy - (n - 1) / 2) / (n / 2)
    r = np.hypot(X, Y)
    pxw = 2.0 / n

    def band(d, w):
        return np.clip((w - d) / pxw + 0.5, 0, 1)
    a = np.maximum(band(np.abs(r - 0.56), 0.035), band(np.abs(r - 0.25), 0.02))
    a = np.maximum(a, band(r, 0.13))
    for k in range(8):
        ux, uy = math.cos(k * math.pi / 4), math.sin(k * math.pi / 4)
        t = np.clip(X * ux + Y * uy, 0, 0.8)
        a = np.maximum(a, band(np.hypot(X - t * ux, Y - t * uy), 0.03))
        a = np.maximum(a, band(np.hypot(X - 0.88 * ux, Y - 0.88 * uy), 0.095))
    save(alpha_img(a), out, "wheel.png")
    # title + its outline (dilated alpha, octagonal footprint)
    title = os.path.join(DATA, "title.png")
    if font:
        os.makedirs(DATA, exist_ok=True)
        f = ImageFont.truetype(font, 300)
        box = f.getbbox("新宿決戦")
        im = Image.new("L", (box[2] - box[0] + 60, box[3] - box[1] + 60), 0)
        ImageDraw.Draw(im).text((30 - box[0], 30 - box[1]), "新宿決戦", font=f, fill=255)
        im = im.filter(ImageFilter.MaxFilter(3))
        save(alpha_img(np.asarray(im).astype(np.float32) / 255), DATA, "title.png")
    shutil.copy(title, os.path.join(out, "title.png"))
    shutil.copy(os.path.join(DATA, "silence.ogg"), os.path.join(out, "silence.ogg"))
    a = np.asarray(Image.open(title).convert("RGBA"))[..., 3].astype(np.float32) / 255
    for k in range(16):
        p = np.pad(a, 1)
        nb = [p[1:-1, :-2], p[1:-1, 2:], p[:-2, 1:-1], p[2:, 1:-1]]
        if k % 2:
            nb += [p[:-2, :-2], p[:-2, 2:], p[2:, :-2], p[2:, 2:]]
        a = np.maximum.reduce([a] + nb)
    save(alpha_img(a), out, "title_outline.png")


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print("mad assets ->", sys.argv[1])
