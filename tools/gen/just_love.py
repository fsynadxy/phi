"""Just Love (feat. PSYQUI) — a showcase chart for Phira, built around the cover illustration:
snow, a swing, blue roses and the snow lotus (雪蓮).

The song is 160 BPM throughout; beat b sounds at 0.0155 + 0.375 b s and bar k starts on beat 3 + 4k.

    bars    beats     music                               picture
    0-7     3-35      chopped vocal harmonies, hard stops  the illustration itself, the title
    8-15    35-67     build: sub drone, four on the floor  the picture dissolves into snow, the line is drawn
    16-47   67-195    drop: two-step break, bent leads      CRYSTALLIZE  a six-armed snow crystal of judge lines
    48-55   195-227   breakdown, build, kick-stop fill      still air; the ice cracks three times and bursts
    56-87   227-355   chorus                                BLOOM  the lotus opens, petals fly out to a ring of lines
    88-103  355-419   quiet half-time, 808 glides           SWING  the judge line hangs from two ropes over a frozen lake
    104-120 419-487   second drop                           PRISM  a hexagon of lines, light split into colours
    121-128 487-519   keys only                             LETTER  the illustration again, slowly panned
    129-136 519-551   build and the same kick-stop fill     the ice cracks again: Just / Love
    137-168 551-679   last chorus                           FULL BLOOM  flower, ring and crystal together
    169-176 679-711   last drop                             the crystal, at full speed
    177-192 711-775   quiet coda, a cappella ending         AFTERGLOW  the swing slows down; the picture; a heart closes
"""
import math
import os
import random
import shutil

import madlib as ML
from chartlib import Chart, DRAG, EPSB, FLICK, HOLD, TAP
from jl_core import (B, BLUSH, DEEP, F, GOLD, ICE, INDIGO, JL, LAVENDER, LINE, MINT, NIGHT, PINK, PX, ROSE, SKY, SNOW,
                     VIOLET, WHITE, FxTrack, Lens, Music, Notes, Rig, Stage, mix)
from madlib import Engine

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "justlove")
BPM = 160.0
OFFSET_MS = 16  # the first beat's transient is at 15.5 ms
END = 782

INFO = {
    "name": "Just Love (feat. PSYQUI)",
    "difficulty": 15.0,
    "level": "SP Lv.?",
    "charter": "claude",
    "composer": "PSYQUI",
    "illustrator": "「雪蓮 YUKI-HASU」封面",
    "chart": "chart.json",
    "format": "rpe",
    "music": "song.ogg",
    "illustration": "illustration.jpg",
    "previewStart": 85.0,
    "previewEnd": 109.0,
    "aspectRatio": 1.7777778,
    "backgroundDim": 0.5,
    "lineLength": 6.0,
    "offset": 0.0,
    "tip": "观赏谱 · 建议开启 Autoplay 与特效观看",
    "tags": ["观赏谱", "showcase", "autoplay", "PSYQUI", "東雪蓮"],
    "intro": "以封面为题的观赏谱：初雪、结晶、雪莲绽放、秋千与冰湖。全曲 160 BPM，谱面与演出逐拍对齐。",
    "holdPartialCover": False,
    "noteUniformScale": False,
    "forceAspectRatio": True,  # the line geometry is built for 16:9; narrower screens get bars instead of a stretched picture
    "useRpe170Speed": False,
    "useAttachUiFix": True,
}

TEX = {
    "white.png": (64, 64), "glow.png": (256, 256), "disc.png": (256, 256), "ring.png": (512, 512), "beam.png": (1024, 64),
    "grad.png": (64, 512), "band.png": (64, 512), "spike.png": (256, 1024), "flake_a.png": (1024, 1024), "flake_b.png": (1024, 1024),
    "flake_s.png": (256, 256), "hex.png": (512, 512), "petal.png": (256, 512), "rose.png": (512, 512),
    "heart.png": (512, 512), "heart_o.png": (512, 512), "spark.png": (256, 256), "bokeh.png": (256, 256),
    "snow_a.png": (1024, 1024), "snow_b.png": (1024, 1024), "stars.png": (2048, 1152), "aurora.png": (1024, 512),
    "rays.png": (1024, 1024), "mist.png": (1024, 576), "vig.png": (512, 288), "crack.png": (1024, 576),
    "cover_wide.png": (1280, 720),
}
SHADERS = ("lens", "kaleido", "shatter", "mirror", "heart", "glow")
LITE = bool(os.environ.get("JL_LITE"))  # no custom GLSL at all (only Phira's built-in shockwave): the fallback package


def _text_sizes():
    from PIL import Image
    out = {}
    for n in sorted(os.listdir(DATA)):
        if n.startswith("t_") and n.endswith(".png"):
            out[n] = Image.open(os.path.join(DATA, n)).size
    return out


TEX.update(_text_sizes())
ML.register_textures(TEX)


def th(name, w):
    """height of a texture drawn w wide"""
    pw, ph = TEX[name]
    return w * ph / pw


# ================================================================== motifs
def glow(s, x, y, d, color, a=255, z=10, start=None, end=None):
    return s.tex("glow.png", x, y, d, d, 0.0, color, a, z, start, end)


def ring(s, x, y, r, color, a=255, z=0, start=None, end=None):
    return s.tex("ring.png", x, y, 2 * r / 0.94, 2 * r / 0.94, 0.0, color, a, z, start, end)


def ripple(s, b, x, y, r0, r1, color, a=220, z=20, dur=1.5, ease="expoOut"):
    b = F(b)
    e = ring(s, x, y, r0, color, a, z, b, b + F(dur))
    e.at(b + F(dur), ease, w=2 * r1 / 0.94, h=2 * r1 / 0.94, alpha=0)
    return e


def sparkle(s, b, x, y, size, color=WHITE, life=1, z=40, a=255, spin=40.0, rot=0.0):
    """a four-pointed glint that pops, turns a little and fades"""
    b, life = F(b), F(life)
    e = s.tex("spark.png", x, y, size * 0.2, size * 0.2, rot, color, a, z, b, b + life)
    e.at(b + life * F(1, 5), "expoOut", w=size, h=size)
    e.at(b + life, "quadIn", w=size * 0.35, h=size * 0.35, alpha=0, rot=rot + spin)
    return e


def burst(s, b, x, y, n, r0, r1, size, color, R, life=1.5, z=40, tex="spark.png", a=255):
    """n particles thrown outwards from (x, y)"""
    b, life = F(b), F(life)
    out = []
    for k in range(n):
        ang = 2 * math.pi * (k + R.uniform(-0.3, 0.3)) / n
        d0, d1 = r0 * R.uniform(0.7, 1.2), r1 * R.uniform(0.6, 1.15)
        sz = size * R.uniform(0.6, 1.3)
        e = s.tex(tex, x + math.cos(ang) * d0, y + math.sin(ang) * d0, sz, sz, R.uniform(0, 90), color, a, z, b, b + life)
        e.at(b + life, "expoOut", x=x + math.cos(ang) * d1, y=y + math.sin(ang) * d1)
        e.at(b + life * F(1, 2), "linear", alpha=a)
        e.at(b + life, "quadIn", alpha=0)
        out.append(e)
    return out


def scroll(s, tex, color, a, w, speed, z, start=None, end=None, rot=0.0, drift=0.0, a_in=0, a_out=0):
    """an endless layer (falling snow): two copies of a square texture sliding `speed` units per beat along the
    texture's own downward direction (rot: degrees clockwise), wrapping every texture height; drift: x slide in total"""
    st = F(start) if start is not None else s.b0
    en = F(end) if end is not None else s.b1
    th_ = math.radians(rot)
    dx, dy = -math.sin(th_), -math.cos(th_)  # texture-down in screen space
    period = F(round(w / abs(speed) * 16), 16)
    span = float(en - st)
    els = []
    for k in range(2):
        ox, oy = -k * w * dx, -k * w * dy
        e = s.tex(tex, ox, oy, w, w, rot, color, 0 if a_in else a, z, st, en)
        b = st
        while b < en:
            b1 = min(en, b + period)
            fr = float((b1 - b) / period)
            d0, d1 = drift * float(b - st) / span, drift * float(b1 - st) / span
            e.at(b1, "linear", x=ox + w * dx * fr + d1, y=oy + w * dy * fr)
            if b1 < en:
                e.at(b1, "linear", x=ox + d1, y=oy)
            b = b1
        if a_in:
            e.at(st + F(a_in), "sineOut", alpha=a)
        if a_out:
            e.at(en - F(a_out), "linear", alpha=a)
            e.at(en, "sineIn", alpha=0)
        els.append(e)
    return els


def snow(s, amount=1.0, speed=1.0, wind=0.0, start=None, end=None, a_in=0, a_out=0, color=SNOW, near=True):
    """far and near snow layers; amount scales opacity, speed the fall, wind the slant (degrees)"""
    scroll(s, "snow_a.png", color, int(150 * amount), 1900, 150 * speed, -22, start, end, rot=wind * 0.6, a_in=a_in, a_out=a_out)
    if near:
        scroll(s, "snow_b.png", color, int(200 * amount), 2100, 290 * speed, 46, start, end, rot=wind, a_in=a_in, a_out=a_out)


def caption(s, tex, b0, b1, x=-560, y=-346, w=None, color=ICE, a=190, z=60):
    """a small chapter caption with a hairline, bottom left"""
    b0, b1 = F(b0), F(b1)
    w = w or TEX[tex][0] * 0.42
    h = th(tex, w)
    t = s.tex(tex, x + w / 2 - 30, y, w, h, 0.0, color, 0, z, b0, b1)
    t.at(b0 + 2, "expoOut", alpha=a, x=x + w / 2).at(b1 - 2, "linear", alpha=a).at(b1, "quadIn", alpha=0)
    r = s.tex("white.png", x - 26, y, 0, 2.5, 0.0, color, a, z, b0, b1)
    r.at(b0 + 2, "expoOut", w=34).at(b1 - 2, "linear", alpha=a).at(b1, "quadIn", alpha=0)
    return t


def watermark(s, tex, b0, b1, x, y, w, color, a=46, z=-36, drift=-40.0):
    """a large, faint glyph behind everything (雪 for the crystal, 蓮 for the lotus)"""
    b0, b1 = F(b0), F(b1)
    e = s.tex(tex, x, y, w, None, 0.0, color, 0, z, b0, b1)
    e.at(b0 + 3, "sineOut", alpha=a).at(b1 - 3, "linear", alpha=a).at(b1, "sineIn", alpha=0)
    e.at(b1, "linear", x=x + drift)
    return e


def heart_up(s, b, x, y, size, color=PINK, rise=150, life=3, z=24, a=210, sway=30.0):
    """a small heart that floats up from a hit and fades"""
    b, life = F(b), F(life)
    e = s.tex("heart.png", x, y, size * 0.3, size * 0.3, 0.0, color, a, z, b, b + life)
    e.at(b + F(1, 4), "backOut", w=size, h=size)
    e.at(b + life, "sineOut", y=y + rise, x=x + sway, alpha=0, rot=-sway * 0.4)
    return e


# ================================================================== the storyboard
class Ctx:
    pass


def build(c):
    m = Music()
    G = Stage(c)
    E = Engine(c, G.root.index)
    N = Notes(m)
    L = Lens()
    R = random.Random(160)
    root = G.root.index
    X = Ctx()
    X.c, X.m, X.G, X.E, X.N, X.L, X.R, X.root = c, m, G, E, N, L, R, root
    X.JL = JL
    X.fx = {name: (_NoFx() if LITE else FxTrack(c, f"/{name}.glsl")) for name in SHADERS if name != "lens"}
    X.pre = []  # preset effects: (name, b0, b1, vars)
    # judge lines (all ride on the stage root so that a shake moves everything)
    X.A = JL(c, "line_a", 110, root, y=-220, sx=0.0)
    X.Bt = JL(c, "line_b", 111, root, y=220, rot=180, sx=0.45)
    X.P = Rig(c, "pivot", root)  # the crystal / ring pivot; its six children are the arms
    X.K = [JL(c, f"arm_{i + 1}", 112 + i, X.P.index, y=0, rot=60.0 * i, sx=0.0) for i in range(6)]
    import jl_scenes as SC
    for scene in SC.SCENES:
        scene(X)

    E.bake()
    G.emit(random.Random(7))
    n = N.write(c)
    print(f"notes turned to their better side: {N.flipped}")
    # effects, in drawing order: scene shaders first, the lens (camera) last
    for name, b0, b1, v in X.pre:
        c.effect(name, b0, b1, v)
    if not LITE:
        c.effect("/lens.glsl", 0, END, L.vars(END))
    return E, n


class _NoFx:
    def add(self, *a, **k):
        pass


def make():
    info = dict(INFO)
    if LITE:
        info["level"] = "SP Lv.? lite"
        info["tip"] = "观赏谱（无自定义着色器版）· 建议开启 Autoplay 观看"
    c = Chart(OFFSET_MS, dict(info, id="claude-just-love-lite" if LITE else "claude-just-love"), bpm=BPM, compact=True)
    E, n = build(c)
    print(f"pooled lines: {E.line_count()}  notes: {n}")
    return c, info


def assets(out, cover=None):
    import jl_assets
    jl_assets.make(out, cover or os.environ.get("JL_COVER"))
    for name in SHADERS:
        dst = os.path.join(out, f"{name}.glsl")
        if LITE:
            if os.path.exists(dst):
                os.remove(dst)
        else:
            shutil.copy(os.path.join(HERE, "jl_shaders", f"{name}.glsl"), dst)


def finalize(out):
    """remove textures and shaders that the built chart does not reference (the asset step makes a few spares)"""
    import json
    chart = json.load(open(os.path.join(out, "chart.json"), encoding="utf-8"))
    extra = json.load(open(os.path.join(out, "extra.json"), encoding="utf-8"))
    used = {ln["Texture"] for ln in chart["judgeLineList"]}
    used |= {e["shader"][1:] for e in extra.get("effects", []) if e["shader"].startswith("/")}
    for name in sorted(os.listdir(out)):
        if name.endswith((".png", ".glsl")) and name not in used:
            os.remove(os.path.join(out, name))
