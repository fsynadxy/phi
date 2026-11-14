"""Textures for the Just Love showcase: procedural and white, so the chart tints them.

usage: python tools/gen/jl_assets.py <out_dir> [--cover cover.jpg] [--fonts font_dir]

* Shapes (snow crystals, lotus petals, hearts, aurora, ...) are generated here, deterministically.
* Lettering is pre-rendered into tools/data/justlove/ (Pinyon Script, Cormorant Garamond, Jost,
  Shippori Mincho - all SIL OFL 1.1); pass --fonts with a folder holding the .ttf files to re-render.
* The two textures cut from the cover illustration are only made when --cover is given; without it a
  neutral placeholder is written (the repository does not ship the artwork).
"""
import argparse
import math
import os
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "justlove")

TEXTS = {  # name: (font file, px size, text, letter spacing in em, glow radius)
    "t_title.png": ("PinyonScript.ttf", 330, "Just Love", 0.0, 0),
    "t_just.png": ("PinyonScript.ttf", 420, "Just", 0.0, 0),
    "t_love.png": ("PinyonScript.ttf", 420, "Love", 0.0, 0),
    "t_feat.png": ("Jost_400.ttf", 64, "FEAT. PSYQUI", 0.42, 0),
    "t_artist.png": ("ShipporiMincho_500.ttf", 84, "東雪蓮", 0.5, 0),
    "t_fin.png": ("CormorantGaramond_i500.ttf", 120, "fin.", 0.04, 0),
    "t_ch1.png": ("Jost_400.ttf", 56, "FIRST SNOW", 0.5, 0),
    "t_ch2.png": ("Jost_400.ttf", 56, "CRYSTALLIZE", 0.5, 0),
    "t_ch3.png": ("Jost_400.ttf", 56, "BLOOM", 0.5, 0),
    "t_ch4.png": ("Jost_400.ttf", 56, "SWING", 0.5, 0),
    "t_ch5.png": ("Jost_400.ttf", 56, "PRISM", 0.5, 0),
    "t_ch6.png": ("Jost_400.ttf", 56, "LETTER", 0.5, 0),
    "t_ch7.png": ("Jost_400.ttf", 56, "FULL BLOOM", 0.5, 0),
    "t_ch8.png": ("Jost_400.ttf", 56, "AFTERGLOW", 0.5, 0),
    "t_yuki.png": ("ShipporiMincho_500.ttf", 560, "雪", 0.0, 0),
    "t_hasu.png": ("ShipporiMincho_500.ttf", 560, "蓮", 0.0, 0),
}


# ------------------------------------------------------------------ helpers
def save(arr, out, name):
    Image.fromarray(np.clip(arr * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(out, name), optimize=True)


def alpha_img(a):
    out = np.ones(a.shape + (4,), np.float32)
    out[..., 3] = np.clip(a, 0, 1)
    return out


def save_l(im, out, name):
    save(alpha_img(np.asarray(im).astype(np.float32) / 255), out, name)


def grid(n, m=None):
    """coordinates in [-1, 1] (x right, y up) for an n x m image"""
    m = m or n
    y, x = np.mgrid[0:m, 0:n].astype(np.float32)
    return (x - (n - 1) / 2) / (n / 2), -(y - (m - 1) / 2) / (m / 2)


def supersample(draw_fn, W, H, k=3):
    im = Image.new("L", (W * k, H * k), 0)
    draw_fn(ImageDraw.Draw(im), k)
    return im.resize((W, H), Image.LANCZOS)


def with_glow(im, radius, gain=0.9):
    """line art + a soft halo of itself"""
    a = np.asarray(im).astype(np.float32) / 255
    g = np.asarray(im.filter(ImageFilter.GaussianBlur(radius))).astype(np.float32) / 255
    return np.clip(np.maximum(a, g * gain), 0, 1)


def value_noise(W, H, cells, seed, octaves=4):
    R = np.random.default_rng(seed)
    out = np.zeros((H, W), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        cw, ch = max(2, cells[0] * 2 ** o), max(2, cells[1] * 2 ** o)
        g = R.random((ch + 1, cw + 1)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8), "L").resize((W, H), Image.BICUBIC)
        out += amp * np.asarray(im).astype(np.float32) / 255
        tot += amp
        amp *= 0.5
    return out / tot


# ------------------------------------------------------------------ shapes
def snowflake(n, seed, branches=4, ornate=True, width=1.0):
    """a six-fold stellar dendrite: one arm is drawn, then mirrored and turned six times"""
    R = np.random.default_rng(seed)
    c = n / 2
    arm = 0.46 * n
    specs = []
    for i in range(branches):
        t = 0.24 + 0.62 * (i + 0.5) / branches + R.uniform(-0.03, 0.03)
        ln = arm * (0.34 - 0.20 * (i / max(1, branches - 1))) * R.uniform(0.85, 1.15)
        specs.append((t, ln, R.random() < 0.55))
    plate = R.uniform(0.10, 0.15) * n

    def draw(d, k):
        def seg(p, q, w):
            d.line([(p[0] * k, p[1] * k), (q[0] * k, q[1] * k)], fill=255, width=max(1, int(round(w * k * width))))

        for a6 in range(6):
            ang = math.radians(60 * a6 - 90)
            ux, uy = math.cos(ang), math.sin(ang)
            seg((c, c), (c + ux * arm, c + uy * arm), 5.0 * n / 1024)
            for t, ln, twig in specs:
                bx, by = c + ux * arm * t, c + uy * arm * t
                for sgn in (-1, 1):
                    b2 = ang + sgn * math.radians(60)
                    ex, ey = bx + math.cos(b2) * ln, by + math.sin(b2) * ln
                    seg((bx, by), (ex, ey), 3.6 * n / 1024)
                    if twig and ornate:
                        mx, my = bx + math.cos(b2) * ln * 0.55, by + math.sin(b2) * ln * 0.55
                        seg((mx, my), (mx + ux * ln * 0.38, my + uy * ln * 0.38), 2.6 * n / 1024)
            # diamond tip
            tx, ty = c + ux * arm, c + uy * arm
            r = 0.022 * n
            px, py = -uy, ux
            d.polygon([((tx + ux * r * 1.8) * k, (ty + uy * r * 1.8) * k), ((tx + px * r) * k, (ty + py * r) * k),
                       ((tx - ux * r * 1.2) * k, (ty - uy * r * 1.2) * k), ((tx - px * r) * k, (ty - py * r) * k)], fill=255)
        # hexagonal plate in the middle
        for rr, w in ((plate, 3.6), (plate * 0.55, 2.4)) if ornate else ((plate * 0.7, 3.0),):
            pts = [(c + rr * math.cos(math.radians(60 * i - 90)), c + rr * math.sin(math.radians(60 * i - 90))) for i in range(7)]
            for p, q in zip(pts, pts[1:]):
                seg(p, q, w * n / 1024)

    return supersample(draw, n, n, 3)


def hexagon(n):
    def draw(d, k):
        c = n / 2
        for rr, w in ((0.47 * n, 5), (0.43 * n, 2)):
            pts = [((c + rr * math.cos(math.radians(60 * i - 90))) * k, (c + rr * math.sin(math.radians(60 * i - 90))) * k) for i in range(7)]
            d.line(pts, fill=255, width=int(w * k * n / 512), joint="curve")
    return supersample(draw, n, n, 3)


def petal(W, H):
    """a lotus petal, tip up: soft body, bright rim, a faint vein; the base fades out"""
    x, y = grid(W, H)
    t = (y + 1) / 2  # 0 base .. 1 tip
    half = 0.92 * np.sin(np.pi * np.clip(t, 0, 1) ** 0.72) ** 0.9 * (1 - 0.18 * t)
    half = np.where(t > 0.97, half * np.clip((1 - t) / 0.03, 0, 1), half)
    d = half - np.abs(x)  # > 0 inside
    inside = np.clip(d / 0.02, 0, 1)
    rim = np.exp(-(np.clip(d, 0, None) / 0.07) ** 2)
    vein = np.exp(-(x / 0.035) ** 2) * np.clip(t * 1.4, 0, 1) * 0.35
    body = 0.34 + 0.30 * t
    a = inside * np.clip(body + 0.62 * rim + vein, 0, 1) * np.clip(t / 0.22, 0, 1) ** 1.2
    return alpha_img(a)


def heart(n, outline=False):
    """a heart that fits its tile with a margin (exact distance field, after iq): tip down, lobes up"""
    x, y = grid(n)
    k = 1.5  # tile units per heart unit; the heart spans x +-0.604, y 0..1.104 in its own units
    px, py = np.abs(x) / k, (y + 0.83) / k

    def dot2(ax, ay):
        return ax * ax + ay * ay
    far = px + py > 1.0
    d_far = np.sqrt(dot2(px - 0.25, py - 0.75)) - math.sqrt(2) / 4
    m = 0.5 * np.maximum(px + py, 0)
    d_near = np.sqrt(np.minimum(dot2(px, py - 1.0), dot2(px - m, py - m))) * np.sign(px - py)
    d = np.where(far, d_far, d_near) * k  # signed distance in tile units, < 0 inside
    if outline:
        a = np.exp(-(d / 0.020) ** 2) + 0.42 * np.exp(-(d / 0.05) ** 2)
    else:
        a = np.clip(-d / 0.012, 0, 1) * (0.80 + 0.20 * np.clip(1 + d / 0.25, 0, 1)) + 0.30 * np.exp(-(np.clip(d, 0, None) / 0.04) ** 2) * (d > 0)
    return alpha_img(a)


def sparkle(n):
    x, y = grid(n)
    r = np.hypot(x, y)
    star = np.exp(-np.abs(x * y) * 260.0) * np.clip(1 - r, 0, 1) ** 1.6
    core = np.exp(-(r / 0.10) ** 2)
    return alpha_img(np.clip(star * 0.95 + core, 0, 1))


def bokeh(n):
    x, y = grid(n)
    r = np.hypot(x, y)
    a = np.clip((0.92 - r) / 0.05, 0, 1) * (0.42 + 0.58 * np.exp(-((r - 0.86) / 0.07) ** 2))
    return alpha_img(a)


def rose(n, seed=5):
    """a rose seen from above: petals spiralling out at the golden angle, drawn as overlapping arcs"""
    R = np.random.default_rng(seed)

    def draw(d, k):
        c = n / 2
        for i in range(26, 0, -1):
            ang = i * 137.5
            rad = 0.021 * n * i ** 0.9
            cx, cy = c + math.cos(math.radians(ang)) * rad * 0.42, c + math.sin(math.radians(ang)) * rad * 0.42
            box = [(cx - rad) * k, (cy - rad) * k, (cx + rad) * k, (cy + rad) * k]
            span = 150 + R.uniform(-20, 25)
            d.arc(box, ang - span / 2, ang + span / 2, fill=255, width=max(1, int((1.6 + i * 0.09) * k * n / 512)))
    return supersample(draw, n, n, 3)


def aurora(W, H, seed):
    """curtains of light: streaks along y, bright lower hem, soft top"""
    R = np.random.default_rng(seed)
    x = np.linspace(0, 1, W, dtype=np.float32)[None, :]
    y = np.linspace(1, 0, H, dtype=np.float32)[:, None]  # 0 bottom .. 1 top
    streak = np.zeros((1, W), np.float32)
    for f in (3, 5, 9, 17, 31, 59):
        streak += np.sin(2 * np.pi * (f * x + R.random())) / f ** 0.7
    streak = (streak - streak.min()) / (streak.max() - streak.min())
    fine = value_noise(W, 8, (160, 2), seed + 1, 2).mean(0, keepdims=True)
    hem = 0.16 + 0.10 * np.sin(2 * np.pi * (2 * x + 0.2)) + 0.05 * np.sin(2 * np.pi * (5 * x + 0.7))
    up = np.clip((y - hem) / 0.035, 0, 1) * np.exp(-np.clip(y - hem, 0, None) / 0.42)
    a = up * (0.25 + 0.75 * streak ** 1.5) * (0.65 + 0.35 * fine)
    a *= np.clip(x / 0.06, 0, 1) * np.clip((1 - x) / 0.06, 0, 1) * np.clip((1 - y) / 0.3, 0, 1)
    return alpha_img(np.clip(a * 1.25, 0, 1))


def rays(n, seed):
    x, y = grid(n)
    r = np.hypot(x, y)
    th = np.arctan2(y, x)
    R = np.random.default_rng(seed)
    a = np.zeros_like(r)
    for f in (6, 12, 18, 30, 54):
        a += np.cos(f * th + R.uniform(0, 6.28)) * R.uniform(0.5, 1.0)
    a = np.clip((a - a.min()) / (a.max() - a.min()), 0, 1) ** 2.2
    a *= np.clip(r / 0.12, 0, 1) * np.clip(1 - r, 0, 1) ** 1.3
    return alpha_img(a)


def soft_dots(W, H, n, rad, alpha, seed, star_every=0):
    """a tileable field of soft round flakes; every star_every-th is a tiny six-armed crystal"""
    R = np.random.default_rng(seed)
    a = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for i in range(n):
        r, al = R.uniform(*rad), R.uniform(*alpha)
        cx, cy = R.uniform(0, W), R.uniform(0, H)
        m = int(r * 4 + 4)
        for ox in (-W, 0, W):
            for oy in (-H, 0, H):
                px, py = cx + ox, cy + oy
                x0, x1, y0, y1 = int(max(0, px - m)), int(min(W, px + m + 1)), int(max(0, py - m)), int(min(H, py + m + 1))
                if x1 <= x0 or y1 <= y0:
                    continue
                dx, dy = xx[y0:y1, x0:x1] - px, yy[y0:y1, x0:x1] - py
                d = np.hypot(dx, dy)
                if star_every and i % star_every == 0:
                    th = np.arctan2(dy, dx)
                    arm = np.abs(np.cos(3 * th)) ** 14
                    v = np.clip(1 - d / (r * 3.2), 0, 1) * arm + np.exp(-(d / (r * 0.7)) ** 2)
                else:
                    v = np.clip(r + 0.5 - d, 0, 1) * 0.7 + 0.6 * np.exp(-(d / (r * 1.6)) ** 2)
                a[y0:y1, x0:x1] = np.maximum(a[y0:y1, x0:x1], np.clip(v, 0, 1) * al)
    return a


def mist(W, H, seed):
    n = value_noise(W, H, (4, 3), seed, 5)
    n = np.clip((n - 0.42) / 0.4, 0, 1) ** 1.4
    x, y = grid(W, H)
    return alpha_img(n * np.clip(1.25 - np.hypot(x * 0.9, y * 1.1), 0, 1))


def vignette(W, H):
    x, y = grid(W, H)
    r = np.hypot(x * 0.82, y * 0.98)
    return alpha_img(np.clip((r - 0.45) / 0.75, 0, 1) ** 1.8)


def crack(W, H, seed):
    """branching fracture lines radiating from the middle (ice under a blow)"""
    R = np.random.default_rng(seed)
    paths = []

    def grow(x, y, ang, length, w, depth):
        pts = [(x, y)]
        n = max(3, int(length / 26))
        for i in range(n):
            ang += R.normal(0, 0.22)
            x += math.cos(ang) * length / n
            y += math.sin(ang) * length / n
            pts.append((x, y))
            if depth < 3 and R.random() < 0.20:
                grow(x, y, ang + R.choice((-1, 1)) * R.uniform(0.45, 1.05), length * R.uniform(0.3, 0.55), w * 0.62, depth + 1)
        paths.append((pts, w))

    for i in range(9):
        grow(W / 2, H / 2, i * 2 * math.pi / 9 + R.uniform(-0.2, 0.2), R.uniform(0.34, 0.5) * W, 4.2, 0)

    def draw(d, k):
        for pts, w in paths:
            d.line([(x * k, y * k) for x, y in pts], fill=255, width=max(1, int(w * k)), joint="curve")
    core = supersample(draw, W, H, 2)
    return alpha_img(with_glow(core, 7, 0.55))


# ------------------------------------------------------------------ lettering
def render_text(font_path, size, text, spacing):
    f = ImageFont.truetype(font_path, size)
    widths = []
    for ch in text:
        widths.append(size * 0.32 if ch == " " else f.getlength(ch))
    gap = size * spacing
    W = int(sum(widths) + gap * (len(text) - 1) + size * 1.6)
    H = int(size * 2.4)
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    if spacing == 0.0:
        d.text((size * 0.8, size * 0.6), text, font=f, fill=255)  # keep the font's own kerning / joins
    else:
        x = size * 0.8
        for ch, w in zip(text, widths):
            if ch != " ":
                d.text((x, size * 0.6), ch, font=f, fill=255)
            x += w + gap
    bbox = im.getbbox()
    pad = max(12, size // 12)
    return im.crop((max(0, bbox[0] - pad), max(0, bbox[1] - pad), min(W, bbox[2] + pad), min(H, bbox[3] + pad)))


def render_texts(fonts):
    os.makedirs(DATA, exist_ok=True)
    for name, (font, size, text, sp, _g) in TEXTS.items():
        im = render_text(os.path.join(fonts, font), size, text, sp)
        save_l(im, DATA, name)


# ------------------------------------------------------------------ cover art
def cover_textures(out, cover):
    """cover_sq.png: the jacket with rounded corners; cover_wide.png: a 16:9 cut whose edges melt away"""
    if cover:
        im = Image.open(cover).convert("RGB")
    else:  # placeholder: a quiet snowy gradient
        g = value_noise(1080, 1080, (3, 3), 77, 4)
        top, bot = np.array([188, 204, 236], np.float32), np.array([226, 234, 250], np.float32)
        t = np.linspace(0, 1, 1080, dtype=np.float32)[:, None, None]
        arr = top * (1 - t) + bot * t + (g[..., None] - 0.5) * 40
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    side = min(im.size)
    sq = im.crop(((im.width - side) // 2, (im.height - side) // 2, (im.width + side) // 2, (im.height + side) // 2))
    sq = sq.resize((900, 900), Image.LANCZOS)
    mask = Image.new("L", (900 * 3, 900 * 3), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 900 * 3 - 1, 900 * 3 - 1), radius=26 * 3, fill=255)
    sq.putalpha(mask.resize((900, 900), Image.LANCZOS))
    sq.save(os.path.join(out, "cover_sq.png"), optimize=True)
    # 16:9 band of the square (the face and the lettering sit in the upper two thirds)
    w = sq.width
    h = round(w * 9 / 16)
    y0 = round(w * 0.085)
    wide = sq.convert("RGB").crop((0, y0, w, y0 + h)).resize((1280, 720), Image.LANCZOS)
    x, y = grid(1280, 720)
    edge = np.clip((1 - np.abs(x)) / 0.16, 0, 1) * np.clip((1 - np.abs(y)) / 0.22, 0, 1)
    edge = edge * edge * (3 - 2 * edge)
    wide.putalpha(Image.fromarray((edge * 255).astype(np.uint8), "L"))
    wide.save(os.path.join(out, "cover_wide.png"), optimize=True)


def illustration(out, cover):
    if cover:
        im = Image.open(cover).convert("RGB")
        if im.width > 1920:
            im = im.resize((1920, round(im.height * 1920 / im.width)), Image.LANCZOS)
        im.save(os.path.join(out, "illustration.jpg"), quality=93)
    else:
        g = value_noise(1280, 720, (4, 3), 78, 4)
        top, bot = np.array([150, 170, 214], np.float32), np.array([214, 224, 246], np.float32)
        t = np.linspace(0, 1, 720, dtype=np.float32)[:, None, None]
        arr = top * (1 - t) + bot * t + (g[..., None] - 0.5) * 46
        Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").save(os.path.join(out, "illustration.jpg"), quality=90)


# ------------------------------------------------------------------ everything
SIZES = {}


def make(out, cover=None, fonts=None):
    os.makedirs(out, exist_ok=True)
    save(np.ones((64, 64, 4), np.float32), out, "white.png")
    x, y = grid(256)
    r = np.hypot(x, y)
    save(alpha_img(np.exp(-(r / 0.42) ** 2) * (r < 1)), out, "glow.png")
    save(alpha_img(np.clip((1 - r) / 0.02, 0, 1)), out, "disc.png")
    x, y = grid(512)
    r = np.hypot(x, y)
    save(alpha_img(np.clip(1 - np.abs(r - 0.94) / 0.012, 0, 1) + 0.45 * np.exp(-((r - 0.94) / 0.035) ** 2)), out, "ring.png")
    yy = np.linspace(-1, 1, 64)[:, None]
    xx = np.linspace(-1, 1, 1024)[None, :]
    save(alpha_img(np.exp(-(yy / 0.3) ** 2) * np.clip((1 - np.abs(xx)) / 0.12, 0, 1)), out, "beam.png")
    save(alpha_img(np.linspace(0, 1, 512)[:, None] ** 1.7 * np.ones((1, 64))), out, "grad.png")
    t = np.clip(np.linspace(0, 1, 512)[:, None] / 0.6, 0, 1)
    save(alpha_img(t * t * (3 - 2 * t) * np.ones((1, 64))), out, "band.png")  # lower third: clear top, solid bottom
    h, w = 1024, 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    save(alpha_img(np.clip((yy / (h - 1)) * (w / 2) - np.abs(xx - (w - 1) / 2) + 0.5, 0, 1)), out, "spike.png")
    # snow crystals
    save(alpha_img(with_glow(snowflake(1024, 3, 4, True), 9, 0.7)), out, "flake_a.png")
    save(alpha_img(with_glow(snowflake(1024, 11, 3, True, 1.25), 9, 0.7)), out, "flake_b.png")
    save(alpha_img(with_glow(snowflake(256, 7, 2, False, 1.7), 3, 0.6)), out, "flake_s.png")
    save(alpha_img(with_glow(hexagon(512), 6, 0.6)), out, "hex.png")
    # flowers and hearts
    save(petal(256, 512), out, "petal.png")
    save(alpha_img(with_glow(rose(512), 4, 0.55)), out, "rose.png")
    save(heart(512), out, "heart.png")
    save(heart(512, True), out, "heart_o.png")
    save(sparkle(256), out, "spark.png")
    save(bokeh(256), out, "bokeh.png")
    # weather and light
    save(alpha_img(soft_dots(1024, 1024, 150, (1.4, 3.6), (0.45, 1.0), 21)), out, "snow_a.png")
    save(alpha_img(soft_dots(1024, 1024, 46, (3.5, 8.0), (0.35, 0.9), 22, star_every=3)), out, "snow_b.png")
    save(alpha_img(soft_dots(2048, 1152, 420, (0.5, 1.5), (0.3, 1.0), 23)), out, "stars.png")
    save(aurora(1024, 512, 31), out, "aurora.png")
    save(rays(1024, 32), out, "rays.png")
    save(mist(1024, 576, 33), out, "mist.png")
    save(vignette(512, 288), out, "vig.png")
    save(crack(1024, 576, 34), out, "crack.png")
    # lettering (pre-rendered)
    if fonts:
        render_texts(fonts)
    for name in TEXTS:
        shutil.copy(os.path.join(DATA, name), os.path.join(out, name))
    cover_textures(out, cover)
    illustration(out, cover)


def sizes(out):
    return {n: Image.open(os.path.join(out, n)).size for n in sorted(os.listdir(out)) if n.endswith(".png")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--cover")
    ap.add_argument("--fonts")
    a = ap.parse_args()
    make(a.out, a.cover, a.fonts)
    for n, s in sizes(a.out).items():
        print(f"{n:16s} {s[0]}x{s[1]}  {os.path.getsize(os.path.join(a.out, n)) / 1024:7.1f} KB")
