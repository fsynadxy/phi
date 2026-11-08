"""新宿决战 — a playable chart (IN Lv.16, constant 16.2) with the original MAD footage at four moments.

* Four moments play the original footage of NinjaristicNinja's Shinjuku Showdown MAD as Phira videos
  (extra.json "videos"): 200% Hollow Purple (beats 73-82), the first domain clash (105-113), the second
  domain clash (144-154) and Unlimited Hollow Purple (216-end). While a clip plays nothing else is drawn:
  the background, the judge line and the HUD step aside, and there are no notes. The judge line fades back
  in over the last beat of each clip.
* Everywhere else: a plain dark background that only shifts its tint with the scenes, one static judge
  line, and notes on seven fixed lanes spread over the whole width (left hand lanes 0-2, right hand 4-6, the
  middle lane for chords, sweeps and bursts).
  The rhythm is the song's 16th-grid onsets (tools/data/mad/steps.npz).
* The footage is not part of the repository (the repo is public). Point MAD_CLIPS at a folder holding
  clip_a.mp4 .. clip_d.mp4 when building; tools/analysis/cut_clips.py cuts them from the video.

Beat k = beat k of the song (153.6 BPM, first beat 0.2935 s), exactly as in mad_shinjuku.py.
"""
import os
import random
import shutil
import sys

import numpy as np

import madlib as ML
import mad_shinjuku as MS
from chartlib import Chart, DRAG, EPSB, FLICK, HOLD, TAP, frac
from madlib import TL

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "mad")
BPM, OFFSET_MS = MS.BPM, MS.OFFSET_MS
F = MS.F
END = 240
VIDEOS = [(73, 82, "clip_a.mp4"), (105, 113, "clip_b.mp4"), (144, 154, "clip_c.mp4"), (216, END, "clip_d.mp4")]
MASK = [(a, b) for a, b, _ in VIDEOS]

INFO = {
    "name": "新宿决战",
    "difficulty": 16.2,
    "level": "IN Lv.16",
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
    "tags": ["新宿决战", "MAD", "视频", "IN"],
    "intro": "四个名场面（200% 虚式「茈」、两次领域对拼、无限制虚式）播放原 MAD 素材，其余部分按 IN 16.2 制谱，七轨分布。",
    "holdPartialCover": False,
    "noteUniformScale": False,
    "forceAspectRatio": False,
    "useRpe170Speed": False,
    "useAttachUiFix": True,
}

W_ = (238, 243, 250)
CY = (96, 226, 255)
RD = (255, 78, 92)
PU = (200, 136, 255)
GD = (255, 224, 150)

# seven lanes, 180 RPE units apart (a note is ~178 wide): the whole width, no two lanes overlap
LANES = [-540, -360, -180, 0, 180, 360, 540]
CYCLES = {  # per-hand lane cycles: left hand lanes 0-2, right hand 4-6
    "open": ((2, 1, 0), (4, 5, 6)),
    "close": ((0, 1, 2), (6, 5, 4)),
    "wave": ((0, 1, 2, 1), (6, 5, 4, 5)),
    "parallel": ((0, 1, 2, 1), (4, 5, 6, 5)),
    "wide": ((0, 1), (6, 5)),
    "inner": ((2, 1), (4, 5)),
    "spread": None,  # random, lanes 0-2 / 4-6, never the same lane twice in a row
}
# the climaxes: streams written at density 4 are charted at full 16ths here
INTENSE = [(24, 35), (40, 44), (48, 53), (64, 73), (82, 96), (113, 125), (129, 144), (161, 176), (186, 192), (196, 203),
           (212, 216)]
CHORDS = [(0, 6), (1, 5), (2, 4), (0, 4), (2, 6), (1, 4), (2, 5), (1, 6), (0, 5)]


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
        self.k, self.lm, self.sn, self.h = (n(d[k]) for k in ("low_p", "lmid_p", "mid_p", "high_p"))
        self.n = len(self.k)

    def st(self, s):
        if not 0 <= s < self.n:
            return 0.0
        return float(max(self.k[s], self.lm[s], self.sn[s], self.h[s]))

    def keep(self, s, dens):
        """is 16th step s part of the rhythm at density dens (2 eighths, 3 + strong 16ths, 4 + most, 5 all)?"""
        v = self.st(s)
        if s % 4 == 0:
            return v > 0.12
        if s % 2 == 0:
            return dens >= 2 and v > 0.25
        return {1: 9, 2: 9, 3: 0.62, 4: 0.36, 5: 0.1}[dens] < v


# ------------------------------------------------------------------ the judge line
P = {"x": "moveX", "y": "moveY", "rot": "rotate", "a": "alpha", "spd": "speed", "col": "color"}


class JL:
    """a judge line with chronological property writers (RPE units, alpha 0..255)."""

    def __init__(self, c, name, z, x=0.0, y=-250.0, rot=0.0, alpha=0.0, speed=9.0, color=W_):
        self.ln = c.line(name, z=z)
        self.tl = {}
        for p, v in (("moveX", x), ("moveY", y), ("rotate", rot), ("alpha", alpha), ("speed", speed), ("color", color)):
            v = tuple(v) if p == "color" else float(v)
            self.ln.ev(p, 0, EPSB, v, v)
            self.tl[p] = TL(self.ln, p, v)

    def at(self, b, **vals):
        b = frac(b)
        for k, v in vals.items():
            v = tuple(v) if k == "col" else float(v)
            t = self.tl[P[k]]
            if t.b == b + EPSB:  # a second jump on the same beat replaces the first one
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


# ------------------------------------------------------------------ lanes and notes
class Picker:
    def __init__(self, style, seed):
        self.cyc = CYCLES[style]
        self.R = random.Random(seed)
        self.i = [0, 0]
        self.last = [None, None]
        self.prev = None
        self.ci = seed

    def lane(self, h):
        if self.cyc:
            c = self.cyc[h]
            ln = c[self.i[h] % len(c)]
            self.i[h] += 1
            if ln == self.last[h] or ln == self.prev:
                ln = c[self.i[h] % len(c)]
                self.i[h] += 1
        else:
            opts = [ln for ln in ((0, 1, 2) if h == 0 else (4, 5, 6)) if ln not in (self.last[h], self.prev)]
            ln = self.R.choice(opts)
        self.last[h] = self.prev = ln
        return ln

    def chord(self):
        a, b = CHORDS[self.ci % len(CHORDS)]
        self.ci += 1
        self.last, self.prev = [a, b], None
        return a, b


class Notes:
    def __init__(self, music, jl):
        self.m = music
        self.jl = jl
        self.items = []

    def add(self, b, lane, kind=TAP, end=None):
        b = frac(b)
        e = frac(end) if end is not None else None
        if masked(b) or (e is not None and masked(b, e)):
            raise ValueError(f"note at beat {float(b)} falls inside a footage segment")
        self.items.append((b, LANES[lane], kind, e))

    def stream(self, b0, b1, style, dens=4, chords=2, flicks=0.35, seed=0, skip=(), chord_th=0.55):
        """the song's 16th rhythm at density dens, alternating hands; chords on kicks every `chords` beats,
        flicks on some backbeats."""
        pk = Picker(style, seed)
        R = random.Random(seed)
        if dens == 4 and any(h0 <= float(b0) < h1 for h0, h1 in INTENSE):
            dens = 5
        hand = 0
        skip = {frac(b) for b in skip}
        for s in range(round(float(b0) * 4), round(float(b1) * 4)):
            b = frac(s, 4)
            if b in skip or masked(b) or not self.m.keep(s, dens):
                continue
            if s % 4 == 0 and chords and (s // 4) % chords == 0 and self.m.k[s] > chord_th:
                a, c = pk.chord()
                self.add(b, a)
                self.add(b, c)
                hand = 1 - hand
                continue
            kind = FLICK if s % 8 == 4 and self.m.sn[s] > 0.6 and R.random() < flicks else TAP
            self.add(b, pk.lane(hand), kind)
            hand = 1 - hand

    def hold_taps(self, b0, b1, lane, dens=4, seed=0):
        """one hand holds `lane`, the other taps the rhythm on the opposite side"""
        self.add(b0, lane, HOLD, end=b1)
        side = (4, 5, 6) if lane <= 3 else (0, 1, 2)
        R = random.Random(seed)
        last = None
        for s in range(round(float(b0) * 4) + 1, round(float(b1) * 4)):
            if self.m.keep(s, dens):
                ln = R.choice([x for x in side if x != last])
                self.add(frac(s, 4), ln)
                last = ln

    def sweep(self, b0, lanes, step=F(1, 4), kind=DRAG):
        for k, ln in enumerate(lanes):
            self.add(frac(b0) + frac(step) * k, ln, kind)

    def sweep_taps(self, b0, b1, lanes, tap_side, dens=3, seed=0):
        """drags walking `lanes` (one per 8th) while the other hand taps the rhythm on tap_side lanes"""
        k = 0
        b = frac(b0)
        while b < frac(b1):
            self.add(b, lanes[k % len(lanes)], DRAG)
            b += F(1, 2)
            k += 1
        R = random.Random(seed)
        last = None
        for s in range(round(float(b0) * 4), round(float(b1) * 4)):
            if s % 2 == 0 or not self.m.keep(s, dens):
                continue
            ln = R.choice([x for x in tap_side if x != last])
            self.add(frac(s, 4), ln)
            last = ln

    def chord(self, b, a, c, ka=TAP, kc=TAP):
        self.add(b, a, ka)
        self.add(b, c, kc)

    def burst(self, b, lanes, gap=F(1, 8), kind=FLICK):
        for k, ln in enumerate(lanes):
            self.add(frac(b) + frac(gap) * k, ln, kind)

    def write(self):
        for b, x, kind, e in self.items:
            self.jl.ln.note(kind, b, x, end=e)
        return len(self.items)


# ------------------------------------------------------------------ background (plain tint) and HUD
BG = [(0, (12, 16, 26)), (1, (28, 10, 14)), (2, (12, 16, 26)), (24, (40, 8, 12)), (35, (14, 18, 28)), (52, (36, 10, 14)),
      (56, (16, 20, 30)), (64, (10, 14, 36)), (71, (34, 14, 10)), (82, (12, 16, 26)), (89, (38, 8, 12)), (92, (12, 16, 26)),
      (96, (8, 22, 32)), (102, (28, 16, 26)), (104, (10, 12, 18)), (113, (30, 14, 24)), (118, (12, 18, 28)), (125, (40, 8, 12)),
      (131, (18, 10, 14)), (135, (8, 20, 30)), (154, (24, 16, 16)), (161, (34, 10, 12)), (163, (10, 18, 30)), (176, (12, 16, 32)),
      (180, (36, 10, 12)), (186, (40, 20, 10)), (188, (16, 16, 24)), (192, (8, 8, 12)), (196, (12, 16, 26)), (203, (10, 16, 48)),
      (210, (22, 22, 26)), (214, (36, 8, 12))]


def background(c):
    bg = c.line("bg", texture="white.png", z=-100)
    sx, sy = 1800 / (64 * ML.TEXK), 1000 / (64 * ML.TEXK)
    for p, v in (("moveX", 0.0), ("moveY", 0.0), ("rotate", 0.0), ("scaleX", sx), ("scaleY", sy), ("alpha", 255.0)):
        bg.ev(p, 0, EPSB, v, v)
    bg.ev("color", 0, EPSB, BG[0][1], BG[0][1])
    col = TL(bg, "color", BG[0][1])
    for b, cc in BG[1:]:
        col.wait(b)
        col.to(frac(b) + F(1, 2), cc, "quadOut")
    lines = [bg]
    for ui in ("pause", "combonumber", "combo", "score", "bar", "name", "level"):
        h = c.line(f"hud_{ui}")
        h.attach = ui
        for p, v in (("moveX", 0.0), ("moveY", 0.0), ("rotate", 0.0), ("alpha", 255.0), ("scaleX", 1.0), ("scaleY", 1.0)):
            h.ev(p, 0, EPSB, v, v)
        lines.append(h)
    tracks = [TL(ln, "alpha", 255.0) for ln in lines]
    for m0, m1 in MASK:
        for t in tracks:
            t.jump(m0, 0.0)
            if m1 < END:
                t.jump(m1, 255.0)


# ------------------------------------------------------------------ the chart
def chart_notes(A, N):
    m = N.m  # noqa: F841

    def back(b, col, spd=9.0):  # after a clip: the line fades in over the clip's last beat
        A.at(b - 1, col=col, spd=spd).to(b - 1, b, "quadIn", a=255)

    # ======== intro: flames, clash, slash, title (0-4)
    A.to(0, 1, "quadOut", a=255)
    N.chord(1, 1, 5)
    A.at(1, col=RD)
    N.add(F(3, 2), 2)
    N.add(F(7, 4), 4)
    A.at(2, col=W_)
    N.chord(2, 0, 6)
    N.stream(F(9, 4), 3, "inner", dens=5, chords=0)
    N.burst(3, [1, 3, 5], gap=F(1, 4))
    N.chord(4, 0, 6, FLICK, FLICK)

    # ======== verse (4-24)
    N.stream(F(17, 4), 8, "spread", dens=3, chords=2, seed=1)
    A.at(8, col=CY)
    N.stream(8, 12, "parallel", dens=4, chords=2, seed=2)
    A.at(12, col=W_)
    N.stream(12, 15, "close", dens=4, chords=2, seed=3)
    N.stream(15, 17, "wave", dens=4, chords=2, seed=4)
    N.stream(17, 19, "open", dens=4, chords=2, seed=5)
    N.hold_taps(19, F(41, 2), 1, dens=4, seed=6)
    N.hold_taps(F(41, 2), 22, 5, dens=4, seed=7)
    A.at(22, col=RD)
    N.stream(22, F(47, 2), "spread", dens=4, chords=2, seed=8)
    N.burst(F(47, 2), [0, 4, 2], gap=F(1, 8), kind=TAP)

    # ======== Sukuna (24-35)
    A.at(24, col=RD, spd=9.5)
    N.chord(24, 0, 6, FLICK, FLICK)
    N.stream(F(97, 4), 25, "wide", dens=5, chords=0)
    N.sweep_taps(25, 29, (4, 5, 6, 5), (0, 1, 2), dens=4, seed=9)
    A.at(29, col=W_)
    N.chord(29, 1, 5, FLICK, TAP)
    N.stream(F(117, 4), 30, "close", dens=5, chords=0, seed=10)
    A.at(30, col=RD)
    N.stream(30, 33, "spread", dens=4, chords=2, seed=11)
    N.chord(33, 0, 6, FLICK, FLICK)
    N.stream(F(133, 4), 35, "open", dens=4, chords=0, seed=12)

    # ======== rooftop, the eye in the white, distant eyes (35-44)
    A.at(35, col=W_, spd=9)
    N.stream(35, 38, "parallel", dens=4, chords=2, seed=13)
    A.at(38, col=CY)
    N.chord(38, 2, 4)
    N.hold_taps(F(153, 4), 40, 1, dens=4, seed=14)
    A.at(40, col=W_)
    N.stream(40, 42, "wave", dens=4, chords=2, seed=15)
    A.at(42, col=RD)
    N.stream(42, 44, "spread", dens=4, chords=2, seed=16)

    # ======== spectators: a chord on every panel (44-48)
    A.at(44, col=W_)
    for k, b in enumerate(range(44, 48)):
        N.chord(b, *((0, 4), (2, 6), (1, 5), (0, 6))[k])
        N.stream(b + F(1, 4), b + 1, "spread", dens=4, chords=0, seed=20 + k)

    # ======== profile, rooftop, red skyline, claws, triple slash (48-56)
    N.chord(48, 1, 5, FLICK, TAP)
    N.stream(F(193, 4), 52, "spread", dens=4, chords=2, seed=24)
    A.at(52, col=RD)
    N.stream(52, 53, "wide", dens=5, chords=2)
    N.sweep_taps(53, 55, (2, 1, 0, 1), (4, 5, 6), dens=4, seed=25)
    A.at(55, col=W_)
    N.burst(55, [1, 5, 2], gap=F(1, 8))
    N.stream(F(223, 4), 56, "inner", dens=5, chords=0)

    # ======== footsteps, the old man, the break (56-64)
    N.stream(56, 60, "close", dens=4, chords=2, seed=26)
    N.hold_taps(60, 62, 2, dens=2, seed=27)
    N.hold_taps(62, 63, 4, dens=3, seed=28)
    N.stream(63, 64, "open", dens=5, chords=0, seed=29)

    # ======== domain expansion (64-73)
    A.at(64, col=CY)
    N.chord(64, 0, 6, FLICK, FLICK)
    N.stream(F(257, 4), 66, "spread", dens=4, chords=2, seed=30)
    A.at(66, col=PU)
    N.stream(66, 68, "wave", dens=4, chords=2, seed=31)
    N.stream(68, 71, "spread", dens=4, chords=2, seed=32)
    A.at(71, col=GD)
    N.stream(71, 73, "parallel", dens=5, chords=2, seed=33)
    A.at(73, a=0)

    # ======== [footage: 200% Hollow Purple] -- the exchange (82-96), one cut per beat
    back(82, CY, 9.5)
    plan = {82: CY, 83: CY, 84: RD, 85: CY, 86: CY, 87: W_, 88: CY, 89: RD, 90: RD, 91: RD, 92: CY, 93: W_, 94: W_, 95: CY}
    for b, col in plan.items():
        A.at(b, col=col)
        if b in (84, 91):
            N.chord(b, 0, 6, FLICK, FLICK)
            N.stream(b + F(1, 4), b + 1, "inner", dens=4, chords=0, seed=b)
        elif b in (89, 90):
            N.burst(b, [1, 5] if b == 89 else [5, 1], gap=F(1, 8))
            N.stream(b + F(1, 2), b + 1, "wide", dens=4, chords=0, seed=b)
        elif b == 87:
            N.stream(b, b + 1, "wide", dens=2, chords=1)
        elif b in (93, 94):
            N.sweep(b, (6, 5, 4, 3) if b == 93 else (0, 1, 2, 3), step=F(1, 4))
            N.add(b + F(1, 2), 1 if b == 93 else 5)
        else:
            N.stream(b, b + 1, "spread", dens=4, chords=1, seed=b)

    # ======== the drop (96-105)
    A.at(96, col=CY)
    N.chord(96, 0, 6, FLICK, FLICK)
    N.stream(F(385, 4), 97, "wide", dens=4, chords=0)
    A.at(97, col=W_)
    N.stream(97, 100, "spread", dens=4, chords=2, seed=40)
    N.burst(100, [0, 6, 2], gap=F(1, 4))
    N.burst(101, [1, 5, 2], gap=F(1, 8))
    N.stream(F(203, 2), 102, "inner", dens=4, chords=0)
    A.at(102, col=PU)
    N.stream(102, 103, "spread", dens=4, chords=1, seed=44)
    A.at(103, col=W_)
    N.sweep(103, (0, 1, 2, 3, 4, 5, 6), step=F(1, 8))
    N.add(F(415, 4), 1)
    A.at(104, col=CY)
    N.chord(104, 2, 4)
    N.stream(F(417, 4), 105, "wide", dens=4, chords=0)
    A.at(105, a=0)

    # ======== [footage: first domain clash] -- the black sphere, black flash (113-118)
    back(113, PU, 8.5)
    N.stream(113, 114, "wide", dens=2, chords=1)
    N.stream(114, F(463, 4), "open", dens=4, chords=0, seed=50)
    A.at(116, col=W_)
    N.chord(116, 0, 6, FLICK, FLICK)
    N.stream(F(465, 4), 118, "spread", dens=4, chords=2, seed=51)

    # ======== slashes across the face (118-125)
    for b in (118, F(239, 2), 120, 122):
        A.at(b, col=RD).at(b + F(1, 2), col=W_)
        N.chord(b, 1, 5, FLICK, FLICK)
    N.stream(F(473, 4), F(239, 2), "spread", dens=4, chords=0, seed=52)
    N.stream(F(479, 4), 120, "inner", dens=4, chords=0)
    N.stream(F(481, 4), 122, "parallel", dens=4, chords=2, seed=53)
    N.stream(F(489, 4), 124, "spread", dens=4, chords=2, seed=54)
    A.at(124, col=CY)
    N.chord(124, 2, 4)
    N.stream(F(497, 4), 125, "wide", dens=4, chords=0)

    # ======== red impact, mudra, shrine, the great eye (125-135)
    A.at(125, col=RD)
    N.chord(125, 0, 6, FLICK, FLICK)
    N.stream(F(501, 4), 126, "close", dens=4, chords=0, seed=55)
    N.hold_taps(126, F(255, 2), 1, dens=4, seed=56)
    N.hold_taps(F(255, 2), 129, 5, dens=4, seed=57)
    A.at(129, col=W_)
    N.stream(129, 131, "wave", dens=4, chords=1, seed=58)
    A.at(131, col=RD)
    N.stream(131, 135, "spread", dens=4, chords=2, seed=59)

    # ======== the barrier, the exchange, slash streaks (135-144)
    A.at(135, col=CY)
    N.stream(135, 137, "parallel", dens=4, chords=2, seed=60)
    for b in (137, 138, 139):
        A.at(b, col=RD if b == 138 else CY)
        N.stream(b, b + 1, "spread", dens=4, chords=1, seed=b)
    A.at(140, col=W_)
    N.burst(140, [0, 4, 2], gap=F(1, 8))
    N.stream(F(281, 2), 141, "inner", dens=4, chords=0)
    for k, b in enumerate((141, 142, 143)):
        A.at(b, col=RD if b == 142 else W_)
        N.chord(b, *((1, 5), (0, 4), (2, 6))[k], FLICK if b == 143 else TAP, TAP)
        N.stream(b + F(1, 4), b + 1, "spread", dens=4, chords=0, seed=b)
    A.at(144, a=0)

    # ======== [footage: second domain clash] -- the standoff, the break (154-161)
    back(154, W_, 8.0)
    N.stream(154, 156, "wide", dens=3, chords=2, seed=70)
    N.add(156, 1, HOLD, end=158)
    N.add(156, 5, HOLD, end=157)
    N.add(157, 4, HOLD, end=158)
    N.hold_taps(158, 160, 5, dens=3, seed=71)
    A.at(160, spd=9.5)
    N.stream(160, 161, "open", dens=5, chords=0, seed=72)

    # ======== bleeding eyes, cyan punch, silhouettes, the beam (161-170)
    A.at(161, col=RD)
    N.chord(161, 1, 5, FLICK, FLICK)
    N.sweep(F(645, 4), (1, 1, 1), step=F(1, 4))
    N.sweep(F(645, 4), (5, 5, 5), step=F(1, 4))
    N.stream(162, 163, "spread", dens=4, chords=1, seed=73)
    A.at(163, col=CY)
    N.sweep_taps(163, 165, (6, 5, 4, 5), (0, 1, 2), dens=4, seed=74)
    A.at(165, col=W_)
    N.stream(165, 167, "parallel", dens=4, chords=2, seed=75)
    A.at(167, col=CY)
    N.chord(167, 0, 6, TAP, FLICK)
    N.hold_taps(F(669, 4), 169, 6, dens=4, seed=76)
    A.at(169, col=RD)
    N.stream(169, 170, "spread", dens=4, chords=1, seed=77)

    # ======== the wheel above the head, orbs, fire (170-176)
    A.at(170, col=W_)
    N.stream(170, 172, "wave", dens=4, chords=2, seed=78)
    A.at(172, col=CY)
    N.stream(172, 173, "spread", dens=4, chords=1, seed=79)
    A.at(173, col=GD)
    N.stream(173, 175, "spread", dens=4, chords=1, seed=80)
    A.at(175, col=W_)
    N.stream(175, 176, "open", dens=4, chords=0, seed=81)

    # ======== the blue orb, the great cyan eye, the red orb, the explosion (176-192)
    A.at(176, col=CY)
    N.stream(176, 178, "close", dens=4, chords=2, seed=82)
    N.chord(178, 0, 6, FLICK, FLICK)
    N.stream(F(713, 4), 179, "inner", dens=4, chords=0)
    N.chord(179, 1, 5)
    N.stream(F(717, 4), 180, "wide", dens=4, chords=0)
    A.at(180, col=RD)
    N.sweep_taps(180, 183, (0, 1, 2, 1), (4, 5, 6), dens=4, seed=83)
    N.chord(183, 0, 6, FLICK, FLICK)
    N.stream(F(733, 4), 185, "spread", dens=4, chords=2, seed=84)
    N.sweep(185, (0, 1, 2, 3, 4, 5, 6), step=F(1, 8))
    N.add(F(371, 2), 1)
    A.at(186, col=GD)
    N.chord(186, 0, 6, FLICK, FLICK)
    N.stream(F(745, 4), 187, "inner", dens=4, chords=0)
    A.at(187, col=CY)
    N.stream(187, 188, "open", dens=4, chords=1, seed=85)
    for b in (188, 189, 190, 191):
        A.at(b, col=GD if b < 190 else (CY if b % 2 == 0 else RD))
        N.stream(b, b + 1, "spread", dens=4, chords=1, seed=b)

    # ======== THE WHEEL (192), reaching (193-196), vertigo (196-203)
    A.at(192, col=W_)
    N.chord(192, 0, 6, FLICK, FLICK)
    N.stream(F(769, 4), F(387, 2), "wide", dens=4, chords=0)
    N.hold_taps(F(387, 2), 196, 1, dens=4, seed=86)
    A.at(196, col=CY)
    N.stream(196, 199, "parallel", dens=4, chords=2, seed=87)
    N.stream(199, 202, "spread", dens=4, chords=2, seed=88)
    A.at(202, col=W_)
    N.chord(202, 0, 6, FLICK, FLICK)
    N.stream(F(809, 4), 203, "inner", dens=4, chords=0)

    # ======== deep blue, the sphere, smoke, cyan lightning, embers (203-216)
    A.at(203, col=CY)
    N.stream(203, 208, "spread", dens=4, chords=2, seed=89)
    N.stream(208, 209, "wave", dens=4, chords=1, seed=90)
    N.sweep(209, (6, 5, 4, 3), step=F(1, 8))
    N.stream(F(419, 2), 210, "wide", dens=4, chords=0)
    A.at(210, col=W_)
    N.hold_taps(210, 211, 1, dens=3, seed=91)
    N.hold_taps(211, 212, 5, dens=3, seed=92)
    A.at(212, col=CY)
    for k, b in enumerate((212, F(849, 4), F(425, 2))):
        N.burst(b, [(0, 4), (1, 5), (2, 6)][k], gap=F(1, 8))
    N.add(F(851, 4), 1)
    N.stream(213, 214, "spread", dens=4, chords=1, seed=93)
    A.at(214, col=RD)
    N.stream(214, F(863, 4), "spread", dens=4, chords=1, seed=94)
    N.chord(F(863, 4), 0, 6, FLICK, FLICK)
    A.at(216, a=0)


def build(chart):
    c = chart
    background(c)
    A = JL(c, "judge", 110, y=-250, speed=9.0, color=CY)
    N = Notes(Music(), A)
    chart_notes(A, N)
    n = N.write()
    for b0, b1 in ((0, 73), (82, 105), (113, 144), (154, 216)):
        c.effect("vignette", b0, b1, {"extend": 0.2, "radius": 18.0})
    for b0, b1, path in VIDEOS:
        c.video(path, b0)
    return n


def make():
    c = Chart(OFFSET_MS, dict(INFO, id="claude-shinjuku-in"), bpm=BPM, compact=True)
    n = build(c)
    print(f"notes: {n}")
    return c, INFO


def assets(out):
    import mad_assets
    os.makedirs(out, exist_ok=True)
    mad_assets.save(np.ones((64, 64, 4), np.float32), out, "white.png")
    ill = os.path.join(DATA, "illustration.jpg")
    shutil.copy(ill, os.path.join(out, "illustration.jpg"))
    clips = os.environ.get("MAD_CLIPS")
    for _, _, name in VIDEOS:
        src = os.path.join(clips, name) if clips else None
        if src and os.path.exists(src):
            shutil.copy(src, os.path.join(out, name))
        else:
            print(f"warning: footage {name} not found (set MAD_CLIPS); the package will not load without it", file=sys.stderr)
