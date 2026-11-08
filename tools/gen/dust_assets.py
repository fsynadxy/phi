"""Textures for 走过漫漫时空 (遗尘漫步): procedural and white, so the chart tints them.

usage: python tools/gen/dust_assets.py <out_dir> [font_dir]
Text textures are pre-rendered into tools/data/dust/ (Noto Serif SC, Cinzel, Rajdhani; all SIL OFL 1.1);
pass a folder holding NotoSerifSC_900.font, NotoSerifSC_600.font, Cinzel_700.font and Rajdhani_600.font
(Google Fonts subsets) to re-render them.
"""
import math
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "dust")

TEXTS = {  # name: (font, size, text, letter spacing in em)
    "t_title.png": ("NotoSerifSC_900.font", 240, "走过漫漫时空", 0.10),
    "t_event.png": ("NotoSerifSC_600.font", 120, "遗尘漫步", 0.30),
    "t_walk.png": ("Cinzel_700.font", 96, "A WALK IN THE DUST", 0.22),
    "t_ch1.png": ("NotoSerifSC_600.font", 150, "漫漫独行", 0.35),
    "t_ch2.png": ("NotoSerifSC_600.font", 150, "浩瀚之旅", 0.35),
    "t_sargon.png": ("Rajdhani_600.font", 72, "SARGON", 0.40),
    "t_ursus.png": ("Rajdhani_600.font", 72, "URSUS / CHERNOBOG", 0.30),
    "t_victoria.png": ("Rajdhani_600.font", 72, "VICTORIA", 0.40),
    "t_terra.png": ("Rajdhani_600.font", 72, "TERRA", 0.40),
}


def save(arr, out, name):
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(out, name), optimize=True)


def alpha_img(a):
    out = np.ones(a.shape + (4,), np.float32)
    out[..., 3] = np.clip(a, 0, 1)
    return out


def save_l(im, out, name):
    save(alpha_img(np.asarray(im).astype(np.float32) / 255), out, name)


def radial(n):
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    return np.hypot(x - (n - 1) / 2, y - (n - 1) / 2) / (n / 2)


def soft_dots(W, H, n, rad, alpha, seed, extra=()):
    """a field of soft round dots (dust, snow)"""
    R = np.random.default_rng(seed)
    a = np.zeros((H, W), np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    specs = [(R.uniform(*rad), R.uniform(*alpha)) for _ in range(n)] + list(extra)
    for r, al in specs:
        cx, cy = R.uniform(0, W), R.uniform(0, H)
        m = int(r * 4 + 3)
        x0, x1, y0, y1 = int(max(0, cx - m)), int(min(W, cx + m + 1)), int(max(0, cy - m)), int(min(H, cy + m + 1))
        if x1 <= x0 or y1 <= y0:
            continue
        d = np.hypot(xx[y0:y1, x0:x1] - cx, yy[y0:y1, x0:x1] - cy)
        v = np.clip(r + 0.5 - d, 0, 1) * 0.7 + 0.6 * np.exp(-(d / (r * 1.6)) ** 2)
        a[y0:y1, x0:x1] = np.maximum(a[y0:y1, x0:x1], np.clip(v, 0, 1) * al)
    return a


def supersample(draw_fn, W, H, k=3):
    im = Image.new("L", (W * k, H * k), 0)
    draw_fn(ImageDraw.Draw(im), k)
    return im.resize((W, H), Image.LANCZOS)


def bolt(W, H, seed):
    """a horizontal lightning bolt with branches: bright core + soft glow"""
    R = np.random.default_rng(seed)

    def path(x0, y0, x1, y1, n, jag):
        pts = [(x0, y0)]
        for i in range(1, n):
            t = i / n
            pts.append((x0 + (x1 - x0) * t + R.uniform(-0.3, 0.3) * (x1 - x0) / n, y0 + (y1 - y0) * t + R.normal(0, jag)))
        pts.append((x1, y1))
        return pts

    main = path(0.01 * W, H / 2, 0.99 * W, H / 2 + R.uniform(-0.1, 0.1) * H, 22, 0.09 * H)
    branches = []
    for _ in range(5):
        i = R.integers(3, len(main) - 4)
        x0, y0 = main[i]
        L = R.uniform(0.12, 0.3) * W
        ang = R.uniform(-0.7, 0.7)
        branches.append(path(x0, y0, x0 + L * math.cos(ang), y0 + L * math.sin(ang) * 0.6, 8, 0.05 * H))

    def draw(d, k):
        for pts, w in [(main, 7)] + [(b, 3) for b in branches]:
            d.line([(x * k, y * k) for x, y in pts], fill=255, width=int(w * k), joint="curve")
    core = supersample(draw, W, H)
    glow = core.filter(ImageFilter.GaussianBlur(10))
    a = np.maximum(np.asarray(core).astype(np.float32) / 255, np.asarray(glow).astype(np.float32) / 255 * 1.6)
    return alpha_img(np.clip(a, 0, 1))


def dunes(W, H, seed, layers):
    """layered dunes: each layer's crest is a normalised sum of skewed sines (gentle windward, steep lee)"""
    R = np.random.default_rng(seed)
    x = np.arange(W, dtype=np.float32)
    a = np.zeros((H, W), np.float32)
    yy = np.arange(H, dtype=np.float32)[:, None]
    for base, amp, shade in layers:
        prof = np.zeros(W, np.float32)
        wsum = 0.0
        for _ in range(4):
            per = R.uniform(0.3, 0.8) * W
            th = 2 * math.pi * x / per + R.uniform(0, 2 * math.pi)
            w = R.uniform(0.4, 1.0)
            prof += w * (0.5 + 0.5 * np.sin(th + 0.6 * np.sin(th)))
            wsum += w
        top = base - amp * prof / wsum
        a = np.maximum(a, np.clip((yy - top[None, :]) / 1.5, 0, 1) * shade)
    return alpha_img(a)


def make(out, fonts=None):
    os.makedirs(out, exist_ok=True)
    save(np.ones((64, 64, 4), np.float32), out, "white.png")
    r = radial(256)
    save(alpha_img(np.exp(-(r / 0.42) ** 2) * (r < 1)), out, "glow.png")
    save(alpha_img(np.clip((1 - r) / 0.02, 0, 1)), out, "disc.png")
    r = radial(512)
    save(alpha_img(np.clip(1 - np.abs(r - 0.94) / 0.012, 0, 1) + 0.45 * np.exp(-((r - 0.94) / 0.035) ** 2)), out, "ring.png")
    yy = np.linspace(-1, 1, 64)[:, None]
    xx = np.linspace(-1, 1, 1024)[None, :]
    save(alpha_img(np.exp(-(yy / 0.3) ** 2) * np.clip((1 - np.abs(xx)) / 0.12, 0, 1)), out, "beam.png")
    save(alpha_img(np.linspace(0, 1, 512)[:, None] ** 1.7 * np.ones((1, 64))), out, "grad.png")
    h, w = 1024, 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    save(alpha_img(np.clip((yy / (h - 1)) * (w / 2) - np.abs(xx - (w - 1) / 2) + 0.5, 0, 1)), out, "spike.png")
    # radial streaks (time vortex)
    n = 1024
    R = np.random.default_rng(3)
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    ang = np.arctan2(yy - (n - 1) / 2, xx - (n - 1) / 2)
    rad = np.hypot(xx - (n - 1) / 2, yy - (n - 1) / 2) / (n / 2)
    a = np.zeros((n, n), np.float32)
    for _ in range(140):
        th, inner, width = R.uniform(-math.pi, math.pi), R.uniform(0.3, 0.7), R.uniform(0.002, 0.008)
        d = np.abs((ang - th + math.pi) % (2 * math.pi) - math.pi)
        a = np.maximum(a, np.clip(1 - d / (width * np.clip((rad - inner) / (1.45 - inner), 0, 1) + 1e-6), 0, 1) * (rad > inner) * R.uniform(0.5, 1))
    save(alpha_img(a * np.clip((1.45 - rad) / 0.1, 0, 1)), out, "focus.png")
    # dust, snow, rain
    save(alpha_img(soft_dots(2048, 1152, 700, (0.5, 2.0), (0.25, 1.0), 5, extra=[(np.random.default_rng(6).uniform(4, 10), 0.18) for _ in range(40)])), out, "dust.png")
    save(alpha_img(soft_dots(1024, 1024, 170, (1.5, 4.5), (0.5, 1.0), 7)), out, "snow.png")
    im = Image.new("L", (1024, 1024), 0)
    d = ImageDraw.Draw(im)
    R = np.random.default_rng(8)
    for _ in range(160):
        x, y, L = R.uniform(0, 1024), R.uniform(-100, 1024), R.uniform(40, 170)
        d.line([(x, y), (x - L * 0.12, y + L)], fill=int(R.uniform(90, 255)), width=int(R.integers(1, 3)))
    save_l(im, out, "rain.png")
    # landscapes (opaque below the skyline)
    save(dunes(2048, 512, 11, [(300, 180, 0.55), (380, 140, 0.8), (450, 90, 1.0)]), out, "dunes.png")

    def ruins_draw(d, k):
        R = np.random.default_rng(12)
        H = 512
        x = 0
        while x < 2048:
            kind = R.choice(["col", "col", "arch", "zig", "block", "obelisk", "gap"])
            if kind == "col":
                w, h = R.uniform(26, 44), R.uniform(160, 380)
                broken = R.random() < 0.5
                top = H - h
                d.rectangle(((x) * k, top * k, (x + w) * k, H * k), fill=255)
                if not broken:
                    d.rectangle(((x - 10) * k, (top - 18) * k, (x + w + 10) * k, top * k), fill=255)
                else:
                    d.polygon([(x * k, top * k), ((x + w) * k, (top + R.uniform(10, 40)) * k), ((x + w) * k, top * k + 40 * k), (x * k, top * k + 40 * k)], fill=255)
                x += w + R.uniform(30, 90)
            elif kind == "arch":
                w, h = R.uniform(150, 240), R.uniform(220, 330)
                top = H - h
                d.rectangle((x * k, top * k, (x + w) * k, H * k), fill=255)
                ow = w * 0.55
                ox = x + (w - ow) / 2
                d.rectangle((ox * k, (top + ow / 2 + 30) * k, (ox + ow) * k, H * k), fill=0)
                d.ellipse((ox * k, (top + 30) * k, (ox + ow) * k, (top + 30 + ow) * k), fill=0)
                x += w + R.uniform(20, 80)
            elif kind == "zig":
                w = R.uniform(260, 380)
                steps = int(R.integers(4, 6))
                for s in range(steps):
                    sw = w * (1 - s / steps)
                    sh = 60
                    d.rectangle(((x + (w - sw) / 2) * k, (H - (s + 1) * sh) * k, (x + (w + sw) / 2) * k, (H - s * sh) * k), fill=255)
                x += w + R.uniform(30, 90)
            elif kind == "block":
                w, h = R.uniform(60, 140), R.uniform(30, 90)
                d.polygon([(x * k, H * k), (x * k, (H - h) * k), ((x + w) * k, (H - h * R.uniform(0.6, 1.2)) * k), ((x + w) * k, H * k)], fill=255)
                x += w + R.uniform(10, 50)
            elif kind == "obelisk":
                w, h = R.uniform(30, 46), R.uniform(300, 430)
                d.polygon([(x * k, H * k), ((x + w * 0.15) * k, (H - h) * k), ((x + w * 0.5) * k, (H - h - 30) * k), ((x + w * 0.85) * k, (H - h) * k), ((x + w) * k, H * k)], fill=255)
                x += w + R.uniform(40, 100)
            else:
                x += R.uniform(40, 160)
        d.rectangle((0, (H - 24) * k, 2048 * k, H * k), fill=255)
    save_l(supersample(ruins_draw, 2048, 512, 2), out, "ruins.png")

    def ark_draw(d, k):  # an excavated ark: a long, tapered hull with towers (abstract)
        H = 512
        hull = [(60, 470), (220, 360), (520, 320), (1500, 300), (1800, 250), (1990, 260), (2000, 300), (1880, 360), (1650, 420), (1200, 470)]
        d.polygon([(x * k, y * k) for x, y in hull], fill=255)
        for x0, w, h in ((700, 90, 120), (820, 60, 190), (900, 140, 80), (1150, 70, 160), (1300, 110, 100), (1550, 50, 130)):
            d.rectangle((x0 * k, (310 - h) * k, (x0 + w) * k, 330 * k), fill=255)
        d.rectangle((0, 470 * k, 2048 * k, H * k), fill=255)
    save_l(supersample(ark_draw, 2048, 512, 2), out, "ark.png")
    for name, seed in (("bolt_a.png", 21), ("bolt_b.png", 22), ("bolt_c.png", 23)):
        save(bolt(1024, 256, seed), out, name)

    def star_draw(d, k):  # Sargon geometric emblem: interlaced eight-pointed stars in rings
        c = 512
        for rr, wid in ((470, 5), (440, 2), (300, 4), (160, 4)):
            d.ellipse(((c - rr) * k, (c - rr) * k, (c + rr) * k, (c + rr) * k), outline=255, width=int(wid * k))
        for rr, wid in ((420, 6), (280, 5), (140, 4)):
            for rot in (0, 45):
                pts = [(c + rr * math.cos(math.radians(rot + 45 + 90 * i)), c + rr * math.sin(math.radians(rot + 45 + 90 * i))) for i in range(4)]
                d.polygon([(x * k, y * k) for x, y in pts], outline=255, width=int(wid * k))
        for i in range(16):
            a = math.radians(i * 22.5)
            d.line([((c + 300 * math.cos(a)) * k, (c + 300 * math.sin(a)) * k), ((c + 440 * math.cos(a)) * k, (c + 440 * math.sin(a)) * k)], fill=255, width=int(2 * k))
        for i in range(8):
            a = math.radians(i * 45 + 22.5)
            x, y = c + 455 * math.cos(a), c + 455 * math.sin(a)
            d.ellipse(((x - 9) * k, (y - 9) * k, (x + 9) * k, (y + 9) * k), fill=255)
    save_l(supersample(star_draw, 1024, 1024, 2), out, "star8.png")

    def arch_draw(d, k):  # gothic lancet window with tracery
        W, H = 512, 1024
        lw = 10
        d.rectangle((40 * k, 400 * k, 472 * k, 1000 * k), outline=255, width=lw * k)
        d.arc((40 * k, 40 * k, 760 * k, 760 * k), 180, 240, fill=255, width=lw * k)
        d.arc((-248 * k, 40 * k, 472 * k, 760 * k), 300, 360, fill=255, width=lw * k)
        d.line((256 * k, 400 * k, 256 * k, 1000 * k), fill=255, width=7 * k)
        for x0 in (40, 256):
            d.arc((x0 * k, 330 * k, (x0 + 216) * k, 546 * k), 180, 360, fill=255, width=6 * k)
        d.ellipse((176 * k, 230 * k, 336 * k, 390 * k), outline=255, width=7 * k)
        for j in range(4):
            y = 520 + j * 120
            d.line((40 * k, y * k, 472 * k, y * k), fill=255, width=4 * k)
    save_l(supersample(arch_draw, 512, 1024, 2), out, "arch.png")

    def foot_draw(d, k):
        d.ellipse((24 * k, 10 * k, 104 * k, 150 * k), fill=255)
        d.ellipse((34 * k, 168 * k, 96 * k, 246 * k), fill=255)
    save_l(supersample(foot_draw, 128, 256, 3), out, "footprint.png")

    def corner_draw(d, k):  # a HUD corner bracket
        d.line((8 * k, 8 * k, 8 * k, 120 * k), fill=255, width=6 * k)
        d.line((8 * k, 8 * k, 120 * k, 8 * k), fill=255, width=6 * k)
        d.rectangle((20 * k, 20 * k, 34 * k, 34 * k), fill=255)
    save_l(supersample(corner_draw, 128, 128, 3), out, "corner.png")

    # clock face with roman numerals (Cinzel, pre-rendered with the texts)
    os.makedirs(DATA, exist_ok=True)
    if fonts:
        render_texts(fonts)
    for name in list(TEXTS) + ["clock.png"]:
        shutil.copy(os.path.join(DATA, name), os.path.join(out, name))


def render_text(font_path, size, text, spacing):
    f = ImageFont.truetype(font_path, size)
    widths = [f.getbbox(ch)[2] - f.getbbox(ch)[0] if ch != " " else size * 0.3 for ch in text]
    gap = size * spacing
    W = int(sum(widths) + gap * (len(text) - 1) + size)
    H = int(size * 1.6)
    im = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(im)
    x = size / 2
    for ch, w in zip(text, widths):
        if ch != " ":
            bb = f.getbbox(ch)
            d.text((x - bb[0], size * 0.3), ch, font=f, fill=255)
        x += w + gap
    bbox = im.getbbox()
    im = im.crop((max(0, bbox[0] - 24), max(0, bbox[1] - 24), min(W, bbox[2] + 24), min(H, bbox[3] + 24)))
    return im


def render_texts(fonts):
    for name, (font, size, text, sp) in TEXTS.items():
        save_l(render_text(os.path.join(fonts, font), size, text, sp), DATA, name)
    # clock face
    n = 1024
    f = ImageFont.truetype(os.path.join(fonts, "Cinzel_700.font"), 70)

    def clock_draw(d, k):
        c = n / 2
        d.ellipse((12 * k, 12 * k, (n - 12) * k, (n - 12) * k), outline=255, width=8 * k)
        d.ellipse((40 * k, 40 * k, (n - 40) * k, (n - 40) * k), outline=255, width=3 * k)
        for i in range(60):
            a = math.radians(i * 6 - 90)
            r0 = 420 if i % 5 == 0 else 448
            w = 7 if i % 5 == 0 else 3
            d.line(((c + r0 * math.cos(a)) * k, (c + r0 * math.sin(a)) * k, (c + 470 * math.cos(a)) * k, (c + 470 * math.sin(a)) * k), fill=255, width=w * k)
    im = supersample(clock_draw, n, n, 2)
    d = ImageDraw.Draw(im)
    for i, rn in enumerate(["XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI"]):
        a = math.radians(i * 30 - 90)
        x, y = n / 2 + 345 * math.cos(a), n / 2 + 345 * math.sin(a)
        bb = f.getbbox(rn)
        d.text((x - (bb[0] + bb[2]) / 2, y - (bb[1] + bb[3]) / 2), rn, font=f, fill=255)
    save_l(im, DATA, "clock.png")


if __name__ == "__main__":
    make(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print("dust assets ->", sys.argv[1])
