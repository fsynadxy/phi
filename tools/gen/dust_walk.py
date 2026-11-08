"""走过漫漫时空 — a super-effects showcase chart for Phira, after Arknights SideStory 「遗尘漫步」.

The song (Monster Siren Records) runs at 160 BPM; bars start on beat 2 and phrases are 16 beats long.
The story of the event is Kal'tsit's long walk through three memories (Sargon, Ursus / Chernobog,
Victoria) that meet again at the excavated ark. The chart follows the music section by section:

    0-34    prelude    a point of light in the dark, a horizon line, footprints, the title      (漫漫独行)
    34-50   dawn       the sun rises behind the dunes
    50-90   Sargon     ruins and drifting sand, judge lines tilting with the dunes
    90-162  Passenger  chain lightning: the judge lines become a lightning chain, an eight-armed star, a storm
    162-178 rewind     a clock running backwards, the lines turn into its hands, the world collapses to a point
    178-194 Chernobog  snow and a heart monitor: every heartbeat is a note on the trace
    194-242 Victoria   rain, lancet windows, the ark rising from the earth
    242-290 journey    the memories meet: a rotating star of lines in four colours                (浩瀚之旅)
    290-306 stillness  time stops, everything dissolves into dust
    306-350 dawn       footprints into the distance, the title again, the line walks away

Beat k = beat k of the song (first beat at 0.0365 s).
"""
import math
import os
import random
import shutil

import numpy as np

import madlib as ML
import mad_shinjuku as MS
from chartlib import Chart, DRAG, EPSB, FLICK, HOLD, TAP, frac
from madlib import TL, Engine

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "dust")
BPM = 160.0
OFFSET_MS = 37
END = 350
F = MS.F
PX = ML.PX

INFO = {
    "name": "走过漫漫时空",
    "difficulty": 15.0,
    "level": "SP Lv.?",
    "charter": "Claude",
    "composer": "塞壬唱片-MSR",
    "illustrator": "Claude (procedural)",
    "chart": "chart.json",
    "format": "rpe",
    "music": "song.ogg",
    "illustration": "illustration.jpg",
    "previewStart": 90.0,
    "previewEnd": 110.0,
    "aspectRatio": 1.7777778,
    "backgroundDim": 0.6,
    "lineLength": 6.0,
    "offset": 0.0,
    "tip": "观赏谱 · 参考《明日方舟》SideStory「遗尘漫步」 · 建议开启 Autoplay 观看",
    "tags": ["观赏谱", "showcase", "autoplay", "明日方舟", "遗尘漫步"],
    "intro": "《走过漫漫时空》（明日方舟「遗尘漫步」OST）的特效观赏谱：萨尔贡的沙、异客的雷、切尔诺伯格的雪、维多利亚的雨，最后在方舟前汇合。",
    "holdPartialCover": False,
    "noteUniformScale": False,
    "forceAspectRatio": False,
    "useRpe170Speed": False,
    "useAttachUiFix": True,
}

ML.register_textures({
    "white.png": (64, 64), "glow.png": (256, 256), "disc.png": (256, 256), "ring.png": (512, 512),
    "beam.png": (1024, 64), "grad.png": (64, 512), "spike.png": (256, 1024), "focus.png": (1024, 1024),
    "dust.png": (2048, 1152), "snow.png": (1024, 1024), "rain.png": (1024, 1024), "dunes.png": (2048, 512),
    "ruins.png": (2048, 512), "ark.png": (2048, 512), "bolt_a.png": (1024, 256), "bolt_b.png": (1024, 256),
    "bolt_c.png": (1024, 256), "star8.png": (1024, 1024), "arch.png": (512, 1024), "footprint.png": (128, 256),
    "corner.png": (128, 128), "clock.png": (1024, 1024),
})


def text_size(name):
    from PIL import Image
    return Image.open(os.path.join(DATA, name)).size


for _t in ("t_title.png", "t_event.png", "t_walk.png", "t_ch1.png", "t_ch2.png", "t_sargon.png", "t_ursus.png",
           "t_victoria.png", "t_terra.png"):
    ML.TEXPX[_t] = text_size(_t)

# ------------------------------------------------------------------ palette
NIGHT = (6, 7, 12)
INK = (4, 5, 8)
PALE = (238, 232, 220)
WHITE = (255, 255, 255)
SAND = (214, 172, 112)
SANDD = (120, 84, 52)
GOLD = (255, 204, 120)
EMBER = (255, 132, 64)
DUSK = (236, 134, 80)
CYAN = (120, 228, 255)
ELEC = (190, 245, 255)
STORM = (14, 16, 34)
ICE = (176, 206, 232)
STEEL = (58, 70, 90)
MOSS = (54, 104, 78)
CRIM = (170, 32, 48)
RAIN = (150, 172, 196)
MON = (96, 255, 176)
VIOLET = (150, 120, 255)
LINE_W = (242, 236, 224)


def mix(a, b, t):
    return tuple(round(p + (q - p) * t) for p, q in zip(a, b))


# ------------------------------------------------------------------ music
class Music:
    def __init__(self):
        d = np.load(os.path.join(DATA, "steps.npz"))

        def n(a):
            return np.clip(a / (np.percentile(a, 98) + 1e-9), 0, 1.5)
        self.k, self.lm, self.sn, self.h, self.mel = (n(d[k]) for k in ("low_p", "lmid_p", "mid_p", "high_p", "mid_h"))
        self.n = len(self.k)

    def st(self, s):
        return float(max(self.k[s], self.lm[s], self.sn[s], self.h[s])) if 0 <= s < self.n else 0.0

    def acc(self, s):
        return float(0.6 * self.k[s] + 0.4 * self.sn[s]) if 0 <= s < self.n else 0.0

    def keep(self, s, dens):
        v = self.st(s)
        if s % 4 == 0:
            return v > 0.15
        if s % 2 == 0:
            return dens >= 2 and v > 0.25
        return {1: 9, 2: 9, 3: 0.85, 4: 0.62, 5: 0.3}[dens] < v

    def accents(self, b0, b1, th=0.75, gap=1.0, grid=2):
        """strong hits (on the 8th grid by default), at least `gap` beats apart"""
        out = []
        for s in range(round(b0 * 4), round(b1 * 4)):
            if s % grid or self.acc(s) < th:
                continue
            if out and s / 4 - out[-1] < gap:
                if self.acc(s) > self.acc(round(out[-1] * 4)):
                    out[-1] = F(s, 4)
                continue
            out.append(F(s, 4))
        return out


# ------------------------------------------------------------------ judge lines
P = {"x": "moveX", "y": "moveY", "rot": "rotate", "a": "alpha", "spd": "speed", "col": "color", "sx": "scaleX"}


class JL:
    def __init__(self, c, name, z, father, x=0.0, y=-250.0, rot=0.0, alpha=0.0, speed=8.0, color=LINE_W, sx=0.45):
        self.ln = c.line(name, z=z, father=father, rot_with_father=True)
        self.tl = {}
        for p, v in (("moveX", x), ("moveY", y), ("rotate", rot), ("alpha", alpha), ("speed", speed), ("color", color),
                     ("scaleX", sx)):
            v = tuple(v) if p == "color" else float(v)
            self.ln.ev(p, 0, EPSB, v, v)
            self.tl[p] = TL(self.ln, p, v)

    def at(self, b, **vals):
        b = frac(b)
        for k, v in vals.items():
            v = tuple(v) if k == "col" else float(v)
            t = self.tl[P[k]]
            if t.b == b + EPSB:
                tr = self.ln.tr(P[k])
                b0, b1, _, _, e = tr.segs[-1]
                tr.segs[-1] = (b0, b1, v, v, e)
                t.v = v
            else:
                t.jump(b, v)
        return self

    def to(self, b0, b1, ease="linear", **vals):
        for k, v in vals.items():
            t = self.tl[P[k]]
            if frac(b0) < t.b - EPSB:
                raise ValueError(f"{self.ln.name}.{P[k]}: animation from {float(b0)} overlaps one ending {float(t.b)}")
            t.wait(b0)
            t.to(b1, tuple(v) if k == "col" else float(v), ease)
        return self

    def v(self, k):
        return self.tl[P[k]].v


# ------------------------------------------------------------------ notes
def zig(cx=300, amp=110, period=4, ph=0.0):
    return lambda h, b, i: (-1 if h == 0 else 1) * cx + amp * math.sin(2 * math.pi * float(b) / period + ph + h * math.pi)


def stair(lo=110, hi=520, n=4, parallel=True):
    def f(h, b, i):
        k = i % (2 * n - 2)
        k = k if k < n else 2 * n - 2 - k
        d = (hi - lo) * k / (n - 1)
        if h == 0:
            return -hi + d if parallel else -(lo + d)
        return lo + d
    return f


def drift(b0, b1, c0, c1, gap=300, amp=50):
    def f(h, b, i):
        t = (float(b) - b0) / max(1e-9, b1 - b0)
        return c0 + (c1 - c0) * t + (-1 if h == 0 else 1) * gap / 2 + amp * math.sin(i * 1.9 + h)
    return f


def trill(w=150, c=0.0):
    return lambda h, b, i: c + (-w if h == 0 else w)


class Notes:
    def __init__(self, music):
        self.m = music
        self.items = []

    def add(self, jl, b, x, kind=TAP, end=None, above=True, fake=False, speed=1.0, alpha=255):
        b = frac(b)
        self.items.append((jl, b, round(float(x), 1), kind, frac(end) if end is not None else None, above, fake, speed, alpha))

    def stream(self, jl, b0, b1, shape, dens=2, chords=2, flicks=0.3, seed=0, drag_off=False, above=True, skip=(),
               lines=None, ab=None):
        """the song's rhythm at density dens, alternating hands. lines: cycle the notes over several judge lines;
        ab: alternate `above` per note."""
        R = random.Random(seed)
        hand, cnt, k = 0, [0, 0], 0
        skip = {frac(b) for b in skip}
        for s in range(round(float(b0) * 4), round(float(b1) * 4)):
            b = frac(s, 4)
            if b in skip or not self.m.keep(s, dens):
                continue
            ln = lines[k % len(lines)] if lines else jl
            up = (k % 2 == 0) if ab else above
            k += 1
            if s % 4 == 0 and chords and (s // 4) % chords == 0 and self.m.k[s] > 0.5:
                for h in (0, 1):
                    self.add(ln, b, shape(h, b, cnt[h]), TAP, above=up)
                    cnt[h] += 1
                hand = 1 - hand
                continue
            kind = TAP
            if s % 8 == 4 and self.m.sn[s] > 0.6 and R.random() < flicks:
                kind = FLICK
            elif drag_off and s % 2 == 1:
                kind = DRAG
            elif drag_off and s % 4 == 2:
                kind = DRAG
            self.add(ln, b, shape(hand, b, cnt[hand]), kind, above=up)
            cnt[hand] += 1
            hand = 1 - hand

    def write(self):
        n = 0
        for jl, b, x, kind, e, above, fake, speed, alpha in self.items:
            jl.ln.note(kind, b, x, end=e, above=above, speed=speed, alpha=alpha, fake=fake)
            n += 0 if fake else 1
        return n


# ------------------------------------------------------------------ scene globals (+ a sky gradient)
class Scene(MS.Globals):
    HIDE_HUD = False

    def __init__(self, c):
        super().__init__(c)
        self.sky = c.line("sky", texture="grad.png", z=-95)
        for p, v in (("moveX", 0.0), ("moveY", 0.0), ("rotate", 0.0), ("scaleX", 1800 / (64 * ML.TEXK)),
                     ("scaleY", 1000 / (512 * ML.TEXK)), ("alpha", 0.0)):
            self.sky.ev(p, 0, EPSB, v, v)
        self.sky.ev("color", 0, EPSB, NIGHT, NIGHT)
        self.sched["sky"] = []
        self.fx = []

    def skyc(self, b, color, alpha, fade=0.0, ease="sineInOut"):
        self.sched["sky"].append((F(b), color, float(alpha), F(fade), ease))

    def emit(self, R):
        super().emit(R)
        col, a = TL(self.sky, "color", NIGHT), TL(self.sky, "alpha", 0.0)
        for b, c_, al, fade, ease in sorted(self.sched["sky"], key=lambda e: e[0]):
            if fade > 0:
                col.wait(b)
                col.to(b + fade, c_, ease)
                a.wait(b)
                a.to(b + fade, al, ease)
            else:
                col.jump(b, c_)
                a.jump(b, al)


# ------------------------------------------------------------------ motifs
glow, disc, ring, spike, spike_from, rect = MS.glow, MS.disc, MS.ring, MS.spike, MS.spike_from, MS.rect


def dust(s, color, a, w=2000, x0=0.0, x1=0.0, y0=0.0, y1=0.0, rot=0.0, z=-30, start=None, end=None, a_in=None, w1=None):
    st = F(start) if start is not None else s.b0
    en = F(end) if end is not None else s.b1
    e = s.tex("dust.png", x0, y0, w, None, rot, color, 0 if a_in else a, z, st, en)
    if a_in:
        e.at(st + F(a_in), "sineOut", alpha=a)
    e.at(en, "linear", x=x1, y=y1, **({"w": w1, "h": w1 * 1152 / 2048} if w1 else {}))
    return e


def scroll(s, tex, color, a, w, speed, z, start=None, end=None, rot=0.0, axis="y"):
    """an endless layer (snow, rain, blown sand): two copies of a texture scrolling `speed` units per beat
    along `axis` (negative = down / left), looping every texture length."""
    st = F(start) if start is not None else s.b0
    en = F(end) if end is not None else s.b1
    pw, ph = ML.TEXPX[tex]
    h = w * ph / pw
    L = h if axis == "y" else w
    period = F(round(L / abs(speed) * 16), 16)
    sgn = 1 if speed > 0 else -1
    els = []
    for k in range(2):
        p0 = -sgn * k * L
        kw = {"y": p0} if axis == "y" else {"x": p0}
        e = s.tex(tex, kw.get("x", 0.0), kw.get("y", 0.0), w, h, rot, color, a, z, st, en)
        b = st
        while b < en:
            b1 = min(en, b + period)
            frac_ = float((b1 - b) / period)
            e.at(b1, "linear", **{axis: p0 + sgn * L * frac_})
            if b1 < en:
                e.at(b1, "linear", **{axis: p0})
            b = b1
        els.append(e)
    return els


def ripple(s, b, x, y, r0, r1, color, a=255, z=20, dur=1.0, thick=False):
    e = ring(s, x, y, r0, color, a, z, b, F(b) + F(dur))
    e.at(F(b) + F(dur), "expoOut", w=2 * r1 / 0.94, h=2 * r1 / 0.94, alpha=0)
    return e


BOLTS = ("bolt_a.png", "bolt_b.png", "bolt_c.png")


def strike(s, b, x, y, length, ang, color, k=0, z=40, dur=F(1, 2), thick=None):
    """a lightning bolt texture flashing at beat b (ang: degrees CCW)"""
    b = F(b)
    h = thick or length * 0.18
    e = s.tex(BOLTS[k % 3], x, y, length, h, -ang, color, 255, z, b, b + F(dur))
    e.at(b + F(dur) * F(1, 4), "linear", alpha=90).at(b + F(dur) * F(3, 8), "linear", alpha=255).at(b + F(dur), "quadIn", alpha=0)
    return e


def footprint(s, b, x, y, ang, size, color, a=200, z=5, life=4):
    b = F(b)
    e = s.tex("footprint.png", x, y, size * 0.5, size, -ang, color, 0, z, b, b + F(life))
    e.at(b + F(1, 8), "expoOut", alpha=a).at(b + F(life), "quadIn", alpha=0)
    return e


def label(s, tex, x, y, w, b0, b1, color=PALE, a=220, z=60):
    """a HUD caption with corner brackets"""
    b0, b1 = F(b0), F(b1)
    t = s.tex(tex, x, y, w, None, 0.0, color, 0, z, b0, b1)
    t.at(b0 + F(1, 2), "expoOut", alpha=a).at(b1 - F(1), "linear", alpha=a).at(b1, "quadIn", alpha=0)
    pw, ph = ML.TEXPX[tex]
    h = w * ph / pw
    for sx_, sy_, r in ((-1, 1, 0.0), (1, -1, 180.0)):
        c = s.tex("corner.png", x + sx_ * (w / 2 + 30), y + sy_ * (h / 2 + 22), 46, 46, r, color, 0, z, b0, b1)
        c.at(b0 + F(1, 2), "expoOut", alpha=a, x=x + sx_ * (w / 2 + 18)).at(b1 - F(1), "linear", alpha=a).at(b1, "quadIn", alpha=0)
    return t


def claws(s, b, x, y, ang, length, color, z=45, dur=F(3, 4)):
    b = F(b)
    els = []
    for k in (-1, 0, 1):
        ox, oy = -math.sin(math.radians(ang)) * 70 * k, math.cos(math.radians(ang)) * 70 * k
        e = spike(s, x + ox, y + oy, length, 46, ang, color, 255, z, b, b + F(dur))
        e.at(b + F(dur), "quadIn", alpha=0, h=length * 1.15)
        els.append(e)
    return els


# ================================================================== the storyboard
class Ctx:
    pass


def build(c):
    m = Music()
    G = Scene(c)
    E = Engine(c, G.root.index)
    N = Notes(m)
    root = G.root.index
    L = Ctx()
    L.A = JL(c, "line_a", 110, root, y=-120, sx=0.0, color=LINE_W)
    L.B = JL(c, "line_b", 111, root, y=240, rot=180, sx=0.45)
    L.C1 = JL(c, "line_c1", 112, root, y=0, sx=0.45)
    L.C2 = JL(c, "line_c2", 113, root, y=0, sx=0.45)
    L.C3 = JL(c, "line_c3", 114, root, y=0, sx=0.45)
    R = random.Random(2021)
    G.bgc(EPSB, NIGHT)
    fx = []

    def effect(name, b0, b1, **vars_):
        fx.append((name, b0, b1, vars_))

    def kf(*pts):
        return c.var_kfs([(b, v, e) for b, v, e in pts])

    sh = E.shot
    A, B, C1, C2, C3 = L.A, L.B, L.C1, L.C2, L.C3

    # ============ prelude (0-34): a point of light, the horizon, footprints, the title  -- 漫漫独行
    s = sh(0, 34, cam=[(34, 1.05, 0, 0, "linear")])
    dust(s, SAND, 120, 2000, 60, -80, 0, 10, start=2, a_in=8, z=-30)
    dust(s, PALE, 70, 2700, -60, 90, 40, -20, rot=180, start=2, a_in=10, z=-29)
    glow(s, 0, -120, 360, EMBER, 255, 20, 2, 6).at(6, "quadIn", alpha=0, w=900, h=900)
    glow(s, 0, -120, 90, WHITE, 255, 21, 2, 4).at(4, "quadIn", alpha=0)
    ripple(s, 2, 0, -120, 20, 700, GOLD, 220, 22, 2)
    G.flash(2, GOLD, 70, 1)
    A.at(2, a=255).to(2, 8, "quartOut", sx=0.45)
    t = s.tex("t_event.png", 0, 260, 300, None, 0.0, GOLD, 0, 50, 8, 22)
    t.at(10, "sineOut", alpha=200).at(18, "linear", alpha=200).at(22, "sineIn", alpha=0, y=290)
    t = s.tex("t_title.png", 0, 150, 920, None, 0.0, PALE, 0, 51, 8, 22)
    t.at(10, "sineOut", alpha=255, w=880, h=880 * ML.TEXPX["t_title.png"][1] / ML.TEXPX["t_title.png"][0])
    t.at(18, "linear", alpha=255).at(22, "sineIn", alpha=0, y=200)
    t = s.tex("t_walk.png", 0, 40, 560, None, 0.0, SAND, 0, 50, 9, 22)
    t.at(11, "sineOut", alpha=190).at(18, "linear", alpha=190).at(22, "sineIn", alpha=0, y=70)
    for b in (22, 30):
        ripple(s, b, 0, -120 if b < 18 else -250, 40, 600, SAND, 160, 22, 2)
    # footsteps: the line is the ground, the notes are the steps
    steps = [b for b in (4, 6, 8, 10, 12, 14, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, F(61, 2), 31, F(63, 2), 32, F(65, 2), 33, F(67, 2))]
    for k, b in enumerate(steps):
        t_ = (float(b) - 4) / 30
        cx = -460 + 920 * t_
        x = cx + (-50 if k % 2 == 0 else 50)
        y_line = -120 if b < 18 else -250
        N.add(A, b, x, TAP if k % 6 != 5 else FLICK)
        footprint(s, b, x / PX, y_line + 40, -8 if k % 2 == 0 else 8, 60, SAND, 170, 5, 6)
    A.to(18, 22, "sineInOut", y=-250)
    G.skyc(18, DUSK, 0)
    G.skyc(18.5, DUSK, 120, 15.5)
    d = s.tex("dunes.png", 0, -760, 2600, None, 0.0, (34, 22, 20), 255, -40, 18, 34)
    d.at(34, "sineOut", y=-300)
    G.bgc(18, (16, 10, 14), 16, "sineInOut")

    # ============ dawn (34-50): the sun rises behind the dunes
    s = sh(34, 50, cam=[(50, 1.04, 0, 0, "linear")])
    G.skyc(34, (255, 168, 92), 190, 16)
    G.bgc(34, (44, 24, 22), 16, "sineInOut")
    glow(s, 260, -330, 900, EMBER, 255, -48).at(50, "sineOut", y=-40)
    disc(s, 260, -330, 70, (255, 236, 200), 255, -47).at(50, "sineOut", y=-40)
    s.tex("dunes.png", 0, -300, 2600, None, 0.0, (34, 22, 20), 255, -40).at(50, "linear", x=-120)
    dust(s, SAND, 130, 2000, 80, -200, 0, 0, z=-30)
    dust(s, GOLD, 80, 2800, -100, 200, 20, 0, rot=180, z=-29)
    label(s, "t_sargon.png", -520, 320, 250, 36, 46, GOLD)
    N.stream(A, 34, 42, zig(280, 90, 4), dens=2, chords=4, seed=1)
    B.at(41, a=0).to(41, 42, "quadOut", a=230)
    for k, b0 in enumerate(range(42, 48, 2)):
        N.stream(B if k % 2 else A, b0, b0 + 2, zig(260, 80, 2), dens=2, chords=2, seed=2 + k)
    N.stream(A, 48, 50, stair(120, 480, 4), dens=4, chords=0, seed=5)
    B.to(48, 49, "quadIn", a=0)

    # ============ Sargon (50-90): ruins, drifting sand, lines tilting with the dunes
    G.flash(50, GOLD, 150, 1.5)
    G.shake(50, 14, 0.8, 0.4)
    G.skyc(50, (255, 186, 110), 200, 2)
    G.bgc(50, (64, 38, 26), 2)
    s = sh(50, 82, cam=[(82, 1.08, 0, 0, "linear")])
    glow(s, 300, 140, 1200, GOLD, 200, -48)
    disc(s, 300, 140, 64, (255, 244, 220), 255, -47)
    s.tex("ruins.png", 260, -250, 2800, None, 0.0, (58, 34, 26), 255, -42).at(82, "linear", x=-260)
    s.tex("dunes.png", 0, -340, 2800, None, 0.0, (78, 50, 34), 255, -38).at(82, "linear", x=-200)
    dust(s, SAND, 150, 2000, 200, -400, 0, -30, z=-30)
    dust(s, GOLD, 110, 2600, -150, -700, 10, 0, rot=180, z=-29)
    scroll(s, "rain.png", SAND, 70, 1100, -260, -28, rot=-82.0, axis="x")
    for b in m.accents(50, 82, 0.95, 4):
        ripple(s, b, R.uniform(-500, 500), R.uniform(-150, 250), 10, 260, GOLD, 140, -10, 1.5)
    for b in range(50, 82, 4):  # heat shimmer: a slight colour split on every bar
        effect("chromatic", b, b + 1, power=kf((b, 0.006, "quadOut"), (b + 1, 0.0, "linear")), sampleCount=4.0)
    for k, b0 in enumerate(range(50, 66, 8)):
        A.to(b0, b0 + 8, "sineInOut", rot=(6, -6)[k % 2])
        N.stream(A, b0, b0 + 8, zig(300, 120, 4), dens=2, chords=2, drag_off=True, seed=10 + k)
    A.to(66, 68, "sineInOut", rot=0)
    B.at(65, rot=180).to(65, 66, "quadOut", a=230, y=220)
    for k, b0 in enumerate(range(66, 82, 4)):
        tilt = (5, -5)[k % 2]
        A.to(b0, b0 + 4, "sineInOut", rot=tilt) if k else None
        B.to(b0, b0 + 4, "sineInOut", rot=180 + tilt)
        N.stream(A, b0, b0 + 2, zig(280, 90, 2), dens=2, chords=2, seed=20 + k)
        N.stream(B, b0 + 2, b0 + 4, zig(280, 90, 2), dens=2, chords=2, seed=30 + k)
    # 82-90: rising
    s = sh(82, 90, cam=[(90, 1.25, 0, 0, "expoIn")])
    G.bgc(82, (90, 52, 30), 8, "quadIn")
    glow(s, 300, 140, 1400, GOLD, 220, -48).at(90, "expoIn", w=2600, h=2600)
    s.tex("ruins.png", -260, -250, 2800, None, 0.0, (58, 34, 26), 255, -42)
    dust(s, SAND, 170, 2000, -400, -900, -30, -30, z=-30)
    A.to(82, 90, "sineInOut", y=-150, rot=0, spd=9)
    B.to(82, 90, "sineInOut", y=150, rot=180, spd=9)
    N.stream(A, 82, 86, zig(260, 100, 2), dens=3, chords=2, seed=40)
    N.stream(B, 86, 88, zig(260, 100, 2), dens=3, chords=2, seed=41)
    N.stream(A, 88, 90, stair(100, 520, 5), dens=5, chords=0, seed=42)
    effect("radialBlur", 87, 90, power=kf((87, 0.0, "quadIn"), (90, 0.04, "linear")), sampleCount=10.0)

    # ============ Passenger (90-162): chain lightning
    G.flash(90, ELEC, 230, 1.5)
    G.shake(90, 24, 1.6, 0.5)
    G.bgc(90, STORM)
    G.skyc(90, (70, 80, 160), 110, 1)
    s = sh(90, 162)
    st8 = s.tex("star8.png", 0, 0, 1150, 1150, 0.0, CYAN, 55, -45)
    st8.at(162, "linear", rot=-90)
    s.tex("ruins.png", 0, -250, 2800, None, 0.0, (10, 12, 26), 255, -42).at(162, "linear", x=-300)
    scroll(s, "rain.png", (190, 160, 120), 60, 1200, -520, -28, rot=-85.0, axis="x")  # the sandstorm
    dust(s, (190, 170, 140), 120, 2000, 300, -2600, 0, 40, z=-30)
    hits = m.accents(90, 162, 0.85, 1.5)
    for k, b in enumerate(hits):
        strike(s, b, R.uniform(-200, 200), R.uniform(-200, 260), 1900, R.uniform(-25, 25), ELEC, k, 35)
        G.flash(b, CYAN, 70, 0.25)
        effect("chromatic", b, b + F(1, 2), power=kf((b, 0.014, "quadOut"), (b + F(1, 2), 0.0, "linear")), sampleCount=5.0)
    for b in sorted(set(range(90, 162, 4)) | {116}):
        big = b in (90, 98, 114, 116, 130, 146)
        effect("shockwave", b, b + F(3, 2), progress=kf((b, 0.02, "quadOut"), (b + F(3, 2), 0.95, "linear")),
               width=0.1 if big else 0.06, distortion=0.8 if big else 0.4, expand=10.0)
    effect("radialBlur", 90, 91, power=kf((90, 0.04, "quadOut"), (91, 0.0, "linear")), sampleCount=10.0)
    A.to(89, 90, "quadIn", a=0)
    B.to(89, 90, "quadIn", a=0)
    # (a) 90-98: three short lines in a zigzag: the chain, current running through it
    seg = 0.114
    chain0 = ((-420, 40, -25), (0, 40, 25), (420, 40, -25))
    for j, (x, y, r) in zip((C1, C2, C3), chain0):
        j.at(89, x=x, y=y, rot=r, sx=seg, col=ELEC, spd=7.5).to(89, 90, "quadOut", a=255)
    s = sh(90, 98)
    for b in range(90, 98):
        for j, (x, y, r) in enumerate(chain0):
            e = s.tex(BOLTS[(b + j) % 3], x / PX, y, 520, 90, float(r), CYAN, 230, 30, b, b + F(1, 2))
            e.at(b + F(1, 2), "quadIn", alpha=0)
    N.stream(C1, 90, 98, trill(120), dens=3, chords=0, seed=50, lines=[C1, C2, C3])
    # (b) 98-114: the eight-armed star turning through the centre
    for j, r in zip((A, C1, C2, C3), (0, 45, 90, 135)):
        j.at(97, col=ELEC, spd=7.5) if j is A else None
        j.to(97, 98, "expoOut", x=0, y=0, rot=r, sx=0.45, a=255)
        j.to(98, 113, "linear", rot=r - 45)
    lines4 = [A, C1, C2, C3]

    def arms(h, b, i):
        return (1 if (i + h) % 2 == 0 else -1) * (220 + 60 * ((i // 2) % 3))
    N.stream(A, 98, 114, arms, dens=3, chords=0, seed=51, lines=lines4, ab=True)
    # (c) 114-130: two lines, bolts between them
    for j in (C1, C2, C3):
        j.to(113, 114, "quadIn", a=0)
    A.to(113, 114, "expoOut", y=-230, rot=0)
    B.at(113, col=ELEC, rot=180, y=230, spd=7.5).to(113, 114, "quadOut", a=255)
    for k, b0 in enumerate(range(114, 130, 2)):
        N.stream(A if k % 2 == 0 else B, b0, b0 + 2, zig(280, 120, 2), dens=3, chords=2, seed=60 + k)
    s = sh(114, 130)
    for k, b in enumerate(m.accents(114, 130, 0.7, 1.0)):
        strike(s, b, R.uniform(-300, 300), 0, 1800, R.uniform(-8, 8), WHITE, k + 1, 36, F(1, 2), 160)
    # (d) 130-146: the chain again, turning around the centre
    A.to(129, 130, "quadIn", a=0)
    B.to(129, 130, "quadIn", a=0)
    for j, (x, y, r) in zip((C1, C2, C3), chain0):
        j.at(129, x=x * 0.8, y=y, rot=r, sx=seg * 0.8).to(129, 130, "quadOut", a=255)
    for q in range(4):
        b0, b1 = 130 + 4 * q, 134 + 4 * q
        ang = -11.25 * (q + 1)
        for j, (x, y, r) in zip((C1, C2, C3), chain0):
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            xp = x * 0.8 / PX
            j.to(b0, b1, "sineInOut", x=(xp * ca - y * sa) * PX, y=xp * sa + y * ca, rot=r - ang)
    N.stream(C1, 130, 146, trill(100), dens=3, chords=0, seed=70, lines=[C1, C2, C3])
    s = sh(130, 146)
    for b in range(130, 146, 2):
        strike(s, b, 0, 40, 1300, 11.25 * ((b - 130) // 4 + 1), CYAN, b, 30, F(1, 2), 200)
    # (e) 146-162: everything merges into one line, which turns a full circle
    for j in (C1, C2, C3):
        j.to(146, 147, "expoOut", x=0, y=0, rot=0, a=0)
    A.at(145, rot=0, y=0, x=0).to(145, 146, "quadOut", a=255)
    A.to(150, 158, "sineInOut", rot=-360)
    N.stream(A, 146, 158, zig(200, 50, 4), dens=3, chords=2, seed=80, ab=True)
    A.to(158, 159, "expoOut", y=-250, rot=-360)
    N.stream(A, 159, 162, stair(110, 520, 4), dens=4, chords=0, seed=81)

    # ============ rewind (162-178): the clock runs backwards, the lines become its hands
    G.bgc(162, (20, 20, 26), 2)
    G.skyc(162, (60, 60, 70), 0, 4)
    s = sh(162, 178, cam=[(170, 1.0, 0, 0, "linear"), (178, 2.6, 0, 0, "expoIn")])
    ck = s.tex("clock.png", 0, 0, 1250, 1250, 0.0, PALE, 0, -40)
    ck.at(164, "sineOut", alpha=120).at(178, "expoIn", rot=200)
    for ln, th, spin in ((560, 9, -1440), (360, 15, -360)):
        h = s.line(0, 0, 90.0, ln / 2, th, PALE, 0, -39)
        h.at(164, "sineOut", alpha=200).at(178, "expoIn", rot=90.0 - spin)
    fo = s.tex("focus.png", 0, 0, 2400, 2400, 0.0, PALE, 0, -35, 166, 178)
    fo.at(176, "quadIn", alpha=160).at(178, "linear", rot=-120)
    dust(s, PALE, 140, 2400, 0, 0, 0, 0, z=-30, w1=300)
    effect("grayscale", 162, 178, factor=kf((162, 0.0, "linear"), (176, 0.9, "linear"), (178, 1.0, "linear")))
    effect("fisheye", 166, 178, power=kf((166, 0.0, "quadIn"), (178, -0.35, "linear")))
    effect("chromatic", 170, 178, power=kf((170, 0.0, "quadIn"), (178, 0.03, "linear")), sampleCount=6.0)
    effect("pixel", 177, 178, size=kf((177, 1.0, "quadIn"), (178, 40.0, "linear")))
    for b in range(168, 178):
        G.shake(b, 4 + (b - 168) * 2.5, 0.4 + (b - 168) * 0.15, 0.4)
    A.at(162, col=PALE).to(162, 164, "expoOut", y=0, sx=0.33)
    A.to(164, 177, "quadIn", rot=-1080)
    B.at(162, col=PALE, rot=90, y=0, sx=0.22).to(162, 164, "quadOut", a=230)
    B.to(164, 177, "quadIn", rot=90 - 360)
    N.stream(A, 162, 166, zig(300, 80, 4), dens=2, chords=2, seed=90, lines=[A, B], ab=True)
    N.stream(A, 166, 176, trill(240), dens=3, chords=0, seed=91, lines=[A, B], ab=True)
    for j in (A, B):
        j.to(176, 178, "expoIn", sx=0.0, a=0)
    G.flash(F(355, 2), WHITE, 255, F(1, 2), "linear")

    # ============ Chernobog (178-194): snow and a heart monitor
    G.bgc(178, (8, 12, 20))
    G.skyc(178, (40, 60, 90), 0)
    G.black(178, F(357, 2))
    s = sh(178, 194)
    scroll(s, "snow.png", ICE, 170, 1700, -60, -30, 179, 194)
    scroll(s, "snow.png", WHITE, 120, 2400, -110, -29, 180, 194, rot=180)
    label(s, "t_ursus.png", -440, 320, 420, 180, 189, ICE)
    effect("grayscale", 178, 194, factor=0.55)
    effect("noise", 178, 194, power=0.0015, seed=12.0)
    # the trace runs left to right across the 16 beats; a heartbeat draws a QRS complex
    beats_hb = [180, 182, 184, 186, 187, 188, 189, 190, F(381, 2), 191, F(383, 2), 192, F(385, 2), 193, F(773, 4), F(387, 2), F(775, 4)]
    X0, XS, Y0 = -760.0, 95.0, -40.0

    def tx(b):
        return X0 + (float(b) - 178) * XS
    pts = [(tx(178), Y0)]
    for h in beats_hb:
        x = tx(h)
        w = min(36.0, XS * 0.35)
        pts += [(x - w * 1.2, Y0), (x - w * 0.9, Y0 + 14), (x - w * 0.6, Y0), (x - w * 0.25, Y0 - 22), (x, Y0 + 190),
                (x + w * 0.25, Y0 - 70), (x + w * 0.55, Y0), (x + w * 1.0, Y0 + 30), (x + w * 1.4, Y0)]
    pts.append((tx(194), Y0))
    for p, q in zip(pts, pts[1:]):
        if q[0] <= p[0]:
            continue
        b_on = 178 + (p[0] - X0) / XS
        bq = F(round(b_on * 48), 48)
        if bq < 178 + EPSB:
            bq = F(178) + EPSB
        if bq > F(194) - F(1, 8):
            continue
        e = s.seg(p, q, 5, MON, 0, 10, start=bq, end=min(F(194), bq + F(5)))
        e.at(bq + F(1, 48), "linear", alpha=255).at(min(F(194), bq + F(5)), "quadIn", alpha=0)
    cur = glow(s, tx(178), Y0, 120, MON, 255, 11, 178, 194)
    cur.at(194, "linear", x=tx(194))
    A.at(178, y=Y0, rot=0, x=0, col=(60, 160, 120), spd=6.5).to(178, 180, "quadOut", sx=0.45, a=150)
    for k, h in enumerate(beats_hb):
        N.add(A, h, tx(h) * PX, TAP)
    N.add(A, 186, -300, HOLD, end=188)
    N.add(A, 188, 420, HOLD, end=190)

    # ============ Victoria (194-242): rain, lancet windows, the ark rising
    G.flash(194, (200, 230, 210), 180, 1)
    G.shake(194, 14, 0.6)
    G.bgc(194, (8, 16, 14))
    s = sh(194, 242, cam=[(226, 1.04, 0, 0, "linear"), (242, 1.12, 0, 0, "quadIn")])
    for k in range(5):
        x = -640 + 320 * k
        glow(s, x, -40, 420, CRIM, 120, -46)
        s.tex("arch.png", x, -60, 250, 500, 0.0, (110, 26, 40), 210, -44)
    scroll(s, "rain.png", RAIN, 150, 1800, -600, -30, rot=8.0)
    scroll(s, "rain.png", PALE, 90, 2400, -900, -29, rot=8.0)
    label(s, "t_victoria.png", -500, 320, 300, 196, 206, (220, 190, 200))
    back = glow(s, 0, -700, 2400, (60, 140, 120), 0, -45, 226, 242)
    back.at(240, "sineOut", y=-200, alpha=170)
    ark = s.tex("ark.png", 0, -900, 2700, None, 0.0, (6, 10, 10), 255, -43, 226, 242)
    ark.at(240, "sineOut", y=-330)
    for k, x in enumerate((-500, -150, 260, 620)):
        bm = s.tex("beam.png", x, -100, 900, 60, 90.0, MON, 0, -41, 230 + k, 242)
        bm.at(234 + k, "sineOut", alpha=140)
    thunder = m.accents(194, 242, 0.95, 4)
    for k, b in enumerate(thunder):
        G.flash(b, (220, 230, 255), 80, 0.3)
        strike(s, b, R.uniform(-500, 500), 260, 700, -80 + R.uniform(-8, 8), PALE, k, -40, F(1, 2), 140)
    for b in (194, 210, 226):
        effect("shockwave", b, b + F(3, 2), progress=kf((b, 0.02, "quadOut"), (b + F(3, 2), 0.95, "linear")), width=0.08,
               distortion=0.6, expand=10.0)
    A.to(193, 194, "expoOut", y=-250, sx=0.45, a=255, col=LINE_W).at(194, spd=8)
    C2.at(193, x=-560, y=0, rot=90, sx=0.3, col=(220, 120, 140), spd=6).to(193, 194, "quadOut", a=230)
    C3.at(193, x=560, y=0, rot=-90, sx=0.3, col=(220, 120, 140), spd=6).to(193, 194, "quadOut", a=230)
    frame_beats = [b for b in range(194, 210, 2) if m.k[b * 4] > 0.45]
    N.stream(A, 194, 210, zig(280, 100, 4), dens=2, chords=0, seed=100, skip=frame_beats)
    for b in frame_beats:
        N.add(C2, b, -120, TAP)
        N.add(C3, b, 120, TAP)
    for k, b0 in enumerate(range(210, 226, 2)):
        N.stream(A, b0, b0 + 1, zig(260, 80, 1), dens=3, chords=2, seed=110 + k)
        N.stream(C2 if k % 2 == 0 else C3, b0 + 1, b0 + 2, trill(140), dens=3, chords=0, seed=120 + k)
    C2.to(226, 240, "sineInOut", x=-330)
    C3.to(226, 240, "sineInOut", x=330)
    A.to(226, 240, "sineInOut", y=-200, spd=9)
    N.stream(A, 226, 236, zig(220, 80, 2), dens=3, chords=2, seed=130)
    N.stream(C2, 236, 240, trill(160), dens=3, chords=0, seed=131, lines=[C2, C3])
    N.stream(A, 240, 242, stair(100, 520, 5), dens=5, chords=0, seed=132)
    effect("radialBlur", 239, 242, power=kf((239, 0.0, "quadIn"), (242, 0.05, "linear")), sampleCount=10.0)

    # ============ journey (242-290): the memories meet  -- 浩瀚之旅
    G.flash(242, WHITE, 240, 1.5)
    G.shake(242, 26, 1.8, 0.5)
    PHASES = [(242, GOLD, (52, 30, 18)), (250, ICE, (14, 20, 34)), (258, CRIM, (40, 8, 14)), (266, MON, (6, 26, 20)),
              (274, GOLD, (52, 30, 18)), (282, MON, (6, 26, 20))]
    s = sh(242, 290)
    t = s.tex("t_ch2.png", 0, 0, 1100, None, 0.0, WHITE, 255, 70, 242, 252)
    t.at(F(487, 2), "expoOut", w=460, h=460 * ML.TEXPX["t_ch2.png"][1] / ML.TEXPX["t_ch2.png"][0], y=330)
    t.at(250, "linear", alpha=230).at(252, "quadIn", alpha=0)
    label(s, "t_terra.png", 520, 320, 220, 244, 256, PALE)
    glow(s, 0, -200, 2400, (60, 140, 120), 120, -46)
    s.tex("ark.png", 0, -330, 2700, None, 0.0, (6, 10, 10), 255, -43)
    st8 = s.tex("star8.png", 0, 0, 1300, 1300, 0.0, GOLD, 80, -45)
    st8.at(290, "linear", rot=-270)
    for b, col, bg in PHASES:
        G.bgc(b, bg, 0.5)
        st8.at(b, "linear", color=st8.kf["color"].value(b)).at(b + F(1, 2), "quadOut", color=col)
        G.flash(b, col, 120, 0.75)
        effect("fisheye", b, b + 1, power=kf((b, -0.12, "quadOut"), (b + 1, 0.0, "linear")))
        if col == MON:
            effect("pixel", b, b + F(1, 2), size=kf((b, 26.0, "quadOut"), (b + F(1, 2), 1.0, "linear")))
        effect("shockwave", b, b + F(3, 2), progress=kf((b, 0.02, "quadOut"), (b + F(3, 2), 0.95, "linear")), width=0.1,
               distortion=0.8, expand=10.0)
        if col == GOLD:
            dust(s, SAND, 160, 2000, 300, -900, 0, 0, z=-30, start=b, end=b + 8)
        elif col == ICE:
            scroll(s, "snow.png", ICE, 170, 1700, -90, -30, b, b + 8)
        elif col == CRIM:
            scroll(s, "rain.png", RAIN, 150, 1800, -700, -30, b, b + 8, rot=8.0)
        else:
            for kk, bb in enumerate(m.accents(b, b + 8, 0.6, 2)):
                claws(s, bb, R.uniform(-400, 400), R.uniform(-150, 200), R.uniform(30, 150), 700, MON, 45)
    for k, b in enumerate(m.accents(242, 290, 0.9, 2)):
        strike(s, b, R.uniform(-300, 300), R.uniform(-150, 250), 1800, R.uniform(-30, 30), WHITE, k, 36)
        effect("chromatic", b, b + F(1, 2), power=kf((b, 0.016, "quadOut"), (b + F(1, 2), 0.0, "linear")), sampleCount=5.0)
    for b in (252, 280):
        effect("glitch", b, b + F(1, 2), power=0.06, rate=0.9, speed=18.0, blockCount=24.0, colorRate=0.015)
        effect("radialBlur", b, b + 1, power=kf((b, 0.05, "quadOut"), (b + 1, 0.0, "linear")), sampleCount=10.0)
        G.flash(b, WHITE, 220, 1)
    # the star of lines: A, C1, C2, C3 through the centre, a quarter turn every 16 beats
    for j, r in zip((A, C1, C2, C3), (0, 45, 90, 135)):
        if j is not A:
            j.at(241, x=0, y=0, sx=0.45, spd=7.5)
        j.to(241, 242, "expoOut", x=0, y=0, rot=r, a=255, sx=0.45)
        j.to(242, 288, "linear", rot=r - 270)
    for j in (C2, C3):
        j.at(241, col=LINE_W)
    for b, col, _bg in PHASES:
        for j in (A, C1, C2, C3):
            j.at(b, col=mix(col, WHITE, 0.35))
    N.stream(A, 242, 288, arms, dens=3, chords=0, seed=140, lines=lines4, ab=True)
    for j in (C1, C2, C3):
        j.to(288, 290, "expoOut", rot=-270, a=0)
    A.to(288, 290, "expoOut", rot=-360, y=0)

    # ============ stillness (290-306): time stops, everything dissolves into dust
    G.bgc(290, (16, 16, 18), 2)
    s = sh(290, 306)
    dd = dust(s, PALE, 200, 2000, 0, 0, 0, 0, z=-30, w1=3600)
    dd.at(306, "linear", alpha=0)
    sweep = s.tex("beam.png", 0, 450, 2400, 70, 0.0, WHITE, 0, 40, 292, 298)
    sweep.at(F(585, 2), "linear", alpha=230).at(298, "sineInOut", y=-450).at(298, "linear", alpha=0)
    effect("grayscale", 290, 306, factor=kf((290, 0.0, "expoOut"), (292, 1.0, "linear"), (300, 1.0, "sineIn"), (306, 0.0, "linear")))
    effect("noise", 292, 306, power=0.006, seed=55.0)
    effect("pixel", F(583, 2), 292, size=kf((F(583, 2), 1.0, "quadIn"), (292, 24.0, "linear")))
    G.flash(292, WHITE, 255, 1)
    A.at(290, col=PALE, spd=7)
    N.stream(A, 290, 298, trill(300), dens=1, chords=0, seed=150)
    N.add(A, 298, -260, HOLD, end=302)
    N.add(A, 302, 260, HOLD, end=306)
    A.to(298, 306, "sineInOut", y=-250)

    # ============ dawn (306-350): footprints into the distance, the title, the line walks away
    G.bgc(306, (30, 18, 18), 8)
    G.skyc(306, (255, 186, 140), 0)
    G.skyc(F(613, 2), (255, 186, 140), 170, 8)
    G.skyc(334, (60, 40, 40), 0, 12)
    G.bgc(334, INK, 12)
    s = sh(306, 350, cam=[(334, 1.06, 0, 0, "linear")])
    glow(s, 0, -150, 1500, EMBER, 0, -48, 306).at(318, "sineOut", alpha=200).at(338, "linear", alpha=200).at(346, "linear", alpha=0)
    s.tex("dunes.png", 0, -330, 2600, None, 0.0, (30, 20, 20), 255, -40, 306, 350).at(350, "linear", alpha=0)
    dust(s, GOLD, 120, 2000, 0, -100, 60, -60, z=-30, a_in=4)
    t1 = s.tex("t_title.png", 0, 190, 760, None, 0.0, PALE, 0, 50, 318, 346)
    t1.at(322, "sineOut", alpha=255).at(334, "linear", alpha=255).at(342, "sineIn", alpha=0, y=230)
    t2 = s.tex("t_walk.png", 0, 95, 520, None, 0.0, SAND, 0, 50, 320, 346)
    t2.at(324, "sineOut", alpha=200).at(334, "linear", alpha=200).at(342, "sineIn", alpha=0, y=125)
    t3 = s.tex("t_event.png", 0, 280, 260, None, 0.0, GOLD, 0, 50, 320, 346)
    t3.at(324, "sineOut", alpha=190).at(334, "linear", alpha=190).at(342, "sineIn", alpha=0)
    late = [b for b in range(306, 334) if m.st(b * 4) > 0.5][::2]
    for k, b in enumerate(late):
        dpt = k / max(1, len(late) - 1)
        y = -420 + 290 * (1 - (1 - dpt) ** 1.6)
        size = 70 * (1 - 0.75 * dpt)
        x = (-1 if k % 2 == 0 else 1) * 26 * (1 - 0.7 * dpt)
        footprint(s, b, x, y, 0, size, SAND, 200, 5, 10)
    A.to(306, 334, "linear", y=-130, sx=0.15)
    for k, b in enumerate(late):
        if not 326 <= b < 330:
            N.add(A, b, (-1 if k % 2 == 0 else 1) * 130, TAP)
    N.add(A, 326, 0, HOLD, end=330)
    A.to(334, 340, "sineIn", a=0, sx=0.0)

    # ------------------------------------------------------------ fake notes: sand / snow / rain drifting on the lines
    for b0, b1, jl, n_, sp in ((50, 82, A, 40, 0.6), (90, 98, C1, 20, 0.8), (194, 226, A, 34, 1.4), (242, 288, A, 50, 0.9)):
        RR = random.Random(b0)
        for _ in range(n_):
            b = F(RR.randint(b0 * 8, b1 * 8 - 1), 8)
            N.add(jl, b, RR.uniform(-600, 600), DRAG, fake=True, speed=sp * RR.uniform(0.7, 1.3), alpha=RR.randint(60, 140))

    E.bake()
    G.emit(random.Random(7))
    n = N.write()
    c.effect("vignette", 0, END, {"extend": 0.22, "radius": 16.0})
    for name, b0, b1, v in fx:
        c.effect(name, b0, b1, v)
    return E, n


def make():
    c = Chart(OFFSET_MS, dict(INFO, id="claude-walk-in-the-dust"), bpm=BPM, compact=True)
    E, n = build(c)
    print(f"pooled lines: {E.line_count()}  notes: {n}")
    return c, INFO


def assets(out):
    import dust_assets
    dust_assets.make(out)
    ill = os.path.join(DATA, "illustration.jpg")
    if os.path.exists(ill):
        shutil.copy(ill, os.path.join(out, "illustration.jpg"))
    else:
        from PIL import Image
        Image.new("RGB", (1920, 1080), NIGHT).save(os.path.join(out, "illustration.jpg"))
