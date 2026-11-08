"""Approximate offline renderer for RPE charts, re-implementing prpr semantics in Python.

Usage:
  python preview.py <pkg_dir> sheet <out.png> <t1,t2,...> [cols] [W]
  python preview.py <pkg_dir> audit
"""
import bisect
import json
import math
import os
import sys
from functools import lru_cache

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RESPACK = os.environ.get("RESPACK", "assets/respack")  # Phira's default resource pack (phira repo: assets/respack)
FONT = os.environ.get("PFONT", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc")
RPE_W, RPE_H = 1350.0, 900.0
HEIGHT_RATIO = 0.83175
SPEED_RATIO = 10.0 / 45.0 / HEIGHT_RATIO
NOTE_W = 0.13175016
ASP = 16 / 9

# ---------------------------------------------------------------- tweens (prpr/src/core/tween.rs)
PI = math.pi


def _sine(x): return 1 - math.cos(x * PI / 2)
def _quad(x): return x * x
def _cubic(x): return x * x * x
def _quart(x): return x ** 4
def _quint(x): return x ** 5
def _expo(x): return 2.0 ** (10 * (x - 1))
def _circ(x): return 1 - math.sqrt(max(0.0, 1 - x * x))
def _back(x):
    c1 = 1.70158; c3 = c1 + 1
    return (c3 * x - c1) * x * x
def _elastic(x):
    c4 = 2 * PI / 3
    return -(2.0 ** (10 * x - 10) * math.sin((x * 10 - 10.75) * c4))
def _bounce(x):
    n1, d1 = 7.5625, 2.75
    x = 1 - x
    if x < 1 / d1: v = n1 * x * x
    elif x < 2 / d1: v = n1 * (x - 1.5 / d1) ** 2 + 0.75
    elif x < 2.5 / d1: v = n1 * (x - 2.25 / d1) ** 2 + 0.9375
    else: v = n1 * (x - 2.625 / d1) ** 2 + 0.984375
    return 1 - v


def _f2(f): return lambda x: 1 - f(1 - x)
def _f3(f):
    def g(x):
        x = x * 2
        return f(x) / 2 if x < 1 else 1 - f(2 - x) / 2
    return g


TW = [lambda x: 0.0, lambda x: 1.0, lambda x: x]
for f in (_sine, _quad, _cubic, _quart, _quint, _expo, _circ, _back, _elastic, _bounce):
    TW += [f, _f2(f), _f3(f)]
# RPE easingType -> TweenId (parse.rs RPE_TWEEN_MAP)
def e_(major, minor): return major * 3 + minor
SINE, QUAD, CUBIC, QUART, QUINT, EXPO, CIRC, BACK, ELASTIC, BOUNCE = range(1, 11)
IN, OUT, IO = 0, 1, 2
RPE_MAP = [2, 2, e_(SINE, OUT), e_(SINE, IN), e_(QUAD, OUT), e_(QUAD, IN), e_(SINE, IO), e_(QUAD, IO), e_(CUBIC, OUT),
           e_(CUBIC, IN), e_(QUART, OUT), e_(QUART, IN), e_(CUBIC, IO), e_(QUART, IO), e_(QUINT, OUT), e_(QUINT, IN),
           e_(EXPO, OUT), e_(EXPO, IN), e_(CIRC, OUT), e_(CIRC, IN), e_(BACK, OUT), e_(BACK, IN), e_(CIRC, IO),
           e_(BACK, IO), e_(ELASTIC, OUT), e_(ELASTIC, IN), e_(BOUNCE, OUT), e_(BOUNCE, IN), e_(BOUNCE, IO), e_(ELASTIC, IO)]


def clamped(tid, left, right):
    """prpr RPEEvent::tween: ClampedTween when a sub-range of the curve is selected."""
    left, right = min(max(left, 0.0), 1.0), min(max(right, 0.0), 1.0)
    if tid <= 2 or (abs(left) < 1e-5 and abs(right - 1) < 1e-5) or left >= right:
        return tid
    F = TW[tid]
    f0, f1 = F(left), F(right)
    return lambda x: (F(left + (right - left) * x) - f0) / (f1 - f0)


def rpe_tween(et):
    et = max(1, int(et))
    return RPE_MAP[et] if et < len(RPE_MAP) else RPE_MAP[0]


def str_tween(x, y, t):
    if "%P%" in x and "%P%" in y:
        xs, ys = x.replace("%P%", ""), y.replace("%P%", "")
        if t >= 1: return ys
        if t <= 0: return xs
        a, b = float(xs or 0), float(ys or 0)
        v = a + t * (b - a)
        return f"{v:.0f}" if a == int(a) and b == int(b) else f"{v:.3f}"
    if not x and not y: return ""
    if not y:
        return str_tween(y, x.replace("%P%", ""), 1 - t)
    if not x:
        return y[: int(round(t * len(y)))]
    if y.startswith(x):
        take = int(math.floor((len(y) - len(x)) * t)) + len(x)
        return y[:take]
    if x.startswith(y):
        take = int(round((len(x) - len(y)) * (1 - t))) + len(y)
        return x[:take]
    return x.replace("%P%", "")


class Anim:
    """prpr Anim with keyframes (time, value, tween_id); value type float, tuple(color) or str."""

    def __init__(self, kfs, kind="f"):
        self.kfs = kfs
        self.times = [k[0] for k in kfs]
        self.kind = kind

    def __call__(self, t):
        if not self.kfs:
            return None
        i = bisect.bisect_right(self.times, t) - 1
        if i < 0:
            i = 0
        if i == len(self.kfs) - 1:
            return self.kfs[i][1]
        (t1, v1, tw), (t2, v2, _) = self.kfs[i], self.kfs[i + 1]
        if t2 == t1:
            return v1
        x = (t - t1) / (t2 - t1)
        y = TW[tw](x) if isinstance(tw, int) else tw(x)
        if self.kind == "f":
            return v1 + (v2 - v1) * y
        if self.kind == "c":
            return tuple(a + (b - a) * y for a, b in zip(v1, v2))
        return str_tween(v1, v2, y)


def tri(v):
    return v[0] + v[1] / v[2]


class Chart:
    def __init__(self, pkg):
        self.pkg = pkg
        self.info = yaml.safe_load(open(os.path.join(pkg, "info.yml"), encoding="utf-8"))
        self.rpe = json.load(open(os.path.join(pkg, self.info["chart"]), encoding="utf-8"))
        self.bpm = self.rpe["BPMList"][0]["bpm"]
        assert len(self.rpe["BPMList"]) == 1
        self.spb = 60.0 / self.bpm
        ex = os.path.join(pkg, "extra.json")
        self.extra = json.load(open(ex, encoding="utf-8")) if os.path.exists(ex) else {"effects": []}
        self.tex = {}
        self.font_cache = {}
        lines = self.rpe["judgeLineList"]
        # max_time as in parse_rpe
        mt = 0.0
        for ln in lines:
            for n in ln.get("notes") or []:
                mt = max(mt, self.sec(n["endTime"]))
            for L in ln["eventLayers"]:
                if not L: continue
                for k in ("alphaEvents", "moveXEvents", "moveYEvents", "rotateEvents"):
                    for e in L.get(k) or []:
                        mt = max(mt, self.sec(e["endTime"]))
            ext = ln.get("extended") or {}
            for k in ("scaleXEvents", "scaleYEvents", "textEvents"):
                for e in ext.get(k) or []:
                    mt = max(mt, self.sec(e["endTime"]))
        self.max_time = mt + 1.0
        self.L = [self._line(ln) for ln in lines]
        # multiple hints
        cnt = {}
        for L in self.L:
            for n in L["notes"]:
                cnt[n["time"]] = cnt.get(n["time"], 0) + 1
        for L in self.L:
            for n in L["notes"]:
                n["mh"] = cnt[n["time"]] > 1
        self.order = sorted(range(len(self.L)), key=lambda i: (self.L[i]["z"], i))
        self._load_respack()
        self._load_bg()

    def sec(self, trip):
        return tri(trip) * self.spb

    # ---------------------------------------------------------------- parsing
    def _anim(self, evs, factor=1.0, kind="f", default=None):
        if not evs:
            return Anim([], kind)
        kfs = []
        if default is not None and tri(evs[0]["startTime"]) != 0.0:
            kfs.append((0.0, default, 0))
        for e in evs:
            s, en = e["start"], e["end"]
            if kind == "f":
                s, en = s * factor, en * factor
            elif kind == "c":
                s, en = tuple(c / 255 for c in s), tuple(c / 255 for c in en)
            kfs.append((self.sec(e["startTime"]), s, clamped(rpe_tween(e.get("easingType", 1)), e.get("easingLeft", 0.0), e.get("easingRight", 1.0))))
            kfs.append((self.sec(e["endTime"]), en, 0))
        return Anim(kfs, kind)

    def _sum_layers(self, ln, key, factor):
        anims = [self._anim(L[key], factor) for L in ln["eventLayers"] if L and L.get(key) is not None]
        if not anims:
            return lambda t: 0.0, False
        def f(t):
            v = 0.0
            for a in anims:
                x = a(t)
                if x is None:
                    raise RuntimeError("empty layer anim -> Phira would panic")
                v += x
            return v
        return f, True

    def _height(self, ln):
        layers = [L["speedEvents"] for L in ln["eventLayers"] if L and L.get("speedEvents")]
        if not layers:
            return None
        anims = []
        for evs in layers:
            kfs = []
            for e in evs:
                kfs.append((self.sec(e["startTime"]), e["start"], 2))
                kfs.append((self.sec(e["endTime"]), e["end"], 0))
            anims.append(Anim(kfs))
        pts = sorted(set([k[0] for a in anims for k in a.kfs] + [self.max_time]))
        spd = lambda t: sum(a(t) for a in anims) * SPEED_RATIO
        # exact trapezoid integration on breakpoints (speed is piecewise linear)
        H = [0.0]
        for a, b in zip(pts, pts[1:]):
            s0, s1 = spd(a), spd(b - 1e-6)
            H.append(H[-1] + (s0 + s1) * (b - a) / 2)
        def height(t):
            if t <= pts[0]:
                return spd(pts[0]) * (t - pts[0])
            i = bisect.bisect_right(pts, t) - 1
            if i >= len(pts) - 1:
                return H[-1] + spd(pts[-1]) * (t - pts[-1])
            a, b = pts[i], pts[i + 1]
            s0, s1 = spd(a), spd(b - 1e-6)
            u = t - a
            return H[i] + s0 * u + (s1 - s0) * u * u / (2 * (b - a))
        return height

    def _ctrl(self, ln, key):
        lst = ln.get(f"{key}Control") or []
        vals = [c[key] for c in lst]
        if not lst or (len(lst) == 2 and lst[0]["easing"] == 1 and abs(vals[0] - 1) < 1e-4):
            return None
        tweens = [RPE_MAP[max(1, c["easing"])] for c in lst[1:]] + [0]
        return Anim([(c["x"], v, tw) for c, v, tw in zip(lst, vals, tweens)])

    def _line(self, ln):
        d = {"name": ln["Name"], "tex": ln["Texture"], "z": ln.get("zOrder", 0), "parent": ln.get("father", -1),
             "rwp": ln.get("rotateWithFather", False), "cover": ln["isCover"] == 1, "attach": ln.get("attachUI")}
        d["alpha"], d["has_alpha"] = self._sum_layers(ln, "alphaEvents", 1 / 255)
        d["x"], _ = self._sum_layers(ln, "moveXEvents", 2 / RPE_W)
        d["y"], _ = self._sum_layers(ln, "moveYEvents", 2 / RPE_H)
        d["rot"], _ = self._sum_layers(ln, "rotateEvents", -1.0)
        if not d["has_alpha"]:
            d["alpha"] = lambda t: 0.0
        ext = ln.get("extended") or {}
        is_line = ln["Texture"] == "line.png"
        texts = ext.get("textEvents")
        factor = 1.0 if is_line else 2 / RPE_W
        default = 1.0 if is_line else factor
        sx_factor = factor * (0.5 if is_line and not texts and "attachUI" not in ln else 1.0)
        sxa = self._anim(ext.get("scaleXEvents"), sx_factor) if ext.get("scaleXEvents") else None
        sya = self._anim(ext.get("scaleYEvents"), factor) if ext.get("scaleYEvents") else None
        d["sx"] = (lambda t: sxa(t)) if sxa else (lambda t: default)
        d["sy"] = (lambda t: sya(t)) if sya else (lambda t: default)
        d["color"] = self._anim(ext["colorEvents"], kind="c", default=(1, 1, 1)) if ext.get("colorEvents") else None
        d["text"] = self._anim(texts, kind="s", default="") if texts else None
        d["incline"] = self._anim(ext["inclineEvents"], default=0.0) if ext.get("inclineEvents") else None
        d["ctrl"] = {k: self._ctrl(ln, k) for k in ("pos", "size", "alpha", "y")}
        h = self._height(ln)
        d["height"] = h
        notes = []
        for n in ln.get("notes") or []:
            t0 = self.sec(n["startTime"])
            t1 = self.sec(n["endTime"])
            notes.append({"kind": n["type"], "time": t0, "end": t1, "x": n["positionX"] / (RPE_W / 2),
                          "yoff": n["yOffset"] * 2 / RPE_H * n["speed"], "h": h(t0) if h else 0.0,
                          "eh": h(t1) if h else 0.0, "speed": n["speed"], "above": n["above"] == 1,
                          "fake": n["isFake"] != 0, "alpha": min(n["alpha"], 255) / 255, "vis": n["visibleTime"],
                          "size": n["size"]})
        d["notes"] = notes
        return d

    # ---------------------------------------------------------------- transforms
    def rot(self, i, t):
        L = self.L[i]
        r = L["rot"](t)
        if L["rwp"] and L["parent"] != -1:
            r += self.rot(L["parent"], t)
        return r

    def pos(self, i, t):
        L = self.L[i]
        p = np.array([L["x"](t), L["y"](t) / ASP])
        if L["parent"] != -1:
            pp = self.pos(L["parent"], t)
            a = math.radians(self.rot(L["parent"], t))
            R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
            return pp + R @ p
        return p

    # ---------------------------------------------------------------- resources
    def _load_respack(self):
        rp = {}
        for k in ("click", "drag", "flick", "hold", "click_mh", "drag_mh", "flick_mh", "hold_mh", "hit_fx"):
            rp[k] = Image.open(os.path.join(RESPACK, f"{k}.png")).convert("RGBA")
        self.rp = rp
        info = yaml.safe_load(open(os.path.join(RESPACK, "info.yml"), encoding="utf-8"))
        self.hold_atlas = tuple(info["holdAtlas"])
        self.hold_atlas_mh = tuple(info["holdAtlasMH"])
        self.hitfx_grid = tuple(info["hitFx"])

    def _load_bg(self):
        im = Image.open(os.path.join(self.pkg, self.info["illustration"])).convert("RGB")
        self.illu = im
        self.bg_blur = im.filter(ImageFilter.GaussianBlur(50))

    def texture(self, name):
        if name not in self.tex:
            self.tex[name] = Image.open(os.path.join(self.pkg, name)).convert("RGBA")
        return self.tex[name]

    def font(self, px):
        px = max(4, int(round(px)))
        if px not in self.font_cache:
            self.font_cache[px] = ImageFont.truetype(FONT, px)
        return self.font_cache[px]

    # ---------------------------------------------------------------- rendering
    def frame(self, t, W=960, show_ui=True, show_fx=True, label=None):
        H = int(round(W / ASP))
        S = W / 2.0  # px per world unit

        def to_px(p):
            return (W / 2 + p[0] * S, H / 2 - p[1] * S)

        bg = self.bg_blur.copy()
        bw, bh = bg.size
        sc = max(W / bw, H / bh)
        bg = bg.resize((int(bw * sc) + 1, int(bh * sc) + 1), Image.BILINEAR)
        ox, oy = (bg.size[0] - W) // 2, (bg.size[1] - H) // 2
        canvas = bg.crop((ox, oy, ox + W, oy + H)).convert("RGBA")
        dim = float(self.info.get("backgroundDim", 0.6))
        canvas = Image.alpha_composite(canvas, Image.new("RGBA", (W, H), (0, 0, 0, int(255 * dim))))
        draw_list = []
        line_tf = {}
        for i in range(len(self.L)):
            line_tf[i] = (self.pos(i, t), math.radians(self.rot(i, t)))
        for i in self.order:
            L = self.L[i]
            alpha = L["alpha"](t)
            p, a = line_tf[i]
            sx, sy = L["sx"](t), L["sy"](t)
            col = L["color"](t) if L["color"] else None
            if L["tex"] == "line.png" and L["text"] is None:
                c = col if col else (1.0, 0.92, 0.6)
                A = max(0.0, alpha)
                if A <= 0.002:
                    continue
                th = (0.0076 if abs(sy - 1) > 1e-4 else 0.01) * sy
                hl = 6.0 * sx
                ca, sa = math.cos(a), math.sin(a)
                dx, dy = ca * hl, sa * hl
                nx, ny = -sa * th / 2, ca * th / 2
                pts = [(p[0] - dx + nx, p[1] - dy + ny), (p[0] + dx + nx, p[1] + dy + ny),
                       (p[0] + dx - nx, p[1] + dy - ny), (p[0] - dx - nx, p[1] - dy - ny)]
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(layer).polygon([to_px(q) for q in pts], fill=tuple(int(255 * min(1, v)) for v in c) + (int(255 * min(1, A)),))
                canvas = Image.alpha_composite(canvas, layer)
            elif L["text"] is not None:
                s = L["text"](t)
                A = max(0.0, alpha)
                if not s or A <= 0.002:
                    continue
                c = col if col else (1, 1, 1)
                em = 0.08 * S
                f = self.font(em * max(abs(sy), 1e-3) * 2)
                tmp = Image.new("RGBA", (1, 1))
                bbox = ImageDraw.Draw(tmp).multiline_textbbox((0, 0), s, font=f, align="center")
                tw, th_ = bbox[2] - bbox[0] + 4, bbox[3] - bbox[1] + 4
                timg = Image.new("RGBA", (tw, th_), (0, 0, 0, 0))
                ImageDraw.Draw(timg).multiline_text((2 - bbox[0], 2 - bbox[1]), s, font=f, align="center",
                                                    fill=tuple(int(255 * min(1, v)) for v in c) + (int(255 * min(1, A)),))
                scale_x = abs(sx) / max(abs(sy), 1e-3) / 2
                scale_y = 0.5
                canvas = self._blit(canvas, timg, p, a, scale_x, scale_y, to_px, W, H, px_units=True)
            else:
                A = max(0.0, alpha)
                if A <= 0.002:
                    continue
                img = self.texture(L["tex"])
                c = col if col else (1, 1, 1)
                img = self._tint(img, c, A)
                canvas = self._blit(canvas, img, p, a, sx, sy, to_px, W, H)
        # notes (all after lines)
        nlayer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        fx = []
        order_kind = {2: 0, 4: 1, 1: 2, 3: 3}
        items = []
        for i in self.order:
            L = self.L[i]
            if L["height"] is None:
                continue
            lh = L["height"](t)
            p, a = line_tf[i]
            inc = L["incline"](t) if L["incline"] else 0.0
            incs = math.sin(math.radians(inc))
            for n in L["notes"]:
                judged = (not n["fake"]) and t >= n["time"]
                if judged and n["kind"] != 2:
                    if t - n["time"] < 0.5:
                        fx.append((i, n, t - n["time"]))
                    continue
                if n["kind"] == 2 and t >= n["end"]:
                    continue
                if n["kind"] == 2 and judged and t - n["time"] < 0.5:
                    fx.append((i, n, t - n["time"]))
                ctrl = L["ctrl"]
                dist = (n["h"] - lh + n["yoff"] / n["speed"]) * RPE_H / 2
                cy = ctrl["y"](dist) if ctrl["y"] else 1.0
                spd = n["speed"] * cy
                base = (n["h"] - lh) / ASP * spd
                cover_base = base
                draw_below = not L["cover"]
                if not draw_below and (((t - 0.16 >= n["time"] or (n["fake"] and t >= n["time"])) and n["kind"] != 2)
                                       or (n["time"] > t and cover_base <= -0.001)):
                    continue
                al = n["alpha"]
                if n["vis"] < n["time"] and t < n["time"] - n["vis"]:
                    al = 0.0
                if ctrl["alpha"]:
                    al *= ctrl["alpha"](dist)
                if not draw_below:
                    al *= max(0.0, min(1.0, (min(n["time"] - t, 0) / 0.16 + 1)))
                    if n["fake"] and t >= n["time"]:
                        al = 0
                if al <= 0.003:
                    continue
                xm = n["x"]
                if n["kind"] != 2:
                    incl = 1 - incs * (base * ASP + n["yoff"]) * RPE_H / 2 / 360
                    xm *= incl * (ctrl["pos"](dist) if ctrl["pos"] else 1.0)
                size = n["size"] * (ctrl["size"](dist) if ctrl["size"] else 1.0)
                yloc = n["yoff"] / ASP + base
                if n["kind"] == 2:
                    yb = max(0.0, base) if t < n["time"] else 0.0
                    ye = (n["eh"] - lh) / ASP * spd
                    items.append((order_kind[2], i, n, xm, yb, ye, size, al, p, a))
                else:
                    items.append((order_kind[n["kind"]], i, n, xm, yloc, None, size, al, p, a))
        items.sort(key=lambda it: it[0])
        for k, i, n, xm, y0, y1, size, al, p, a in items:
            nlayer = self._draw_note(nlayer, n, xm, y0, y1, size, al, p, a, to_px, W, H, S)
        canvas = Image.alpha_composite(canvas, nlayer)
        if show_fx:
            canvas = self._effects(canvas, t)
        # hit effects
        hit = self.rp["hit_fx"]
        gx, gy = self.hitfx_grid
        fw, fh = hit.size[0] // gx, hit.size[1] // gy
        for i, n, dt in fx:
            p, a = line_tf[i]
            ca, sa = math.cos(a), math.sin(a)
            wp = (p[0] + ca * n["x"], p[1] + sa * n["x"])
            k = min(gx * gy - 1, int(dt / 0.5 * gx * gy))
            fr = hit.crop(((k % gx) * fw, (k // gx) * fh, (k % gx + 1) * fw, (k // gx + 1) * fh))
            size = int(NOTE_W * 2 * S * 0.9 * 1.1)
            fr = fr.resize((size, size), Image.BILINEAR)
            fr = self._tint(fr, (1.0, 0.93, 0.62), 1.0)
            cx, cy = to_px(wp)
            canvas.alpha_composite(fr, (int(cx - size / 2), int(cy - size / 2))) if 0 <= cx < W and 0 <= cy < H else None
        if show_ui:
            d = ImageDraw.Draw(canvas)
            f = self.font(H * 0.035)

            def ui_a(el, a):  # attachUI: the element takes the alpha of the line it hangs from (position ignored)
                for L in self.L:
                    if L["attach"] == el:
                        return int(a * max(0.0, min(1.0, L["alpha"](t))))
                return a
            for el, xy, txt, ft, a, anc in (("pause", (W * 0.012, H * 0.012), "II", f, 200, "la"),
                                            ("score", (W * 0.985, H * 0.015), "1000000", f, 220, "ra"),
                                            ("name", (W * 0.015, H * 0.965), self.info["name"], self.font(H * 0.03), 220, "ls"),
                                            ("level", (W * 0.985, H * 0.965), self.info["level"], self.font(H * 0.03), 220, "rs")):
                a = ui_a(el, a)
                if a > 0:
                    d.text(xy, txt, font=ft, fill=(255, 255, 255, a), anchor=anc)
        if label:
            d = ImageDraw.Draw(canvas)
            d.rectangle((0, H - 18, 150, H), fill=(0, 0, 0, 160))
            d.text((4, H - 16), label, font=self.font(13), fill=(255, 255, 0, 255))
        return canvas

    @staticmethod
    def _tint(img, c, A):
        arr = np.asarray(img).astype(np.float32)
        arr[..., 0] *= min(1, c[0]); arr[..., 1] *= min(1, c[1]); arr[..., 2] *= min(1, c[2])
        arr[..., 3] *= min(1.0, A)
        return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

    def _blit(self, canvas, img, p, a, sx, sy, to_px, W, H, px_units=False):
        """draw img centered at world p, rotated by a (rad, CCW in world), world size = img_px * (sx, sy)."""
        S = W / 2.0
        iw, ih = img.size
        if px_units:
            kx, ky = sx, sy  # canvas px per image px
        else:
            kx, ky = sx * S, sy * S
        if abs(kx) < 1e-6 or abs(ky) < 1e-6:
            return canvas
        cx, cy = to_px(p)
        # canvas -> image: rotate by +a in screen terms (screen y down => angle sign flips)
        ca, sa = math.cos(a), math.sin(a)
        # forward: img (u,v) centered -> canvas: X = cx + (u*kx)*ca + (v*ky)*sa ; Y = cy - (u*kx)*sa + (v*ky)*ca
        # inverse:
        A11, A12, A21, A22 = kx * ca, ky * sa, -kx * sa, ky * ca
        det = A11 * A22 - A12 * A21
        i11, i12, i21, i22 = A22 / det, -A12 / det, -A21 / det, A11 / det
        # u = i11*(X-cx) + i12*(Y-cy) + iw/2
        coeffs = (i11, i12, -i11 * cx - i12 * cy + iw / 2, i21, i22, -i21 * cx - i22 * cy + ih / 2)
        out = img.transform((W, H), Image.AFFINE, coeffs, resample=Image.BILINEAR, fillcolor=(0, 0, 0, 0))
        return Image.alpha_composite(canvas, out)

    def _draw_note(self, layer, n, xm, y0, y1, size, al, p, a, to_px, W, H, S):
        mh = n["mh"]
        kind = {1: "click", 3: "flick", 4: "drag", 2: "hold"}[n["kind"]]
        key = kind + ("_mh" if mh else "")
        tex = self.rp[key]
        base_w = self.rp[kind].size[0]
        half = NOTE_W * (tex.size[0] / base_w)
        sgn = 1 if n["above"] else -1
        ca, sa = math.cos(a), math.sin(a)
        def world(lx, ly):
            ly *= sgn
            return (p[0] + ca * lx - sa * ly, p[1] + sa * lx + ca * ly)
        rot = a if n["above"] else a + math.pi
        if n["kind"] != 2:
            img = tex
            hw = half * size
            hh = half * tex.size[1] / tex.size[0]
            c = world(xm, y0)
            if not (-1.3 < c[0] < 1.3 and -0.9 < c[1] < 0.9):
                return layer
            img = self._tint(img, (1, 1, 1), al)
            return self._blit(layer, img, c, rot, hw * 2 / img.size[0], hh * 2 / img.size[1], to_px, W, H)
        # hold: simple body rectangle + head
        atlas = self.hold_atlas_mh if mh else self.hold_atlas
        th = tex.size[1]
        body = tex.crop((0, atlas[1] if False else atlas[0], tex.size[0], th - atlas[1]))
        hw = half * size
        length = max(1e-4, y1 - y0)
        mid = world(xm, (y0 + y1) / 2)
        bimg = self._tint(body, (1, 1, 1), al)
        layer = self._blit(layer, bimg, mid, rot, hw * 2 / bimg.size[0], length / bimg.size[1], to_px, W, H)
        return layer

    # ---------------------------------------------------------------- effects
    def _effect_vars(self, ef, t):
        vals = {}
        for k, v in (ef.get("vars") or {}).items():
            if isinstance(v, (int, float)):
                vals[k] = float(v)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                a = Anim([], "f")
                kfs = []
                for kf in v:
                    sv, evv = kf["start"], kf["end"]
                    kfs.append((self.sec(kf["startTime"]), sv, rpe_tween(kf["easingType"])))
                    kfs.append((self.sec(kf["endTime"]), evv, 0))
                kind = "f" if isinstance(v[0]["start"], (int, float)) else "c"
                if kind == "c":
                    kfs = [(a_, tuple(x), b_) for a_, x, b_ in kfs]
                vals[k] = Anim(kfs, kind)(t)
            else:
                vals[k] = v
        return vals

    def _effects(self, canvas, t):
        arr = None
        for ef in self.extra.get("effects", []):
            if not (self.sec(ef["start"]) <= t < self.sec(ef["end"])):
                continue
            if arr is None:
                arr = np.asarray(canvas.convert("RGB")).astype(np.float32) / 255
            v = self._effect_vars(ef, t)
            sh = ef["shader"]
            arr = apply_shader(arr, sh, v, t)
        if arr is None:
            return canvas
        return Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")


def _sample(arr, u, v):
    """bilinear sample arr (H,W,3) at uv in [0,1] (v=0 is bottom like GL)."""
    H, W, _ = arr.shape
    x = np.clip(u * W - 0.5, 0, W - 1)
    y = np.clip((1 - v) * H - 0.5, 0, H - 1)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    x1 = np.minimum(x0 + 1, W - 1); y1 = np.minimum(y0 + 1, H - 1)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    return (arr[y0, x0] * (1 - fx) * (1 - fy) + arr[y0, x1] * fx * (1 - fy) + arr[y1, x0] * (1 - fx) * fy + arr[y1, x1] * fx * fy)


def apply_shader(arr, sh, v, t):
    H, W, _ = arr.shape
    ys, xs = np.mgrid[0:H, 0:W]
    u = (xs + 0.5) / W
    vv = 1 - (ys + 0.5) / H
    if sh == "vignette":
        col = np.array(v.get("color", (0, 0, 0, 1))[:3], dtype=np.float32)
        ext = v.get("extend", 0.25); rad = v.get("radius", 15.0)
        nu, nv = u * (1 - vv), vv * (1 - u)
        vig = np.clip(nu * nv * rad, 1e-9, None) ** ext
        vig = vig[..., None]
        return col * (1 - vig) + arr * vig
    if sh == "grayscale":
        f = v.get("factor", 1.0)
        g = (arr @ np.array([0.299, 0.587, 0.114], dtype=np.float32))[..., None]
        return arr * (1 - f) + g * f
    if sh == "chromatic":
        p = v.get("power", 0.01)
        ou, ov = (u - 0.5), -(vv - 0.5)
        r = _sample(arr, u - p * ou, vv + p * ov)[..., 0]
        b = _sample(arr, u + p * ou, vv - p * ov)[..., 2]
        out = arr.copy(); out[..., 0] = r; out[..., 2] = b
        return out
    if sh == "radialBlur":
        cx, cy, p, n = v.get("centerX", 0.5), v.get("centerY", 0.5), v.get("power", 0.01), int(v.get("sampleCount", 6))
        acc = np.zeros_like(arr)
        for i in range(max(1, n)):
            acc += _sample(arr, u - p * (u - cx) * i, vv - p * (vv - cy) * i)
        return acc / max(1, n)
    if sh == "shockwave":
        prog, cx, cy = v.get("progress", 0.2), v.get("centerX", 0.5), v.get("centerY", 0.5)
        wd, dist_, expand = v.get("width", 0.1), v.get("distortion", 0.8), v.get("expand", 10.0)
        aspect = H / W
        ccy = (cy - 0.5) * aspect + 0.5
        ty = (vv - 0.5) * aspect + 0.5
        d = np.sqrt((u - cx) ** 2 + (ty - ccy) ** 2) + 1e-6
        m = (prog - wd <= d) & (d <= prog + wd)
        diff = d - prog
        sd = 1 - np.abs(diff * expand) ** dist_
        dt = diff * sd
        nu = u + (u - cx) / d * dt / (prog * d * 40 + 1e-6)
        nty = ty + (ty - ccy) / d * dt / (prog * d * 40 + 1e-6)
        src = _sample(arr, np.where(m, nu, u), np.where(m, (nty - 0.5) / aspect + 0.5, vv))
        src = src + np.where(m[..., None], src * sd[..., None] / (prog * d[..., None] * 40 + 1e-6), 0)
        return src
    if sh == "fisheye":
        p = v.get("power", -0.1)
        aspect = W / H
        px, py = u, vv / aspect
        mx, my = 0.5, 0.5 / aspect
        dx, dy = px - mx, py - my
        r = np.sqrt(dx * dx + dy * dy) + 1e-9
        npow = (2 * math.pi / (2 * math.sqrt(mx * mx + my * my))) * p
        if npow > 0:
            bind = math.sqrt(mx * mx + my * my)
            k = np.tan(r * npow) * bind / math.tan(bind * npow)
        else:
            bind = mx if aspect < 1 else my
            k = np.arctan(r * -npow * 10) * bind / math.atan(-npow * bind * 10) if npow != 0 else r
        nx, ny = mx + dx / r * k, my + dy / r * k
        return _sample(arr, nx, ny * aspect)
    if sh == "pixel":
        s = max(1.0, v.get("size", 10.0))
        fx_, fy_ = W / s, H / s
        nx = np.floor(u * fx_ + 0.5) / fx_
        ny = np.floor(vv * fy_ + 0.5) / fy_
        return _sample(arr, nx, ny)
    if sh == "glitch":
        p, rate, spd, bc, cr = v.get("power", 0.03), v.get("rate", 0.6), v.get("speed", 5.0), v.get("blockCount", 30.5), v.get("colorRate", 0.01)
        def rnd(s): return (543.2543 * np.sin(np.asarray(s) * 3525.46 + np.asarray(s) * -54.3415)) % 1.0
        en = float(rnd(math.trunc(t * spd)) < rate)
        nu = u + (rnd(np.trunc(vv * bc) / bc + t) - 0.5) * p * en
        out = _sample(arr, nu, vv)
        if en:
            out[..., 0] = _sample(arr, nu + cr, vv)[..., 0]
            out[..., 2] = _sample(arr, nu - cr, vv)[..., 2]
        return out
    if sh == "noise":
        p = v.get("power", 0.03); seed = v.get("seed", 81.0)
        rx = (np.sin((u + seed) * 12.9898 + vv * 78.233) * 43758.5453) % 1.0
        ry = (np.sin((u + seed) * -148.998 + vv * -65.233) * 43758.5453) % 1.0
        return _sample(arr, u + (rx - 0.5) * p, vv + (ry - 0.5) * p)
    return arr


def sheet(chart, times, out, cols=4, W=640, labels=None):
    frames = [chart.frame(t, W=W, label=(labels[i] if labels else f"{t:7.2f}s b{t / chart.spb:6.2f}")) for i, t in enumerate(times)]
    H = frames[0].size[1]
    rows = (len(frames) + cols - 1) // cols
    sh = Image.new("RGB", (cols * W + (cols - 1) * 4, rows * H + (rows - 1) * 4), (40, 40, 40))
    for k, f in enumerate(frames):
        sh.paste(f.convert("RGB"), ((k % cols) * (W + 4), (k // cols) * (H + 4)))
    sh.save(out)
    return out


def audit(chart, report_limit=40):
    """Check every real note: hit point on screen, visible approach time, overlapping simultaneous notes."""
    probs = []
    stats = {"notes": 0, "offscreen_hit": 0, "short_view": 0, "overlap": 0}
    hits = {}
    for i, L in enumerate(chart.L):
        if L["height"] is None:
            continue
        for n in L["notes"]:
            if n["fake"]:
                continue
            stats["notes"] += 1
            t = n["time"]
            p = chart.pos(i, t)
            a = math.radians(chart.rot(i, t))
            hp = (p[0] + math.cos(a) * n["x"], p[1] + math.sin(a) * n["x"])
            if not (-1.0 < hp[0] < 1.0 and -1 / ASP < hp[1] < 1 / ASP):
                stats["offscreen_hit"] += 1
                probs.append(f"off-screen hit: line {i}({L['name']}) t={t:.2f} b={t / chart.spb:.2f} at {hp[0]:.2f},{hp[1]:.2f}")
            # approach visibility: time the note is on screen before hit (sample)
            seen = 0.0
            for k in range(1, 41):
                tt = t - k * 0.05
                if tt < 0:
                    break
                pp = chart.pos(i, tt)
                aa = math.radians(chart.rot(i, tt))
                lh = L["height"](tt)
                y = (n["h"] - lh) / ASP * n["speed"] * (1 if n["above"] else -1)
                if (n["h"] - lh) * n["speed"] < -0.001 and L["cover"]:
                    break
                wx = pp[0] + math.cos(aa) * n["x"] - math.sin(aa) * y
                wy = pp[1] + math.sin(aa) * n["x"] + math.cos(aa) * y
                vis_ok = not (n["vis"] < n["time"] and tt < n["time"] - n["vis"])
                if -1.05 < wx < 1.05 and -0.6 < wy < 0.6 and vis_ok:
                    seen = k * 0.05
                else:
                    break
            if seen < 0.30:
                stats["short_view"] += 1
                probs.append(f"short approach ({seen:.2f}s): line {i}({L['name']}) b={t / chart.spb:.2f}")
            key = round(t, 4)
            for q in hits.get(key, []):
                if abs(q[0] - hp[0]) < 0.12 and abs(q[1] - hp[1]) < 0.05:
                    stats["overlap"] += 1
                    probs.append(f"overlapping simultaneous notes b={t / chart.spb:.2f} at {hp[0]:.2f},{hp[1]:.2f}")
            hits.setdefault(key, []).append(hp)
    return stats, probs[:report_limit]


if __name__ == "__main__":
    pkg = sys.argv[1]
    mode = sys.argv[2]
    ch = Chart(pkg)
    if mode == "sheet":
        out = sys.argv[3]
        times = [float(x) for x in sys.argv[4].split(",")]
        cols = int(sys.argv[5]) if len(sys.argv) > 5 else 4
        W = int(sys.argv[6]) if len(sys.argv) > 6 else 640
        sheet(ch, times, out, cols, W)
        print("saved", out)
    elif mode == "audit":
        st, pr = audit(ch)
        print(st)
        for p in pr:
            print(" ", p)
