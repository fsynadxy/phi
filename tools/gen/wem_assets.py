"""Textures for world.execute(me); (all procedural, except the cover pieces which come from the user's cover).

Pixel art is drawn on a small grid and enlarged with nearest-neighbour, so it stays crisp in Phira
(textures are sampled linearly). White textures are tinted in the chart with colour events; the coloured
ones (wings, icons, windows, the cover ring) are drawn with white tint.

save_all(out, cover=None) writes every texture into the package folder `out`. With a cover image the
illustration, the full-screen cover texture and its 6x4 tiles are cut from it; without one (the public
repository has no cover) a procedural stand-in is drawn.
"""
import math
import os
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "wem")
RNG = np.random.default_rng(20161205)

TILE_COLS, TILE_ROWS = 6, 4
COVER_W, COVER_H = 1350, 760  # full-screen texture size at scale 1 (16:9)


def save(im, out, name):
    im.save(os.path.join(out, name), optimize=True)
    return im.size


# ------------------------------------------------------------------ pixel art helpers
def pixel(rows, pal, k):
    h, w = len(rows), max(len(r) for r in rows)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in pal:
                px[x, y] = pal[ch]
    return im.resize((w * k, h * k), Image.NEAREST)


def outline(mask, col=(16, 20, 32, 255)):
    """1-pixel dark outline around an RGBA pixel image (before upscaling)."""
    a = np.array(mask)
    al = a[..., 3] > 0
    grow = al.copy()
    grow[1:] |= al[:-1]
    grow[:-1] |= al[1:]
    grow[:, 1:] |= al[:, :-1]
    grow[:, :-1] |= al[:, 1:]
    edge = grow & ~al
    a[edge] = col
    return Image.fromarray(a, "RGBA")


CURSOR = [
    "X...........",
    "XX..........",
    "XWX.........",
    "XWWX........",
    "XWWWX.......",
    "XWWWWX......",
    "XWWWWWX.....",
    "XWWWWWWX....",
    "XWWWWWWWX...",
    "XWWWWWWWWX..",
    "XWWWWWWWWWX.",
    "XWWWWWWXXXXX",
    "XWWWXWWX....",
    "XWWX.XWWX...",
    "XWX..XWWX...",
    "XX....XWWX..",
    "X.....XWWX..",
    ".......XWWX.",
    ".......XXX..",
]
POWER = [
    "................",
    ".......WW.......",
    ".......WW.......",
    "...WW..WW..WW...",
    "..WW...WW...WW..",
    ".WW....WW....WW.",
    ".WW....WW....WW.",
    "WW.....WW.....WW",
    "WW............WW",
    "WW............WW",
    ".WW..........WW.",
    ".WW..........WW.",
    "..WW........WW..",
    "...WWW....WWW...",
    ".....WWWWWW.....",
    "................",
]
HEART = [
    "..XXX...XXX..",
    ".XHHXX.XXXXX.",
    "XHHXXXXXXXXXX",
    "XHXXXXXXXXXXX",
    "XXXXXXXXXXXXX",
    ".XXXXXXXXXXX.",
    "..XXXXXXXXX..",
    "...XXXXXXX...",
    "....XXXXX....",
    ".....XXX.....",
    "......X......",
]
HOURGLASS = [
    "XXXXXXXXXXX",
    ".X.......X.",
    ".X.......X.",
    "..X.RRR.X..",
    "...X.R.X...",
    "....XRX....",
    "....XRX....",
    "...X.R.X...",
    "..X..R..X..",
    ".X..RRR..X.",
    ".X.RRRRR.X.",
    "XXXXXXXXXXX",
]
FACE_BASE = [
    ".....XXXXXX.....",
    "...XXYYYYYYXX...",
    "..XYYYYYYYYYYX..",
    ".XYYYYYYYYYYYYX.",
    ".XYYYYYYYYYYYYX.",
    "XYYYYYYYYYYYYYYX",
    "XYYYYYYYYYYYYYYX",
    "XYYYYYYYYYYYYYYX",
    "XYYYYYYYYYYYYYYX",
    "XYYYYYYYYYYYYYYX",
    "XYYYYYYYYYYYYYYX",
    ".XYYYYYYYYYYYYX.",
    ".XYYYYYYYYYYYYX.",
    "..XYYYYYYYYYYX..",
    "...XXYYYYYYXX...",
    ".....XXXXXX.....",
]
FACES = {  # (row, col, char) overlays on FACE_BASE
    "smile": [(5, 4, "X"), (5, 5, "X"), (5, 10, "X"), (5, 11, "X"), (6, 4, "X"), (6, 5, "X"), (6, 10, "X"), (6, 11, "X"),
              (9, 3, "X"), (10, 4, "X"), (11, 5, "X"), (11, 6, "X"), (11, 7, "X"), (11, 8, "X"), (11, 9, "X"), (11, 10, "X"),
              (10, 11, "X"), (9, 12, "X")],
    "laugh": [(5, 3, "X"), (4, 4, "X"), (5, 5, "X"), (5, 10, "X"), (4, 11, "X"), (5, 12, "X"),
              (8, 3, "X"), (8, 4, "X"), (8, 5, "X"), (8, 6, "X"), (8, 7, "X"), (8, 8, "X"), (8, 9, "X"), (8, 10, "X"), (8, 11, "X"), (8, 12, "X"),
              (9, 4, "R"), (9, 5, "R"), (9, 6, "R"), (9, 7, "R"), (9, 8, "R"), (9, 9, "R"), (9, 10, "R"), (9, 11, "R"),
              (10, 5, "R"), (10, 6, "R"), (10, 7, "P"), (10, 8, "P"), (10, 9, "R"), (10, 10, "R"), (11, 6, "X"), (11, 7, "X"), (11, 8, "X"), (11, 9, "X"),
              (9, 3, "X"), (9, 12, "X"), (10, 4, "X"), (10, 11, "X")],
    "angry": [(4, 3, "X"), (5, 4, "X"), (5, 5, "X"), (4, 12, "X"), (5, 11, "X"), (5, 10, "X"), (6, 5, "X"), (6, 10, "X"),
              (11, 5, "X"), (10, 6, "X"), (10, 7, "X"), (10, 8, "X"), (10, 9, "X"), (11, 10, "X")],
    "dizzy": [(4, 3, "X"), (6, 3, "X"), (5, 4, "X"), (4, 5, "X"), (6, 5, "X"), (4, 10, "X"), (6, 10, "X"), (5, 11, "X"), (4, 12, "X"), (6, 12, "X"),
              (10, 6, "X"), (9, 7, "X"), (10, 8, "X"), (9, 9, "X"), (10, 10, "X")],
}
EGGPLANT = [
    "..........GG....",
    ".........GGG....",
    "......GGGGGGG...",
    ".....GGGGGGGGG..",
    "....XPPGGGGGXX..",
    "...XPPPPPPPPPX..",
    "..XPPHPPPPPPPX..",
    "..XPHPPPPPPPPX..",
    ".XPPHPPPPPPPX...",
    ".XPPPPPPPPPPX...",
    "XPPPPPPPPPPX....",
    "XPPPPPPPPPX.....",
    "XPPPPPPPPX......",
    ".XPPPPPXX.......",
    "..XXXXX.........",
]
TOMATO = [
    "......G..G......",
    "....XGGGGGGX....",
    "...XRGGGGGGRX...",
    "..XRRRRGGRRRRX..",
    ".XRRHRRRRRRRRRX.",
    ".XRHHRRRRRRRRRX.",
    "XRRHRRRRRRRRRRRX",
    "XRRRRRRRRRRRRRRX",
    "XRRRRRRRRRRRRRRX",
    "XRRRRRRRRRRRRRRX",
    ".XRRRRRRRRRRRRX.",
    ".XRRRRRRRRRRRRX.",
    "..XRRRRRRRRRRX..",
    "...XXRRRRRRXX...",
    ".....XXXXXX.....",
]
CAT = [
    ".X............X.",
    "XOX..........XOX",
    "XOOX........XOOX",
    "XOPOXXXXXXXXOPOX",
    "XOOOOODOODOOOOOX",
    "XOOOOODOODOOOOOX",
    "XOOOOOOOOOOOOOOX",
    "XOOGGOOOOOOGGOOX",
    "XOOGKOOOOOOGKOOX",
    "XDOOOOOOOOOOOODX",
    "XOOOOOOPPOOOOOOX",
    "WWOOOOXOOXOOOOWW",
    "XOOOOOOXXOOOOOOX",
    ".XOOOOOOOOOOOOX.",
    "..XXXXXXXXXXXX..",
]
PAL = {
    "X": (16, 20, 32, 255), "W": (255, 255, 255, 255), "R": (236, 40, 64, 255), "H": (255, 255, 255, 200),
    "Y": (255, 214, 48, 255), "P": (255, 120, 150, 255), "G": (90, 200, 80, 255), "O": (255, 160, 60, 255),
    "D": (190, 96, 30, 255), "K": (16, 20, 32, 255),
}


def face(kind):
    rows = [list(r) for r in FACE_BASE]
    for y, x, ch in FACES[kind]:
        rows[y][x] = ch
    return pixel(["".join(r) for r in rows], PAL, 16)


def eggplant():
    pal = dict(PAL, P=(122, 64, 196, 255), H=(196, 150, 255, 255))
    return pixel(EGGPLANT, pal, 16)


def wing():
    """the green pixel wing of the cover (right wing; mirror for the left one). 48x34 grid, x16."""
    W, H = 48, 34
    g = np.zeros((H, W), np.int8)  # 0 empty, 1 dark, 2 mid, 3 light, 4 highlight
    yy, xx = np.mgrid[0:H, 0:W]
    sx, sy = 2.0, 13.0  # shoulder
    # primaries: long feathers fanning down-right, drawn back to front
    for k in range(7):
        ang = math.radians(-8 + k * 13)
        length = 44 - k * 4.2
        wid = 3.0 + 0.2 * k
        ex, ey = math.cos(ang), math.sin(ang)
        px_, py_ = xx - sx, yy - sy
        u = px_ * ex + py_ * ey
        v = -px_ * ey + py_ * ex
        inside = (u > 4) & (u < length) & (np.abs(v) < wid * np.clip((length - u) / 6 + 0.2, 0, 1) * (0.55 + 0.45 * np.clip(u / 14, 0, 1)))
        g[inside] = 2 if k % 2 else 3
        edge = inside & (np.abs(v) > wid * 0.55)
        g[edge & (g > 0)] = 2
    # coverts: rounded scallops along the top
    for k in range(6):
        cx, cy, r = 6 + k * 6.3, 9.5 + k * 0.9, 5.2 - k * 0.35
        m = (xx - cx) ** 2 + ((yy - cy) * 1.25) ** 2 < r * r
        g[m] = 3 if k % 2 == 0 else 4
    # shoulder / arm
    m = ((xx - 5) ** 2) / 36 + ((yy - 10) ** 2) / 20 < 1
    g[m] = 4
    # outline
    al = g > 0
    grow = al.copy()
    grow[1:] |= al[:-1]; grow[:-1] |= al[1:]; grow[:, 1:] |= al[:, :-1]; grow[:, :-1] |= al[:, 1:]
    g[grow & ~al] = 1
    cols = {1: (14, 70, 56, 255), 2: (60, 190, 96, 255), 3: (150, 236, 110, 255), 4: (226, 255, 170, 255)}
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p = im.load()
    for y in range(H):
        for x in range(W):
            if g[y, x]:
                p[x, y] = cols[int(g[y, x])]
    return im.resize((W * 16, H * 16), Image.NEAREST)


FONT5 = {  # 5x7 pixel glyphs for the window captions
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R":["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "W": ["10001", "10001", "10001", "10101", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    "?": ["01110", "10001", "00001", "00110", "00100", "00000", "00100"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    " ": ["00000"] * 7,
}


def text5(d, x, y, s, col):
    for ch in s:
        g = FONT5[ch]
        for yy, row in enumerate(g):
            for xx, v in enumerate(row):
                if v == "1":
                    d.point((x + xx, y + yy), fill=col)
        x += 6


def window(kind):
    """retro dialog windows (pixel grid x4), like the pop-ups on the cover."""
    w, h = {"exec": (128, 72), "error": (128, 64), "load": (128, 48), "blank": (96, 64)}[kind]
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body, light, dark, ink = (198, 198, 206, 255), (250, 250, 255, 255), (96, 96, 110, 255), (16, 20, 32, 255)
    d.rectangle((0, 0, w - 1, h - 1), fill=body, outline=ink)
    d.line((1, 1, w - 2, 1), fill=light); d.line((1, 1, 1, h - 2), fill=light)
    d.line((1, h - 2, w - 2, h - 2), fill=dark); d.line((w - 2, 1, w - 2, h - 2), fill=dark)
    title = {"exec": (40, 44, 80, 255), "error": (150, 30, 50, 255), "load": (40, 44, 80, 255), "blank": (40, 44, 80, 255)}[kind]
    d.rectangle((3, 3, w - 4, 12), fill=title)
    for i, x in enumerate((w - 30, w - 21, w - 12)):  # _ [] x buttons
        d.rectangle((x, 4, x + 7, 11), fill=body, outline=ink)
        if i == 0:
            d.line((x + 2, 9, x + 5, 9), fill=ink)
        elif i == 1:
            d.rectangle((x + 2, 6, x + 5, 9), outline=ink)
        else:
            d.line((x + 2, 6, x + 5, 9), fill=ink); d.line((x + 2, 9, x + 5, 6), fill=ink)
    screen = (24, 30, 48, 255)
    green = (110, 255, 140, 255)
    text5(d, 5, 5, {"exec": "WORLD.EXE", "error": "SYSTEM", "load": "SETUP", "blank": "ME.EXE"}[kind], light)
    if kind == "exec":
        d.rectangle((6, 16, w - 7, 44), fill=screen)
        text5(d, 31, 27, "EXECUTE ME?", green)
        for bx, col, s in ((14, (236, 40, 64, 255), "YES"), (74, (255, 120, 190, 255), "NO")):  # YES / NO buttons
            d.rectangle((bx, 52, bx + 40, 66), fill=light, outline=ink)
            d.rectangle((bx + 2, 54, bx + 38, 64), outline=col)
            text5(d, bx + 20 - 3 * len(s), 56, s, col)
    elif kind == "error":
        d.ellipse((8, 20, 30, 42), fill=(236, 40, 64, 255), outline=ink)
        d.line((14, 26, 24, 36), fill=light, width=2); d.line((14, 36, 24, 26), fill=light, width=2)
        d.rectangle((38, 22, w - 9, 40), fill=screen)
        text5(d, 48, 28, "ERROR!", (255, 90, 110, 255))
        d.rectangle((44, 48, 84, 59), fill=light, outline=ink)
        text5(d, 58, 50, "OK", ink)
    elif kind == "load":
        text5(d, 8, 16, "LOADING...", ink)
        d.rectangle((8, 26, w - 9, 38), fill=screen, outline=ink)
    else:
        d.rectangle((6, 16, w - 7, h - 7), fill=screen)
    return im.resize((w * 4, h * 4), Image.NEAREST)


def ring_cover():
    """the chunky blue-violet ring of the cover: pixel bands, inner white glow band."""
    n = 160
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.hypot(xx - (n - 1) / 2, yy - (n - 1) / 2) / (n / 2)
    im = np.zeros((n, n, 4), np.uint8)
    bands = [(0.70, 0.76, (110, 96, 240)), (0.76, 0.82, (150, 140, 255)), (0.82, 0.86, (230, 236, 255)),
             (0.86, 0.92, (150, 140, 255)), (0.92, 0.98, (96, 80, 220))]
    ang = np.arctan2(yy - n / 2, xx - n / 2)
    for a, b, c in bands:
        m = (r >= a) & (r < b)
        im[m, :3] = c
        im[m, 3] = 255
    # dither stripes like the cover's glitchy ring
    stripe = ((np.floor((ang + math.pi) / (2 * math.pi) * 48) % 7) == 0) & (r > 0.7) & (r < 0.98)
    im[stripe, :3] = (200, 210, 255)
    out = Image.fromarray(im, "RGBA")
    return out.resize((n * 6, n * 6), Image.NEAREST)


def radial(n, f):
    y, x = np.mgrid[0:n, 0:n]
    r = np.hypot(x - (n - 1) / 2, y - (n - 1) / 2) / (n / 2)
    a = np.ones((n, n, 4), np.float32)
    a[..., 3] = np.clip(f(r), 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8), "RGBA")


def grid_tex():
    w, h, step = 1280, 720, 80
    im = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    for x in range(0, w + 1, step):
        d.line((x, 0, x, h), fill=(255, 255, 255, 110), width=2)
    for y in range(0, h + 1, step):
        d.line((0, y, w, y), fill=(255, 255, 255, 110), width=2)
    d.line((w // 2, 0, w // 2, h), fill=(255, 255, 255, 230), width=4)
    d.line((0, h // 2, w, h // 2), fill=(255, 255, 255, 230), width=4)
    return im


def scan_tex():
    w, h = 1350, 760
    a = np.zeros((h, w, 4), np.uint8)
    a[::4, :, 3] = 90
    a[1::4, :, 3] = 40
    return Image.fromarray(a, "RGBA")


def binary_tex():
    """columns of 0/1 in a 5x7 pixel font (procedural), for data rain."""
    glyph = {"0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
             "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"]}
    cols, rows = 16, 40
    W, H = cols * 8, rows * 9
    a = np.zeros((H, W, 4), np.uint8)
    for c in range(cols):
        for r in range(rows):
            if RNG.random() < 0.18:
                continue
            g = glyph["01"[int(RNG.random() < 0.5)]]
            lum = int(110 + 145 * RNG.random())
            for yy, row in enumerate(g):
                for xx, ch in enumerate(row):
                    if ch == "1":
                        a[r * 9 + yy, c * 8 + xx] = (255, 255, 255, lum)
    return Image.fromarray(a, "RGBA").resize((W * 4, H * 4), Image.NEAREST)


def glitch_tex():
    w, h = 64, 64
    a = np.zeros((h, w, 4), np.uint8)
    y = 0
    while y < h:
        bh = int(RNG.integers(1, 4))
        if RNG.random() < 0.55:
            x0 = int(RNG.integers(0, w - 8)); x1 = int(min(w, x0 + RNG.integers(6, 40)))
            a[y:y + bh, x0:x1] = (255, 255, 255, int(RNG.integers(90, 255)))
        y += bh + int(RNG.integers(0, 3))
    return Image.fromarray(a, "RGBA").resize((w * 12, h * 12), Image.NEAREST)


def sine_tex():
    w, h = 1024, 256
    im = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    pts = [(x, h / 2 - 0.4 * h * math.sin(x / w * 4 * math.pi)) for x in range(0, w + 1, 4)]
    d.line(pts, fill=(255, 255, 255, 255), width=7)
    return im.filter(ImageFilter.GaussianBlur(0.8))


def clock_tex():
    n = 512
    im = Image.new("RGBA", (n, n), (255, 255, 255, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((8, 8, n - 9, n - 9), outline=(255, 255, 255, 255), width=10)
    for k in range(60):
        a = k / 60 * 2 * math.pi
        r0 = n / 2 - (54 if k % 5 == 0 else 34)
        r1 = n / 2 - 22
        w = 10 if k % 5 == 0 else 4
        d.line((n / 2 + r0 * math.sin(a), n / 2 - r0 * math.cos(a), n / 2 + r1 * math.sin(a), n / 2 - r1 * math.cos(a)),
               fill=(255, 255, 255, 255), width=w)
    return im


def stand_in_cover():
    """procedural glitch-art stand-in when no cover image is given."""
    w, h = 1368, 855
    a = np.zeros((h, w, 3), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    a[..., 0] = 0.15 + 0.25 * np.sin(xx / 90.0) ** 2
    a[..., 1] = 0.55 + 0.35 * np.sin((xx + yy) / 140.0)
    a[..., 2] = 0.55 + 0.35 * np.cos(yy / 70.0)
    for _ in range(140):
        y0 = int(RNG.integers(0, h)); hh = int(RNG.integers(2, 26)); x0 = int(RNG.integers(0, w)); ww = int(RNG.integers(40, 500))
        a[y0:y0 + hh, x0:x0 + ww] = RNG.random(3)
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im)
    r = 300
    d.ellipse((w / 2 - r, h / 2 - r, w / 2 + r, h / 2 + r), outline=(140, 130, 255), width=60)
    return im


def cover_set(out, cover):
    im = Image.open(cover).convert("RGB") if cover else stand_in_cover()
    # full-screen texture: cover crop to 16:9 at 1350x760
    sw, sh = im.size
    s = max(COVER_W / sw, COVER_H / sh)
    big = im.resize((round(sw * s), round(sh * s)), Image.LANCZOS)
    ox, oy = (big.width - COVER_W) // 2, (big.height - COVER_H) // 2
    full = big.crop((ox, oy, ox + COVER_W, oy + COVER_H))
    full.save(os.path.join(out, "cover_full.jpg"), quality=90)
    tw, th = COVER_W // TILE_COLS, COVER_H // TILE_ROWS
    for r in range(TILE_ROWS):
        for c in range(TILE_COLS):
            full.crop((c * tw, r * th, (c + 1) * tw, (r + 1) * th)).save(os.path.join(out, f"tile_{r}{c}.jpg"), quality=90)
    # pixelated copies (the "loading" look)
    for k in (8, 24):
        small = full.resize((COVER_W // k, COVER_H // k), Image.BOX)
        small.resize((COVER_W, COVER_H), Image.NEAREST).save(os.path.join(out, f"cover_px{k}.jpg"), quality=88)
    # illustration (song select / blurred backdrop)
    ill = im if im.width <= 1920 else im.resize((1920, round(im.height * 1920 / im.width)), Image.LANCZOS)
    ill.save(os.path.join(out, "illustration.jpg"), quality=92)
    return tw, th


def save_all(out, cover=None):
    os.makedirs(out, exist_ok=True)
    sizes = {}

    def put(name, im):
        sizes[name] = save(im, out, name)

    put("white.png", Image.new("RGBA", (64, 64), (255, 255, 255, 255)))
    put("glow.png", radial(256, lambda r: np.exp(-(r / 0.42) ** 2) * (r < 1)))
    put("disc.png", radial(256, lambda r: np.clip((1 - r) * 60, 0, 1)))
    put("ring.png", radial(512, lambda r: np.clip(1 - np.abs(r - 0.94) / 0.02, 0, 1) + 0.4 * np.exp(-((r - 0.94) / 0.04) ** 2)))
    put("ring_cover.png", ring_cover())
    put("cursor.png", pixel(CURSOR, PAL, 12))
    put("power.png", pixel(POWER, PAL, 16))
    put("heart.png", pixel(HEART, dict(PAL, X=(255, 92, 150, 255)), 16))
    for k in FACES:
        put(f"face_{k}.png", face(k))
    put("eggplant.png", eggplant())
    put("tomato.png", pixel(TOMATO, PAL, 16))
    put("cat.png", pixel(CAT, dict(PAL, P=(255, 140, 170, 255)), 16))
    w = wing()
    put("wing_r.png", w)
    put("wing_l.png", w.transpose(Image.FLIP_LEFT_RIGHT))
    for k in ("exec", "error", "load", "blank"):
        put(f"win_{k}.png", window(k))
    put("grid.png", grid_tex())
    put("scan.png", scan_tex())
    put("binary.png", binary_tex())
    put("sine.png", sine_tex())
    put("clock.png", clock_tex())
    for f in sorted(os.listdir(DATA)):
        if f.startswith("t_") and f.endswith(".png"):
            shutil.copy(os.path.join(DATA, f), os.path.join(out, f))
            sizes[f] = Image.open(os.path.join(DATA, f)).size
    tw, th = cover_set(out, cover)
    sizes["cover_full.jpg"] = (COVER_W, COVER_H)
    sizes["cover_px8.jpg"] = (COVER_W, COVER_H)
    sizes["cover_px24.jpg"] = (COVER_W, COVER_H)
    for r in range(TILE_ROWS):
        for c in range(TILE_COLS):
            sizes[f"tile_{r}{c}.jpg"] = (tw, th)
    return sizes


if __name__ == "__main__":
    import sys
    s = save_all(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    for k, v in s.items():
        print(k, v)
