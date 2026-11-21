"""Building blocks for the world.execute(me); chart: music data, judge lines, the note writer, the stage.

Units: physical canvas x in [-800, 800], y in [-450, 450] (16:9, isotropic, +y up), rotation in degrees
(+ clockwise, as RPE). Beat k = beat k of the song (130 BPM, beat 0 at 0.2205 s); bars start on beats 0 mod 4.
"""
import math
import os
import random
from fractions import Fraction as F

import numpy as np

import madlib as ML
from chartlib import DRAG, EPSB, FLICK, HOLD, TAP, frac
from madlib import TL, Engine

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "wem")
PX = ML.PX
LINE_LEN = ML.LINE_LEN  # physical half length of a normal line per scaleX unit


# ------------------------------------------------------------------ palette (sampled from the cover)
INK = (8, 10, 18)
NIGHT = (14, 16, 34)
WHITE = (255, 255, 255)
PALE = (232, 236, 255)
TERM = (110, 255, 140)       # terminal green
NEON = (150, 240, 110)       # wing green
CYAN = (70, 232, 220)
TEAL = (30, 150, 160)
MAGENTA = (236, 64, 150)
PINK = (255, 120, 190)
RED = (236, 40, 64)
CRIMSON = (150, 20, 40)
VIOLET = (130, 116, 255)     # the ring
PURPLE = (120, 64, 196)
YELLOW = (255, 214, 48)
ORANGE = (255, 150, 60)
GOLD = (255, 214, 130)
BLUE = (40, 60, 220)
SKY = (120, 176, 230)


def mix(a, b, t):
    return tuple(round(p + (q - p) * t) for p, q in zip(a, b))


def hsv(h, s=1.0, v=1.0):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (round(r * 255), round(g * 255), round(b * 255))


# ------------------------------------------------------------------ music (per 16th step; step 4k = beat k)
class Music:
    def __init__(self):
        d = np.load(os.path.join(DATA, "stems.npz"))
        self.kick, self.snare, self.hat, self.synth, self.bass = (d[k] for k in ("kick", "snare", "hat", "synth", "bass"))
        self.syl, self.pitch, self.vp = d["syl"], d["pitch"], d["v_pres"]
        self.n = len(self.kick)

    def g(self, arr, s):
        return float(arr[s]) if 0 <= s < self.n else 0.0

    def vocal(self, b0, b1, th=0.3, min_gap=F(1, 4)):
        """syllables in [b0, b1): dicts b, w (strength), p (pitch, MIDI), sus (sustain in beats)."""
        out = []
        s0, s1 = round(float(b0) * 4), round(float(b1) * 4)
        for s in range(s0, s1):
            w = self.g(self.syl, s)
            if w < th:
                continue
            b = F(s, 4)
            if out and b - out[-1]["b"] < min_gap:
                if w > out[-1]["w"]:
                    out[-1] = dict(out[-1], b=b, w=w, p=self.g(self.pitch, s))
                continue
            p = self.g(self.pitch, s) or (out[-1]["p"] if out else 62.0)
            out.append({"b": b, "w": w, "p": p, "src": "v"})
        for i, e in enumerate(out):  # sustain: voiced steps until the next syllable
            s = round(float(e["b"]) * 4) + 1
            nxt = round(float(out[i + 1]["b"]) * 4) if i + 1 < len(out) else s1
            k = s
            while k < nxt and self.g(self.vp, k) > 0.5:
                k += 1
            e["sus"] = F(k - round(float(e["b"]) * 4), 4)
        return out

    def drums(self, b0, b1, kick=0.45, snare=9.0, hat=9.0, grid=1):
        """percussive hits on a grid of `grid` 16ths: dicts b, w, src in k/s/h."""
        out = []
        for s in range(round(float(b0) * 4), round(float(b1) * 4)):
            if s % grid:
                continue
            k, sn, h = self.g(self.kick, s), self.g(self.snare, s), self.g(self.hat, s)
            src = None
            if k >= kick:
                src, w = "k", k
            elif sn >= snare:
                src, w = "s", sn
            elif h >= hat:
                src, w = "h", h
            if src:
                out.append({"b": F(s, 4), "w": w, "p": 62.0, "sus": F(0), "src": src})
        return out

    def synths(self, b0, b1, th=0.6, grid=2):
        out = []
        for s in range(round(float(b0) * 4), round(float(b1) * 4)):
            if s % grid == 0 and self.g(self.synth, s) >= th:
                out.append({"b": F(s, 4), "w": self.g(self.synth, s), "p": 62.0, "sus": F(0), "src": "y"})
        return out


def merge(*lists, gap=F(1, 4)):
    """merge event lists; events closer than `gap` keep the stronger (vocals win ties)."""
    allv = sorted((e for L in lists for e in L), key=lambda e: (e["b"], e["src"] != "v"))
    out = []
    for e in allv:
        if out and e["b"] - out[-1]["b"] < gap:
            if out[-1]["src"] != "v" and e["w"] > out[-1]["w"]:
                out[-1] = e
            continue
        out.append(e)
    return out


# ------------------------------------------------------------------ judge lines
P = {"x": "moveX", "y": "moveY", "rot": "rotate", "a": "alpha", "spd": "speed", "col": "color", "sx": "scaleX",
     "sy": "scaleY"}


class JL:
    """a judge line (physical units for x) with chronological property writers."""

    def __init__(self, c, name, z=0, father=-1, x=0.0, y=-260.0, rot=0.0, alpha=0.0, speed=9.0, color=WHITE, sx=1.0,
                 sy=1.0, cover=True):
        self.ln = c.line(name, z=z, father=father, rot_with_father=True, cover=cover)
        self.tl = {}
        self.name = name
        for k, v in (("x", x), ("y", y), ("rot", rot), ("a", alpha), ("spd", speed), ("col", color), ("sx", sx),
                     ("sy", sy)):
            v = self._conv(k, v)
            self.ln.ev(P[k], 0, EPSB, v, v)
            self.tl[k] = TL(self.ln, P[k], v)
        self.notes = []

    @staticmethod
    def _conv(k, v):
        if k == "col":
            return tuple(int(c) for c in v)
        if k == "x":
            return float(v) * PX
        return float(v)

    def at(self, b, **vals):
        b = frac(b)
        for k, v in vals.items():
            v = self._conv(k, v)
            t = self.tl[k]
            if t.b == b + EPSB:  # a second jump on the same beat replaces the first one
                tr = self.ln.tr(P[k])
                b0_, b1_, _, _, e = tr.segs[-1]
                tr.segs[-1] = (b0_, b1_, v, v, e)
                t.v = v
            else:
                t.jump(b, v)
        return self

    def to(self, b0, b1, ease="linear", **vals):
        for k, v in vals.items():
            t = self.tl[k]
            if frac(b0) < t.b - EPSB:
                raise ValueError(f"{self.name}.{P[k]}: animation from {float(b0)} overlaps one ending {float(t.b)}")
            t.wait(b0)
            t.to(b1, self._conv(k, v), ease)
        return self

    def v(self, k):
        v = self.tl[k].v
        return v / PX if k == "x" else v

    def free(self, k):
        """beat from which property k can be animated again"""
        return self.tl[k].b


# ------------------------------------------------------------------ notes
class Notes:
    """collects notes, then writes them; place() turns an event list into a two-hand pattern."""

    def __init__(self):
        self.items = []  # (jl, b, x_phys, kind, end, above, fake, speed, alpha)
        self.busy_until = {}

    def add(self, jl, b, x, kind=TAP, end=None, above=True, fake=False, speed=1.0, alpha=255):
        self.items.append((jl, frac(b), float(x), kind, frac(end) if end is not None else None, above, fake, speed, alpha))

    def place(self, events, line, zone=(140, 560), hold_min=F(1), hold_max=F(4), flicks=(), chord_at=(),
              drag_runs=True, seed=0, kinds=None, xfun=None, prange=None, mirror=False, max_x=None):
        """events -> notes. Hands alternate (left x<0, right x>0); a hold keeps its hand busy and the other hand
        takes everything meanwhile. Within its zone a note's distance follows the melody (higher = more right).
        line: JL or f(event, index) -> JL. flicks / chord_at: beats that get a flick / a second note."""
        R = random.Random(seed)
        flicks = {frac(b) for b in flicks}
        chord_at = {frac(b) for b in chord_at}
        ps = [e["p"] for e in events if e.get("p")]
        lo, hi = prange if prange else ((min(ps), max(ps)) if ps else (60, 70))
        if hi - lo < 4:
            mid = (hi + lo) / 2
            lo, hi = mid - 2, mid + 2
        hand = 0
        busy = [F(-1), F(-1)]  # hold end per hand
        last = [None, None]  # (b, x) per hand
        out = []
        i = 0
        while i < len(events):
            e = events[i]
            b = e["b"]
            ln = line(e, i) if callable(line) else line
            # a run of 16ths -> one hand slides through it as drags
            run = [e]
            if drag_runs:
                j = i + 1
                while j < len(events) and events[j]["b"] - run[-1]["b"] <= F(1, 4) and len(run) < 6:
                    run.append(events[j])
                    j += 1
            if len(run) >= 3:
                h = hand if busy[hand] <= b else 1 - hand
                xs = self._slide(run, h, zone, lo, hi)
                for k, (ev, x) in enumerate(zip(run, xs)):
                    out.append((ln if not callable(line) else line(ev, i + k), ev["b"], x, TAP if k == 0 else DRAG, None))
                last[h] = (run[-1]["b"], xs[-1])
                hand = 1 - h
                i += len(run)
                continue
            # hand choice
            h = hand
            if busy[h] > b:
                h = 1 - h
            if busy[h] > b:  # both busy: skip
                i += 1
                continue
            if last[h] and b - last[h][0] < F(1, 4) and busy[1 - h] <= b:
                h = 1 - h
            t = (e["p"] - lo) / (hi - lo) if e.get("p") else 0.5
            t = min(1.0, max(0.0, t))
            if xfun:
                x = xfun(e, h, i)
            else:
                d = zone[0] + (zone[1] - zone[0]) * ((1 - t) if (h == 0 and not mirror) else t)
                x = (-d if h == 0 else d)
                if last[h] and abs(last[h][1] - x) < 60 and b - last[h][0] < F(1, 2):  # avoid stacking
                    x += (-90 if h == 0 else 90) * (1 if abs(x) < zone[1] - 90 else -1)
            if max_x is not None:
                x = max(-max_x, min(max_x, x))
            kind = TAP
            end = None
            nxt = events[i + 1]["b"] if i + 1 < len(events) else b + 99
            if kinds and b in kinds:
                kind = kinds[b]
            elif e.get("sus", 0) >= hold_min and e["src"] == "v":
                end = b + min(hold_max, e["sus"])
                kind = HOLD
            elif b in flicks:
                kind = FLICK
            if kind == HOLD and end is None:
                end = b + max(hold_min, min(hold_max, e.get("sus", hold_min)))
            if kind == HOLD:
                busy[h] = end + F(1, 8)
            out.append((ln, b, x, kind, end))
            last[h] = (b, x)
            if b in chord_at and busy[1 - h] <= b:
                x2 = -x if abs(x) > 100 else (x + 300 if x < 0 else x - 300)
                out.append((ln, b, x2, FLICK if kind == FLICK else TAP, None))
                last[1 - h] = (b, x2)
            hand = 1 - h
            i += 1
        for ln, b, x, kind, end in out:
            self.add(ln, b, x, kind, end)
        return out

    @staticmethod
    def _slide(run, h, zone, lo, hi):
        """x positions of a drag run on hand h: follow the pitch, at least 50 apart, inside the hand zone."""
        xs = []
        for k, ev in enumerate(run):
            t = (ev["p"] - lo) / (hi - lo) if ev.get("p") else 0.5
            t = min(1.0, max(0.0, t))
            d = zone[0] + (zone[1] - zone[0]) * t
            xs.append(-d if h == 0 else d)
        for k in range(1, len(xs)):  # make it move
            if abs(xs[k] - xs[k - 1]) < 50:
                step = 70 if h == 1 else -70
                xs[k] = xs[k - 1] + (step if abs(xs[k - 1] + step) < zone[1] + 60 else -step)
        return xs

    def write(self):
        n = 0
        for jl, b, x, kind, end, above, fake, speed, alpha in sorted(self.items, key=lambda it: (it[1], it[2])):
            jl.ln.note(kind, b, x * PX, end=end, above=above, fake=fake, speed=speed, alpha=alpha)
            n += 0 if fake else 1
        return n


# ------------------------------------------------------------------ stage: camera, background, hud, effects
class Stage:
    def __init__(self, c):
        self.c = c
        self.cam = c.line("cam", z=-200)
        for p, v in (("moveX", 0.0), ("moveY", 0.0), ("rotate", 0.0), ("alpha", 0.0)):
            self.cam.ev(p, 0, EPSB, v, v)
        self.cam_tl = {k: TL(self.cam, p, 0.0) for k, p in (("x", "moveX"), ("y", "moveY"), ("rot", "rotate"))}
        self.eng = Engine(c, self.cam.index)
        # background: a full-screen white block tinted per scene (outside the camera so shakes never show edges)
        self.bg = c.line("bg", texture="white.png", z=-150)
        sx, sy = 1900 / (64 * ML.TEXK), 1100 / (64 * ML.TEXK)
        for p, v in (("moveX", 0.0), ("moveY", 0.0), ("rotate", 0.0), ("scaleX", sx), ("scaleY", sy), ("alpha", 255.0)):
            self.bg.ev(p, 0, EPSB, v, v)
        self.bg.ev("color", 0, EPSB, INK, INK)
        self.bg_col = TL(self.bg, "color", INK)
        self.bg_a = TL(self.bg, "alpha", 255.0)
        self.hud = {}
        for ui in ("pause", "combonumber", "combo", "score", "bar", "name", "level"):
            h = c.line(f"hud_{ui}")
            h.attach = ui
            for p, v in (("moveX", 0.0), ("moveY", 0.0), ("rotate", 0.0), ("alpha", 0.0), ("scaleX", 1.0),
                         ("scaleY", 1.0)):
                h.ev(p, 0, EPSB, v, v)
            h.ev("color", 0, EPSB, WHITE, WHITE)
            self.hud[ui] = {k: TL(h, p, 0.0 if p != "color" else WHITE) for k, p in
                            (("x", "moveX"), ("y", "moveY"), ("a", "alpha"), ("col", "color"), ("rot", "rotate"))}
            self.hud[ui]["sx"] = TL(h, "scaleX", 1.0)
            self.hud[ui]["sy"] = TL(h, "scaleY", 1.0)

    # ---- background
    def bgc(self, b, col, dur=F(1, 2), ease="quadOut"):
        self.bg_col.wait(b)
        if dur == 0:
            self.bg_col.jump(b, tuple(col))
        else:
            self.bg_col.to(frac(b) + frac(dur), tuple(col), ease)

    def bga(self, b, a, dur=F(1, 2), ease="quadOut"):
        self.bg_a.wait(b)
        if dur == 0:
            self.bg_a.jump(b, float(a))
        else:
            self.bg_a.to(frac(b) + frac(dur), float(a), ease)

    # ---- camera (root of every judge line and decoration)
    def cam_to(self, b0, b1, ease="linear", **vals):
        for k, v in vals.items():
            t = self.cam_tl[k]
            t.wait(b0)
            t.to(b1, float(v * PX if k == "x" else v), ease)

    def cam_at(self, b, **vals):
        for k, v in vals.items():
            self.cam_tl[k].jump(b, float(v * PX if k == "x" else v))

    def shake(self, b, amp=18.0, beats=F(1, 2), n=6, seed=0):
        R = random.Random(seed)
        b = frac(b)
        dt = frac(beats) / n
        for k in range(1, n + 1):
            f = 1 - k / n
            self.cam_to(b + dt * (k - 1), b + dt * k, "linear", x=(R.uniform(-1, 1) * amp * f),
                        y=(R.uniform(-1, 1) * amp * f))

    def sway(self, b0, b1, amp, period=2, ease="sineInOut"):
        """camera roll: +amp, -amp, ... and back to 0 on the last half period (ends exactly at b1)."""
        b0, b1, half = frac(b0), frac(b1), F(period) / 2
        n = int((b1 - b0) / half)
        b, sgn = b0, 1
        for _ in range(n - 1):
            self.cam_to(b, b + half, ease, rot=amp * sgn)
            b += half
            sgn = -sgn
        self.cam_to(b, b1, ease, rot=0)

    # ---- HUD
    def hud_to(self, b0, b1, ease="linear", which=None, **vals):
        for ui in (which or self.hud):
            for k, v in vals.items():
                t = self.hud[ui][k]
                t.wait(b0)
                v = tuple(v) if k == "col" else float(v * PX if k == "x" else v)
                if frac(b1) == frac(b0):
                    t.jump(b0, v)
                else:
                    t.to(b1, v, ease)

    def hud_in(self, b0, b1):
        for ui in self.hud:
            d = -170 if ui in ("name", "level") else 170
            self.hud_to(b0, b0, which=[ui], y=d, a=0)
            self.hud_to(b0, b1, "quartOut", which=[ui], y=0, a=255)

    def hud_out(self, b0, b1):
        for ui in self.hud:
            d = -170 if ui in ("name", "level") else 170
            self.hud_to(b0, b1, "quartIn", which=[ui], y=d, a=0)

    # ---- shaders
    def fx(self, shader, b0, b1, **vars):
        self.c.effect(shader, b0, b1, vars)

    def fxk(self, shader, b0, b1, keys, **const):
        """keys: {var: [(beat, value, ease_into_next), ...]}"""
        v = dict(const)
        for k, pts in keys.items():
            v[k] = self.c.var_kfs(pts)
        self.c.effect(shader, b0, b1, v)

    def shock(self, b, cx=0.5, cy=0.5, beats=F(3, 2), width=0.1, distortion=0.8, p0=0.0):
        """a shockwave ring; p0 = 0 starts with the shader's bright burst at the centre, p0 > width skips it."""
        b = frac(b)
        self.fxk("shockwave", b, b + beats, {"progress": [(b, p0, "quadOut"), (b + beats, 1.2, "linear")]},
                 centerX=cx, centerY=cy, width=width, distortion=distortion, expand=10.0)

    def chroma(self, b, power=0.012, beats=F(1, 2)):
        b = frac(b)
        self.fxk("chromatic", b, b + beats, {"power": [(b, power, "quadOut"), (b + beats, 0.0, "linear")]}, sampleCount=4)

    def glitch(self, b0, b1, power=0.04, rate=0.7, speed=8.0, block=30.5, color=0.012):
        self.fx("glitch", b0, b1, power=power, rate=rate, speed=speed, blockCount=block, colorRate=color)
