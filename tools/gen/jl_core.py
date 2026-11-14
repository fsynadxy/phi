"""Stage machinery for the Just Love showcase: the song's grid, the stage (background planes, HUD, flashes),
the always-on lens shader with keyframed uniforms, judge-line wrappers and a rhythm-driven note writer.

Beat b of the chart sounds at 0.0155 + 0.375 b seconds; bar k starts on beat 3 + 4k (see tools/analysis/jl_steps.py).
"""
import math
import os
import random
from fractions import Fraction

import numpy as np

import madlib as ML
from chartlib import DRAG, EASE, EPSB, FLICK, HOLD, TAP, frac, triple
from madlib import TL

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "justlove")
PX = ML.PX
TEXK = ML.TEXK


def F(x, d=None):
    return frac(x, d)


def B(bar, beat=0):
    """chart beat of (bar, beat in bar)"""
    return F(3 + 4 * bar) + F(beat)


def mix(a, b, t):
    return tuple(round(p + (q - p) * t) for p, q in zip(a, b))


# ------------------------------------------------------------------ palette (after the cover: snow, ice, lavender)
NIGHT = (9, 11, 28)
INDIGO = (22, 26, 64)
DEEP = (34, 42, 104)
VIOLET = (112, 104, 214)
LAVENDER = (178, 164, 244)
SKY = (132, 172, 246)
ICE = (186, 216, 255)
SNOW = (244, 248, 255)
WHITE = (255, 255, 255)
PINK = (255, 168, 206)
ROSE = (255, 122, 172)
BLUSH = (255, 214, 230)
MINT = (140, 255, 214)
GOLD = (255, 232, 176)
LINE = (236, 244, 255)


# ------------------------------------------------------------------ the song
class Music:
    """analysis data on the 32nd-note grid (8 values per beat)"""

    def __init__(self):
        d = np.load(os.path.join(DATA, "steps.npz"))
        self.d = {k: d[k] for k in d.files}
        self.n = len(self.d["kick"])

    def v(self, key, beat):
        s = int(round(float(beat) * 8))
        return float(self.d[key][s]) if 0 <= s < self.n else 0.0

    def scale(self, key, b0, b1, q=97):
        """local normaliser: value / percentile over [b0, b1)"""
        a = self.d[key][int(float(b0) * 8):int(float(b1) * 8)]
        ref = float(np.percentile(a, q)) + 1e-9 if len(a) else 1.0
        return lambda beat: self.v(key, beat) / ref

    def pitch(self, beat, floor=0.3):
        s = int(round(float(beat) * 8))
        if not 0 <= s < self.n or self.d["pitch_w"][s] < floor:
            return None
        return float(self.d["pitch"][s])

    def silent(self, beat):
        s = int(round(float(beat) * 8))
        return bool(self.d["silent"][s]) if 0 <= s < self.n else True

    def vis(self, beat, band):
        i = int(float(beat) * 4)
        v = self.d["vis"]
        return float(v[i, band]) if 0 <= i < len(v) else 0.0

    def hits(self, key, b0, b1, thresh, grid=4, gap=0, q=97):
        """beats in [b0, b1) on a 1/grid lattice where the locally normalised strength exceeds thresh"""
        f = self.scale(key, b0, b1, q)
        out = []
        for i in range(int(math.ceil(float(b0) * grid)), int(math.ceil(float(b1) * grid))):
            b = F(i, grid)
            if f(b) >= thresh and (not out or b - out[-1] >= gap):
                out.append(b)
        return out


# ------------------------------------------------------------------ lens: one shader, keyframed for the whole song
class Uniform:
    """base track (set / ramp, held in between) plus additive pulses, baked into extra.json keyframes"""

    def __init__(self, default):
        self.default = float(default)
        self.base = []  # (b0, b1, v0, v1, ease)
        self.pulses = []  # (b0, b1, amp, ease): amp decays to 0

    def ramp(self, b0, b1, v0, v1, ease="linear"):
        self.base.append((F(b0), F(b1), float(v0), float(v1), ease))

    def set(self, b, v):
        self.base.append((F(b), F(b), float(v), float(v), "linear"))

    def pulse(self, b, amp, dur, ease="quadOut"):
        self.pulses.append((F(b), F(b) + F(dur), float(amp), ease))

    def hold(self, b, v, dur):
        """jump to v for dur beats, then back to the default (impact frames)"""
        self.set(b, v)
        self.set(F(b) + F(dur), self.default)

    def _base_at(self, t, left=False):
        v = self.default
        for b0, b1, v0, v1, e in self._sorted:
            if b0 < t or (b0 == t and not left):
                if t >= b1:
                    v = v1
                else:
                    v = v0 + (v1 - v0) * ML.ease_fn(e)(float((t - b0) / (b1 - b0)))
            else:
                break
        return v

    def value(self, t, left=False):
        v = self._base_at(t, left)
        for b0, b1, amp, e in self.pulses:
            if (b0 < t or (b0 == t and not left)) and (t < b1 or (t == b1 and left)):
                v += amp * (1 - ML.ease_fn(e)(float((t - b0) / (b1 - b0))))
        return v

    def keyframes(self, end):
        self._sorted = sorted(self.base, key=lambda s: (s[0], s[1]))
        pts = {F(0), F(end)}
        for b0, b1, *_ in self._sorted:
            pts |= {b0, b1}
        for b0, b1, *_ in self.pulses:
            pts |= {b0, b1}
        pts = sorted(p for p in pts if 0 <= p <= F(end))
        out = []

        def emit(a, b, v0, v1, ease=1, el=0.0, er=1.0):
            out.append({"startTime": triple(a), "endTime": triple(b), "start": round(v0, 5), "end": round(v1, 5),
                        "easingType": ease, "easingLeft": round(el, 5), "easingRight": round(er, 5)})

        emit(F(0), F(0) + EPSB, self.value(F(0)), self.value(F(0)))
        for a, b in zip(pts, pts[1:]):
            if b <= a:
                continue
            a2 = max(a, EPSB) if a == 0 else a
            moving = [s for s in self._sorted if s[0] <= a and s[1] >= b and s[1] > s[0] and s[2] != s[3]]
            active = [p for p in self.pulses if p[0] <= a and p[1] >= b and p[2] != 0.0]
            v0, v1 = self.value(a), self.value(b, left=True)
            if not moving and not active:
                if not out or abs(out[-1]["end"] - v0) > 1e-6:
                    emit(a2, a2 + EPSB if a2 + EPSB < b else b, v0, v0)
                continue
            if len(moving) + len(active) == 1:
                seg = (moving or active)[0]
                name = seg[4] if moving else seg[3]
                s0, s1 = seg[0], seg[1]
                el, er = float((a - s0) / (s1 - s0)), float((b - s0) / (s1 - s0))
                f = ML.ease_fn(name)
                if name == "linear" or abs(f(er) - f(el)) < 1e-6:
                    emit(a2, b, v0, v1)
                elif not moving:  # a decaying pulse runs the easing curve backwards: sample it instead
                    self._sampled(emit, a2, b)
                else:
                    emit(a2, b, v0, v1, EASE[name], max(0.0, el), min(1.0, er))
            else:
                self._sampled(emit, a2, b)
        return out

    def _sampled(self, emit, a, b, step=Fraction(1, 16), tol=None):
        n = max(1, int(math.ceil(float((b - a) / step))))
        ts = [a + (b - a) * Fraction(k, n) for k in range(n + 1)]
        vs = [self.value(ts[0])] + [self.value(t, left=True) for t in ts[1:]]
        # merge collinear runs
        i = 0
        while i < n:
            j = i + 1
            while j < n:
                k = float((ts[j] - ts[i]) / (ts[j + 1] - ts[i]))
                if abs(vs[i] + (vs[j + 1] - vs[i]) * k - vs[j]) > self.tol:
                    break
                j += 1
            emit(ts[i], ts[j], vs[i], vs[j])
            i = j

    tol = 1e-4


class Lens:
    KEYS = {"zoom": 1.0, "roll": 0.0, "shiftX": 0.0, "shiftY": 0.0, "split": 0.0, "sat": 1.0, "invert": 0.0,
            "wash": 0.0, "frost": 0.0}
    TOL = {"zoom": 4e-4, "roll": 0.02, "shiftX": 2e-4, "shiftY": 2e-4, "split": 3e-4, "sat": 4e-3, "invert": 0.01,
           "wash": 4e-3, "frost": 4e-3}

    def __init__(self):
        self.u = {k: Uniform(v) for k, v in self.KEYS.items()}
        for k, t in self.TOL.items():
            self.u[k].tol = t
        self.colors = {"washColor": [], "frostColor": []}

    def __getattr__(self, k):
        if k in self.KEYS:
            return self.u[k]
        raise AttributeError(k)

    def color(self, key, b, rgb, fade=0):
        self.colors[key].append((F(b), tuple(rgb), F(fade)))

    def punch(self, b, zoom=0.03, dur=1, ease="expoOut"):
        """the camera kicks in on a hit and settles back"""
        self.u["zoom"].pulse(b, zoom, dur, ease)

    def vars(self, end):
        out = {}
        for k, u in self.u.items():
            kfs = u.keyframes(end)
            if len(kfs) > 1 or abs(kfs[0]["start"] - self.KEYS[k]) > 1e-9:
                out[k] = kfs
        for key, evs in self.colors.items():
            if not evs:
                continue
            kfs, cur, t = [], None, F(0)
            for b, rgb, fade in sorted(evs, key=lambda e: e[0]):
                c4 = [int(v) for v in rgb] + [255]
                if cur is None:
                    kfs.append({"startTime": triple(0), "endTime": triple(EPSB), "start": c4, "end": c4, "easingType": 1})
                    cur = c4
                    if b <= EPSB:
                        continue
                b = max(b, t, EPSB)
                e = b + (fade if fade > 0 else EPSB)
                kfs.append({"startTime": triple(b), "endTime": triple(e), "start": cur if fade > 0 else c4, "end": c4, "easingType": 1})
                cur, t = c4, e
            out[key] = kfs
        return out


class FxTrack:
    """a custom shader that is switched on for some ranges, with per-uniform keyframes [(beat, value, ease)]"""

    def __init__(self, chart, shader):
        self.c, self.shader = chart, shader

    def add(self, b0, b1, **tracks):
        vars_ = {}
        for k, pts in tracks.items():
            if isinstance(pts, (int, float)):
                vars_[k] = float(pts)
            elif isinstance(pts, tuple):  # colour
                vars_[k] = [int(v) for v in pts] + ([255] if len(pts) == 3 else [])
            else:
                pts = [(F(b), v, e) for b, v, e in pts]
                if pts[0][0] > F(b0):
                    pts.insert(0, (F(b0), pts[0][1], "linear"))
                if len(pts) == 1:
                    vars_[k] = float(pts[0][1])
                    continue
                vars_[k] = self.c.var_kfs(pts)
        self.c.effect(self.shader, b0, b1, vars_)


# ------------------------------------------------------------------ stage: planes, HUD, flashes, shake
class Stage:
    def __init__(self, c):
        self.c = c
        self.root = c.line("cam")
        for p in ("moveX", "moveY", "rotate"):
            self.root.ev(p, 0, EPSB, 0.0, 0.0)
            self.root.ev(p, 0, EPSB, 0.0, 0.0, layer=1)
        sx, sy = 1800 / (64 * TEXK), 1000 / (64 * TEXK)

        def plane(name, z, color, alpha, tex="white.png", w=64, h=64):
            ln = c.line(name, texture=tex, z=z)
            for p, v in (("moveX", 0.0), ("moveY", 0.0), ("rotate", 0.0), ("scaleX", 1800 / (w * TEXK)), ("scaleY", 1000 / (h * TEXK)),
                         ("alpha", float(alpha))):
                ln.ev(p, 0, EPSB, v, v)
            ln.ev("color", 0, EPSB, color, color)
            return ln

        self.bg = plane("bg", -100, NIGHT, 255)
        self.vg = plane("vignette", 70, NIGHT, 200, "vig.png", 512, 288)
        self.blk = plane("blackout", 85, NIGHT, 0)
        self.fl = plane("flash", 90, WHITE, 0)
        self.hud = []
        for ui in ("pause", "combonumber", "combo", "score", "bar", "name", "level"):
            h = c.line(f"hud_{ui}")
            h.attach = ui
            for p in ("moveX", "moveY", "rotate", "alpha"):
                h.ev(p, 0, EPSB, 0.0, 0.0)
            h.ev("color", 0, EPSB, ICE, ICE)
            self.hud.append(h)
        self.sched = {"bg": [], "vg": [], "blk": [], "fl": [], "shk": [], "hud": []}

    def bgc(self, b, color, alpha=None, fade=0, ease="sineInOut"):
        """background plane: colour and how much of Phira's blurred illustration it hides (255 = all)"""
        self.sched["bg"].append((F(b), tuple(color), alpha, F(fade), ease))

    def vig(self, b, color, alpha, fade=0):
        self.sched["vg"].append((F(b), tuple(color), alpha, F(fade), "sineInOut"))

    def black(self, b0, b1, alpha=255):
        self.sched["blk"].append((F(b0), F(b1), alpha))

    def flash(self, b, color=WHITE, peak=255, dur=0.5, ease="expoOut"):
        self.sched["fl"].append((F(b), tuple(color), peak, F(dur), ease))

    def shake(self, b, amp=12.0, rot=0.0, dur=0.3):
        self.sched["shk"].append((F(b), amp, rot, F(dur)))

    def hud_alpha(self, b, alpha, fade=0):
        self.sched["hud"].append((F(b), float(alpha), F(fade)))

    def emit(self, R):
        for ln, key, c0, a0 in ((self.bg, "bg", NIGHT, 255.0), (self.vg, "vg", NIGHT, 200.0)):
            col, al = TL(ln, "color", c0), TL(ln, "alpha", a0)
            for b, c_, a, fade, ease in sorted(self.sched[key], key=lambda e: e[0]):
                for tl, v in ((col, c_), (al, None if a is None else float(a))):
                    if v is not None:
                        self._go(tl, b, v, fade, ease)
        a = TL(self.blk, "alpha", 0.0)
        for b0, b1, al in sorted(self.sched["blk"]):
            if b0 < a.b:
                continue
            a.jump(b0, float(al))
            a.wait(b1)
            a.jump(b1, 0.0)
        fa, fc = TL(self.fl, "alpha", 0.0), TL(self.fl, "color", WHITE)
        last = {}
        for e in self.sched["fl"]:
            last[e[0]] = e
        fl = sorted(last.values(), key=lambda e: e[0])
        for i, (b, c_, peak, dur, ease) in enumerate(fl):
            end = b + dur
            if i + 1 < len(fl):
                end = min(end, fl[i + 1][0] - 2 * EPSB)
            if b < fc.b:
                continue
            fc.jump(b, c_)
            fa.jump(b, float(peak))
            if end > fa.b:
                fa.to(end, 0.0, ease)
        sh = sorted(self.sched["shk"], key=lambda e: e[0])
        tx, ty, tr = TL(self.root, "moveX", 0.0), TL(self.root, "moveY", 0.0), TL(self.root, "rotate", 0.0)
        for i, (b, amp, rot, dur) in enumerate(sh):
            nxt = sh[i + 1][0] if i + 1 < len(sh) else b + dur
            L = min(dur, nxt - b)
            if L <= 0 or b < tx.b:
                continue
            ang = R.uniform(0, 2 * math.pi)
            for t, v in ((tx, amp * math.cos(ang) * PX), (ty, amp * math.sin(ang)), (tr, rot * R.choice((-1, 1)))):
                self.root.ev(t.p, b, b + L, v, 0.0, "quadOut", layer=1)
                t.b = b + L
        for h in self.hud:
            al = TL(h, "alpha", 0.0)
            for b, v, fade in sorted(self.sched["hud"], key=lambda e: e[0]):
                self._go(al, b, v, fade, "sineInOut")

    @staticmethod
    def _go(tl, b, v, fade=0, ease="linear"):
        """change a plane property at beat b (or as soon as the previous change on it has finished)"""
        b = max(F(b), tl.b)
        if fade > 0:
            tl.wait(b)
            tl.to(b + F(fade), v, ease)
        else:
            tl.jump(b, v)


# ------------------------------------------------------------------ judge lines
P = {"x": "moveX", "y": "moveY", "rot": "rotate", "a": "alpha", "spd": "speed", "col": "color", "sx": "scaleX"}


class JL:
    """a judge line with one timeline per property (x in physical units: the wrapper converts to RPE)"""

    def __init__(self, c, name, z, father=-1, x=0.0, y=-250.0, rot=0.0, alpha=0.0, speed=8.0, color=LINE, sx=0.45, cover=True):
        self.ln = c.line(name, z=z, father=father, rot_with_father=True, cover=cover)
        self.tl = {}
        for p, v in (("moveX", x * PX), ("moveY", y), ("rotate", rot), ("alpha", alpha), ("speed", speed), ("color", color),
                     ("scaleX", sx)):
            v = tuple(v) if p == "color" else float(v)
            self.ln.ev(p, 0, EPSB, v, v)
            self.tl[p] = TL(self.ln, p, v)

    @property
    def index(self):
        return self.ln.index

    @staticmethod
    def _conv(k, v):
        if k == "col":
            return tuple(v)
        return float(v) * PX if k == "x" else float(v)

    def at(self, b, **vals):
        b = F(b)
        for k, v in vals.items():
            v = self._conv(k, v)
            t = self.tl[P[k]]
            if t.b == b + EPSB:  # a jump was already written on this beat: overwrite it
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
            if F(b0) < t.b - EPSB:
                raise ValueError(f"{self.ln.name}.{P[k]}: animation from {float(b0)} overlaps one ending {float(t.b)}")
            t.wait(b0)
            t.to(b1, self._conv(k, v), ease)
        return self

    def v(self, k):
        v = self.tl[P[k]].v
        return v / PX if k == "x" else v


class Rig:
    """an invisible pivot line; children ride on it (position and rotation, not scale)"""

    def __init__(self, c, name, father, x=0.0, y=0.0, rot=0.0):
        self.ln = c.line(name, father=father, rot_with_father=True)
        self.tl = {}
        for p, v in (("moveX", x * PX), ("moveY", y), ("rotate", rot), ("alpha", 0.0)):
            self.ln.ev(p, 0, EPSB, float(v), float(v))
            self.tl[p] = TL(self.ln, p, float(v))

    @property
    def index(self):
        return self.ln.index

    def at(self, b, **vals):
        for k, v in vals.items():
            self.tl[P[k]].jump(F(b), float(v) * (PX if k == "x" else 1.0))
        return self

    def to(self, b0, b1, ease="linear", **vals):
        for k, v in vals.items():
            t = self.tl[P[k]]
            t.wait(b0)
            t.to(b1, float(v) * (PX if k == "x" else 1.0), ease)
        return self

    def v(self, k):
        v = self.tl[P[k]].v
        return v / PX if k == "x" else v


# ------------------------------------------------------------------ notes
class Notes:
    def __init__(self, music):
        self.m = music
        self.items = []
        self.fx = None  # hit-effect tint for the notes written from now on

    def add(self, jl, b, x, kind=TAP, end=None, above=True, fake=False, speed=1.0, alpha=255, size=1.0, vis=None, yoff=0.0):
        """x in physical units along the line"""
        self.items.append({"jl": jl, "b": F(b), "x": round(float(x) * PX, 1), "kind": kind, "end": F(end) if end is not None else None,
                           "above": above, "fake": fake, "speed": speed, "alpha": alpha, "size": size, "vis": vis, "fx": self.fx,
                           "yoff": yoff})

    def taken(self, b, jl=None):
        b = F(b)
        return [it for it in self.items if it["b"] == b and not it["fake"] and (jl is None or it["jl"] is jl)]

    def holding(self, b, jl):
        b = F(b)
        return any(it["kind"] == HOLD and it["jl"] is jl and it["b"] < b < it["end"] for it in self.items)

    def write(self):
        n = 0
        for it in sorted(self.items, key=lambda i: i["b"]):
            ln = it["jl"].ln
            ln.note(it["kind"], it["b"], it["x"], end=it["end"], above=it["above"], speed=it["speed"], alpha=it["alpha"],
                    size=it["size"], fake=it["fake"], visible=it["vis"] if it["vis"] is not None else 999999.0, yoff=it["yoff"])
            if it["fx"] is not None and not it["fake"]:
                ln.notes[-1]["tintHitEffects"] = [int(v) for v in it["fx"]]
            n += 0 if it["fake"] else 1
        return n
