"""新宿决战 — a note-free judge-line performance after NinjaristicNinja's Gojo vs Sukuna MMV
(the Bilibili re-upload whose audio is "雨爱 (DJ版)").

The storyboard follows the reference beat by beat (cuts on the same beats, same colour script:
cold blue-grey base, cyan / red / purple accents, red impact frames, black punctuation frames,
white-out ending). Everything is abstract line art: eyes, flames, slashes, lightning, skylines,
the floating panels of the void, the shrine, the wheel, the mudra graphic, the purple burst.

Beat k of the chart = beat k of the song (153.6 BPM, first beat 0.2935 s). No notes except one
invisible "seal" tap on the final burst so Phira's result screen has a defined accuracy.
"""
import math
import os
import random
import shutil

import madlib as ML
from chartlib import Chart, EPSB, TAP, frac
from madlib import Engine

HERE = os.path.dirname(os.path.abspath(__file__))
BPM = 153.6
OFFSET_MS = 294
SILENCE = "silence.ogg"  # silent hitsound for the seal note

INFO = {
    "name": "新宿决战",
    "difficulty": 0.0,
    "level": "MAD",
    "charter": "Claude",
    "composer": "雨爱 (DJ版) - 杨丞琳",
    "illustrator": "Claude (procedural)",
    "chart": "chart.json",
    "format": "rpe",
    "music": "song.ogg",
    "illustration": "illustration.jpg",
    "previewStart": 37.8,
    "previewEnd": 57.8,
    "aspectRatio": 1.7777778,
    "backgroundDim": 0.6,
    "lineLength": 6.0,
    "offset": 0.0,
    "tip": "纯判定线演出 · 参考 NinjaristicNinja《新宿决战》MMV",
    "tags": ["判定线演出", "MAD", "新宿决战", "无note"],
    "intro": "参考 NinjaristicNinja 的《新宿决战》静止画 MAD，逐拍复刻剪辑节奏与配色的纯判定线演出。",
    "holdPartialCover": False,
    "noteUniformScale": False,
    "forceAspectRatio": False,
    "useRpe170Speed": False,
    "useAttachUiFix": True,
}

ML.register_textures({
    "white.png": (64, 64), "glow.png": (256, 256), "disc.png": (256, 256), "ring.png": (512, 512),
    "beam.png": (1024, 64), "spike.png": (256, 1024), "focus.png": (1024, 1024), "speed.png": (1024, 256),
    "grad.png": (64, 512), "frame.png": (512, 512), "skyline_far.png": (2048, 512), "skyline_near.png": (2048, 512),
    "title.png": (1306, 383), "title_outline.png": (1306, 383), "wheel.png": (1024, 1024),
    "stars.png": (2048, 1152), "city_top.png": (2048, 1152),
})

# ------------------------------------------------------------------ palette
INK = (6, 8, 12)
NAVY = (16, 22, 34)
NAVY2 = (26, 36, 52)
STEEL = (52, 66, 86)
MIST = (150, 168, 190)
PALE = (222, 230, 240)
PAPER = (238, 241, 246)
WHITE = (255, 255, 255)
CYAN = (80, 228, 255)
CYAN2 = (40, 150, 255)
BLUE = (40, 80, 255)
DEEP = (16, 28, 96)
RED = (232, 26, 40)
RED2 = (120, 8, 18)
EMBER = (255, 90, 40)
ORANGE = (255, 120, 50)
PINK = (255, 120, 170)
PURPLE = (150, 60, 255)
MAGENTA = (255, 60, 225)
SEPIA = (70, 46, 44)


def mix(a, b, t):
    return tuple(round(p + (q - p) * t) for p, q in zip(a, b))


def F(x, d=None):
    return frac(x, d)


# ------------------------------------------------------------------ globals
class Globals:
    def __init__(self, c):
        self.c = c
        self.root = c.line("cam")
        for p in ("moveX", "moveY", "rotate"):
            self.root.ev(p, 0, EPSB, 0.0, 0.0)
            self.root.ev(p, 0, EPSB, 0.0, 0.0, layer=1)
        full = dict(texture="white.png")
        self.bg = c.line("bg", z=-100, **full)
        self.lbt = c.line("letterbox_top", z=80, **full)
        self.lbb = c.line("letterbox_bottom", z=80, **full)
        self.blk = c.line("blackout", z=85, **full)
        self.fl = c.line("flash", z=90, **full)
        sx, sy = 1800 / (64 * ML.TEXK), 1000 / (64 * ML.TEXK)
        for ln, y, h, col, a in ((self.bg, 0, 1000, NAVY, 255), (self.blk, 0, 1000, INK, 0), (self.fl, 0, 1000, WHITE, 0),
                                 (self.lbt, 520, 110, INK, 255), (self.lbb, -520, 110, INK, 255)):
            ln.ev("moveX", 0, EPSB, 0.0, 0.0)
            ln.ev("rotate", 0, EPSB, 0.0, 0.0)
            ln.ev("scaleX", 0, EPSB, sx, sx)
            ln.ev("scaleY", 0, EPSB, h / (64 * ML.TEXK), h / (64 * ML.TEXK))
            ln.ev("moveY", 0, EPSB, float(y), float(y))
        self.bg.ev("alpha", 0, EPSB, 255.0, 255.0)
        self.bg.ev("color", 0, EPSB, NAVY, NAVY)
        for ln in (self.blk, self.fl):
            ln.ev("alpha", 0, EPSB, 0.0, 0.0)
        for ln in (self.lbt, self.lbb):
            ln.ev("alpha", 0, EPSB, 255.0, 255.0)
            ln.ev("color", 0, EPSB, INK, INK)
        self.blk.ev("color", 0, EPSB, INK, INK)
        # hide the HUD: every UI element hangs from an invisible line
        for ui in ("pause", "combonumber", "combo", "score", "bar", "name", "level"):
            h = c.line(f"hud_{ui}")
            h.attach = ui
            for p in ("moveX", "moveY", "rotate", "alpha"):
                h.ev(p, 0, EPSB, 0.0, 0.0)
        self.sched = {"bg": [], "lb": [], "blk": [], "fl": [], "shk": [], "roll": []}

    def bgc(self, b, color, fade=0.0, ease="linear"):
        self.sched["bg"].append((F(b), color, F(fade), ease))

    def letterbox(self, b, on):
        self.sched["lb"].append((F(b), on))

    def black(self, b0, b1):
        self.sched["blk"].append((F(b0), F(b1)))

    def flash(self, b, color=WHITE, peak=255, dur=0.5, ease="expoOut"):
        self.sched["fl"].append((F(b), color, peak, F(dur), ease))

    def shake(self, b, amp=12.0, rot=0.0, dur=0.3):
        self.sched["shk"].append((F(b), amp, rot, F(dur)))

    def roll(self, b, deg, ease="linear"):
        self.sched["roll"].append((F(b), deg, ease))

    def emit(self, R):
        TL = ML.TL
        for key in ("bg", "lb", "fl"):  # one entry per beat (the last one registered wins)
            last = {}
            for e in self.sched[key]:
                last[e[0]] = e
            self.sched[key] = list(last.values())
        col = TL(self.bg, "color", NAVY)
        for b, c_, fade, ease in sorted(self.sched["bg"], key=lambda e: e[0]):
            if fade > 0:
                col.wait(b)
                col.to(b + fade, c_, ease)
            else:
                col.jump(b, c_)
        top, bot = TL(self.lbt, "moveY", 520.0), TL(self.lbb, "moveY", -520.0)
        state = False
        for b, on in sorted(self.sched["lb"], key=lambda e: e[0]):
            if on == state:
                continue
            state = on
            top.jump(b, 395.0 if on else 520.0)
            bot.jump(b, -395.0 if on else -520.0)
        a = TL(self.blk, "alpha", 0.0)
        for b0, b1 in sorted(self.sched["blk"]):
            a.jump(b0, 255.0)
            a.wait(b1)
            a.jump(b1, 0.0)
        fa, fc = TL(self.fl, "alpha", 0.0), TL(self.fl, "color", WHITE)
        fl = sorted(self.sched["fl"], key=lambda e: e[0])
        for i, (b, c_, peak, dur, ease) in enumerate(fl):
            end = b + dur
            if i + 1 < len(fl):
                end = min(end, fl[i + 1][0] - 2 * EPSB)
            fc.jump(b, c_)
            fa.jump(b, float(peak))
            if end > fa.b:
                fa.to(end, 0.0, ease)
        sh = sorted(self.sched["shk"], key=lambda e: e[0])
        tx, ty, tr = TL(self.root, "moveX", 0.0), TL(self.root, "moveY", 0.0), TL(self.root, "rotate", 0.0)
        for t in (tx, ty, tr):
            t.b = EPSB
        for i, (b, amp, rot, dur) in enumerate(sh):
            nxt = sh[i + 1][0] if i + 1 < len(sh) else b + dur
            L = min(dur, nxt - b)
            if L <= 0:
                continue
            ang = R.uniform(0, 2 * math.pi)
            for t, v in ((tx, amp * math.cos(ang) * ML.PX), (ty, amp * math.sin(ang)), (tr, rot * R.choice((-1, 1)))):
                t.wait(b)
                self.root.ev(t.p, b, b + L, v, 0.0, "quadOut", layer=1)
                t.b = b + L
        rl = TL(self.root, "rotate", 0.0)
        for b, deg, ease in sorted(self.sched["roll"], key=lambda e: e[0]):
            rl.to(b, deg, ease)


# ------------------------------------------------------------------ motifs
def seg_params(p, q):
    (x1, y1), (x2, y2) = p, q
    return ((x1 + x2) / 2, (y1 + y2) / 2, -math.degrees(math.atan2(y2 - y1, x2 - x1)), math.hypot(x2 - x1, y2 - y1) / 2)


def poly(s, pts, thick, color, a=255, z=0, closed=False, start=None, end=None):
    els = []
    P = list(pts) + ([pts[0]] if closed else [])
    for p, q in zip(P, P[1:]):
        els.append(s.seg(p, q, thick, color, a, z, start, end))
    return els


def rect(s, x, y, w, h, color, a=255, z=0, rot=0.0, start=None, end=None):
    return s.tex("white.png", x, y, w, h, rot, color, a, z, start, end)


def glow(s, x, y, d, color, a=255, z=10, start=None, end=None):
    return s.tex("glow.png", x, y, d, d, 0.0, color, a, z, start, end)


def disc(s, x, y, r, color, a=255, z=0, start=None, end=None):
    return s.tex("disc.png", x, y, 2 * r, 2 * r, 0.0, color, a, z, start, end)


def ring(s, x, y, r, color, a=255, z=0, start=None, end=None):
    return s.tex("ring.png", x, y, 2 * r / 0.94, 2 * r / 0.94, 0.0, color, a, z, start, end)


def spike(s, x, y, length, width, ang, color, a=255, z=0, start=None, end=None):
    """spike whose tip points along `ang` (degrees, CCW from +x); (x,y) is its centre."""
    return s.tex("spike.png", x, y, width, length, 90.0 - ang, color, a, z, start, end)


def spike_from(s, base, ang, length, width, color, a=255, z=0, start=None, end=None):
    bx, by = base
    cx = bx + math.cos(math.radians(ang)) * length / 2
    cy = by + math.sin(math.radians(ang)) * length / 2
    return spike(s, cx, cy, length, width, ang, color, a, z, start, end)


def sky(s, color, horizon, height=520, a=220, z=-60):
    return s.tex("grad.png", 0, horizon + height / 2, 1800, height, 0.0, color, a, z)


def skyline(s, name, base_y, color, a=255, z=-40, w=2700, x=0.0, x1=None, start=None, end=None):
    h = w * 512 / 2048
    e = s.tex(name, x, base_y + h / 2, w, h, 0.0, color, a, z, start, end)
    if x1 is not None:
        e.at(end if end is not None else s.b1, "linear", x=x1)
    return e


def figure(s, x, y, h, color=INK, a=255, z=0, rim=None, start=None, end=None):
    els = [rect(s, x, y + 0.31 * h, 0.30 * h, 0.62 * h, color, a, z, start=start, end=end),
           rect(s, x, y + 0.58 * h, 0.40 * h, 0.12 * h, color, a, z, start=start, end=end),
           disc(s, x, y + 0.76 * h, 0.105 * h, color, a, z, start=start, end=end)]
    if rim:
        els.append(s.seg((x - 0.15 * h, y), (x - 0.15 * h, y + 0.62 * h), 3, rim, 200, z + 1, start, end))
    return els


def hair(s, x, y, n, length, spread, color, thick=(6, 16), a=255, z=5, seed=0, down=True, start=None, end=None):
    R = random.Random(seed)
    els = []
    for i in range(n):
        ang = (-90 if down else 90) + R.uniform(-spread, spread)
        L = length * R.uniform(0.6, 1.1)
        x0 = x + R.uniform(-1, 1) * length * 0.35
        els.append(spike_from(s, (x0, y), ang, L, R.uniform(*thick) * 2.2, color, a, z, start, end))
    return els


def eye(s, x, y, w, h, iris=CYAN, lid=PALE, thick=8, z=10, open_b=None, open_dur=0.5, lower=0.6, pupil=INK,
        glow_a=210, iris_r=0.36, start=None, end=None):
    n = 6
    els = []

    def pts(f, upper):
        out = []
        for i in range(n + 1):
            u = -0.5 + i / n
            k = max(0.0, 1 - (2 * u) ** 2) ** 0.8
            out.append((x + u * w, y + (h / 2) * k * f * (1 if upper else -lower)))
        return out

    for upper in (True, False):
        P1 = pts(1.0, upper)
        P0 = pts(0.03, upper) if open_b is not None else P1
        for i in range(n):
            cx0, cy0, r0, L0 = seg_params(P0[i], P0[i + 1])
            cx1, cy1, r1, L1 = seg_params(P1[i], P1[i + 1])
            th = thick * (1.0 if upper else 0.7)
            e = s.line(cx0, cy0, r0, L0, th, lid, 255, z, start, end)
            if open_b is not None:
                if F(open_b) > e.start:
                    e.at(open_b, "linear", x=cx0, y=cy0, rot=r0, w=L0)
                e.at(F(open_b) + F(open_dur), "expoOut", x=cx1, y=cy1, rot=r1, w=L1)
            els.append(e)
    st = F(open_b) + F(open_dur) * F(1, 3) if open_b is not None else start
    if glow_a > 0:
        els.append(glow(s, x, y, h * 1.9, iris, glow_a, z - 1, start=st, end=end))
    els.append(ring(s, x, y, h * iris_r, iris, 255, z + 1, start=st, end=end))
    if pupil is not None:
        els.append(disc(s, x, y, h * 0.12, pupil, 255, z + 2, start=st, end=end))
        els.append(disc(s, x + h * 0.1, y + h * 0.1, h * 0.045, WHITE, 230, z + 3, start=st, end=end))
    return els


def red_eyes(s, x, y, sc=1.0, a=255, z=10, start=None, end=None, bright_b=None):
    els = []
    for dx, dy, r in ((-150, 0, 1.0), (150, 0, 1.0), (-205, 70, 0.62), (205, 70, 0.62)):
        g = glow(s, x + dx * sc, y + dy * sc, 150 * r * sc, RED, a if bright_b is None else int(a * 0.45), z, start, end)
        c = disc(s, x + dx * sc, y + dy * sc, 13 * r * sc, (255, 210, 200), a, z + 1, start, end)
        if bright_b is not None:
            g.at(bright_b, "linear", alpha=a * 0.45).at(F(bright_b) + F(1, 4), "expoOut", alpha=a, w=200 * r * sc, h=200 * r * sc)
        lid = s.line(x + dx * sc, y + dy * sc + 22 * r * sc, -12 if dx < 0 else 12, 46 * r * sc, 7 * r * sc, RED2, a, z + 2, start, end)
        els += [g, c, lid]
    return els


def flame(s, x, y, color, sc=1.0, z=10, seed=0, start=None, end=None):
    R = random.Random(seed)
    b0 = F(start) if start is not None else s.b0
    b1 = F(end) if end is not None else s.b1
    els = [glow(s, x, y + 60 * sc, 560 * sc, color, 210, z - 2, b0, b1), glow(s, x, y + 30 * sc, 240 * sc, mix(color, WHITE, 0.6), 235, z + 2, b0, b1)]
    for i in range(9):
        dx = R.uniform(-90, 90) * sc
        L = R.uniform(140, 330) * sc
        lean = R.uniform(-25, 25)
        thick = R.uniform(10, 26) * sc
        col = mix(color, WHITE, R.uniform(0.0, 0.45))

        def tongue(L_, lean_):
            ang = math.radians(90 + lean_)
            p0 = (x + dx, y)
            p1 = (x + dx + math.cos(ang) * L_, y + math.sin(ang) * L_)
            return seg_params(p0, p1)
        cx, cy, rr, hl = tongue(L, lean)
        e = s.line(cx, cy, rr, hl, thick, col, 230, z, b0, b1)
        t = b0
        k = 0
        while t + F(1, 4) <= b1:
            t += F(1, 4)
            k += 1
            cx, cy, rr, hl = tongue(L * R.uniform(0.65, 1.2), lean + R.uniform(-14, 14))
            e.at(t, "sineInOut", x=cx, y=cy, rot=rr, w=hl)
        els.append(e)
    return els


def slash(s, x, y, L, ang, color, b, dur=0.75, thick=10, glow_h=80, z=30, a=255):
    b = F(b)
    end = b + F(dur)
    core = s.line(x, y, -ang, 0.0, thick, color, a, z, start=b, end=end)
    core.at(b + F(dur) * F(1, 4), "expoOut", w=L / 2)
    core.at(end, "quadIn", alpha=0, h=thick * 0.3)
    g = s.tex("beam.png", x, y, 10, glow_h, -ang, color, int(a * 0.6), z - 1, start=b, end=end)
    g.at(b + F(dur) * F(1, 4), "expoOut", w=L * 1.06)
    g.at(end, "quadIn", alpha=0)
    return [core, g]


def bolt(s, p0, p1, color, b, dur, seed=0, thick=6, n=10, jag=0.12, z=35, glow_d=220):
    R = random.Random(seed)
    b = F(b)
    end = b + F(dur)
    (x0, y0), (x1, y1) = p0, p1
    L = math.hypot(x1 - x0, y1 - y0)
    nx, ny = -(y1 - y0) / L, (x1 - x0) / L
    pts = [p0]
    for i in range(1, n):
        t = i / n
        off = R.uniform(-jag, jag) * L
        pts.append((x0 + (x1 - x0) * t + nx * off, y0 + (y1 - y0) * t + ny * off))
    pts.append(p1)
    els = []
    for p, q in zip(pts, pts[1:]):
        e = s.seg(p, q, thick * R.uniform(0.7, 1.2), color, 255, z, b, end)
        e.at(b + F(dur) * F(3, 10), "linear", alpha=255).at(b + F(dur) * F(4, 10), "linear", alpha=70)
        e.at(b + F(dur) * F(5, 10), "linear", alpha=255).at(end, "quadIn", alpha=0)
        els.append(e)
    if glow_d:
        g = glow(s, x1, y1, glow_d, color, 230, z - 1, b, end)
        g.at(end, "quadIn", alpha=0)
        els.append(g)
    return els


def focus(s, x, y, d, color, a=200, z=-20, rot0=0.0, rot1=25.0, start=None, end=None):
    e = s.tex("focus.png", x, y, d, d, rot0, color, a, z, start, end)
    e.at(end if end is not None else s.b1, "linear", rot=rot1)
    return e


def speed(s, color, a=140, y=0.0, h=900, z=50, direction=-1, start=None, end=None, rot=0.0):
    b1 = end if end is not None else s.b1
    els = []
    for k in (0, 1):
        x0 = (k * 2400 - 600) * (-direction)
        e = s.tex("speed.png", x0, y, 2400, h, rot, color, a, z, start, end)
        e.at(b1, "linear", x=x0 + direction * 2400)
        els.append(e)
    return els


def wheel(s, x, y, r, color, keys, a=255, z=10, start=None, end=None):
    """the eight-handled wheel; r = radius of its rim, keys: [(beat, deg, ease)] rotation (CCW degrees)."""
    d = 2 * r / 0.56
    e = s.tex("wheel.png", x, y, d, d, -keys[0][1], color, a, z, start, end)
    for b, deg, ease in keys[1:]:
        e.at(b, ease, rot=-deg)
    return [e]


def shrine(s, x, y, sc, color, thick=8, a=255, z=0, start=None, end=None, teeth=True):
    L = [((-120, 150), (120, 150)), ((-120, 150), (-230, 82)), ((120, 150), (230, 82)), ((-230, 82), (-275, 106)),
         ((230, 82), (275, 106)), ((-110, 150), (-110, 96)), ((110, 150), (110, 96)), ((-110, 96), (110, 96)),
         ((-180, 40), (180, 40)), ((-180, 40), (-325, -20)), ((180, 40), (325, -20)), ((-325, -20), (-368, 8)),
         ((325, -20), (368, 8)),
         ((-200, -20), (200, -20)), ((-170, -92), (170, -92)), ((-150, -20), (-150, -240)), ((150, -20), (150, -240)),
         ((-60, -20), (-60, -240)), ((60, -20), (60, -240)), ((-285, -240), (285, -240)), ((-305, -264), (305, -264))]
    els = poly_list(s, [((x + p[0] * sc, y + p[1] * sc), (x + q[0] * sc, y + q[1] * sc)) for p, q in L], thick * sc, color, a, z, start, end)
    if teeth:
        for k in range(-6, 7):
            els.append(spike(s, x + k * 44 * sc, y - 42 * sc, 46 * sc, 22 * sc, -90, color, a, z, start, end))
    return els


def poly_list(s, segs, thick, color, a, z, start=None, end=None):
    return [s.seg(p, q, thick, color, a, z, start, end) for p, q in segs]


def cubes(s, x, y, n, color, b, dur, seed=0, z=20, spread=900):
    R = random.Random(seed)
    b = F(b)
    els = []
    for i in range(n):
        size = R.uniform(14, 60)
        ang = R.uniform(0, 2 * math.pi)
        dist = R.uniform(0.3, 1.0) * spread
        e = rect(s, x, y, size, size, mix(color, WHITE, R.uniform(0, 0.4)), 255, z, R.uniform(0, 90), b, b + F(dur))
        e.at(b + F(dur), "expoOut", x=x + math.cos(ang) * dist, y=y + math.sin(ang) * dist, rot=R.uniform(180, 720))
        els.append(e)
    return els


def embers(s, color, n, b0, b1, seed=0, z=30, rise=True, area=(800, 450), size=(10, 26)):
    R = random.Random(seed)
    els = []
    b0, b1 = F(b0), F(b1)
    for i in range(n):
        st = b0 + F(R.randint(0, int((b1 - b0) * 8) - 1), 8) if b1 - b0 > F(1, 4) else b0
        life = min(b1 - st, F(R.randint(4, 16), 8))
        if life <= 0:
            continue
        x0, y0 = R.uniform(-area[0], area[0]), R.uniform(-area[1], area[1])
        dy = R.uniform(120, 420) * (1 if rise else -1) * float(life)
        d = R.uniform(*size)
        e = glow(s, x0, y0, d * 3, mix(color, WHITE, R.uniform(0, 0.35)), 255, z, st, st + life)
        e.at(st + life, "linear", x=x0 + R.uniform(-60, 60), y=y0 + dy, alpha=0)
        els.append(e)
    return els


def stars(s, color, a=255, z=-30, w=1800, rot=0.0, drift=0.0, start=None, end=None):
    """a pre-rendered starfield (one line); drift slowly zooms it towards the viewer."""
    e = s.tex("stars.png", 0, 0, w, None, rot, color, a, z, start, end)
    if drift:
        e.at(end if end is not None else s.b1, "linear", w=w * (1 + drift), h=w * (1 + drift) * 1152 / 2048)
    return [e]


def void_panels(s, n, color, seed=0, z=-20, start=None, end=None):
    R = random.Random(seed)
    b1 = end if end is not None else s.b1
    els = []
    for i in range(n):
        ang = R.uniform(0, 2 * math.pi)
        r0 = R.uniform(140, 520)
        x0, y0 = math.cos(ang) * r0 * 1.4, math.sin(ang) * r0
        w0 = R.uniform(50, 150)
        k = R.uniform(1.3, 1.8)
        fill = rect(s, x0, y0, w0, w0 * 0.75, color, 50, z, R.uniform(-20, 20), start, end)
        fill.at(b1, "linear", x=x0 * k, y=y0 * k, w=w0 * k, h=w0 * 0.75 * k)
        fr = s.tex("frame.png", x0, y0, w0, w0 * 0.75, R.uniform(-20, 20), color, 230, z + 1, start, end)
        fr.at(b1, "linear", x=x0 * k, y=y0 * k, w=w0 * k, h=w0 * 0.75 * k)
        els += [fill, fr]
    return els


def fingers(s, x, y, sc, color, thick=7, a=255, z=10, flip=1, start=None, end=None):
    els = []
    for k, (dy, L, bend) in enumerate(((60, 200, 30), (20, 240, 22), (-20, 230, 18), (-60, 190, 26), (-110, 120, 40))):
        pts = []
        for i in range(5):
            t = i / 4
            pts.append((x - flip * t * L * sc, y + dy * sc - math.sin(t * math.pi * 0.8) * bend * sc * (1 if k < 4 else -1)))
        els += poly(s, pts, thick, color, a, z, start=start, end=end)
    return els


def split(s, ang, col_a, col_b, z=-80, line_col=PALE, start=None, end=None):
    th = math.radians(ang)
    nx, ny = -math.sin(th), math.cos(th)
    rot = -ang
    return [rect(s, nx * 1000, ny * 1000, 4000, 2000, col_a, 255, z, rot, start, end),
            rect(s, -nx * 1000, -ny * 1000, 4000, 2000, col_b, 255, z, rot, start, end),
            s.line(0, 0, rot, 1400, 10, line_col, 255, z + 1, start, end)]


def streak(s, p0, p1, color, b, dur, width=90, core=14, z=30):
    """energy streak travelling from p0 to p1."""
    b = F(b)
    end = b + F(dur)
    cx, cy, rr, hl = seg_params(p0, p1)
    g = s.tex("beam.png", p0[0], p0[1], 10, width, rr, color, 230, z, b, end)
    g.at(b + F(dur) * F(1, 2), "expoOut", x=cx, y=cy, w=hl * 2.1).at(end, "quadIn", alpha=0)
    c = s.line(p0[0], p0[1], rr, 0.0, core, mix(color, WHITE, 0.5), 255, z + 1, b, end)
    c.at(b + F(dur) * F(1, 2), "expoOut", x=cx, y=cy, w=hl).at(end, "quadIn", alpha=0)
    hit = glow(s, p1[0], p1[1], width * 4, color, 0, z - 1, b, end)
    hit.at(b + F(dur) * F(2, 5), "linear", alpha=0).at(b + F(dur) * F(1, 2), "expoOut", alpha=255).at(end, "quadIn", alpha=0)
    return [g, c, hit]


def face_lines(s, x, y, sc, color, thick=6, a=255, z=0, start=None, end=None):
    jaw = [(x - 260 * sc, y + 120 * sc), (x - 250 * sc, y - 40 * sc), (x - 190 * sc, y - 190 * sc), (x - 70 * sc, y - 280 * sc),
           (x + 40 * sc, y - 300 * sc), (x + 160 * sc, y - 230 * sc), (x + 240 * sc, y - 90 * sc), (x + 260 * sc, y + 100 * sc)]
    nose = [(x, y - 20 * sc), (x - 12 * sc, y - 110 * sc), (x + 18 * sc, y - 120 * sc)]
    mouth = [(x - 70 * sc, y - 200 * sc), (x + 80 * sc, y - 190 * sc)]
    return poly(s, jaw, thick, color, a, z, start=start, end=end) + poly(s, nose, thick * 0.8, color, a, z, start=start, end=end) + \
        poly(s, mouth, thick, color, a, z, start=start, end=end)


def smile(s, x, y, w, color, thick=7, a=255, z=10, start=None, end=None):
    pts = [(x + (i / 6 - 0.5) * w, y - math.sin(i / 6 * math.pi) * w * 0.18) for i in range(7)]
    return poly(s, pts, thick, color, a, z, start=start, end=end)


# ================================================================== storyboard
def storyboard(E, G):
    R = random.Random(1224)
    sh = E.shot

    # ---------------- bars 0-1: flames, clash, slash, title card
    s = sh(0, 1)
    flame(s, 0, -260, CYAN2, 1.15, seed=1)
    s = sh(1, 2)
    flame(s, 40, -250, RED, 1.15, seed=2)
    G.bgc(1, (20, 8, 12))
    s = sh(2, 3, cam=[(3, 1.08, 0, 0, "linear")])
    G.bgc(2, NAVY)
    flame(s, -330, -240, CYAN2, 0.9, seed=3)
    flame(s, 330, -240, RED, 0.9, seed=4)
    for k in range(14):
        a = math.radians(R.uniform(0, 360))
        s.seg((0, -60), (math.cos(a) * 60, -60 + math.sin(a) * 60), 5, mix(CYAN, RED, k / 13), 255, 25, 2, 2.5).at(2.5, "expoOut", w=R.uniform(120, 300))
    G.shake(2, 10, 0.6)
    s = sh(3, 4)
    G.bgc(3, INK)
    s.line(0, 0, -28, 0.0, 170, PAPER, 255, 0).at(3.25, "expoOut", w=1300)
    for off in (-200, 210):
        s.line(off * 0.47, off, -28, 0.0, 10, PAPER, 220, 0, start=3.125).at(3.4, "expoOut", w=1300)
    G.shake(3, 14, 1.0)
    s = sh(4, 5)
    G.bgc(4, PAPER)
    glow(s, 0, 0, 1500, (200, 170, 255), 120, -30)
    for k, (cx, cy, th) in enumerate(((-560, 330, 150), (560, -330, 150), (-420, 420, 26), (430, -430, 26))):
        s.line(cx, cy, -24, 1400, th, INK, 255, -10)
    s.line(0, -20, -24, 1400, 6, RED, 255, -9, start=4.0625).at(4.375, "expoOut", w=1400)
    for name, col in (("title_outline.png", PAPER), ("title.png", INK)):
        t = s.tex(name, 0, 10, 1280, None, 0.0, col, 255, 20 if col == PAPER else 21)
        t.at(5, "linear", w=1340, h=1340 * 383 / 1306)
    G.shake(4, 18, 1.2, 0.35)
    G.flash(4, WHITE, 200, 0.25)

    # ---------------- bars 1.1-2.0: the quiet room (lockers)
    G.letterbox(5, True)
    G.bgc(5, NAVY2)
    s = sh(5, 9, cam=[(9, 1.06, -40, 0, "linear")])
    for i in range(-2, 6):
        s.line(i * 150 + 120, 0, 90, 300, 4, STEEL, 255, -20)
    for j in range(-2, 3):
        s.line(450, j * 120 + 30, 0, 420, 4, STEEL, 255, -20)
    for i in range(0, 5):
        for j in range(-2, 2):
            rect(s, i * 150 + 195, j * 120 + 90, 30, 6, MIST, 200, -19)
    figure(s, -420, -300, 330, INK, 255, 0, rim=MIST)
    figure(s, 540, -340, 470, INK, 255, 0, rim=MIST)
    glow(s, -420, 10, 40, CYAN, 0, 5, 7, 9).at(7.5, "sineOut", alpha=200)

    # ---------------- bar 2.1-2.3: the eyes open
    G.bgc(9, NAVY)
    s = sh(9, F(11) + F(5, 8), cam=[(F(11) + F(5, 8), 1.14, 0, 20, "sineIn")])
    for k in range(24):
        spike_from(s, (R.uniform(-820, 820), 480), -90 + R.uniform(-32, 32), R.uniform(200, 380), R.uniform(40, 80), PALE, 225, 0)
    eye(s, -300, 0, 430, 170, CYAN, PALE, 9, 12, open_b=9, open_dur=0.6)
    eye(s, 300, 0, 430, 170, CYAN, PALE, 9, 12, open_b=9, open_dur=0.6)
    G.black(F(11) + F(5, 8), 12)

    # ---------------- bars 3.0-3.2: walking; 3.3-4.0 high-key hair
    G.bgc(12, NAVY2)
    s = sh(12, 15, cam=[(15, 1.05, 0, 0, "linear")])
    s.line(0, -170, 0, 900, 4, MIST, 200, -10)
    for k, (x0, h) in enumerate(((-420, 360), (-120, 400), (220, 380))):
        for e in figure(s, x0, -170, h, INK, 255, 0, rim=PALE):
            e.at(15, "linear", x=e.kf["x"].k[0][1] - 90)
    G.bgc(15, PAPER)
    G.letterbox(15, False)
    s = sh(15, 17, cam=[(17, 1.07, 0, 0, "linear")])
    hair(s, 120, 520, 16, 520, 40, INK, (10, 22), 255, 0, seed=5)
    poly(s, [(-200, -60), (-120, -260), (60, -330), (230, -240)], 8, INK, 255, 0)

    # ---------------- bars 4.1-5.0: dark close-up, black, Sukuna's marks
    G.letterbox(17, True)
    G.bgc(17, (12, 18, 30))
    s = sh(17, 21, cam=[(21, 1.1, 30, 0, "linear")])
    disc(s, -260, -80, 420, (22, 32, 50), 255, -30)
    eye(s, 300, 60, 380, 110, (90, 170, 220), MIST, 7, 10, glow_a=120)
    hair(s, -300, 470, 12, 420, 30, (36, 48, 70), (12, 26), 255, -25, seed=6)
    G.bgc(21, INK)
    G.bgc(22, (12, 8, 12))
    s = sh(22, 24, cam=[(24, 1.08, 0, 0, "linear")])
    hair(s, 420, 470, 14, 380, 35, (90, 90, 100), (8, 18), 255, -10, seed=7)
    for k in range(2):
        s.line(-120 + k * 50, -60 - k * 20, -20, 0.0, 10, RED, 255, 10, start=22.25).at(22.6, "expoOut", w=160)
    glow(s, -100, -60, 520, RED, 150, -20)

    # ---------------- bar 6-8: red impact, red backlight, Sukuna's face
    G.letterbox(24, False)
    G.bgc(24, RED)
    s = sh(24, 25)
    for k in range(9):
        spike_from(s, (-800 + k * 200 + R.uniform(-40, 40), -470), 90 + R.uniform(-25, 25), R.uniform(260, 520), R.uniform(70, 140), INK, 255, 0)
        spike_from(s, (-700 + k * 190, 470), -90 + R.uniform(-30, 30), R.uniform(160, 380), R.uniform(50, 110), INK, 255, 0)
    for k in range(3):
        slash(s, R.uniform(-200, 200), R.uniform(-100, 100), 1100, R.uniform(15, 35), PAPER, 24 + k * 0.125, 0.85, 8, 50, 20)
    G.shake(24, 22, 1.6, 0.4)
    G.bgc(25, (12, 4, 6))
    G.letterbox(25, True)
    s = sh(25, 29, cam=[(29, 1.08, 0, 0, "linear")])
    for k in range(9):
        x0 = -760 + k * 190
        s.tex("grad.png", x0, 120, 120, 900, 180.0, RED if k % 2 else RED2, 200, -40)
    disc(s, -120, -300, 380, INK, 255, 0)
    hair(s, -120, 60, 10, 260, 60, INK, (14, 28), 255, 1, seed=8, down=False)
    G.bgc(29, RED)
    s = sh(29, 30)
    disc(s, 80, -160, 300, INK, 255, 0)
    hair(s, 80, 80, 12, 300, 70, INK, (14, 30), 255, 1, seed=9, down=False)
    G.shake(29, 18, 1.2)
    G.bgc(30, (14, 6, 8))
    s = sh(30, 34, cam=[(34, 1.16, 0, -10, "sineIn")])
    glow(s, 0, 160, 1300, RED, 170, -40)
    face_lines(s, 0, 80, 1.15, (60, 30, 34), 9, 255, -10)
    red_eyes(s, 0, 60, 1.0, 255, 10, bright_b=33)
    for side in (-1, 1):
        for k in range(2):
            s.line(side * (150 + k * 26), -40 - k * 20, side * 70, 40, 7, RED, 230, 9)
    G.flash(33, RED, 120, 0.5)
    G.bgc(34, INK)
    G.letterbox(34, False)

    # ---------------- bar 8.3-10: rooftop, red sky, eyes in the distance
    G.letterbox(35, True)
    G.bgc(35, NAVY)
    s = sh(35, 37, cam=[(37, 1.04, -60, 0, "linear")])
    sky(s, RED, -200, 560, 230)
    skyline(s, "skyline_far.png", -330, (40, 40, 56), 255, -40, 2800, 0, -80)
    skyline(s, "skyline_near.png", -470, INK, 255, -30, 2800, 60, 160)
    figure(s, 260, -160, 160, INK, 255, 0, rim=PALE)
    hair(s, 260, -22, 6, 40, 70, PALE, (3, 6), 255, 2, seed=10, down=False)
    G.bgc(37, (10, 12, 18))
    s = sh(37, 38)
    disc(s, 120, -100, 520, (20, 26, 38), 255, -20)
    s.line(-300, 120, 30, 500, 4, MIST, 180, 0)
    G.bgc(38, PAPER)
    G.letterbox(38, False)
    s = sh(38, 40, cam=[(40, 1.06, 0, 0, "linear")])
    disc(s, 330, -260, 520, INK, 255, -10)
    hair(s, 330, 260, 10, 300, 70, INK, (16, 30), 255, -9, seed=11, down=False)
    glow(s, 260, -40, 160, CYAN, 255, 10)
    disc(s, 260, -40, 12, WHITE, 255, 11)
    G.letterbox(40, True)
    G.bgc(40, NAVY)
    s = sh(40, 42, cam=[(42, 1.05, 0, 0, "linear")])
    sky(s, RED, -220, 560, 200)
    skyline(s, "skyline_near.png", -470, INK, 255, -30, 2800, 0, -100)
    figure(s, 0, -210, 150, INK, 255, 0)
    for dx in (-10, 10):
        glow(s, dx, -80, 30, RED, 255, 5).at(41, "linear", alpha=255).at(41.25, "expoOut", w=60, h=60)
    G.bgc(42, (16, 8, 10))
    s = sh(42, F(43) + F(11, 16), cam=[(F(43) + F(11, 16), 1.12, 0, 0, "sineIn")])
    for k in range(4):
        rect(s, -620 + k * 60, -120 + k * 30, 110, 700, (40, 32, 40), 255, -30)
    face_lines(s, 120, 60, 1.0, (70, 36, 40), 8, 255, -10)
    red_eyes(s, 120, 40, 0.9, 255, 10)
    G.black(F(43) + F(11, 16), 44)

    # ---------------- bar 11-12: spectators in panels, profile, rooftop
    G.bgc(44, (30, 42, 60))
    G.letterbox(44, False)
    s = sh(44, 48)
    panels = [(-470, 40, 560, 700), (60, 120, 480, 520), (480, -140, 560, 460)]
    for k, (x0, y0, w, h) in enumerate(panels):
        b = 44 + k
        rect(s, x0, y0, w, h, (46, 62, 86), 255, -20, start=b)
        for e in poly(s, [(x0 - w / 2, y0 - h / 2), (x0 + w / 2, y0 - h / 2), (x0 + w / 2, y0 + h / 2), (x0 - w / 2, y0 + h / 2)], 8, PAPER, 255, -10, closed=True, start=b):
            e.at(b + 0.25, "expoOut", alpha=255)
        figure(s, x0, y0 - h / 2 + 10, h * 0.8, (20, 28, 40), 255, -15, rim=MIST, start=b)
        G.shake(b, 6, 0.3)
    G.bgc(48, (176, 192, 210))
    s = sh(48, 49, cam=[(49, 1.04, 0, 0, "linear")])
    poly(s, [(-200, 450), (-230, 200), (-170, 90), (-250, 20), (-200, -40), (-230, -120), (-150, -260), (-60, -450)], 12, INK, 255, 0)
    glow(s, -120, 120, 110, CYAN, 255, 10)
    G.bgc(49, NAVY2)
    s = sh(49, 52, cam=[(52, 1.06, 0, 0, "linear")])
    rect(s, 0, -330, 1800, 220, (190, 200, 214), 255, -30)
    figure(s, -330, -230, 300, INK, 255, 0, rim=MIST)
    figure(s, 260, -230, 340, INK, 255, 0, rim=MIST)
    s.line(390, -110, -80, 260, 8, PALE, 255, 1)

    # ---------------- bar 13-15: red skyline, claws, three slashes, footsteps, old man
    G.letterbox(52, True)
    G.bgc(52, NAVY)
    s = sh(52, 53)
    sky(s, RED, -150, 600, 255)
    skyline(s, "skyline_near.png", -470, INK, 255, -30, 2800, 0, -60)
    G.bgc(53, (22, 8, 10))
    s = sh(53, 55, cam=[(55, 1.08, 0, 0, "linear")])
    s.tex("grad.png", 600, 0, 700, 1000, 90.0, RED, 230, -40)
    fingers(s, 520, 40, 1.3, PALE, 8, 255, 0)
    fingers(s, 560, -200, 1.0, MIST, 7, 255, 0, start=54)
    G.bgc(55, (70, 78, 90))
    G.letterbox(55, False)
    s = sh(55, 56)
    figure(s, 0, -330, 620, (40, 46, 58), 255, -20)
    for k in range(3):
        slash(s, -60 + k * 120, 40, 1300, 62, PAPER, 55 + k * 0.125, 0.875, 9, 60, 20)
    G.shake(55, 10, 0.6)
    G.bgc(56, (58, 64, 76))
    G.letterbox(56, True)
    for b0 in (56, 62):
        G.bgc(b0, (58, 64, 76))
        s = sh(b0, b0 + 1, cam=[(b0 + 1, 1.05, 0, 0, "linear")])
        s.tex("speed.png", 0, -250, 2400, 400, 0.0, (110, 118, 132), 120, -30)
        for k in range(2):
            fx, fy, st = -150 + k * 280, -250 + k * 40, b0 + k * F(1, 2)
            rg = s.tex("ring.png", fx, fy - 30, 130, 44, 0.0, PALE, 255, -1, start=st)
            rg.at(st + F(1, 2), "expoOut", w=560, h=180, alpha=0)
            s.tex("disc.png", fx, fy, 64, 150, -8 + k * 16, PALE, 255, 0, start=st)
    G.bgc(57, (28, 38, 54))
    s = sh(57, 60, cam=[(60, 1.08, 0, 0, "linear")])
    disc(s, -200, -320, 300, INK, 255, -10)
    for k in range(5):
        spike_from(s, (180, -120), 100 + k * 18, 520, 120, (14, 18, 26), 255, -12)
    eye(s, -200, -40, 160, 56, (120, 190, 230), MIST, 5, 10, glow_a=100)
    G.bgc(60, (60, 62, 70))
    s = sh(60, 62, cam=[(62, 1.04, 0, 0, "linear")])
    figure(s, 60, -330, 520, (26, 28, 34), 255, -10)
    s.seg((260, -420), (230, 330), 8, PALE, 255, 0)
    G.bgc(63, PAPER)
    G.letterbox(63, False)
    s = sh(63, 64)
    hair(s, 0, 520, 18, 600, 50, INK, (12, 26), 255, 0, seed=12)
    G.flash(F(63) + F(3, 4), WHITE, 255, 0.25, "linear")

    # ---------------- bar 16-19: domain expansion — backlight, the void, fire, purple
    G.bgc(64, INK)
    s = sh(64, 66, cam=[(66, 1.06, 0, 0, "linear")])
    for (x0, y0, w, h, r) in ((-560, 180, 260, 420, -8), (-300, 300, 200, 260, 6), (380, 220, 300, 440, 10), (620, -60, 220, 360, -6),
                              (-620, -200, 200, 300, 4), (250, -260, 180, 220, -10)):
        rect(s, x0, y0, w, h, PAPER, 255, -20, r)
    glow(s, 0, 80, 1500, WHITE, 255, -25)
    rect(s, 20, 150, 560, 520, PAPER, 255, -21, 3.0)
    figure(s, 0, -470, 820, INK, 255, 0)
    hair(s, 0, 130, 16, 230, 80, INK, (16, 30), 255, 1, seed=13, down=False)
    G.flash(64, WHITE, 255, 0.75)
    G.shake(64, 20, 1.0, 0.4)
    G.bgc(66, DEEP)
    s = sh(66, 67, cam=[(67, 1.1, 0, 0, "linear")])
    stars(s, PALE, 255, drift=0.08)
    void_panels(s, 14, CYAN, seed=15)
    figure(s, 0, -260, 360, INK, 255, 0, rim=CYAN)
    glow(s, 0, -80, 700, CYAN2, 120, -10)
    G.bgc(67, (34, 54, 110))
    s = sh(67, 69, cam=[(69, 1.08, 0, 0, "linear")])
    stars(s, CYAN, 255, 30, 2000, 180.0, drift=0.2)
    for x0 in (-200, 200):
        ring(s, x0, 60, 130, PALE, 255, 0)
    s.line(0, 60, 0, 70, 8, PALE, 255, 0)
    face_lines(s, 0, 40, 1.3, PALE, 6, 160, -5)
    for k in range(4):
        s.seg((-380 + k * 30, -40), (-390 + k * 30, -120), 6, CYAN, 200, 2)
    speed(s, CYAN, 90, 0, 900, 40)
    G.bgc(69, DEEP)
    s = sh(69, 71, cam=[(71, 1.2, 0, 0, "linear")])
    stars(s, PALE, 255, w=1900, rot=90.0, drift=0.15)
    void_panels(s, 22, CYAN2, seed=18)
    G.bgc(71, (46, 12, 8))
    s = sh(71, 73, cam=[(73, 1.06, 0, 0, "linear")])
    for k in range(3):
        streak(s, (-900, -300 + k * 160), (900, 260 + k * 120), (ORANGE, EMBER, RED)[k], 71 + k * 0.25, 1.5, 200 - k * 40, 18)
    embers(s, EMBER, 40, 71, 73, seed=19)
    G.shake(71, 14, 1.0)
    G.bgc(73, (34, 22, 44))
    s = sh(73, 74)
    sky(s, (170, 60, 110), -230, 600, 230)
    skyline(s, "skyline_far.png", -350, (30, 26, 40), 255, -40, 2800, 0, -50)
    figure(s, -120, -240, 120, INK, 255, 0)
    G.bgc(74, (20, 24, 34))
    s = sh(74, 75)
    rect(s, 0, -330, 1800, 200, (40, 44, 56), 255, -20)
    figure(s, -220, -250, 320, INK, 255, 0, rim=MIST)
    figure(s, 220, -250, 300, INK, 255, 0, rim=MIST)
    G.bgc(75, (24, 20, 40))
    s = sh(75, 76, cam=[(76, 1.12, 0, 0, "expoIn")])
    figure(s, -140, -470, 700, (14, 14, 22), 255, -10)
    glow(s, 180, 0, 760, PURPLE, 255, 10)
    glow(s, 180, 0, 210, WHITE, 255, 11)
    fingers(s, 360, -10, 1.1, PALE, 7, 255, 12)
    G.bgc(76, (70, 10, 70))
    s = sh(76, 78, cam=[(78, 1.1, 0, 0, "linear")])
    glow(s, 0, 60, 1500, MAGENTA, 255, -20)
    glow(s, 0, 60, 600, WHITE, 255, -19)
    for k in range(6):
        a = math.radians(-30 + k * 45)
        bolt(s, (0, 60), (math.cos(a) * 900, 60 + math.sin(a) * 600), PALE if k % 2 else PINK, 76 + k * 0.125, 1.25, seed=20 + k, thick=7, n=7)
    skyline(s, "skyline_near.png", -470, (20, 6, 24), 255, -10, 2800)
    G.flash(76, MAGENTA, 230, 0.5)
    G.shake(76, 26, 1.8, 0.45)
    G.shake(77, 14, 1.0)
    G.bgc(78, (22, 34, 80))
    s = sh(78, 79)
    skyline(s, "skyline_far.png", -360, (40, 60, 120), 255, -30, 2800)
    fingers(s, 260, 80, 1.6, PALE, 9, 255, 0)
    G.bgc(79, PAPER)
    s = sh(79, 80)
    G.bgc(80, (34, 10, 44))
    s = sh(80, 81)
    skyline(s, "skyline_near.png", -470, INK, 255, -30, 2800)
    bolt(s, (-200, 470), (120, -180), MAGENTA, 80, 1.0, seed=30, thick=10, n=12)
    glow(s, 120, -180, 500, MAGENTA, 220, -20)
    G.shake(80, 16, 1.0)

    # ---------------- bar 20.1-23.3: the first exchange (one cut per beat)
    G.letterbox(81, True)
    G.bgc(81, NAVY)
    s = sh(81, 82)
    skyline(s, "skyline_near.png", -470, INK, 255, -30, 2800, 0, -100)
    plan = [(82, "clash"), (83, "cyan"), (84, "red_burst"), (85, "cyan_diag"), (86, "cyan_big"), (87, "calm"), (88, "cyan_fist"),
            (89, "red_slash"), (90, "red_slash2"), (91, "red_frame"), (92, "red_eyes_blue"), (93, "fall"), (94, "fall"), (95, "grin")]
    for b, kind in plan:
        s = sh(b, b + 1, cam=[(b + 1, 1.06, 0, 0, "linear")])
        if kind in ("calm", "fall"):
            G.bgc(b, NAVY)
            skyline(s, "skyline_far.png", -360, (34, 44, 64), 255, -40, 2800, 0, -80)
            skyline(s, "skyline_near.png", -470, INK, 255, -30, 2800, 0, -160)
            if kind == "fall":
                for e in figure(s, -60 + (b - 93) * 160, 200, 110, INK, 255, 0, rim=PALE):
                    e.at(b + 1, "quadIn", y=e.kf["y"].k[0][1] - 260)
            continue
        if kind == "grin":
            G.bgc(b, (34, 52, 74))
            eye(s, -150, 90, 300, 90, CYAN, PALE, 7, 10)
            smile(s, 60, -170, 360, PALE, 8)
            hair(s, 0, 470, 12, 260, 40, PALE, (8, 18), 230, 0, seed=b)
            continue
        if kind == "red_frame":
            G.bgc(b, RED)
            fingers(s, 160, 120, 1.4, PAPER, 10, 255, 0)
            figure(s, -200, -470, 600, (120, 10, 20), 255, -10)
            G.shake(b, 12, 0.8)
            continue
        if kind == "red_eyes_blue":
            G.bgc(b, (30, 48, 80))
            red_eyes(s, 0, 30, 1.2, 255, 10)
            continue
        G.bgc(b, (14, 18, 30))
        skyline(s, "skyline_far.png", -360, (30, 38, 56), 255, -40, 2800, 0, -60)
        if kind == "clash":
            streak(s, (-900, -100), (0, 0), CYAN, b, 0.9, 140, 16)
            streak(s, (900, -60), (0, 0), RED, b, 0.9, 140, 16)
            G.shake(b, 14, 1.0)
        elif kind == "cyan":
            streak(s, (-900, -40), (300, 20), CYAN, b, 0.9, 160, 18)
            speed(s, CYAN, 70, 0, 900, 40, -1)
            G.shake(b, 10, 0.6)
        elif kind == "red_burst":
            glow(s, 0, 0, 900, RED, 255, -10).at(b + 1, "quadIn", alpha=0)
            for k in range(10):
                spike_from(s, (0, 0), k * 36 + R.uniform(-8, 8), R.uniform(300, 600), R.uniform(40, 90), EMBER, 255, 0, b, b + 1)
            G.flash(b, RED, 140, 0.4)
            G.shake(b, 20, 1.4)
        elif kind == "cyan_diag":
            streak(s, (-800, 420), (420, -300), CYAN, b, 0.9, 150, 16)
            figure(s, 300, -420, 380, INK, 255, 0, rim=CYAN)
            G.shake(b, 10, 0.6)
        elif kind == "cyan_big":
            streak(s, (-900, 0), (500, 0), CYAN, b, 0.9, 260, 24)
            ring(s, 500, 0, 60, CYAN, 255, 20, b, b + 1).at(b + 1, "expoOut", w=900, h=900, alpha=0)
            G.shake(b, 18, 1.2)
        elif kind == "cyan_fist":
            glow(s, -260, -40, 800, CYAN, 255, -5)
            fingers(s, -120, -40, 1.2, PALE, 9, 255, 5, flip=-1)
            speed(s, CYAN, 90, 0, 900, 40, 1)
            G.shake(b, 14, 1.0)
        elif kind in ("red_slash", "red_slash2"):
            slash(s, 0, 0, 1700, 20 if kind == "red_slash" else -18, RED, b, 0.9, 22, 160, 20)
            embers(s, EMBER, 20, b, b + 1, seed=b)
            G.shake(b, 16, 1.2)

    # ---------------- bar 24-25: the drop — cyan triangle, overhead city, beam, slashes, debris
    G.letterbox(96, False)
    G.bgc(96, (8, 18, 30))
    s = sh(96, 97, cam=[(97, 1.08, 0, 0, "linear")])
    tri = [(-430, -330), (430, -330), (0, 330)]
    for e in poly(s, tri, 14, CYAN, 255, 10, closed=True):
        e.at(96.25, "expoOut", h=10)
    glow(s, 0, -60, 1100, CYAN2, 180, -10)
    skyline(s, "skyline_near.png", -470, INK, 255, 20, 2800)
    G.flash(96, CYAN, 220, 0.4)
    G.shake(96, 22, 1.4, 0.4)
    G.letterbox(97, True)
    G.bgc(97, (24, 34, 50))
    s = sh(97, 100, cam=[(100, 1.12, 0, 0, "linear")])
    s.tex("city_top.png", 0, 0, 1900, None, 2.0, MIST, 170, -10)
    figure(s, -60, -40, 90, INK, 255, 0, rim=PALE)
    figure(s, 90, -20, 90, INK, 255, 0, rim=RED)
    G.bgc(100, (10, 12, 18))
    s = sh(100, 101)
    slash(s, 0, 0, 2200, 38, PAPER, 100, 1.0, 60, 260, 10)
    figure(s, 80, -470, 700, (60, 66, 80), 255, -10)
    G.shake(100, 18, 1.2)
    G.bgc(101, (14, 16, 22))
    s = sh(101, 102)
    for k, (ang, y0) in enumerate(((20, 60), (-35, -40), (70, 0), (-70, 30))):
        slash(s, 0, y0, 1800, ang, PAPER, 101 + k * 0.125, 0.875, 4, 30, 10)
    figure(s, 0, -470, 620, (30, 34, 44), 255, -10)
    G.bgc(102, (64, 40, 52))
    s = sh(102, 103)
    cubes(s, -100, 0, 26, PINK, 102, 1.0, seed=21)
    figure(s, 200, -400, 500, (40, 24, 34), 255, -10)
    G.shake(102, 12, 0.8)
    G.bgc(103, NAVY)
    s = sh(103, 104)
    skyline(s, "skyline_far.png", -360, (40, 46, 70), 255, -40, 2800)
    skyline(s, "skyline_near.png", -470, INK, 255, -30, 2800)
    for e in figure(s, 0, -200, 120, INK, 255, 0, rim=PALE):
        e.at(104, "expoOut", y=e.kf["y"].k[0][1] + 300)

    # ---------------- bar 26-28: one eye, the mudra, the domain clash
    G.bgc(104, (8, 10, 16))
    s = sh(104, 105, cam=[(105, 1.1, 0, 0, "linear")])
    eye(s, 200, 40, 360, 110, CYAN, (90, 110, 140), 7, 10)
    hair(s, 100, 470, 14, 300, 30, (40, 50, 70), (10, 22), 255, 0, seed=22)
    G.bgc(105, (60, 26, 32))
    s = sh(105, 108, cam=[(108, 1.1, 0, 0, "linear")])
    G.bgc(107, (22, 10, 14), 0.5)
    glow(s, 0, 0, 1400, PINK, 120, -20)
    mudra_hands = [((-40, -330), (-150, 60)), ((-150, 60), (0, 260)), ((40, -330), (150, 60)), ((150, 60), (0, 260)),
                   ((-150, 60), (150, 60)), ((-90, -120), (90, -120))]
    poly_list(s, mudra_hands, 10, PALE, 255, 0)
    red_eyes(s, 0, 250, 0.9, 255, 10)
    G.bgc(108, (28, 18, 40))
    s = sh(108, 113, cam=[(113, 1.14, 60, 0, "sineIn")])
    focus(s, 320, 60, 3000, PINK, 200, -30, 0, 18)
    focus(s, 320, 60, 2600, CYAN, 130, -29, 40, 10)
    shrine(s, 330, 30, 0.95, RED, 8, 255, -10)
    glow(s, 330, 60, 900, RED, 140, -35)
    figure(s, -520, -470, 640, INK, 255, 0, rim=CYAN)
    hair(s, -520, 170, 12, 160, 70, PALE, (10, 20), 255, 1, seed=23, down=False)
    glow(s, -520, 100, 700, CYAN2, 150, -5)
    embers(s, PINK, 30, 108, 113, seed=24)
    G.shake(108, 18, 1.2, 0.4)
    G.flash(108, PINK, 150, 0.5)

    # ---------------- bar 28.1-29.0: black sphere, black flash
    G.bgc(113, (70, 34, 46))
    s = sh(113, 115, cam=[(115, 1.15, 0, 0, "expoIn")])
    focus(s, 0, 0, 2600, PINK, 230, -20, 0, 60)
    d = disc(s, 0, 0, 90, INK, 255, 0)
    d.at(115, "expoIn", w=560, h=560)
    r_ = ring(s, 0, 0, 100, PINK, 255, 1)
    r_.at(115, "expoIn", w=600, h=600)
    G.bgc(115, (44, 30, 44))
    s = sh(115, 117, cam=[(117, 1.06, 0, 0, "linear")])
    disc(s, 0, -60, 460, INK, 255, 0)
    for k in range(7):
        a = math.radians(30 + k * 20 + R.uniform(-5, 5))
        bolt(s, (math.cos(a) * 300, -60 + math.sin(a) * 300), (math.cos(a) * 900, -60 + math.sin(a) * 700), PAPER, 116, 1.0, seed=40 + k, thick=6, n=7, glow_d=0)
    G.black(F(115) + F(25, 32), 116)
    G.flash(116, WHITE, 230, 0.3)
    G.shake(116, 26, 2.0, 0.4)
    G.bgc(117, (20, 24, 30))
    s = sh(117, 118)
    hair(s, 0, 520, 20, 560, 60, PAPER, (12, 28), 255, 0, seed=25)
    G.shake(117, 10, 0.6)

    # ---------------- bar 29.2-31.0: slashes across the face
    G.letterbox(118, True)
    G.bgc(118, (44, 64, 86))
    s = sh(118, 124, cam=[(124, 1.12, 0, 10, "linear")])
    face_lines(s, 0, 40, 1.25, PALE, 7, 230, -10)
    hair(s, 0, 470, 18, 300, 40, PALE, (10, 22), 230, -9, seed=26)
    eye(s, 120, 100, 280, 80, CYAN, PALE, 6, 0)
    eye(s, -200, 100, 280, 80, CYAN, PALE, 6, 0)
    for k, (b, y0) in enumerate(((118, 140), (F(119) + F(1, 2), 20), (120, -120), (122, 60))):
        s.line(-60, y0, -28, 0.0, 14, RED, 255, 20, start=b).at(b + 0.15, "expoOut", w=820).at(124, "linear", h=10)
        G.shake(b, 12, 0.6)
    G.bgc(124, (44, 64, 86))
    s = sh(124, 125)
    glow(s, -100, 100, 300, CYAN, 255, 10)
    fingers(s, 240, -80, 1.0, PALE, 7, 255, 0)
    smile(s, -60, -150, 260, PALE, 7)

    # ---------------- bar 31.1-33.2: red impact, mudra in red/white, the shrine, the great eye
    G.letterbox(125, False)
    G.bgc(125, RED)
    s = sh(125, 126)
    disc(s, 0, -380, 360, INK, 255, 0)
    hair(s, 0, -40, 14, 320, 70, INK, (16, 30), 255, 1, seed=27, down=False)
    for k in range(3):
        slash(s, 0, R.uniform(-200, 200), 1600, R.uniform(10, 30), PAPER, 125 + k * 0.125, 0.75, 6, 40, 10)
    G.shake(125, 22, 1.6, 0.4)
    G.bgc(126, (238, 226, 230))
    s = sh(126, 129, cam=[(129, 1.08, 0, 0, "linear")])
    rect(s, 0, 0, 2400, 380, RED, 255, -20, 30.0)
    rect(s, 200, 300, 2400, 90, WHITE, 255, -19, 30.0)
    poly_list(s, mudra_hands, 11, INK, 255, 0)
    red_eyes(s, 0, 250, 0.9, 255, 10)
    G.bgc(129, RED)
    s = sh(129, 131, cam=[(131, 1.1, 0, 0, "linear")])
    shrine(s, 0, -20, 1.25, INK, 14, 255, 0)
    for k in range(14):
        spike_from(s, (R.uniform(-800, 800), -470), 90 + R.uniform(-30, 30), R.uniform(200, 520), R.uniform(40, 100), INK, 255, 1)
    for k in range(8):
        s.seg((R.uniform(-800, 800), 470), (R.uniform(-800, 800), -470), R.uniform(8, 20), INK, 255, 2)
    G.shake(129, 20, 1.4, 0.4)
    G.shake(130, 14, 1.0)
    G.bgc(131, PAPER)
    s = sh(131, 135, cam=[(135, 1.05, 0, 0, "linear")])
    rect(s, -400, 0, 900, 1100, RED, 255, -20, 8.0)
    eye(s, -380, 40, 560, 240, INK, INK, 12, 10, pupil=PAPER, glow_a=0, iris_r=0.4)
    for k in range(5):
        s.seg((-820 + k * 55, 470), (-760 + k * 40, -470), R.uniform(12, 30), INK, 255, 5)
    hair(s, 420, 470, 10, 340, 30, (60, 60, 70), (10, 20), 255, 0, seed=28)
    G.shake(131, 12, 0.8)

    # ---------------- bar 33.3-36.0: the barrier, the exchange, split screen
    G.bgc(135, (8, 18, 28))
    s = sh(135, 137, cam=[(137, 1.08, 0, 0, "linear")])
    ring(s, 0, -380, 520, CYAN, 255, 10)
    glow(s, 0, -380, 1300, CYAN2, 150, -10)
    figure(s, 0, -330, 520, INK, 255, 0, rim=PALE)
    embers(s, CYAN, 30, 135, 137, seed=29)
    G.bgc(137, (16, 22, 34))
    for b, kind in ((137, "cyan"), (138, "both"), (139, "cyan")):
        s = sh(b, b + 1)
        figure(s, -200, -470, 600, INK, 255, -10, rim=CYAN if kind == "cyan" else RED)
        if kind == "both":
            streak(s, (-800, 200), (100, -40), CYAN, b, 0.9, 150, 16)
            streak(s, (800, -260), (100, -40), RED, b, 0.9, 150, 16)
        else:
            streak(s, (-800, -200), (600, 120), CYAN, b, 0.9, 170, 18)
        G.shake(b, 12, 0.8)
    G.bgc(140, PAPER)
    s = sh(140, 141)
    for k in range(7):
        slash(s, R.uniform(-300, 300), R.uniform(-260, 260), 1900, R.uniform(-15, 15), INK if k % 3 else RED, 140 + k * 0.0625, 0.9, R.uniform(14, 40), 40, 10)
    G.shake(140, 18, 1.2)
    G.bgc(141, (30, 34, 44))
    for b in (141, 142, 143):
        s = sh(b, b + 1)
        figure(s, (b - 142) * 260, -470, 560, INK, 255, -10, rim=PALE)
        slash(s, 0, R.uniform(-150, 150), 2000, R.uniform(-30, 30), PAPER, b, 0.8, 12, 120, 10)
        G.shake(b, 10, 0.6)
    s = sh(144, 145)
    G.bgc(144, INK)
    split(s, 70, (40, 70, 110), (64, 18, 24))
    eye(s, -320, 60, 300, 90, CYAN, PALE, 6, 10)
    red_eyes(s, 360, 40, 0.7, 255, 10)
    G.shake(144, 16, 1.0)
    G.bgc(145, INK)

    # ---------------- bar 36.2-38.2: the graphic mudras (cyan, red, inverted)
    G.bgc(146, INK)
    s = sh(146, 149, cam=[(149, 1.08, 0, 0, "linear")])
    for k in range(9):
        spike_from(s, (-560 + R.uniform(-80, 80), 470), -90 + R.uniform(-50, 50), R.uniform(300, 560), R.uniform(80, 150), CYAN, 255, -10)
    disc(s, 520, -80, 300, CYAN, 255, -10)
    eye(s, -260, 0, 340, 150, INK, PAPER, 9, 10, pupil=INK, glow_a=0, iris_r=0.4)
    poly_list(s, [((p[0] * 0.8 + 150, p[1] * 0.8 - 60), (q[0] * 0.8 + 150, q[1] * 0.8 - 60)) for p, q in mudra_hands], 9, PAPER, 255, 5)
    eye(s, 520, -40, 200, 70, PAPER, INK, 7, 12, pupil=INK, glow_a=0)
    G.bgc(149, INK)
    s = sh(149, 150)
    for k in range(12):
        spike_from(s, (R.uniform(-800, 800), R.uniform(-450, 450)), R.uniform(0, 360), R.uniform(200, 600), R.uniform(40, 120), CYAN if k % 2 else PAPER, 255, -10)
    eye(s, -200, 0, 380, 160, INK, PAPER, 10, 10, pupil=INK, glow_a=0, iris_r=0.4)
    G.shake(149, 14, 1.0)
    G.bgc(150, INK)
    s = sh(150, 153, cam=[(153, 1.1, 0, 0, "linear")])
    for side in (-1, 1):
        for k in range(4):
            spike_from(s, (side * 820, -300 + k * 200), 90 + side * 90 + R.uniform(-8, 8), 520, 220, RED, 255, -20)
        eye(s, side * 470, 80, 260, 90, RED, PAPER, 8, 10, pupil=INK, glow_a=60)
    spike(s, -95, -40, 980, 300, 78, INK, 255, -5)
    spike(s, 95, -40, 980, 300, 102, INK, 255, -5)
    for side in (-1, 1):
        s.seg((side * 20, 420), (side * 230, -470), 7, PAPER, 255, 0)
        s.seg((side * 70, 300), (side * 300, -470), 5, PAPER, 220, 0)
    rect(s, 0, 150, 1800, 26, RED, 255, -30, 0.0)
    G.shake(150, 14, 1.0)
    G.shake(152, 18, 1.2)
    G.bgc(153, INK)
    s = sh(153, 154)
    for side in (-1, 1):
        s.seg((side * 20, 420), (side * 230, -470), 6, PAPER, 255, 0)
        s.seg((side * 70, 300), (side * 300, -470), 4, PAPER, 220, 0)
        for k in range(3):
            s.seg((side * 820, -300 + k * 200), (side * 300, -300 + k * 200), 4, PAPER, 255, 0)
        eye(s, side * 470, 80, 260, 90, PAPER, PAPER, 5, 10, pupil=INK, glow_a=0)
    G.shake(153, 16, 1.0)
    G.bgc(154, INK)

    # ---------------- bar 38.3-40.0: the standoff in the street
    G.letterbox(155, True)
    G.bgc(155, SEPIA)
    s = sh(155, 161, cam=[(161, 1.22, 0, 20, "sineIn")])
    vx, vy = 0, 40
    for side in (-1, 1):
        for k in range(7):
            yy = -470 + k * 150
            s.seg((side * 820, yy * 1.4), (vx + side * 60, vy + (yy - vy) * 0.1), 3, (120, 84, 80), 200, -30)
        for k in range(6):
            x0 = side * (160 + k * 110)
            s.seg((x0, -470), (x0, 470), 2, (110, 76, 72), 160, -31)
    glow(s, 0, 40, 600, RED, 160, -40)
    figure(s, -260, -360, 330, INK, 255, 0, rim=PALE)
    figure(s, 260, -360, 340, INK, 255, 0, rim=RED)

    # ---------------- bar 40-42: bleeding eyes, charge, silhouettes, punch, the wheel on a figure
    G.letterbox(161, False)
    G.bgc(161, PAPER)
    s = sh(161, 163, cam=[(163, 1.08, 0, 0, "linear")])
    face_lines(s, 0, 40, 1.3, (60, 64, 76), 7, 255, -10)
    red_eyes(s, 0, 70, 1.1, 255, 10)
    for dx in (-165, 165):
        for k in range(3):
            s.line(dx + (k - 1) * 14, 70, 90, 0.0, 9 - k * 2, RED, 255, 9, start=161.25 + k * 0.125).at(162 + k * 0.125, "expoOut", w=230, y=-160)
    G.letterbox(163, True)
    G.bgc(163, (20, 30, 48))
    s = sh(163, 165)
    skyline(s, "skyline_far.png", -360, (34, 46, 70), 255, -40, 2800, 0, -100)
    glow(s, 320, -60, 520, CYAN, 255, 0)
    fingers(s, 420, -60, 1.0, PALE, 8, 255, 5)
    speed(s, CYAN, 80, 0, 900, 40, -1)
    G.letterbox(165, False)
    G.bgc(165, PAPER)
    s = sh(165, 167)
    for e in figure(s, -260, -160, 300, INK, 255, 0):
        e.at(167, "linear", x=e.kf["x"].k[0][1] + 60)
    for e in figure(s, 240, -100, 320, INK, 255, 0):
        e.at(167, "linear", x=e.kf["x"].k[0][1] - 60)
    streak(s, (-700, 300), (240, 40), CYAN, 166, 0.9, 120, 14)
    G.shake(166, 12, 0.8)
    G.letterbox(167, True)
    G.bgc(167, (16, 26, 40))
    s = sh(167, 169)
    streak(s, (-900, -40), (900, 60), CYAN, 167, 1.5, 300, 30)
    figure(s, -380, -470, 560, INK, 255, -10, rim=CYAN)
    G.shake(167, 20, 1.4, 0.4)
    G.bgc(169, (44, 12, 16))
    s = sh(169, 170)
    figure(s, 0, -470, 620, INK, 255, -10, rim=RED)
    glow(s, 0, -100, 900, RED, 160, -20)
    G.bgc(170, (40, 40, 52))
    s = sh(170, 172, cam=[(172, 1.06, 0, 0, "linear")])
    figure(s, 0, -470, 640, INK, 255, -10, rim=MIST)
    wheel(s, 0, 290, 120, PALE, [(170, 0, "linear"), (171, 45, "backOut")], 255, 5)

    # ---------------- bar 43-47: orbs, the big eye, red orb, fire
    for b, kind in ((172, "blue"), (173, "fire"), (174, "fire"), (175, "dark")):
        s = sh(b, b + 1)
        G.bgc(b, (14, 20, 32))
        if kind == "blue":
            streak(s, (-900, -200), (700, -100), CYAN2, b, 0.9, 120, 12)
            figure(s, 300, -200, 160, INK, 255, 0, rim=CYAN)
        elif kind == "fire":
            figure(s, -150, -470, 560, INK, 255, -10, rim=ORANGE)
            figure(s, 200, -470, 520, INK, 255, -10, rim=PALE)
            glow(s, 0, -60, 700, ORANGE, 200, -20)
            embers(s, EMBER, 18, b, b + 1, seed=b)
            G.shake(b, 14, 1.0)
        else:
            disc(s, 0, 0, 600, (24, 30, 44), 255, -20)
    G.bgc(176, NAVY)
    s = sh(176, 178, cam=[(178, 1.06, -40, 0, "linear")])
    skyline(s, "skyline_near.png", -470, INK, 255, -30, 2800, 0, -120)
    glow(s, 420, 140, 700, CYAN2, 255, -10)
    glow(s, 420, 140, 200, WHITE, 255, -9)
    ring(s, 420, 140, 260, PALE, 200, -8)
    figure(s, -60, 60, 140, INK, 255, 0, rim=PALE)
    G.bgc(178, (12, 16, 24))
    s = sh(178, 179, cam=[(179, 1.12, 0, 0, "linear")])
    eye(s, 0, 0, 1100, 330, CYAN, PALE, 12, 10)
    s = sh(179, 180)
    eye(s, -260, 20, 420, 130, CYAN, PALE, 8, 10)
    eye(s, 260, 20, 420, 130, CYAN, PALE, 8, 10)
    G.bgc(180, (44, 8, 12))
    s = sh(180, 184, cam=[(184, 1.1, 0, 0, "linear")])
    figure(s, -260, -470, 640, INK, 255, -10, rim=RED)
    glow(s, 320, 60, 520, RED, 255, -5)
    ring(s, 320, 60, 110, (255, 180, 160), 255, -4)
    embers(s, EMBER, 34, 180, 184, seed=31)
    streak(s, (-900, 260), (900, -120), RED, 183, 0.9, 120, 14)
    G.shake(182, 10, 0.6)
    G.shake(183, 14, 1.0)
    G.bgc(184, (30, 10, 14))
    s = sh(184, 186)
    skyline(s, "skyline_near.png", -470, INK, 255, -30, 2800)
    o = glow(s, -200, 120, 900, RED, 255, -20)
    o.at(185, "linear", alpha=255).at(F(185) + F(1, 8), "expoOut", x=280, y=40, w=300, h=300)
    G.bgc(186, (90, 34, 10))
    s = sh(186, 187)
    glow(s, 0, 0, 1700, ORANGE, 255, -20)
    for k in range(12):
        spike_from(s, (0, -100), 30 + k * 10 + R.uniform(-5, 5), R.uniform(300, 700), R.uniform(40, 100), (255, 200, 120), 255, 0, 186, 187)
    G.flash(186, ORANGE, 200, 0.4)
    G.shake(186, 22, 1.6, 0.4)
    G.bgc(187, (40, 34, 36))
    s = sh(187, 188, cam=[(188, 1.1, 0, 0, "linear")])
    eye(s, 60, 0, 700, 220, CYAN, (140, 130, 130), 10, 10)
    for b in (188, 189, 190, 191):
        s = sh(b, b + 1)
        G.bgc(b, (40, 14, 10) if b < 190 else (16, 20, 30))
        if b < 190:
            glow(s, 0, 0, 1100, EMBER, 200, -20)
            streak(s, (-900, -300), (300, 100), CYAN, b, 0.9, 110, 12)
            figure(s, 200, -470, 520, INK, 255, -10, rim=ORANGE)
            embers(s, EMBER, 16, b, b + 1, seed=b)
        else:
            figure(s, -150, -470, 560, INK, 255, -10, rim=PALE)
            figure(s, 230, -470, 520, INK, 255, -10, rim=RED)
        G.shake(b, 12, 0.8)

    # ---------------- bar 48-50: THE WHEEL, reaching, falling
    G.letterbox(192, False)
    G.bgc(192, INK)
    s = sh(192, 193)
    wheel(s, 0, 0, 230, PAPER, [(192, -45, "linear"), (F(192) + F(1, 2), 0, "backOut")], 255, 10)
    G.flash(192, WHITE, 120, 0.3)
    G.shake(192, 20, 1.2)
    G.bgc(193, PAPER)
    s = sh(193, 196, cam=[(196, 1.06, 0, 0, "linear")])
    figure(s, 120, -470, 640, INK, 255, -10)
    s.seg((60, 0), (-460, 160), 26, INK, 255, -9)
    fingers(s, -460, 160, 0.9, INK, 8, 255, -8)
    G.letterbox(196, True)
    G.bgc(196, (20, 28, 40))
    s = sh(196, 203, cam=[(200, 1.35, 0, 0, "sineIn"), (203, 1.6, 0, 0, "linear")])
    for k in range(16):
        a = math.radians(k * 22.5 + 11)
        s.seg((math.cos(a) * 90, math.sin(a) * 60), (math.cos(a) * 1300, math.sin(a) * 900), 5, MIST, 180, -20)
    for k in range(6):
        r0 = 60 + k * 90
        poly(s, [(-r0 * 1.4, -r0), (r0 * 1.4, -r0), (r0 * 1.4, r0), (-r0 * 1.4, r0)], 3, STEEL, 200, -21, closed=True)
    for e in figure(s, 0, -60, 120, INK, 255, 0, rim=PALE):
        e.at(203, "linear", x=e.kf["x"].k[0][1] + 40)
    G.roll(196, 0)
    G.roll(203, 25, "sineInOut")
    spike(s, 300, 0, 1000, 500, 110, INK, 255, 10, start=202, end=203)

    # ---------------- bar 50.3-52.1: deep blue, the blue sphere
    G.roll(F(203) + F(1, 16), 0)
    G.bgc(203, (14, 30, 120))
    s = sh(203, 208, cam=[(208, 1.1, 0, 0, "linear")])
    glow(s, 360, 160, 600, BLUE, 255, -10)
    disc(s, 360, 160, 120, (30, 50, 200), 255, -9)
    ring(s, 360, 160, 130, CYAN, 230, -8)
    eye(s, -260, 60, 320, 100, CYAN, PALE, 7, 10)
    smile(s, -200, -160, 300, PALE, 7, start=205)
    fingers(s, 60, -120, 1.1, PALE, 8, 255, 5, start=205)
    G.bgc(208, (10, 20, 80))
    s = sh(208, 210, cam=[(210, 1.06, 0, 0, "linear")])
    skyline(s, "skyline_far.png", -360, (20, 40, 110), 255, -40, 2800, 0, -60)
    sph = disc(s, -280, 60, 260, (40, 70, 230), 230, -10)
    sph.at(209, "linear", x=-280).at(F(209) + F(1, 4), "expoOut", x=260, w=640, h=640)
    rg = ring(s, -280, 60, 270, CYAN, 255, -9)
    rg.at(209, "linear", x=-280).at(F(209) + F(1, 4), "expoOut", x=260, w=640 / 0.94, h=640 / 0.94)

    # ---------------- bar 52.2-55.0: smoke, cyan lightning, red embers, pointing up
    G.bgc(210, (62, 66, 74))
    s = sh(210, 212)
    for k in range(10):
        glow(s, R.uniform(-700, 700), R.uniform(-400, 300), R.uniform(400, 800), (120, 124, 132), 180, -20).at(212, "linear", x=R.uniform(-700, 700))
    figure(s, 0, -470, 600, INK, 255, -10)
    red_eyes(s, 0, 100, 0.5, 255, 10)
    G.letterbox(212, False)
    G.bgc(212, PAPER)
    s = sh(212, 214)
    for k in range(3):
        bolt(s, (-600 + k * 120, -450), (-420 + k * 90, 300), CYAN, 212 + k * 0.25, 1.5, seed=50 + k, thick=8)
    face_lines(s, 260, 40, 1.0, INK, 8, 255, -10)
    smile(s, 270, -150, 220, INK, 8)
    G.letterbox(214, True)
    G.bgc(214, (20, 10, 14))
    s = sh(214, 218)
    G.bgc(216, RED2)
    figure(s, 0, -470, 520, INK, 255, -10, rim=RED)
    embers(s, EMBER, 30, 215, 216, seed=60)
    embers(s, RED, 50, 216, 218, seed=61)
    glow(s, 0, 0, 1500, RED, 0, -30, start=216).at(216.25, "linear", alpha=200)
    G.bgc(218, (24, 34, 50))
    s = sh(218, 219)
    figure(s, 0, -470, 620, INK, 255, -10, rim=PALE)
    s.seg((60, 0), (220, 420), 24, INK, 255, -9)
    G.bgc(219, (20, 28, 40))
    s = sh(219, 221, cam=[(221, 1.3, 0, 0, "sineIn")])
    for k in range(16):
        a = math.radians(k * 22.5)
        s.seg((math.cos(a) * 80, math.sin(a) * 60), (math.cos(a) * 1300, math.sin(a) * 900), 4, MIST, 170, -20)
    figure(s, 0, -40, 110, INK, 255, 0, rim=PALE)

    # ---------------- bar 55.1-57: hollow purple
    G.bgc(221, (52, 46, 84))
    s = sh(221, 224, cam=[(224, 1.08, 0, 0, "linear")])
    skyline(s, "skyline_far.png", -360, (40, 34, 70), 255, -40, 2800)
    for color, x0 in ((CYAN2, -420), (RED, 420)):
        g = glow(s, x0, 60, 300, color, 255, 0)
        g.at(224, "quadIn", x=x0 * 0.35, w=420, h=420)
    figure(s, 0, -470, 520, INK, 255, -10, rim=(200, 160, 255))
    G.bgc(224, (90, 40, 160))
    s = sh(224, 228, cam=[(228, 1.18, 0, 0, "expoIn")])
    G.bgc(226, (70, 30, 150))
    orb = glow(s, 0, 80, 760, (200, 110, 255), 255, -10)
    orb.at(228, "expoIn", w=1700, h=1700)
    core = glow(s, 0, 80, 170, WHITE, 255, -9)
    core.at(228, "expoIn", w=700, h=700)
    fc = focus(s, 0, 80, 3200, (225, 170, 255), 90, -15, 0, 30)
    fc.at(228, "quadIn", alpha=230, w=2200, h=2200)
    for b in (224, 225, 226, 227):  # one pulse per beat, tightening towards the release
        rg = ring(s, 0, 80, 520 - (b - 224) * 80, PINK, 230, -8, start=b, end=b + 1)
        rg.at(b + 1, "expoIn", w=120, h=120, alpha=60)
    figure(s, 0, -470, 700, (30, 14, 50), 255, 0, start=226)
    glow(s, 30, 74, 120, CYAN, 255, 2, start=226)
    disc(s, 30, 74, 9, WHITE, 255, 3, start=226)
    G.flash(225, MAGENTA, 200, 0.5)
    for b in (224, 225, 226, 227):
        G.shake(b, 6 + (b - 224) * 4, 0.4)
    G.bgc(228, (230, 210, 255))
    s = sh(228, 229)
    glow(s, 0, 0, 2600, PURPLE, 255, -20)
    figure(s, 0, -470, 820, (50, 20, 80), 255, 0)
    glow(s, 34, 165, 130, CYAN, 255, 10)
    G.flash(228, WHITE, 255, 0.6)
    G.shake(228, 30, 2.2, 0.5)
    G.bgc(229, (70, 20, 120))
    s = sh(229, 232, cam=[(232, 1.08, 0, 0, "linear")])
    sun = glow(s, 0, 160, 600, WHITE, 255, -20)
    sun.at(232, "expoIn", w=2600, h=2600)
    glow(s, 0, 100, 1800, MAGENTA, 220, -21)
    focus(s, 0, 160, 3000, (240, 200, 255), 150, -15, 0, 20)
    skyline(s, "skyline_near.png", -470, (24, 6, 40), 255, -10, 2800)
    G.shake(229, 14, 1.0)
    G.shake(230, 10, 0.6)
    G.bgc(232, PAPER)
    s = sh(232, 236)
    glow(s, 0, -500, 1600, PURPLE, 200, -10).at(234, "linear", alpha=0)
    G.bgc(236, (180, 178, 186))
    G.bgc(237, (110, 106, 118))
    G.bgc(238, INK, 0.5)


def build(chart):
    G = Globals(chart)
    E = Engine(chart, G.root.index)
    storyboard(E, G)
    E.bake()
    G.emit(random.Random(7))
    # effects (post-processing)
    c = chart
    c.effect("vignette", 0, 240, {"extend": 0.2, "radius": 18.0})
    for b0, b1, p in ((4, 5, 0.008), (24, 25, 0.012), (29, 30, 0.01), (76, 78, 0.012), (125, 126, 0.012), (129, 131, 0.012),
                      (146, 150, 0.014), (150, 153, 0.012), (153, 154, 0.02), (228, 229, 0.015)):
        c.effect("chromatic", b0, b1, {"power": c.var_kfs([(b0, p, "quadOut"), (b1, p * 0.3, "linear")]), "sampleCount": 5.0})
    for b0, b1, p in ((64, 65, 0.03), (76, 77, 0.03), (96, 97, 0.03), (113, 115, 0.035), (116, 117, 0.04), (186, 187, 0.03), (228, 230, 0.05)):
        c.effect("radialBlur", b0, b1, {"power": c.var_kfs([(b0, p, "quadOut"), (b1, 0.0, "linear")]), "sampleCount": 10.0})
    for b in (4, 24, 64, 96, 116, 129, 192, 228):
        c.effect("shockwave", b, b + 1.5, {"progress": c.var_kfs([(b, 0.02, "quadOut"), (b + 1.5, 0.95, "linear")]),
                                           "width": 0.1, "distortion": 0.8, "expand": 10.0})
    for b0, b1 in ((149, 150), (153, 154), (116, 116.25)):
        c.effect("glitch", b0, b1, {"power": 0.05, "rate": 0.9, "speed": 18.0, "blockCount": 24.0, "colorRate": 0.015})
    # the seal: one tap on the final burst so Phira's accuracy is defined (0 notes -> 0/0). It is fully hidden:
    # alpha 0, its line parked far below the screen (the hit effect is emitted at the note, so it lands
    # off-screen) and a silent custom hitsound (prpr plays the note's hitsound on autoplay hits).
    seal = c.line("seal")
    for p, v in (("moveX", 0.0), ("moveY", -3000.0), ("rotate", 0.0), ("speed", 8.0)):
        seal.ev(p, 0, EPSB, v, v)
    seal.note(TAP, 228, 0.0, alpha=0)
    seal.notes[-1]["hitsound"] = SILENCE
    return E


def make():
    c = Chart(OFFSET_MS, dict(INFO, id="claude-mad-shinjuku"), bpm=BPM, compact=True)
    E = build(c)
    print(f"pooled lines: {E.line_count()}  shots: {len(E.shots)}  elements: {sum(len(s.elems) for s in E.shots)}")
    return c, INFO


def assets(out):
    import mad_assets
    mad_assets.make(out)
    ill = os.path.join(HERE, "..", "data", "mad", "illustration.jpg")
    if os.path.exists(ill):
        shutil.copy(ill, os.path.join(out, "illustration.jpg"))
    else:  # placeholder until the cover is rendered
        from PIL import Image
        Image.new("RGB", (1920, 1080), NAVY).save(os.path.join(out, "illustration.jpg"))
