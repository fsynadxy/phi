"""新宿决战 — a playable chart (AT Lv.16, constant 16.5) on top of the MAD performance.

* Four moments play the original footage of NinjaristicNinja's Shinjuku Showdown MAD as Phira videos
  (extra.json "videos"): 200% Hollow Purple (beats 73-82), the first domain clash (105-113), the second
  domain clash (144-154) and Unlimited Hollow Purple (216-end). While a clip plays nothing else is drawn:
  the background, the judge lines and the HUD step aside, and there are no notes.
* Everywhere else the MAD storyboard (mad_shinjuku.py) runs dimmed behind the play field and the judge
  lines carry the chart: 16th streams with chords, flick bursts on the slashes, drags against taps,
  holds under streams, two-line reading, tilting / rotating / crossing lines, speed changes.
* The footage is not part of the repository (the repo is public). Point MAD_CLIPS at a folder holding
  clip_a.mp4 .. clip_d.mp4 when building; tools/analysis/cut_clips.py cuts them from the video.

Beat k = beat k of the song (153.6 BPM, first beat 0.2935 s), exactly as in mad_shinjuku.py.
"""
import math
import os
import random
import shutil
import sys

import numpy as np

import madlib as ML
import mad_shinjuku as MS
from chartlib import Chart, DRAG, EPSB, FLICK, HOLD, TAP, frac
from madlib import TL, Engine

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "mad")
BPM, OFFSET_MS = MS.BPM, MS.OFFSET_MS
F = MS.F
END = 240
VIDEOS = [(73, 82, "clip_a.mp4"), (105, 113, "clip_b.mp4"), (144, 154, "clip_c.mp4"), (216, END, "clip_d.mp4")]
MASK = [(a, b) for a, b, _ in VIDEOS]

INFO = {
    "name": "新宿决战",
    "difficulty": 16.5,
    "level": "AT Lv.16",
    "charter": "Claude",
    "composer": "雨爱 (DJ版) - 杨丞琳",
    "illustrator": "NinjaristicNinja《新宿决战》MAD",
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
    "tip": "素材：NinjaristicNinja《新宿决战》MAD（B站 BV1dGTu66Eo4）",
    "tags": ["新宿决战", "MAD", "视频", "AT"],
    "intro": "四个名场面（200% 虚式「茈」、两次领域对拼、无限制虚式）播放原 MAD 素材，其余部分按 16.5 定数制谱。",
    "holdPartialCover": False,
    "noteUniformScale": False,
    "forceAspectRatio": False,
    "useRpe170Speed": False,
    "useAttachUiFix": True,
}

# judge line colours (brighter than the scene palette so the lines read on any background)
W_ = (238, 243, 250)
CY = (96, 226, 255)
RD = (255, 78, 92)
PU = (200, 136, 255)
GD = (255, 224, 150)
XMAX = 560  # |positionX| limit: keeps the whole note on screen


def masked(b, b1=None):
    b = frac(b)
    for m0, m1 in MASK:
        if b1 is None:
            if m0 <= b < m1:
                return True
        elif frac(b1) > m0 and b < m1:
            return True
    return False


# ------------------------------------------------------------------ music (16th grid, bar 0 at beat 0)
class Music:
    def __init__(self):
        d = np.load(os.path.join(DATA, "steps.npz"))

        def n(a):
            return np.clip(a / (np.percentile(a, 98) + 1e-9), 0, 1.5)
        self.k, self.lm, self.sn, self.h, self.mel = (n(d[k]) for k in ("low_p", "lmid_p", "mid_p", "high_p", "mid_h"))
        self.n = len(self.k)

    def st(self, s):
        if not 0 <= s < self.n:
            return 0.0
        return float(max(self.k[s], self.lm[s], self.sn[s], self.h[s]))

    def keep(self, s, dens):
        """is 16th step s part of the rhythm at density level dens (1 quarters .. 5 all 16ths)?"""
        v = self.st(s)
        if s % 4 == 0:
            return v > 0.12
        if s % 2 == 0:
            return dens >= 2 and v > 0.25
        return {1: 9, 2: 9, 3: 0.62, 4: 0.36, 5: 0.1}[dens] < v


# ------------------------------------------------------------------ judge lines
P = {"x": "moveX", "y": "moveY", "rot": "rotate", "a": "alpha", "spd": "speed", "col": "color"}


class JL:
    """a judge line with chronological property writers (values in RPE units, alpha 0..255)."""

    def __init__(self, c, name, z, x=0.0, y=-250.0, rot=0.0, alpha=0.0, speed=9.0, color=W_):
        self.ln = c.line(name, z=z)
        self.tl = {}
        for p, v in (("moveX", x), ("moveY", y), ("rotate", rot), ("alpha", alpha), ("speed", speed), ("color", color)):
            v = tuple(v) if p == "color" else float(v)
            self.ln.ev(p, 0, EPSB, v, v)
            self.tl[p] = TL(self.ln, p, v)
        self.mirror = False  # True while the line is upside down (screen x = -positionX)

    def at(self, b, **vals):
        b = frac(b)
        for k, v in vals.items():
            v = tuple(v) if k == "col" else float(v)
            t = self.tl[P[k]]
            if t.b == b + EPSB:  # a second jump on the same beat replaces the first one
                tr = self.ln.tr(P[k])
                b0, b1, _, _, e = tr.segs[-1]
                assert b0 == b
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

    def val(self, k):
        return self.tl[P[k]].v


# ------------------------------------------------------------------ x shapes: f(hand, beat, n-th note of that hand) -> screen x
def zig(cx=300, amp=110, period=4, ph=0.0):
    return lambda h, b, i: (-1 if h == 0 else 1) * cx + amp * math.sin(2 * math.pi * float(b) / period + ph + h * math.pi)


def stair(lo=110, hi=520, n=4, parallel=True, shift=0):
    def f(h, b, i):
        k = (i + shift) % (2 * n - 2)
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


def scatter(seed, lo=120, hi=540):
    R = random.Random(seed)
    return lambda h, b, i: (-1 if h == 0 else 1) * R.uniform(lo, hi)


# ------------------------------------------------------------------ notes
class Notes:
    def __init__(self, music):
        self.m = music
        self.items = []

    def add(self, jl, b, x, kind=TAP, end=None, above=True):
        b = frac(b)
        e = frac(end) if end is not None else None
        if masked(b, e if e is not None else None) or (e is None and masked(b)):
            raise ValueError(f"note at beat {float(b)} falls inside a footage segment")
        x = max(-XMAX, min(XMAX, float(x)))
        if jl.mirror:
            x = -x
        self.items.append((jl, b, round(x, 1), kind, e, above))

    def stream(self, jl, b0, b1, shape, dens=4, chords=2, flicks=0.4, seed=0, drag_offbeats=False, skip=(),
               above=True, chord_th=0.55):
        """the song's 16th rhythm at density `dens`, alternating hands, chords on kicks every `chords` beats,
        flicks on some backbeats; returns the beats used."""
        R = random.Random(seed)
        hand, cnt, used = 0, [0, 0], []
        skip = {frac(b) for b in skip}
        for s in range(round(float(b0) * 4), round(float(b1) * 4)):
            b = frac(s, 4)
            if b in skip or masked(b) or not self.m.keep(s, dens):
                continue
            used.append(b)
            if s % 4 == 0 and chords and (s // 4) % chords == 0 and self.m.k[s] > chord_th:
                for h in (0, 1):
                    self.add(jl, b, shape(h, b, cnt[h]), TAP, above=above)
                    cnt[h] += 1
                hand = 1 - hand
                continue
            kind = TAP
            if s % 8 == 4 and self.m.sn[s] > 0.6 and R.random() < flicks:
                kind = FLICK
            elif drag_offbeats and s % 2 == 1:
                kind = DRAG
            self.add(jl, b, shape(hand, b, cnt[hand]), kind, above=above)
            cnt[hand] += 1
            hand = 1 - hand
        return used

    def hold(self, jl, b0, b1, x, above=True):
        self.add(jl, b0, x, HOLD, end=b1, above=above)

    def drags(self, jl, b0, b1, path, step=F(1, 4), above=True):
        b = frac(b0)
        while b < frac(b1):
            if not masked(b):
                self.add(jl, b, path(float(b)), DRAG, above=above)
            b += frac(step)

    def burst(self, jl, b, xs, gap=F(1, 8), kind=FLICK, above=True):
        for k, x in enumerate(xs):
            self.add(jl, frac(b) + frac(gap) * k, x, kind, above=above)

    def chord(self, jl, b, x1, x2, k1=TAP, k2=TAP, above=True):
        self.add(jl, b, x1, k1, above=above)
        self.add(jl, b, x2, k2, above=above)

    def taps_on(self, jl, b0, b1, dens, xfun, kind=TAP, above=True, only=None):
        """single-hand rhythm (e.g. under a hold or against drags); only: subset of steps mod 4"""
        out = []
        for s in range(round(float(b0) * 4), round(float(b1) * 4)):
            b = frac(s, 4)
            if masked(b) or not self.m.keep(s, dens) or (only is not None and s % 4 not in only):
                continue
            self.add(jl, b, xfun(float(b), len(out)), kind, above=above)
            out.append(b)
        return out

    def write(self):
        for jl, b, x, kind, e, above in self.items:
            jl.ln.note(kind, b, x, end=e, above=above)
        return len(self.items)


# ------------------------------------------------------------------ background: the MAD storyboard, dimmed
class PlayGlobals(MS.Globals):
    HIDE_HUD = False

    def __init__(self, c):
        super().__init__(c)
        sx, sy = 1800 / (64 * ML.TEXK), 1000 / (64 * ML.TEXK)
        self.dim = c.line("dim", texture="white.png", z=60)
        for p, v in (("moveX", 0.0), ("moveY", 0.0), ("rotate", 0.0), ("scaleX", sx), ("scaleY", sy), ("alpha", 150.0)):
            self.dim.ev(p, 0, EPSB, v, v)
        self.dim.ev("color", 0, EPSB, MS.INK, MS.INK)
        self.hud = []
        for ui in ("pause", "combonumber", "combo", "score", "bar", "name", "level"):
            h = c.line(f"hud_{ui}")
            h.attach = ui
            for p, v in (("moveX", 0.0), ("moveY", 0.0), ("rotate", 0.0), ("alpha", 255.0), ("scaleX", 1.0), ("scaleY", 1.0)):
                h.ev(p, 0, EPSB, v, v)
            self.hud.append(h)
        self.dim_kfs = []

    # the play field must stay readable: no letterbox, softer flashes and shakes, nothing during the footage
    def letterbox(self, b, on):
        pass

    def flash(self, b, color=MS.WHITE, peak=255, dur=0.5, ease="expoOut"):
        if not masked(b):
            super().flash(b, color, min(peak, 110), dur, ease)

    def shake(self, b, amp=12.0, rot=0.0, dur=0.3):
        if not masked(b):
            super().shake(b, amp * 0.6, rot * 0.5, dur)

    def black(self, b0, b1):
        if not masked(b0):
            super().black(b0, b1)

    def roll(self, b, deg, ease="linear"):
        super().roll(b, deg, ease)

    def emit(self, R):
        super().emit(R)
        tracks = [TL(self.bg, "alpha", 255.0), TL(self.dim, "alpha", 150.0)] + [TL(h, "alpha", 255.0) for h in self.hud]
        for m0, m1 in MASK:
            for t in tracks:
                t.jump(m0, 0.0)
            if m1 < END:
                for t, v in zip(tracks, [255.0, 150.0] + [255.0] * len(self.hud)):
                    t.jump(m1, v)


# ------------------------------------------------------------------ the chart
def chart_notes(c, N):
    A = JL(c, "judge_main", 110, y=-250, speed=9.0, color=CY)
    T = JL(c, "judge_top", 111, y=250, rot=180, speed=9.0)
    X = JL(c, "judge_aux", 112, y=-60, speed=9.0)
    T.mirror = True
    m = N.m

    def hide_all(b):
        for j in (A, T, X):
            if j.val("a") > 0:
                j.at(b, a=0)

    # ======== intro: flames, clash, slash, title (0-4)
    A.to(0, 1, "quadOut", a=255)
    N.chord(A, 1, -300, 300)
    A.at(1, col=RD)
    N.add(A, F(3, 2), -120)
    N.add(A, F(7, 4), 120)
    A.at(2, col=W_)
    N.chord(A, 2, -200, 200)
    N.stream(A, F(9, 4), 3, trill(170), dens=5, chords=0)
    A.to(3, F(13, 4), "expoOut", rot=-24)
    N.burst(A, 3, [-260, 40, 300], gap=F(1, 4))
    A.to(F(15, 4), 4, "expoIn", rot=0)
    N.chord(A, 4, -380, 380, FLICK, FLICK)

    # ======== verse (4-24): eyes, walking, high-key hair, dark close-up, red marks
    N.stream(A, F(17, 4), 8, zig(260, 70), dens=3, chords=2)
    A.at(8, col=CY)
    N.stream(A, 8, 12, stair(140, 480, 4), dens=4, chords=2, seed=1)
    A.at(12, col=W_).to(12, 15, "sineInOut", x=-90)
    N.stream(A, 12, 15, drift(12, 15, 160, -200, 320), dens=4, chords=2, seed=2)
    # 15-17: high key, the second line answers from the top
    T.to(14, 15, "quadOut", a=255)
    A.to(15, F(31, 2), "quadOut", x=0)
    for k, b in enumerate(range(15, 17)):
        jl = T if k % 2 == 0 else A
        N.stream(jl, b, b + F(3, 4), zig(250, 80), dens=4, chords=1, seed=3 + k)
    N.stream(A, 17, 19, zig(300, 120), dens=4, chords=2, seed=5)
    T.to(17, 18, "quadIn", a=0)
    # 19-21: hold under a stream
    N.hold(A, 19, F(41, 2), -360)
    N.taps_on(A, 19, F(41, 2), 4, lambda b, i: 140 + 70 * (i % 4))
    N.hold(A, F(41, 2), 22, 360)
    N.taps_on(A, F(41, 2), 22, 4, lambda b, i: -140 - 70 * (i % 4))
    A.at(22, col=RD)
    N.stream(A, 22, F(47, 2), zig(280, 90, 2), dens=4, chords=2, seed=6)
    N.burst(A, F(47, 2), [-420, 160, -160], gap=F(1, 8), kind=TAP)

    # ======== Sukuna (24-35): red impact, backlight, four eyes
    A.at(24, col=RD, spd=10)
    N.chord(A, 24, -420, 420, FLICK, FLICK)
    N.stream(A, F(97, 4), 25, trill(140), dens=5, chords=0)
    # 25-29: drags against taps
    N.drags(A, 25, 29, lambda b: 260 + 180 * math.sin((b - 25) * math.pi / 2), step=F(1, 4))
    N.taps_on(A, 25, 29, 3, lambda b, i: -260 - 120 * ((i // 2) % 2), only=(0, 2))
    A.at(29, col=(255, 255, 255))
    N.chord(A, 29, -330, 330, FLICK, TAP)
    N.stream(A, F(117, 4), 30, stair(120, 480, 4, False), dens=5, chords=0, seed=7)
    A.at(30, col=RD)
    T.at(30, col=RD).to(30, F(61, 2), "quadOut", a=255)
    for k, b in enumerate(range(30, 34)):  # a 16th of air before every change of line
        jl = A if k % 2 == 0 else T
        N.stream(jl, b, b + F(3, 4), zig(300, 100, 2), dens=4, chords=1, seed=8 + k, skip=(33,))
    N.chord(A, 33, -440, 440, FLICK, FLICK)
    T.to(34, F(69, 2), "quadIn", a=0)
    N.stream(A, 34, 35, stair(100, 500, 5), dens=5, chords=0, seed=12)

    # ======== rooftop, the eye in the white, distant eyes (35-44)
    A.at(35, col=W_, spd=9)
    N.stream(A, 35, 38, drift(35, 38, -180, 180, 340), dens=4, chords=2, seed=13)
    A.at(38, col=CY)
    N.chord(A, 38, -300, 300)
    N.hold(A, F(153, 4), 40, -300)
    N.taps_on(A, F(153, 4), 40, 4, lambda b, i: 120 + 90 * (i % 3))
    A.at(40, col=W_)
    N.stream(A, 40, 42, zig(320, 120, 4), dens=4, chords=2, seed=14)
    A.at(42, col=RD).to(42, F(175, 4), "sineInOut", rot=8)
    N.stream(A, 42, F(175, 4), stair(100, 520, 4), dens=5, chords=2, seed=15)
    A.to(F(175, 4), 44, "quadOut", rot=0)

    # ======== spectators (44-48): a panel per beat, top / bottom call and response
    A.at(44, col=W_)
    T.at(44, col=W_).to(F(87, 2), 44, a=255)
    for k, b in enumerate(range(44, 48)):
        jl = A if k % 2 == 0 else T
        N.chord(jl, b, -360 + 120 * k, 120 + 120 * (k % 2))
        N.stream(jl, b + F(1, 4), b + F(3, 4), scatter(20 + k, 140, 480), dens=4, chords=0, seed=20 + k)
    T.to(48, F(97, 2), a=0)

    # ======== profile, rooftop, red skyline, claws, triple slash (48-56)
    N.chord(A, 48, -200, 200, FLICK, TAP)
    N.stream(A, F(193, 4), 52, zig(300, 140, 3), dens=5, chords=2, seed=24)
    A.at(52, col=RD)
    N.stream(A, 52, 53, trill(200), dens=5, chords=1)
    N.drags(A, 53, 55, lambda b: 420 - 260 * (b - 53), step=F(1, 4))
    N.taps_on(A, 53, 55, 4, lambda b, i: -200 - 90 * (i % 3), only=(0, 2, 3))
    A.at(55, col=W_).to(55, F(221, 4), "expoOut", rot=-20)
    N.burst(A, 55, [-320, 220, -80], gap=F(1, 8))
    N.stream(A, F(223, 4), 56, trill(220), dens=5, chords=0)
    A.to(F(223, 4), 56, "quadOut", rot=0)

    # ======== footsteps, crouch, the old man; the break (56-64)
    N.stream(A, 56, 60, stair(120, 440, 3), dens=4, chords=2, seed=25)
    N.hold(A, 60, 62, -280)
    N.taps_on(A, 60, 62, 2, lambda b, i: 200 + 80 * (i % 3))
    N.hold(A, 62, 63, 280)
    N.taps_on(A, 62, 63, 3, lambda b, i: -200 - 80 * (i % 3))
    A.at(63, col=W_)
    N.stream(A, 63, 64, stair(100, 520, 4), dens=5, chords=0, seed=26)

    # ======== domain expansion (64-73): the void, the face, fire streaks, dusk
    A.at(64, col=CY, spd=9.5)
    N.chord(A, 64, -440, 440, FLICK, FLICK)
    N.stream(A, F(257, 4), 66, zig(300, 120), dens=4, chords=2, seed=27)
    # 66-71: the line rises to the middle and slowly turns; notes from both sides
    A.to(66, F(133, 2), "quartOut", y=-40).to(66, 71, "sineInOut", rot=-24)
    for k, b in enumerate(range(66, 71)):
        N.stream(A, b, b + 1, zig(280, 90, 2), dens=4, chords=2 if k % 2 == 0 else 0, seed=30 + k, above=(k % 2 == 0))
    A.to(71, F(143, 2), "quartOut", y=-250, rot=0)
    A.at(71, col=GD)
    N.stream(A, F(285, 4), 73, drift(71, 73, -260, 260, 300), dens=5, chords=2, seed=36)
    hide_all(73)

    # ======== [footage: 200% Hollow Purple] -- exchange (82-96), one cut per beat
    A.at(81, col=CY, spd=10, rot=0).to(81, 82, "quadIn", a=255)  # the line fades in over the last beat of the clip
    plan = {82: (CY, 6), 83: (CY, -8), 84: (RD, 0), 85: (CY, 14), 86: (CY, 0), 87: (W_, 0), 88: (CY, -6), 89: (RD, 18),
            90: (RD, -16), 91: (RD, 0), 92: (CY, 0), 93: (W_, 4), 94: (W_, -4), 95: (CY, 0)}
    for b, (col, rot) in plan.items():
        A.at(b, col=col).to(b, b + F(1, 4), "expoOut", rot=rot)
        if b in (84, 91):
            N.chord(A, b, -420, 420, FLICK, FLICK)
            N.stream(A, b + F(1, 4), b + 1, trill(160 if b == 84 else 240), dens=5, chords=0, seed=b)
        elif b in (89, 90):
            N.burst(A, b, [-320, 320] if b == 89 else [320, -320], gap=F(1, 8))
            N.stream(A, b + F(1, 2), b + 1, zig(260, 60, 1), dens=5, chords=0, seed=b)
        elif b == 87:
            N.stream(A, b, b + 1, trill(300), dens=2, chords=1)
        elif b in (93, 94):
            N.drags(A, b, b + 1, (lambda b0: (lambda t: (-1 if b0 == 93 else 1) * (420 - 600 * (t - b0))))(b), step=F(1, 8))
            N.add(A, b, 380 if b == 93 else -380)
        else:
            N.stream(A, b, b + 1, zig(300, 100, 1), dens=5, chords=1, seed=b)

    # ======== the drop (96-105): cyan triangle, overhead city, beam, crossing slashes, debris
    A.at(96, col=CY, rot=0)
    N.chord(A, 96, -440, 440, FLICK, FLICK)
    N.stream(A, F(385, 4), 97, trill(200), dens=5, chords=0)
    T.at(97, col=W_).to(F(193, 2), 97, a=255)
    for k, b in enumerate(range(97, 100)):
        N.stream(A if k % 2 == 0 else T, b, b + F(3, 4), stair(120, 460, 4, k % 2 == 0), dens=5, chords=1, seed=40 + k)
    T.to(100, F(201, 2), a=0)
    A.at(100, col=W_).to(100, F(401, 4), "expoOut", rot=-30)
    N.burst(A, 100, [-360, -60, 240], gap=F(1, 4), kind=FLICK)
    A.to(F(403, 4), 101, "quadOut", rot=0)
    N.burst(A, 101, [-380, 380, -140, 140], gap=F(1, 8))
    N.stream(A, F(203, 2), 102, trill(260), dens=5, chords=0)
    A.at(102, col=PU)
    N.stream(A, 102, 103, scatter(44, 100, 520), dens=5, chords=1, seed=44)
    A.at(103, col=W_)
    N.drags(A, 103, 104, lambda b: -480 + 900 * (b - 103), step=F(1, 8))
    N.add(A, F(207, 2), -300)
    A.at(104, col=CY)
    N.chord(A, 104, -300, 300)
    N.stream(A, F(417, 4), 105, trill(180), dens=5, chords=0)
    hide_all(105)

    # ======== [footage: first domain clash] -- the black sphere, black flash (113-118)
    A.at(112, col=PU, spd=8, rot=0).to(112, 113, "quadIn", a=255)
    N.stream(A, 113, 114, trill(200), dens=2, chords=1)
    A.to(114, F(463, 4), "quadIn", spd=12)
    N.stream(A, 114, F(463, 4), stair(100, 480, 4), dens=5, chords=0, seed=50)
    A.at(116, col=W_, spd=10)
    N.chord(A, 116, -440, 440, FLICK, FLICK)
    N.stream(A, F(465, 4), 118, zig(320, 120, 2), dens=5, chords=2, seed=51)

    # ======== slashes across the face (118-125)
    for k, b in enumerate((118, F(239, 2), 120, 122)):
        A.at(b, col=RD).to(b, b + F(1, 8), "expoOut", rot=-14).to(b + F(1, 8), b + F(1, 2), "quadOut", rot=0)
        A.at(b + F(1, 2), col=W_)
        N.chord(A, b, -260, 260, FLICK, FLICK)
    N.stream(A, F(473, 4), F(239, 2), zig(300, 100), dens=5, chords=0, seed=52)
    N.stream(A, F(479, 4), 120, trill(180), dens=5, chords=0)
    N.stream(A, F(481, 4), 122, stair(110, 500, 4, False), dens=5, chords=2, seed=53)
    N.stream(A, F(489, 4), 124, zig(280, 140, 2), dens=5, chords=2, seed=54)
    A.at(124, col=CY)
    N.chord(A, 124, -320, 320)
    N.stream(A, F(497, 4), 125, trill(150), dens=5, chords=0)

    # ======== red impact, mudra, shrine, the great eye (125-135)
    A.at(125, col=RD, spd=10.5)
    N.chord(A, 125, -440, 440, FLICK, FLICK)
    N.stream(A, F(501, 4), 126, stair(100, 500, 4), dens=5, chords=0, seed=55)
    N.hold(A, 126, F(255, 2), -320)
    N.taps_on(A, 126, F(255, 2), 5, lambda b, i: 120 + 110 * (i % 4))
    N.hold(A, F(255, 2), 129, 320)
    N.taps_on(A, F(255, 2), 129, 5, lambda b, i: -120 - 110 * (i % 4))
    A.at(129, col=(255, 255, 255))
    N.stream(A, 129, 131, zig(320, 110, 1), dens=5, chords=1, seed=56, chord_th=0.3)
    A.at(131, col=RD)
    T.at(131, col=W_).to(F(261, 2), 131, a=255)
    for k, b in enumerate(range(131, 135)):
        N.stream(A if k % 2 == 0 else T, b, b + F(3, 4), zig(280, 120, 2), dens=5, chords=1, seed=60 + k)
    T.to(135, F(271, 2), a=0)

    # ======== the barrier, the exchange, slash streaks, split (135-144)
    A.at(135, col=CY).to(135, F(271, 2), "quartOut", y=-60).to(135, 137, "sineInOut", rot=30)
    N.stream(A, 135, 136, zig(260, 80), dens=4, chords=2, seed=64)
    N.stream(A, 136, 137, zig(260, 80), dens=4, chords=2, seed=65, above=False)
    A.to(137, F(275, 2), "quartOut", y=-250, rot=0)
    for b in (137, 138, 139):
        A.at(b, col=RD if b == 138 else CY)
        N.stream(A, b, b + 1, zig(300, 120, 1), dens=5, chords=1, seed=b)
    A.at(140, col=W_).to(140, F(561, 4), "expoOut", rot=10)
    N.burst(A, 140, [-420, 420, -180, 180], gap=F(1, 8))
    N.stream(A, F(281, 2), 141, trill(240), dens=5, chords=0)
    A.to(F(563, 4), 141, rot=0)
    for b in (141, 142, 143):
        A.at(b, col=W_ if b != 142 else RD)
        N.chord(A, b, -380, 380, FLICK if b == 143 else TAP, TAP)
        N.stream(A, b + F(1, 4), b + 1, stair(120, 500, 4, b % 2 == 0), dens=5, chords=0, seed=b)
    hide_all(144)

    # ======== [footage: second domain clash] -- the standoff, the break (154-161)
    A.at(153, col=W_, spd=8.5, rot=0).to(153, 154, "quadIn", a=255)
    N.stream(A, 154, 156, zig(260, 80), dens=3, chords=2, seed=70)
    N.hold(A, 156, 158, -300)
    N.hold(A, 156, 157, 300)
    N.hold(A, 157, 158, 200)
    N.hold(A, 158, 160, 300)
    N.taps_on(A, 158, 160, 3, lambda b, i: -160 - 90 * (i % 3))
    A.to(159, 161, "quadIn", spd=11)
    N.stream(A, 160, 161, stair(100, 500, 5), dens=5, chords=0, seed=71)

    # ======== bleeding eyes, cyan punch, silhouettes, the beam (161-170)
    A.at(161, col=RD, spd=10)
    N.chord(A, 161, -300, 300, FLICK, FLICK)
    N.drags(A, F(645, 4), 162, lambda b: -300, step=F(1, 8))
    N.drags(A, F(645, 4), 162, lambda b: 300, step=F(1, 8))
    N.stream(A, 162, 163, zig(320, 80), dens=5, chords=1, seed=72)
    A.at(163, col=CY)
    N.drags(A, 163, 165, lambda b: 380 - 160 * math.sin((b - 163) * math.pi), step=F(1, 4))
    N.taps_on(A, 163, 165, 4, lambda b, i: -180 - 120 * ((i // 2) % 2), only=(0, 1, 2, 3))
    A.at(165, col=W_)
    N.stream(A, 165, 167, stair(120, 480, 4), dens=5, chords=2, seed=73)
    A.at(167, col=CY)
    N.chord(A, 167, -420, 420, FLICK, TAP)
    N.hold(A, F(669, 4), 169, 420)
    N.taps_on(A, F(669, 4), 169, 5, lambda b, i: -100 - 100 * (i % 4))
    A.at(169, col=RD)
    N.stream(A, 169, 170, zig(300, 120, 1), dens=5, chords=1, seed=74)

    # ======== the wheel above the head, orbs, fire (170-176)
    A.at(170, col=W_).to(171, F(343, 2), "backOut", rot=12).to(F(343, 2), 172, "backOut", rot=0)
    N.stream(A, 170, 172, zig(300, 100, 2), dens=5, chords=2, seed=75)
    A.at(172, col=CY)
    N.stream(A, 172, 173, drift(172, 173, 60, 300, 400), dens=5, chords=1, seed=76)
    A.at(173, col=GD)
    N.stream(A, 173, 175, zig(330, 120, 1), dens=5, chords=1, seed=77)
    A.at(175, col=W_)
    N.stream(A, 175, 176, stair(100, 500, 5), dens=5, chords=0, seed=78)

    # ======== the blue orb, the great cyan eye, the red orb, the explosion (176-192)
    A.at(176, col=CY)
    N.stream(A, 176, 178, drift(176, 178, 200, -200, 320), dens=4, chords=2, seed=79)
    N.chord(A, 178, -460, 460, FLICK, FLICK)
    N.stream(A, F(713, 4), 179, trill(140), dens=5, chords=0)
    T.at(179, col=CY).to(F(357, 2), 179, a=255)
    N.chord(T, 179, -300, 300)
    N.stream(T, F(717, 4), 180, trill(220), dens=5, chords=0)
    T.to(180, F(361, 2), a=0)
    A.at(180, col=RD)
    N.drags(A, 180, 183, lambda b: -300 + 200 * math.sin((b - 180) * math.pi * 2 / 3), step=F(1, 4))
    N.taps_on(A, 180, 183, 4, lambda b, i: 200 + 110 * (i % 3))
    N.chord(A, 183, -420, 420, FLICK, FLICK)
    N.stream(A, F(733, 4), 185, zig(320, 120, 2), dens=5, chords=2, seed=80)
    N.drags(A, 185, 186, lambda b: -440 + 880 * (b - 185), step=F(1, 8))
    A.at(186, col=GD)
    N.chord(A, 186, -460, 460, FLICK, FLICK)
    N.stream(A, F(745, 4), 187, trill(200), dens=5, chords=0)
    A.at(187, col=CY)
    N.stream(A, 187, 188, stair(120, 480, 4), dens=5, chords=1, seed=81)
    for b in (188, 189, 190, 191):
        A.at(b, col=GD if b < 190 else (CY if b % 2 == 0 else RD)).to(b, b + F(1, 4), "expoOut", rot=(8, -8, 8, -8)[b - 188])
        N.stream(A, b, b + 1, zig(320, 110, 1), dens=5, chords=1, seed=b)
    A.to(F(767, 4), 192, rot=0)

    # ======== THE WHEEL (192), reaching (193-196), vertigo (196-203)
    A.at(192, col=W_)
    X.at(192, col=W_, rot=90, y=0, x=0).to(192, F(385, 2), "backOut", rot=45, a=255)
    A.to(192, F(385, 2), "backOut", rot=-45, y=0)
    A.mirror = False
    N.chord(A, 192, -360, 360, FLICK, FLICK)
    N.chord(X, F(193, 1), -300, 300)
    N.stream(A, F(1541, 8), 193, trill(200), dens=4, chords=0)
    X.to(193, F(387, 2), a=0)
    A.to(193, F(387, 2), "quartOut", rot=0, y=-250)
    N.hold(A, F(387, 2), 196, -380)
    N.taps_on(A, F(387, 2), 196, 4, lambda b, i: 100 + 120 * (i % 4))
    A.at(196, col=CY).to(196, 203, "sineIn", spd=12)
    N.stream(A, 196, 202, stair(100, 520, 4), dens=5, chords=2, seed=82)
    A.at(202, col=W_)
    N.chord(A, 202, -440, 440, FLICK, FLICK)
    N.stream(A, F(809, 4), 203, trill(160), dens=5, chords=0)

    # ======== deep blue, the sphere, smoke, cyan lightning, embers (203-216)
    A.at(203, col=CY, spd=10)
    T.at(203, col=CY).to(203, F(407, 2), a=255)
    for k, b in enumerate(range(203, 208)):
        N.stream(A if k % 2 == 0 else T, b, b + F(3, 4), zig(280, 120, 2), dens=4, chords=2 if k % 2 == 0 else 1, seed=90 + k)
    T.to(208, F(417, 2), a=0)
    N.stream(A, 208, 209, stair(120, 460, 4), dens=4, chords=1, seed=95)
    N.drags(A, 209, F(419, 2), lambda b: -400 + 1600 * (b - 209), step=F(1, 8))
    N.stream(A, F(419, 2), 210, trill(200), dens=5, chords=0)
    A.at(210, col=W_)
    N.hold(A, 210, 211, -300)
    N.taps_on(A, 210, 211, 3, lambda b, i: 160 + 120 * (i % 3))
    N.hold(A, 211, 212, 300)
    N.taps_on(A, 211, 212, 3, lambda b, i: -160 - 120 * (i % 3))
    A.at(212, col=CY)
    for k, b in enumerate((212, F(849, 4), F(425, 2))):
        N.burst(A, b, [-440 + 90 * k, 200 + 90 * k], gap=F(1, 8))
    N.add(A, F(851, 4), -160)
    N.stream(A, 213, 214, zig(320, 120, 1), dens=5, chords=1, seed=96)
    A.at(214, col=RD)
    N.stream(A, 214, 215, stair(100, 520, 4), dens=5, chords=1, seed=97)
    N.stream(A, 215, F(863, 4), zig(340, 120, 1), dens=5, chords=1, seed=98)
    N.chord(A, F(863, 4), -460, 460, FLICK, FLICK)
    hide_all(216)
    return A, T, X


def build(chart):
    m = Music()
    G = PlayGlobals(chart)
    E = Engine(chart, G.root.index)
    E.mask = MASK
    MS.storyboard(E, G)
    E.bake()
    G.emit(random.Random(7))
    N = Notes(m)
    chart_notes(chart, N)
    n = N.write()
    c = chart
    c.effect("vignette", 0, END, {"extend": 0.2, "radius": 18.0})
    for b0, b1, p in ((4, 5, 0.006), (24, 25, 0.009), (29, 30, 0.007), (125, 126, 0.009), (129, 131, 0.008), (186, 187, 0.009)):
        c.effect("chromatic", b0, b1, {"power": c.var_kfs([(b0, p, "quadOut"), (b1, p * 0.3, "linear")]), "sampleCount": 5.0})
    for b0, b1, p in ((64, 65, 0.02), (96, 97, 0.02), (116, 117, 0.025), (186, 187, 0.02)):
        c.effect("radialBlur", b0, b1, {"power": c.var_kfs([(b0, p, "quadOut"), (b0 + F(1, 2), 0.0, "linear")]), "sampleCount": 8.0})
    for b in (24, 64, 96, 116, 192):
        c.effect("shockwave", b, b + 1.5, {"progress": c.var_kfs([(b, 0.02, "quadOut"), (b + 1.5, 0.95, "linear")]),
                                           "width": 0.08, "distortion": 0.5, "expand": 10.0})
    for b0, b1, path in VIDEOS:
        c.video(path, b0)
    return E, n


def make():
    c = Chart(OFFSET_MS, dict(INFO, id="claude-shinjuku-at"), bpm=BPM, compact=True)
    E, n = build(c)
    print(f"pooled lines: {E.line_count()}  notes: {n}")
    return c, INFO


def assets(out):
    MS.assets(out)
    clips = os.environ.get("MAD_CLIPS")
    for _, _, name in VIDEOS:
        src = os.path.join(clips, name) if clips else None
        if src and os.path.exists(src):
            shutil.copy(src, os.path.join(out, name))
        else:
            print(f"warning: footage {name} not found (set MAD_CLIPS); the package will not load without it", file=sys.stderr)
