"""Small authoring library for Re:PhiEdit (RPE) JSON charts targeting Phira.

Conventions (verified against prpr/src/parse/rpe.rs):
  * coordinates: x in [-675, 675], y in [-450, 450] (+y is up), rotation in degrees (+ is clockwise)
  * speed v moves notes ~120*v RPE-y-units per second
  * an empty event array in a layer crashes Phira's Anim::chain -> never emit empty arrays
  * a line without alpha events is fully transparent -> every visible line gets alpha events
  * every line that carries notes needs speed events starting at beat 0
"""
from __future__ import annotations

import colorsys
import json
import math
from fractions import Fraction

BPM = 123.0
SPB = 60.0 / BPM

EASE = {
    "linear": 1, "sineOut": 2, "sineIn": 3, "quadOut": 4, "quadIn": 5, "sineInOut": 6, "quadInOut": 7,
    "cubicOut": 8, "cubicIn": 9, "quartOut": 10, "quartIn": 11, "cubicInOut": 12, "quartInOut": 13,
    "quintOut": 14, "quintIn": 15, "expoOut": 16, "expoIn": 17, "circOut": 18, "circIn": 19,
    "backOut": 20, "backIn": 21, "circInOut": 22, "backInOut": 23, "elasticOut": 24, "elasticIn": 25,
    "bounceOut": 26, "bounceIn": 27, "bounceInOut": 28, "elasticInOut": 29,
}

TAP, HOLD, FLICK, DRAG = 1, 2, 3, 4
EPSB = Fraction(1, 96)  # tiny beat length used for "instant" jumps


def frac(b, d=None) -> Fraction:
    if d is not None:
        return Fraction(b, d)
    if isinstance(b, Fraction):
        return b
    return Fraction(b).limit_denominator(1920)


def triple(b):
    f = frac(b)
    w = math.floor(f)
    r = f - w
    return [int(w), int(r.numerator), int(r.denominator)]


def ease_id(e):
    if isinstance(e, int):
        return e
    return EASE[e]


def hsv(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
    return (round(r * 255), round(g * 255), round(b * 255))


def mix(c1, c2, t):
    return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


class Track:
    """One animated property in one event layer: a list of non-overlapping segments."""

    def __init__(self, name):
        self.name = name
        self.segs = []  # (b0, b1, v0, v1, ease)

    def add(self, b0, b1, v0, v1, ease="linear"):
        b0, b1 = frac(b0), frac(b1)
        if b1 < b0:
            raise ValueError(f"{self.name}: segment ends before start {b0}->{b1}")
        self.segs.append((b0, b1, v0, v1, ease if isinstance(ease, tuple) else ease_id(ease)))
        return self

    def sorted(self):
        s = sorted(self.segs, key=lambda x: (x[0], x[1]))
        for a, b in zip(s, s[1:]):
            if b[0] < a[1]:
                raise ValueError(f"{self.name}: overlapping segments {a[:4]} / {b[:4]}")
        return s

    def value_at(self, b):
        """Value semantics of Phira's Anim (hold after a segment, extrapolate only before the first)."""
        b = frac(b)
        s = self.sorted()
        if not s:
            return None
        cur = None
        for seg in s:
            if seg[0] <= b:
                cur = seg
        if cur is None:
            return s[0][2]
        b0, b1, v0, v1, e = cur
        if b >= b1:
            return v1
        return (v0, v1, float((b - b0) / (b1 - b0)), e)

    def to_json(self, kind="float", compact=False):
        out = []
        for b0, b1, v0, v1, e in self.sorted():
            el, er = 0.0, 1.0
            if isinstance(e, tuple):  # (rpe easing id, easingLeft, easingRight): a clipped part of the curve
                e, el, er = e
            ev = {
                "bezier": 0, "bezierPoints": [0.0, 0.0, 0.0, 0.0], "easingLeft": round(float(el), 6),
                "easingRight": round(float(er), 6),
                "easingType": e, "linkgroup": 0, "start": v0, "end": v1,
                "startTime": triple(b0), "endTime": triple(b1),
            }
            if kind == "float":
                ev["start"] = round(float(v0), 3 if compact else 4)
                ev["end"] = round(float(v1), 3 if compact else 4)
            elif kind == "color":
                ev["start"] = [int(max(0, min(255, round(c)))) for c in v0]
                ev["end"] = [int(max(0, min(255, round(c)))) for c in v1]
            if compact:  # drop fields whose serde defaults in prpr are identical
                for k in ("bezier", "bezierPoints", "linkgroup"):
                    ev.pop(k)
                if ev["easingLeft"] == 0.0 and ev["easingRight"] == 1.0:
                    ev.pop("easingLeft"), ev.pop("easingRight")
                if ev["easingType"] == 1:
                    ev.pop("easingType")
            out.append(ev)
        return out


class Line:
    PROPS = ("alpha", "moveX", "moveY", "rotate", "speed")
    EXT = ("scaleX", "scaleY", "color", "text", "incline")

    def __init__(self, chart, name, texture="line.png", z=0, cover=True, father=-1, rot_with_father=True):
        self.chart = chart
        self.name = name
        self.texture = texture
        self.z = z
        self.cover = cover
        self.father = father
        self.rot_with_father = rot_with_father
        self.layers = [dict() for _ in range(4)]
        self.ext = {}
        self.notes = []
        self.ctrl = {}
        self.index = None

    # ---- tracks -------------------------------------------------------------
    def tr(self, prop, layer=0):
        if prop in self.EXT:
            return self.ext.setdefault(prop, Track(f"{self.name}.{prop}"))
        return self.layers[layer].setdefault(prop, Track(f"{self.name}.{prop}[{layer}]"))

    def ev(self, prop, b0, b1, v0, v1, ease="linear", layer=0):
        self.tr(prop, layer).add(b0, b1, v0, v1, ease)
        return self

    def kf(self, prop, pts, layer=0):
        """pts: [(beat, value, ease_into_next), ...] -> contiguous segments."""
        for (b0, v0, e), (b1, v1, _e) in zip(pts, pts[1:]):
            if frac(b1) > frac(b0):
                self.ev(prop, b0, b1, v0, v1, e, layer)
        return self

    def set(self, prop, b, v, layer=0):
        """instant change at beat b (tiny segment)."""
        self.ev(prop, frac(b), frac(b) + EPSB, v, v, "linear", layer)
        return self

    # ---- notes --------------------------------------------------------------
    def note(self, kind, b, x=0.0, end=None, above=True, speed=1.0, alpha=255, size=1.0, fake=False,
             visible=999999.0, yoff=0.0):
        b = frac(b)
        e = frac(end) if end is not None else b
        if kind == HOLD and e <= b:
            raise ValueError("hold needs end > start")
        self.notes.append({
            "type": kind, "above": 1 if above else 2, "startTime": triple(b), "endTime": triple(e),
            "positionX": round(float(x), 3), "yOffset": round(float(yoff), 3), "alpha": int(alpha), "size": float(size),
            "speed": float(speed), "isFake": 1 if fake else 0, "visibleTime": float(visible),
            "_b": b,
        })
        return self

    def control(self, kind, pts):
        """kind in pos/size/alpha/y; pts [(x_distance, value, easing_into_this_point)] (>=3 points)."""
        assert kind in ("pos", "size", "alpha", "y") and len(pts) >= 3
        self.ctrl[kind] = [{"easing": ease_id(e), "x": float(x), kind: float(v)} for x, v, e in pts]
        return self

    # ---- export -------------------------------------------------------------
    def to_json(self, compact=False):
        layers = []
        for li, L in enumerate(self.layers):
            d = {}
            for p in self.PROPS:
                t = L.get(p)
                if t is not None and t.segs:
                    key = {"alpha": "alphaEvents", "moveX": "moveXEvents", "moveY": "moveYEvents",
                           "rotate": "rotateEvents", "speed": "speedEvents"}[p]
                    d[key] = t.to_json(compact=compact)
            layers.append(d if d else None)
        while layers and layers[-1] is None:
            layers.pop()
        if not layers:
            layers = [None]
        ext = {}
        for p in self.EXT:
            t = self.ext.get(p)
            if t is not None and t.segs:
                key = {"scaleX": "scaleXEvents", "scaleY": "scaleYEvents", "color": "colorEvents",
                       "text": "textEvents", "incline": "inclineEvents"}[p]
                ext[key] = t.to_json("color" if p == "color" else ("str" if p == "text" else "float"), compact)
        notes = sorted(self.notes, key=lambda n: n["_b"])
        notes = [{k: v for k, v in n.items() if not k.startswith("_")} for n in notes]
        d = {
            "Group": 0, "Name": self.name, "Texture": self.texture, "bpmfactor": 1.0,
            "eventLayers": layers, "father": self.father, "isCover": 1 if self.cover else 0,
            "notes": notes, "numOfNotes": sum(1 for n in notes if not n["isFake"]), "zOrder": self.z,
            "rotateWithFather": self.rot_with_father,
        }
        if ext:
            d["extended"] = ext
        for k, v in self.ctrl.items():
            d[f"{k}Control"] = v
        if getattr(self, "attach", None):
            d["attachUI"] = self.attach
        return d


class Chart:
    def __init__(self, offset_ms, meta, bpm=BPM, compact=False):
        self.bpm = bpm
        self.compact = compact
        self.offset_ms = offset_ms
        self.meta = meta
        self.lines: list[Line] = []
        self.effects = []
        self.videos = []

    def line(self, name, **kw):
        ln = Line(self, name, **kw)
        ln.index = len(self.lines)
        self.lines.append(ln)
        return ln

    def effect(self, shader, b0, b1, vars=None, glob=False):
        self.effects.append({"start": triple(b0), "end": triple(b1), "shader": shader, "vars": vars or {}, "global": glob})

    def video(self, path, b, scale="cropCenter", alpha=1.0, dim=0.0):
        """a video played from beat b (prpr: extra.json "videos"; drawn under all judge lines, only while it lasts)."""
        self.videos.append({"path": path, "time": triple(b), "scale": scale, "alpha": alpha, "dim": dim})

    @staticmethod
    def var_kfs(pts):
        """pts: [(beat, value, ease_into_next)] -> extra.json keyframe list."""
        out = []
        for (b0, v0, e), (b1, v1, _e) in zip(pts, pts[1:]):
            out.append({"startTime": triple(b0), "endTime": triple(b1), "start": v0, "end": v1,
                        "easingType": ease_id(e), "easingLeft": 0.0, "easingRight": 1.0})
        return out

    def to_json(self):
        m = self.meta
        return {
            "BPMList": [{"bpm": self.bpm, "startTime": [0, 0, 1]}],
            "META": {"RPEVersion": 150, "background": m["illustration"], "charter": m["charter"],
                     "composer": m["composer"], "id": m.get("id", "0"), "illustration": m["illustrator"],
                     "level": m["level"], "name": m["name"], "offset": int(self.offset_ms), "song": m["music"]},
            "judgeLineGroup": ["Default"],
            "judgeLineList": [ln.to_json(self.compact) for ln in self.lines],
            "multiLineString": "",
            "multiScale": 1.0,
        }

    def extra_json(self):
        d = {"bpm": [{"time": [0, 0, 1], "bpm": self.bpm}], "effects": self.effects}
        if self.videos:
            d["videos"] = self.videos
        return d

    def note_count(self):
        return sum(1 for ln in self.lines for n in ln.notes if not n["isFake"])


def dump(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
