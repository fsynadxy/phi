"""Engine for note-free line performances ("判定线演出") in Phira.

* Canvas in physical units: x in [-800, 800], y in [-450, 450] (16:9, isotropic, +y up).
* Each Shot owns elements (texture lines; strokes are stretched white.png). Elements borrow lines from a pool
  keyed by (texture, zOrder) and give them back when they end, so a long storyboard stays at a few
  hundred lines.
* A Shot has a virtual camera (zoom about the screen centre + pan). Phira's parenting carries position and
  rotation but not scale, so the camera is baked into every element. Sub-intervals of an eased curve are
  written with easingLeft/easingRight (ClampedTween in prpr), which keeps the composition exact as long as
  the element and the camera do not both move during the same interval (then it falls back to dense linear
  pieces).
* All pooled lines hang from one root line ("cam") used for screen shake / roll.
"""
import math
from fractions import Fraction

from chartlib import EASE, EPSB, frac

PX = 1350.0 / 1600.0  # RPE x units per physical unit
TEXK = 1600.0 / 1350.0  # physical units per (texture pixel * RPE scale)
LINE_LEN = 2400.0  # physical half-length per scaleX unit of a normal line (line.png)
LINE_TH = 6.08  # physical thickness per scaleY unit (scaled normal line)

TEXPX = {"white.png": (64, 64)}  # texture name -> (w, h) pixels, filled by register_textures


def register_textures(d):
    TEXPX.update(d)


# ------------------------------------------------------------------ easing (prpr tween table)
def _f2(f):
    return lambda x: 1 - f(1 - x)


def _f3(f):
    def g(x):
        x = x * 2
        return f(x) / 2 if x < 1 else 1 - f(2 - x) / 2
    return g


def _sine(x): return 1 - math.cos(x * math.pi / 2)
def _quad(x): return x * x
def _cubic(x): return x ** 3
def _quart(x): return x ** 4
def _quint(x): return x ** 5
def _expo(x): return 2.0 ** (10 * (x - 1))
def _circ(x): return 1 - math.sqrt(max(0.0, 1 - x * x))
def _back(x): return (2.70158 * x - 1.70158) * x * x
def _elastic(x): return -(2.0 ** (10 * x - 10) * math.sin((x * 10 - 10.75) * (2 * math.pi / 3)))
def _bounce(x):
    x = 1 - x
    if x < 1 / 2.75: v = 7.5625 * x * x
    elif x < 2 / 2.75: v = 7.5625 * (x - 1.5 / 2.75) ** 2 + 0.75
    elif x < 2.5 / 2.75: v = 7.5625 * (x - 2.25 / 2.75) ** 2 + 0.9375
    else: v = 7.5625 * (x - 2.625 / 2.75) ** 2 + 0.984375
    return 1 - v


_TW = [lambda x: 0.0, lambda x: 1.0, lambda x: x]
for _f in (_sine, _quad, _cubic, _quart, _quint, _expo, _circ, _back, _elastic, _bounce):
    _TW += [_f, _f2(_f), _f3(_f)]
_IN, _OUT, _IO = 0, 1, 2
_MAP = {  # RPE easing id -> tween id
    1: 2, 2: 4, 3: 3, 4: 7, 5: 6, 6: 5, 7: 8, 8: 10, 9: 9, 10: 13, 11: 12, 12: 11, 13: 14, 14: 16, 15: 15,
    16: 19, 17: 18, 18: 22, 19: 21, 20: 25, 21: 24, 22: 23, 23: 26, 24: 28, 25: 27, 26: 31, 27: 30, 28: 32, 29: 29,
}


def ease_fn(name):
    return _TW[_MAP[EASE[name]]]


# ------------------------------------------------------------------ keyframe tracks
class KF:
    """keyframes [(beat, value, ease_into)] with prpr hold semantics; same-beat keyframes = jump."""

    def __init__(self, beat, value):
        self.k = [(frac(beat), value, "linear")]

    def add(self, beat, value, ease="linear"):
        beat = frac(beat)
        if beat < self.k[-1][0]:
            raise ValueError(f"keyframes must be chronological ({float(beat)} < {float(self.k[-1][0])})")
        self.k.append((beat, value, ease))

    def beats(self):
        return [k[0] for k in self.k]

    def interval(self, t):
        """(index i, progress) of the keyframe interval containing t (left-closed); None if outside."""
        k = self.k
        if t < k[0][0]:
            return None
        for i in range(len(k) - 1):
            a, b = k[i][0], k[i + 1][0]
            if a <= t < b:
                return i
        return None

    def value(self, t, left=False):
        """value at t; left=True gives the limit from the left (before a jump at t)."""
        t = frac(t)
        k = self.k
        cur = None  # last keyframe at (or, for left limits, strictly before) t
        for i, (b, v, e) in enumerate(k):
            if b < t or (b == t and not left):
                cur = i
        if cur is None:
            return k[0][1]
        if cur == len(k) - 1:
            return k[cur][1]
        b0, v0, _ = k[cur]
        b1, v1, e1 = k[cur + 1]
        if b1 == b0:
            return v1
        x = float((t - b0) / (b1 - b0))
        return lerp(v0, v1, ease_fn(e1)(x))


def _same(a, b):
    if isinstance(a, tuple) or isinstance(b, tuple):
        return tuple(round(float(x)) for x in a) == tuple(round(float(x)) for x in b)
    return abs(float(a) - float(b)) < 1e-6


def lerp(a, b, y):
    if isinstance(a, tuple):
        return tuple(p + (q - p) * y for p, q in zip(a, b))
    return a + (b - a) * y


# ------------------------------------------------------------------ timeline writer
class TL:
    def __init__(self, ln, prop, v0):
        self.ln, self.p, self.v, self.b = ln, prop, v0, EPSB

    def to(self, b, v, ease="linear"):
        b = frac(b)
        if b < self.b:
            raise ValueError(f"{self.ln.name}.{self.p}: back in time {float(self.b)} -> {float(b)}")
        if b > self.b:
            self.ln.ev(self.p, self.b, b, self.v, v, ease)
        self.b, self.v = b, v

    def jump(self, b, v):
        b = frac(b)
        if b < self.b:
            raise ValueError(f"{self.ln.name}.{self.p}: jump back {float(self.b)} -> {float(b)}")
        self.ln.ev(self.p, b, b + EPSB, v, v, "linear")
        self.b, self.v = b + EPSB, v

    def wait(self, b):
        b = frac(b)
        if b > self.b:
            self.b = b


class Slot:
    PROPS = ("moveX", "moveY", "rotate", "alpha", "color", "scaleX", "scaleY")

    def __init__(self, ln, is_line):
        self.ln = ln
        self.free_from = Fraction(0)
        init = {"moveX": 0.0, "moveY": 0.0, "rotate": 0.0, "alpha": 0, "color": (255, 255, 255),
                "scaleX": 0.0 if is_line else 1.0, "scaleY": 1.003 if is_line else 1.0}
        self.tl = {}
        for p, v in init.items():
            ln.ev(p, 0, EPSB, v, v)
            self.tl[p] = TL(ln, p, v)


class Engine:
    def __init__(self, chart, root_index):
        self.c = chart
        self.root = root_index
        self.pools = {}
        self.shots = []
        self.mask = []  # [(b0, b1)] beat ranges in which nothing may be shown (e.g. while a video plays)

    def slot(self, tex, z, b0, b1):
        key = (tex, z)
        pool = self.pools.setdefault(key, [])
        for s in pool:
            if s.free_from <= b0:
                s.free_from = frac(b1) + 2 * EPSB
                return s
        ln = self.c.line(f"{tex.split('.')[0]}_z{z}_{len(pool)}", texture=tex, z=z, father=self.root,
                         rot_with_father=True)
        s = Slot(ln, tex == "line.png")
        s.free_from = frac(b1) + 2 * EPSB
        pool.append(s)
        return s

    def shot(self, b0, b1, cam=None):
        sh = Shot(self, b0, b1, cam)
        self.shots.append(sh)
        return sh

    def _apply_mask(self, e):
        """clip an element against the masked ranges; False if nothing is left."""
        for m0, m1 in self.mask:
            m0, m1 = frac(m0), frac(m1)
            if e.end <= m0 or e.start >= m1:
                continue
            if e.start >= m0 and e.end <= m1:
                return False
            if e.start < m0:
                e.end = m0
            else:
                e.start = m1
        return e.end > e.start

    def bake(self):
        elems = [e for sh in self.shots for e in sh.elems]
        if self.mask:
            elems = [e for e in elems if self._apply_mask(e)]
        elems.sort(key=lambda e: (e.start, e.shot_order))
        for e in elems:
            e.bake()

    def line_count(self):
        return sum(len(p) for p in self.pools.values())


class Shot:
    def __init__(self, eng, b0, b1, cam=None):
        self.eng, self.b0, self.b1 = eng, frac(b0), frac(b1)
        self.elems = []
        self.cam = KF(b0, (1.0, 0.0, 0.0))
        for c in cam or []:
            b, z, px, py = c[:4]
            self.cam.add(b, (float(z), float(px), float(py)), c[4] if len(c) > 4 else "linear")

    # element factories --------------------------------------------------------
    def seg(self, p1, p2, thick=6.0, color=(255, 255, 255), alpha=255, z=0, start=None, end=None):
        (x1, y1), (x2, y2) = p1, p2
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        L = math.hypot(x2 - x1, y2 - y1) / 2
        rot = -math.degrees(math.atan2(y2 - y1, x2 - x1))
        return self.line(cx, cy, rot, L, thick, color, alpha, z, start, end)

    def line(self, x, y, rot, half_len, thick=6.0, color=(255, 255, 255), alpha=255, z=0, start=None, end=None):
        """a straight stroke: a white.png texture line (w = half length, h = thickness). Unlike a normal judge
        line, a texture line with alpha 0 is not drawn at all, and strokes share the pools of filled shapes."""
        e = Elem(self, "white.png", z, start, end, kind="line")
        e.init(x=x, y=y, rot=rot, w=half_len, h=thick, alpha=alpha, color=color)
        return e

    def tex(self, tex, x, y, w, h=None, rot=0.0, color=(255, 255, 255), alpha=255, z=0, start=None, end=None):
        if h is None:
            pw, ph = TEXPX[tex]
            h = w * ph / pw
        e = Elem(self, tex, z, start, end)
        e.init(x=x, y=y, rot=rot, w=w, h=h, alpha=alpha, color=color)
        return e


class Elem:
    CAMERA_PROPS = ("x", "y", "w", "h")

    def __init__(self, shot, tex, z, start=None, end=None, kind="tex"):
        self.shot = shot
        self.tex, self.z, self.kind = tex, z, kind
        self.start = max(frac(start) if start is not None else shot.b0, EPSB)  # beat 0 holds the slot init
        self.end = frac(end) if end is not None else shot.b1
        self.kf = {}
        self.shot_order = len(shot.elems)
        shot.elems.append(self)

    def init(self, **vals):
        for p, v in vals.items():
            self.kf[p] = KF(self.start, tuple(v) if p == "color" else float(v))

    def at(self, beat, ease="linear", **vals):
        for p, v in vals.items():
            self.kf[p].add(beat, tuple(v) if p == "color" else float(v), ease)
        return self

    def to(self, beat, ease="linear", **vals):
        return self.at(beat, ease, **vals)

    # ------------------------------------------------------------------ baking
    def _screen(self, p, t, left=False):
        v = self.kf[p].value(t, left)
        if p not in self.CAMERA_PROPS:
            return v
        z, px, py = self.shot.cam.value(t, left)
        if p == "x":
            return v * z + px
        if p == "y":
            return v * z + py
        return v * z

    def _out(self, p, v):
        """physical -> RPE event value for slot property."""
        if p == "x":
            return "moveX", v * PX
        if p == "y":
            return "moveY", v
        if p == "rot":
            return "rotate", v
        if p == "alpha":
            return "alpha", max(0.0, min(255.0, v))
        if p == "color":
            return "color", v
        if self.tex == "line.png":
            if p == "w":
                return "scaleX", max(0.0, v) / LINE_LEN
            s = max(0.02, v / LINE_TH)
            return "scaleY", s if abs(s - 1) > 1e-3 else 1.003
        pw, ph = TEXPX[self.tex]
        if p == "w":
            return "scaleX", max(0.0, v) * (2 if self.kind == "line" else 1) / (pw * TEXK)
        return "scaleY", max(0.0, v) / (ph * TEXK)

    def bake(self):
        s0, s1 = self.start, self.end
        slot = self.shot.eng.slot(self.tex, self.z, s0, s1)
        cam = self.shot.cam
        for p, track in self.kf.items():
            prop, v0 = self._out(p, self._screen(p, s0))
            tl = slot.tl[prop]
            if not _same(tl.v, v0):  # the borrowed line may already hold this value
                tl.jump(s0, v0)
            else:
                tl.wait(s0)
            bps = {s0, s1} | {b for b in track.beats() if s0 < b < s1}
            if p in self.CAMERA_PROPS:
                bps |= {b for b in cam.beats() if s0 < b < s1}
            bps = sorted(bps)
            for a, b in zip(bps, bps[1:]):
                if b <= a:
                    continue
                vb = self._screen(p, b, left=True)
                e_moving = track.value(a) != track.value(b, left=True)
                c_moving = p in self.CAMERA_PROPS and cam.value(a) != cam.value(b, left=True)
                if e_moving and c_moving:
                    n = max(1, int(math.ceil(float(b - a) * 4)))
                    for k in range(1, n + 1):
                        t = a + (b - a) * Fraction(k, n)
                        tl.to(t, self._out(p, self._screen(p, t, left=(k == n)))[1], "linear")
                else:
                    src = track if e_moving else (cam if c_moving else None)
                    tl.to(b, self._out(p, vb)[1], self._clip(src, a, b) if src else "linear")
                vr = self._screen(p, b)
                if b < s1 and vr != vb:  # jump at b
                    tl.jump(b, self._out(p, vr)[1])
        # cut at the end
        slot.tl["alpha"].wait(s1)
        slot.tl["alpha"].jump(s1, 0)

    @staticmethod
    def _clip(track, a, b):
        """ease covering [a,b] as a clipped part of the keyframe interval that contains it."""
        i = track.interval(a)
        if i is None or i + 1 >= len(track.k):
            return "linear"
        b0, b1 = track.k[i][0], track.k[i + 1][0]
        name = track.k[i + 1][2]
        if name == "linear" or b1 <= b0:
            return "linear"
        left = float((a - b0) / (b1 - b0))
        right = float((b - b0) / (b1 - b0))
        if left <= 1e-6 and right >= 1 - 1e-6:
            return name
        f = ease_fn(name)
        if abs(f(right) - f(left)) < 1e-5:
            return "linear"
        return (EASE[name], max(0.0, left), min(1.0, right))
