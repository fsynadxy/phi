"""Procedural illustration + white line textures (tinted in-chart via color events)."""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = sys.argv[1] if __name__ == "__main__" and len(sys.argv) > 1 else os.environ.get("ASSET_OUT", ".")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20261108)


def save_rgba(arr, name):
    Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8), "RGBA").save(os.path.join(OUT, name), optimize=True)


def radial(n, f):
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(x - (n - 1) / 2, y - (n - 1) / 2) / (n / 2)
    a = f(r)
    out = np.ones((n, n, 4), np.float32)
    out[..., 3] = np.clip(a, 0, 1)
    return out


# soft glow orb
save_rgba(radial(256, lambda r: np.exp(-(r / 0.42) ** 2) * (r < 1)), "glow.png")
# thin ring with glow
save_rgba(radial(512, lambda r: np.clip(1 - np.abs(r - 0.94) / 0.012, 0, 1) + 0.45 * np.exp(-((r - 0.94) / 0.035) ** 2)), "ring.png")
# solid white block
save_rgba(np.ones((64, 64, 4), np.float32), "white.png")
# horizontal light beam (soft vertical profile, soft ends)
h, w = 64, 1024
yy = np.linspace(-1, 1, h)[:, None]
xx = np.linspace(-1, 1, w)[None, :]
beam = np.exp(-(yy / 0.28) ** 2) * np.clip((1 - np.abs(xx)) / 0.15, 0, 1)
b = np.ones((h, w, 4), np.float32); b[..., 3] = beam
save_rgba(b, "beam.png")
# vertical gradient pillar (opaque bottom -> transparent top)
h, w = 512, 64
g = np.ones((h, w, 4), np.float32)
xx = np.linspace(-1, 1, w)[None, :]
yy = np.linspace(0, 1, h)[:, None]
g[..., 3] = (yy ** 1.6) * np.exp(-(xx / 0.55) ** 2)
save_rgba(g, "pillar.png")
# square frame outline (for diamonds / boxes)
n = 512
f = np.zeros((n, n, 4), np.float32); f[..., :3] = 1
y, x = np.mgrid[0:n, 0:n]
d = np.minimum(np.minimum(x, n - 1 - x), np.minimum(y, n - 1 - y))
f[..., 3] = np.clip(1 - np.abs(d - 10) / 3.0, 0, 1) + 0.35 * np.exp(-((d - 10) / 9.0) ** 2)
save_rgba(f, "frame.png")


# equalizer bar: visible upper half (centre is placed on the screen bottom edge)
h, w = 256, 32
e = np.ones((h, w, 4), np.float32)
rows = np.arange(h)[:, None].astype(np.float32)
cols = np.linspace(-1, 1, w)[None, :]
prof = np.clip((1 - np.abs(cols)) / 0.25, 0, 1)
cap = np.exp(-((rows - 3) / 2.5) ** 2)
body = 0.30 + 0.45 * np.exp(-(rows - 3) / 40.0)
e[..., 3] = np.clip((np.where(rows < 128, body, 0.30) + cap) * prof, 0, 1)
save_rgba(e, "eqbar.png")

# ------------------------------------------------------------------ illustration 1920x1080
W, H = 1920, 1080
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
u, v = x / W, y / H


def blob(cx, cy, rx, ry, col, k=1.0):
    d = ((u - cx) / rx) ** 2 + ((v - cy) / ry) ** 2
    return np.exp(-d)[..., None] * np.array(col, np.float32)[None, None, :] * k


base = np.zeros((H, W, 3), np.float32)
top = np.array([10, 12, 34], np.float32) / 255
bot = np.array([30, 18, 58], np.float32) / 255
base += top * (1 - v[..., None]) + bot * v[..., None]
base += blob(0.18, 0.86, 0.40, 0.35, (0.05, 0.36, 0.48), 0.9)    # teal low-left
base += blob(0.86, 0.12, 0.38, 0.30, (0.42, 0.10, 0.36), 0.85)   # magenta up-right
base += blob(0.62, 0.52, 0.30, 0.30, (0.20, 0.16, 0.42), 0.8)    # violet core
ocx, ocy = 0.62 * W, 0.52 * H
dist = np.hypot(x - ocx, (y - ocy) * 1.0)
base += (np.exp(-(dist / 55) ** 2) * 0.8 + np.exp(-(dist / 190) ** 2) * 0.28)[..., None] * np.array([1.0, 0.86, 0.62])[None, None, :]

img = Image.fromarray(np.clip(base * 255, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
# orbits (tilted ellipses)
tilt = math.radians(-14)
for k, (a, b_, al) in enumerate([(230, 82, 120), (380, 136, 95), (560, 200, 80), (780, 280, 62), (1040, 372, 46)]):
    pts = []
    for i in range(721):
        th = 2 * math.pi * i / 720
        ex, ey = a * math.cos(th), b_ * math.sin(th)
        pts.append((ocx + ex * math.cos(tilt) - ey * math.sin(tilt), ocy + ex * math.sin(tilt) + ey * math.cos(tilt)))
    d.line(pts, fill=(200, 220, 255, al), width=2)
    # a planet on each orbit
    th = [0.4, 2.3, 4.1, 5.5, 1.2][k]
    ex, ey = a * math.cos(th), b_ * math.sin(th)
    px_, py_ = ocx + ex * math.cos(tilt) - ey * math.sin(tilt), ocy + ex * math.sin(tilt) + ey * math.cos(tilt)
    rr = [9, 6, 12, 7, 5][k]
    col = [(255, 210, 140), (130, 230, 255), (255, 120, 190), (200, 170, 255), (170, 255, 220)][k]
    d.ellipse((px_ - rr * 3, py_ - rr * 3, px_ + rr * 3, py_ + rr * 3), fill=col + (40,))
    d.ellipse((px_ - rr, py_ - rr, px_ + rr, py_ + rr), fill=col + (255,))
# stars
for _ in range(900):
    sx, sy = rng.uniform(0, W), rng.uniform(0, H)
    m = rng.uniform(0.3, 1.0) ** 3
    rr = 0.6 + 1.8 * m
    al = int(60 + 195 * m)
    d.ellipse((sx - rr, sy - rr, sx + rr, sy + rr), fill=(235, 240, 255, al))
# constellation
cons = [(260, 210), (350, 160), (470, 205), (545, 140), (640, 190), (720, 120)]
d.line(cons, fill=(190, 215, 255, 110), width=2)
for p in cons:
    d.ellipse((p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4), fill=(240, 245, 255, 255))
cons2 = [(1450, 900), (1560, 860), (1640, 930), (1760, 880)]
d.line(cons2, fill=(190, 215, 255, 90), width=2)
for p in cons2:
    d.ellipse((p[0] - 3, p[1] - 3, p[0] + 3, p[1] + 3), fill=(240, 245, 255, 230))
glow = ov.filter(ImageFilter.GaussianBlur(3))
img = Image.alpha_composite(img, glow)
img = Image.alpha_composite(img, ov)
# grain
arr = np.asarray(img.convert("RGB")).astype(np.float32)
arr += rng.normal(0, 3.0, arr.shape)
Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").save(os.path.join(OUT, "illustration.jpg"), quality=92)
print("assets written to", OUT)
