"""Showcase chart ("观赏谱") generator — twelve movements around an orbit / night-sky motif.

Beat numbering: RPE beat k == analysis beat k (BPM 123), bar n starts at beat 2 + 4n (see music.B).
META offset = 329 ms (grid phase) + 25 ms (MP3 decoder delay that Phira/symphonia does not trim).
"""
import math
import random

import numpy as np

import music as M
from chartlib import Chart, DRAG, EPSB, FLICK, HOLD, TAP, frac, hsv, mix

B = M.B
R = random.Random(20261108)
ASP = 16 / 9
OFFSET_MS = 354


def RX(w):  # world x -> RPE x
    return w * 675.0


def RY(w):  # world y -> RPE y
    return w * 800.0


# ------------------------------------------------------------------ palette
PALE = (214, 236, 255)
ICE = (168, 206, 255)
CYAN = (118, 226, 255)
TEAL = (96, 238, 206)
VIOLET = (186, 146, 255)
LILAC = (222, 190, 255)
MAGENTA = (255, 98, 176)
ROSE = (255, 160, 205)
GOLD = (255, 212, 124)
AMBER = (255, 182, 108)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

INFO = {
    "name": "未命名曲目",
    "difficulty": 15.0,
    "level": "SP Lv.?",
    "charter": "Claude",
    "composer": "未知",
    "illustrator": "Claude (procedural)",
    "chart": "chart.json",
    "format": "rpe",
    "music": "song.mp3",
    "illustration": "illustration.jpg",
    "previewStart": 93.0,
    "previewEnd": 113.0,
    "aspectRatio": 1.7777778,
    "backgroundDim": 0.55,
    "lineLength": 6.0,
    "offset": 0.0,
    "tip": "观赏谱 · 建议开启 Autoplay 观看",
    "tags": ["观赏谱", "showcase", "autoplay"],
    "intro": "十二个乐章的观赏谱：序 · 升 · 绽 · 息 · 律 · 回响 · 环 · 幻 · 极 · 忆 · 终 · 尾声。",
    "holdPartialCover": False,
    "noteUniformScale": False,
    "forceAspectRatio": False,
    "useRpe170Speed": False,
    "useAttachUiFix": True,
}


# ------------------------------------------------------------------ timeline helper
class TL:
    """Sequential timeline for one property of one line (guarantees non-overlapping segments)."""

    def __init__(self, ln, prop, v0, b0=EPSB, layer=0):
        self.ln, self.p, self.v, self.b, self.layer = ln, prop, v0, frac(b0), layer

    def to(self, b, v, ease="linear"):
        b = frac(b)
        if b < self.b:
            raise ValueError(f"{self.ln.name}.{self.p}: going back in time {float(self.b)} -> {float(b)}")
        if b > self.b:
            self.ln.ev(self.p, self.b, b, self.v, v, ease, self.layer)
        self.b, self.v = b, v
        return self

    def jump(self, b, v):
        b = frac(b)
        if b < self.b:
            raise ValueError(f"{self.ln.name}.{self.p}: jump back {float(self.b)} -> {float(b)}")
        self.ln.ev(self.p, b, b + EPSB, v, v, "linear", self.layer)
        self.b, self.v = b + EPSB, v
        return self

    def wait(self, b):
        b = frac(b)
        if b > self.b:
            self.b = b
        return self


class Ctx:
    def __init__(self):
        meta = dict(INFO, id="claude-showcase")
        self.c = Chart(OFFSET_MS, meta)
        self.tls = {}

    def line(self, name, *, tex="line.png", z=0, x=0.0, y=0.0, rot=0.0, alpha=0, color=None, sx=None, sy=None,
             speed=None, father=-1, cover=True, rwf=True):
        ln = self.c.line(name, texture=tex, z=z, cover=cover, father=father, rot_with_father=rwf)
        init = {"moveX": x, "moveY": y, "rotate": rot, "alpha": alpha}
        if color is not None:
            init["color"] = color
        if sx is not None:
            init["scaleX"] = sx
        if sy is not None:
            init["scaleY"] = sy
        if speed is not None:
            init["speed"] = speed
        for p, v in init.items():
            ln.ev(p, 0, EPSB, v, v)
            self.tls[(ln.index, p, 0)] = TL(ln, p, v)
        return ln

    def tl(self, ln, prop, layer=0):
        key = (ln.index, prop, layer)
        if key not in self.tls:
            v0 = WHITE if prop == "color" else ("" if prop == "text" else 0.0)
            ln.ev(prop, 0, EPSB, v0, v0, "linear", layer)
            self.tls[key] = TL(ln, prop, v0, b0=EPSB, layer=layer)
        return self.tls[key]

    def fx(self, shader, b0, b1, **vars):
        self.c.effect(shader, b0, b1, vars)


def kfv(*pts):
    return Chart.var_kfs(list(pts))


def pulses(ctx, ln, prop, beats, amp, length, ease="quadOut", layer=1):
    """additive decaying pulses on a dedicated layer."""
    beats = sorted(set(frac(b) for b in beats))
    tl = ctx.tl(ln, prop, layer)
    for i, b in enumerate(beats):
        nxt = beats[i + 1] if i + 1 < len(beats) else b + frac(length)
        L = min(frac(length), nxt - b)
        a = amp(b) if callable(amp) else amp
        tl.wait(b)
        tl.ln.ev(prop, b, b + L, a, 0, ease, layer)
        tl.b, tl.v = b + L, 0


def sway(tl, b0, b1, amp, period, center=0.0, ease="sineInOut", sign=1):
    """oscillate between center±amp every half period, starting from the current value."""
    tl.wait(b0)
    b = frac(b0)
    half = frac(period) / 2
    while b + half <= frac(b1):
        b += half
        tl.to(b, center + sign * amp, ease)
        sign = -sign
    return tl


# ------------------------------------------------------------------ rhythm extraction
def groove(bar0, bar1, beat_thr=0.5, off_thr=0.72, six_thr=1.05, fill_bars=(), fill_thr=0.62):
    """-> list of (beat, role, strength).  roles: kick (on beat), clap (beat 2/4 with high-band hit),
    off (8th off-beat), six (16th)."""
    out = []
    for bar in range(bar0, bar1):
        for i in range(16):
            s = bar * 16 + i
            p, h = M.perc(s), M.harm(s)
            v = max(p, h)
            b = M.step_beat(s)
            if i % 4 == 0:
                if v >= beat_thr:
                    clap = i in (4, 12) and M.val("high_p", s) >= 0.62
                    out.append((b, "clap" if clap else "kick", v))
            elif i % 2 == 0:
                if v >= off_thr or (bar in fill_bars and v >= fill_thr * 0.9):
                    out.append((b, "off", v))
            else:
                if v >= six_thr or (bar in fill_bars and v >= fill_thr):
                    out.append((b, "six", v))
    return out


def harmonic_hits(bar0, bar1, q=0.75, min_gap=2):
    """melodic/harmonic onsets: strongest harmonic-flux steps, at least min_gap 16ths apart."""
    st = list(range(bar0 * 16, bar1 * 16))
    v = np.array([M.harm(s) for s in st])
    thr = np.quantile(v, q)
    cand = sorted([(v[i], s) for i, s in enumerate(st) if v[i] >= thr], reverse=True)
    taken = []
    for val_, s in cand:
        if all(abs(s - t) >= min_gap for t in taken):
            taken.append(s)
    return sorted(taken)


def pitch_x(s, span=300.0):
    """smoothed pitch-centroid deviation -> x offset."""
    w = [M.PITCH[k] for k in range(max(0, s - 12), min(M.NSTEP, s + 1))]
    base = float(np.median(w)) if w else 70.0
    return float(np.clip((M.PITCH[s] - base) * span / 8.0, -span, span))


class Lane:
    """x-position generator: keeps simultaneous / near notes apart."""

    def __init__(self, lo=-420, hi=420, min_sep=230):
        self.lo, self.hi, self.min_sep = lo, hi, min_sep
        self.recent = []  # (beat, x)
        self.blocked = []  # (b0, b1, x) hold bodies

    def block(self, b0, b1, x):
        self.blocked.append((float(b0), float(b1), float(x)))

    def ok(self, b, x, window=0.26):
        for b0, b1, xx in self.blocked:
            if b0 < b <= b1 + 0.01 and abs(xx - x) < 210:
                return False
        for bb, xx in self.recent:
            if abs(bb - b) < 1e-6 and abs(xx - x) < 260:
                return False
            if 0 < abs(bb - b) <= window and abs(xx - x) < 70:
                return False
        return True

    def put(self, b, x):
        x = float(np.clip(x, self.lo, self.hi))
        if not self.ok(b, x):
            for d in (180, -180, 300, -300, 420, -420):
                if self.lo <= x + d <= self.hi and self.ok(b, x + d):
                    x = x + d
                    break
        self.recent.append((b, x))
        self.recent = [r for r in self.recent if b - r[0] < 1.0]
        return x


# ------------------------------------------------------------------ shared decorations
def shared(ctx):
    S = {}
    S["curtain"] = ctx.line("curtain", tex="white.png", z=-40, color=BLACK, sx=24, sy=13.5)
    S["flash"] = ctx.line("flash", tex="white.png", z=60, color=WHITE, sx=24, sy=13.5)
    S["capzh"] = ctx.line("caption_zh", z=50, y=-352, color=PALE, sx=0.92, sy=0.92)
    S["capen"] = ctx.line("caption_en", z=50, y=-406, color=ICE, sx=0.46, sy=0.46)
    S["wash"] = ctx.line("colour_wash", tex="white.png", z=-35, color=BLACK, sx=24, sy=13.5)
    S["eq"] = [ctx.line(f"eq{i}", tex="eqbar.png", z=-20, x=RX(-0.94 + i * 0.125), y=-450, color=CYAN, sx=2.2, sy=0.0)
               for i in range(16)]
    S["rings"] = [ctx.line(f"ripple{i}", tex="ring.png", z=-10, color=GOLD, sx=0.3, sy=0.3) for i in range(4)]
    S["glow"] = ctx.line("core_glow", tex="glow.png", z=-12, color=GOLD, sx=1.5, sy=1.5)
    S["moon"] = ctx.line("moon_ring", tex="ring.png", z=-26, y=70, color=ICE, sx=1.0, sy=1.0)
    S["moonglow"] = ctx.line("moon_glow", tex="glow.png", z=-27, y=70, color=ICE, sx=2.6, sy=2.6)
    for ln in [S["capzh"], S["capen"]]:
        ln.ev("text", 0, EPSB, "", "")
        ctx.tls[(ln.index, "text", 0)] = TL(ln, "text", "")
    return S


def flash(ctx, S, b, peak=230, dur=1.0, color=WHITE, ease="expoOut"):
    a = ctx.tl(S["flash"], "alpha")
    col = ctx.tl(S["flash"], "color")
    col.jump(b, color)
    a.jump(b, peak).to(frac(b) + frac(dur), 0, ease)


def caption(ctx, S, b, zh, en, hold=6.0):
    for ln, txt, amax in ((S["capzh"], zh, 235), (S["capen"], en, 200)):
        t = ctx.tl(ln, "text")
        t.jump(b, "")
        t.to(frac(b) + 2, txt, "linear")
        a = ctx.tl(ln, "alpha")
        a.wait(b).to(frac(b) + 1, amax, "sineOut").wait(frac(b) + hold).to(frac(b) + hold + 2, 0, "sineIn")


def ripples(ctx, S, beats, color_fn, max_scale=1.6, life=1.5, amax=150):
    """expanding rings from the centre on given beats (round-robin over 4 ring lines)."""
    for k, b in enumerate(sorted(beats)):
        ln = S["rings"][k % 4]
        sx, sy, a, c = (ctx.tl(ln, p) for p in ("scaleX", "scaleY", "alpha", "color"))
        if frac(b) < a.b:
            continue
        c.jump(b, color_fn(b))
        sx.jump(b, 0.2).to(frac(b) + frac(life), max_scale, "quadOut")
        sy.jump(b, 0.2).to(frac(b) + frac(life), max_scale, "quadOut")
        a.jump(b, amax).to(frac(b) + frac(life), 0, "quadOut")


def eq_run(ctx, S, b0, b1, colors, amax=78, hmax=2.0, floor=0.05):
    """audio-reactive equalizer bars between beats b0..b1 (per 8th note)."""
    n = len(S["eq"])
    for i, ln in enumerate(S["eq"]):
        a = ctx.tl(ln, "alpha")
        c = ctx.tl(ln, "color")
        c.jump(b0 - 1, colors(i / (n - 1)))
        a.wait(b0 - 1).to(b0, amax, "sineOut").wait(b1 - 1).to(b1, 0, "sineIn")
        sy = ctx.tl(ln, "scaleY")
        sy.wait(b0)
        b = frac(b0)
        while b < frac(b1):
            e = M.vis(float(b), i)
            h = floor + (hmax - floor) * e ** 1.6
            ln.ev("scaleY", b, b + frac(1, 2), h, h * 0.45, "quadOut")
            sy.b, sy.v = b + frac(1, 2), h * 0.45
            b += frac(1, 2)
        sy.to(frac(b1) + 1, 0.0, "quadIn")


# ------------------------------------------------------------------ note helpers
PHRASE_HOLDS = {B(b) for b in (51, 59, 67, 75, 83, 91, 99, 107, 115, 123, 131, 135, 143)}


def as_phrase_hold(b, role):
    return role == "kick" and frac(b) in PHRASE_HOLDS


def place(ln, kind, b, x, role, lane=None, **kw):
    """note, or a 1.5-beat hold when it is the kick that opens a phrase. returns True if a hold was placed."""
    if as_phrase_hold(b, role):
        ln.note(HOLD, b, x, end=frac(b) + frac(3, 2), **kw)
        if lane is not None:
            lane.block(b, frac(b) + frac(3, 2), x)
        return True
    ln.note(kind, b, x, **kw)
    return False


def put_notes(ln, items, lane=None, above=True, kinds=None, xfun=None, speed=1.0, visible=999999.0, alpha=255):
    """items: [(beat, role, strength)]; kinds: role->kind; xfun(beat, role, idx)->x."""
    kinds = kinds or {"kick": TAP, "clap": FLICK, "off": DRAG, "six": DRAG, "hold": HOLD}
    n = 0
    for idx, it in enumerate(items):
        b, role = it[0], it[1]
        x = xfun(b, role, idx) if xfun else 0.0
        if lane is not None:
            x = lane.put(b, x)
        k = kinds.get(role, TAP)
        if as_phrase_hold(b, role):
            ln.note(HOLD, b, x, end=frac(b) + frac(3, 2), above=above, speed=speed, visible=visible, alpha=alpha)
            if lane is not None:
                lane.block(b, frac(b) + frac(3, 2), x)
        elif k == HOLD:
            ln.note(HOLD, b, x, end=it[3], above=above, speed=speed, visible=visible, alpha=alpha)
            if lane is not None:
                lane.block(b, it[3], x)
        else:
            ln.note(k, b, x, above=above, speed=speed, visible=visible, alpha=alpha)
        n += 1
    return n


# ================================================================== scenes
def scene_prelude(ctx, S):
    """I 序 Prelude — bars 0..26.  A dot becomes a line; stars breathe; a second line answers."""
    c = ctx
    b_start, b_end = B(0), B(27)
    # opening dot
    dot = c.line("open_dot", tex="glow.png", z=5, y=-200, color=PALE, sx=0.0, sy=0.0)
    c.tl(dot, "alpha").wait(0.25).to(1.5, 255, "sineOut").wait(2.0).to(2.6, 0, "quadIn")
    c.tl(dot, "scaleX").wait(0.25).to(1.75, 0.42, "sineOut").to(2.0, 0.95, "expoOut").to(2.6, 0.0, "quadIn")
    c.tl(dot, "scaleY").wait(0.25).to(1.75, 0.42, "sineOut").to(2.0, 0.95, "expoOut").to(2.6, 0.0, "quadIn")
    flash(c, S, B(0), peak=90, dur=1.5, color=PALE)
    c.fx("shockwave", B(0), B(0, 2), progress=kfv((B(0), 0.02, "quadOut"), (B(0, 2), 0.9, "linear")),
         centerY=kfv((B(0), 0.5 - 200 / 900, "linear"), (B(0, 2), 0.5 - 200 / 900, "linear")), width=0.08, distortion=0.8, expand=10.0)

    main = c.line("prelude_main", color=PALE, y=-200, sx=0.0, speed=6.5)
    top = c.line("prelude_top", color=LILAC, y=200, sx=0.0, speed=6.5)
    a = c.tl(main, "alpha")
    a.wait(1.75).to(2.0, 255, "linear")
    sx = c.tl(main, "scaleX")
    sx.wait(2).to(B(1), 0.34, "expoOut").wait(B(8)).to(B(9), 1.0, "sineInOut")
    caption(c, S, B(0, 2), "序", "I  ·  PRELUDE")
    # sway & structure
    rot = c.tl(main, "rotate")
    sway(rot, B(1), B(16), 3.0, 16)
    rot.to(B(16, 2), 0.0, "sineInOut")
    y = c.tl(main, "moveY")
    # top line arrives for phrase 2
    ta, tsx, ty, tr = c.tl(top, "alpha"), c.tl(top, "scaleX"), c.tl(top, "moveY"), c.tl(top, "rotate")
    ta.wait(B(7, 2)).to(B(8), 230, "sineOut")
    tsx.wait(B(7, 2)).to(B(8, 2), 1.0, "expoOut")
    # phrase 3: lines approach and rock in opposition
    y.wait(B(16)).to(B(18), -130, "sineInOut")
    ty.wait(B(16)).to(B(18), 130, "sineInOut")
    rot.wait(B(18))
    tr.wait(B(18))
    for k in range(3):
        b = B(18 + 2 * k)
        rot.to(b + 4, 7 if k % 2 == 0 else -7, "sineInOut").to(b + 8, 0, "sineInOut")
        tr.to(b + 4, -7 if k % 2 == 0 else 7, "sineInOut").to(b + 8, 0, "sineInOut")
    # transition bars 24..26: merge at centre, then main sinks for the build
    y.wait(B(24)).to(B(26), 0, "quadInOut")
    ty.wait(B(24)).to(B(26), 0, "quadInOut")
    ta.wait(B(25, 3)).to(B(26), 0, "sineIn")
    c.tl(main, "color").wait(B(24)).to(B(27), VIOLET, "linear")

    # ---- a faint moon rises behind the prelude
    for key, al, s0, s1 in (("moon", 46, 0.85, 1.25), ("moonglow", 34, 2.2, 3.2)):
        mo = S[key]
        c.tl(mo, "alpha").wait(B(1)).to(B(5), al, "sineInOut").wait(B(25)).to(B(27), 0, "sineIn")
        c.tl(mo, "scaleX").wait(B(1)).to(B(27), s1, "sineOut")
        c.tl(mo, "scaleY").wait(B(1)).to(B(27), s1, "sineOut")
        c.tl(mo, "moveY").wait(B(1)).to(B(27), 150, "sineOut")
    # ---- stars
    for k in range(14):
        sx_, sy_ = R.uniform(-600, 600), R.uniform(-60, 420)
        st = c.line(f"star{k}", tex="glow.png", z=-25, x=sx_, y=sy_, color=mix(PALE, CYAN, R.random()), sx=0.16, sy=0.16)
        base = R.randint(35, 80)
        sa = c.tl(st, "alpha")
        sa.wait(B(0) + R.uniform(0, 3)).to(B(1) + R.uniform(0, 4), base, "sineOut")
        beats = [B(bar, k2) for bar in range(0, 26) for k2 in range(4) if R.random() < 0.10]
        pulses(c, st, "alpha", beats, 150, 1.5, "quadOut", layer=1)
        sa.wait(B(26)).to(B(27, 2), 0, "sineIn")
        drift = c.tl(st, "moveY")
        drift.wait(B(1)).to(B(27), sy_ - R.uniform(40, 90), "linear")

    # ---- notes
    lane = Lane(-400, 400)
    # phrase 1 (bars 0-7): half-note pulses + chord holds
    items = []
    main.note(TAP, B(0), 0, visible=1.0)
    for bar in range(0, 8):
        s0 = bar * 16
        if bar == 0:
            pass
        elif bar % 2 == 0:
            items.append((B(bar), "hold", 1.0, B(bar, 1.75)))
        else:
            items.append((B(bar), "kick", 1.0))
        items.append((B(bar, 2), "kick", 1.0))
        for i in (6, 10, 14):
            if bar >= 4 and M.harm(s0 + i) > 0.62:
                items.append((M.step_beat(s0 + i), "off", M.harm(s0 + i)))
    items.sort(key=lambda t: t[0])
    flow = {"x": -220}

    def xf(b, role, idx):
        if role in ("hold", "kick"):
            flow["x"] = -flow["x"] if abs(flow["x"]) > 100 else 220
            return flow["x"] * (0.6 + 0.4 * math.sin(b * 0.37))
        return pitch_x(int((b - 2) * 4), 330)
    put_notes(main, items, lane, xfun=xf)
    # phrase 2 (bars 8-15): kicks on main, melodic answers on top (from below)
    kicks = [(b, "kick", v) for (b, r, v) in groove(8, 16, beat_thr=0.55) if r in ("kick", "clap")]
    put_notes(main, kicks, lane, xfun=lambda b, r, i: 260 * math.sin(b * math.pi / 4))
    lane_t = Lane(-380, 380)
    mel = [(M.step_beat(s), "off", 1.0) for s in harmonic_hits(8, 16, q=0.78, min_gap=3) if s % 4 != 0]
    put_notes(top, mel, lane_t, above=False, kinds={"off": DRAG}, xfun=lambda b, r, i: pitch_x(int((b - 2) * 4), 340))
    # phrase 3 (bars 16-23): quarters split, 8th drags denser
    g = groove(16, 24, beat_thr=0.55, off_thr=0.78)
    put_notes(main, [it for it in g if it[1] in ("kick", "clap") and int(it[0]) % 2 == 0], lane,
              kinds={"kick": TAP, "clap": TAP}, xfun=lambda b, r, i: -240 + 120 * ((i % 5) - 2) * 0.5)
    put_notes(top, [it for it in g if it[1] in ("kick", "clap") and int(it[0]) % 2 == 1], lane_t, above=False,
              kinds={"kick": TAP, "clap": TAP}, xfun=lambda b, r, i: 240 - 60 * (i % 5))
    put_notes(main, [it for it in g if it[1] == "off"], lane, kinds={"off": DRAG},
              xfun=lambda b, r, i: 330 * math.sin(b * math.pi / 2.0))
    # transition 24-26: holds on the chord changes, rising drags
    for bar, x in ((24, -200), (25, 200)):
        main.note(HOLD, B(bar), x, end=B(bar, 3))
        main.note(TAP, B(bar, 3), -x * 0.5)
    for k in range(8):
        main.note(DRAG, B(26) + frac(k, 2), -350 + k * 100)
    main.note(FLICK, B(26, 3.5) + frac(1, 4), 0)
    return main


def scene_ascent(ctx, S, main):
    """II 升 Ascent — bars 27..33.  The line sinks, then climbs while everything tightens."""
    c = ctx
    b0, b1 = B(27), B(34)
    caption(c, S, b0, "升", "II  ·  ASCENT", hold=5)
    y = c.tl(main, "moveY")
    y.wait(b0).to(b0 + 2, -300, "expoOut").wait(B(28)).to(B(33, 2), -40, "quadIn").to(b1, 0, "sineOut")
    sp = c.tl(main, "speed")
    sp.wait(b0).to(B(33), 11.0, "linear").to(b1, 13.0, "linear")
    rot = c.tl(main, "rotate")
    rot.wait(B(33)).to(B(33, 2.75), -360, "expoIn").jump(B(33, 2.75) + EPSB, 0)
    # shakes on 8ths in the last two bars (additive layer)
    pulses(c, main, "rotate", [B(31) + frac(k, 2) for k in range(8)], lambda b: 3 if (b * 2) % 2 == 0 else -3, 0.5, "quadOut", layer=1)
    # vignette + darkening curtain
    c.fx("vignette", b0, b1, extend=kfv((b0, 0.25, "linear"), (b1, 0.62, "linear")),
         radius=kfv((b0, 15.0, "quadIn"), (b1, 3.2, "linear")), color=[0.0, 0.0, 0.0, 1.0])
    c.tl(S["curtain"], "alpha").wait(b0).to(B(33, 2), 120, "quadIn").to(b1, 170, "linear").jump(b1, 0)
    # rising streaks
    for k in range(10):
        x = -620 + k * 135 + R.uniform(-40, 40)
        st = c.line(f"streak{k}", tex="pillar.png", z=-15, x=x, y=-700, rot=180, color=LILAC, sx=0.5, sy=1.2)
        a, yy = c.tl(st, "alpha"), c.tl(st, "moveY")
        a.wait(b0).to(b0 + 2, 70, "sineOut").wait(b1 - 0.5).to(b1, 0, "linear")
        b = frac(b0) + frac(R.randint(0, 3), 4)
        per = frac(2)
        while b + per <= b1:
            yy.jump(b, -760).to(b + per, 760, "quadIn")
            b += per
            if b >= B(31):
                per = frac(1)
            if b >= B(33):
                per = frac(1, 2)
    # notes: quarter -> 8th -> 16th -> spiral
    lane = Lane(-420, 420)
    items = []
    for bar in range(27, 34):
        for i in range(16):
            s = bar * 16 + i
            v = max(M.perc(s), M.harm(s))
            b = M.step_beat(s)
            if bar <= 28:
                if i % 4 == 0:
                    items.append((b, "kick", v))
            elif bar <= 30:
                if i % 4 == 0:
                    items.append((b, "kick", v))
                elif i % 2 == 0 and v > 0.55:
                    items.append((b, "off", v))
            elif bar <= 32:
                if i % 4 == 0:
                    items.append((b, "kick", v))
                elif v > 0.48 or i % 2 == 0:
                    items.append((b, "six", v))
    put_notes(main, items, lane, xfun=lambda b, r, i: (300 * math.sin(b * math.pi / 2) if r != "kick" else (-260 if i % 2 else 260)))
    # last bar: a spiral of drags, then silence before the drop
    for k in range(10):
        b = B(33) + frac(k, 4)
        main.note(DRAG, b, 380 * math.cos(k * 0.9), speed=1.0)
    main.note(HOLD, B(33, 3), 0, end=B(33, 3.75))


def scene_bloom(ctx, S, finale=False):
    """III 绽 Bloom (bars 34..42) / XI 终 Finale (bars 159..167): notes burst from the centre onto
    orbiting petals."""
    c = ctx
    bar0, bar1 = (159, 168) if finale else (34, 43)
    b0, b1 = B(bar0), B(bar1)
    tag = "fin" if finale else "bloom"
    npet = 8 if finale else 6
    rho = 0.34 if finale else 0.31
    if finale:
        caption(c, S, b0, "终", "XI  ·  FINALE")
    else:
        caption(c, S, b0, "绽", "III  ·  BLOOM")
    flash(c, S, b0, peak=205, dur=1.25)
    c.fx("shockwave", b0, b0 + 2, progress=kfv((b0, 0.02, "quadOut"), (b0 + 2, 0.95, "linear")), width=0.1, distortion=0.8, expand=10.0)
    c.fx("radialBlur", b0, b0 + 1.5, power=kfv((b0, 0.03, "quadOut"), (b0 + 1.5, 0.0, "linear")), sampleCount=10.0)
    mid = B(bar0 + 4)
    c.fx("radialBlur", mid, mid + 1, power=kfv((mid, 0.025, "quadOut"), (mid + 1, 0.0, "linear")), sampleCount=8.0)
    chrom = []
    for k in range(int(b1 - b0)):
        chrom.append((b0 + k, 0.014 if k % 4 == 0 else 0.008, "quadOut"))
        chrom.append((b0 + k + 0.95, 0.0015, "linear"))
    chrom.append((b1, 0.0, "linear"))
    c.fx("chromatic", b0, b1, power=kfv(*chrom), sampleCount=5.0)
    # hub + petals
    hub = c.line(f"{tag}_hub")
    hr = c.tl(hub, "rotate")
    hr.wait(b0).to(B(bar0 + 4), -90, "linear").to(B(bar1 - 2), -40, "sineInOut").to(B(bar1 - 1, 3), 300, "quadIn")
    petals = []
    cols = [GOLD, MAGENTA] if not finale else [GOLD, MAGENTA, CYAN, WHITE]
    for k in range(npet):
        phi = 360.0 * k / npet + 90
        px, py = RX(rho * math.cos(math.radians(phi))), RY(rho * math.sin(math.radians(phi)))
        p = c.line(f"{tag}_petal{k}", father=hub.index, x=px, y=py, rot=-(phi + 90), color=cols[k % len(cols)],
                   sx=0.0, speed=4.0, z=4)
        a, sx = c.tl(p, "alpha"), c.tl(p, "scaleX")
        a.jump(b0, 255)
        sx.wait(b0).to(b0 + 0.75, 0.05, "backOut")
        # breathe outward on the middle crash, contract during the fill
        mx, my = c.tl(p, "moveX"), c.tl(p, "moveY")
        r2, r3 = rho * 1.18, rho * 0.55
        mx.wait(mid).to(mid + 1, RX(r2 * math.cos(math.radians(phi))), "backOut")
        my.wait(mid).to(mid + 1, RY(r2 * math.sin(math.radians(phi))), "backOut")
        mx.wait(B(bar1 - 1)).to(b1 - 0.25, RX(r3 * math.cos(math.radians(phi))), "quadIn")
        my.wait(B(bar1 - 1)).to(b1 - 0.25, RY(r3 * math.sin(math.radians(phi))), "quadIn")
        a.wait(b1 - 0.25).to(b1, 0, "linear")
        petals.append(p)
    # centre glow
    g = S["glow"]
    ga, gsx, gsy, gc = (c.tl(g, p) for p in ("alpha", "scaleX", "scaleY", "color"))
    gc.jump(b0, GOLD if not finale else WHITE)
    ga.wait(b0 - 0.5).to(b0, 150, "linear").wait(b1 - 1).to(b1, 0, "linear")
    beats = [b0 + j for j in range(int(b1 - b0))]
    gsx.wait(b0)
    gsy.wait(b0)
    for b in beats:
        gsx.jump(b, 1.45).to(b + 0.9, 1.0, "quadOut")
        gsy.jump(b, 1.45).to(b + 0.9, 1.0, "quadOut")
    ripples(c, S, [b for b in beats if (b - b0) % 2 == 0], lambda b: (GOLD if int(b) % 4 < 2 else MAGENTA), 1.8, 2.0, 130)
    # equalizer in the finale
    if finale:
        eq_run(c, S, b0, b1, lambda u: hsv(0.55 + 0.45 * u, 0.55, 1.0), amax=90)
    # notes: burst outward to petals (visible only from the centre)
    g_items = groove(bar0, bar1, beat_thr=0.5, off_thr=0.80, six_thr=1.1, fill_bars=(bar1 - 1,), fill_thr=0.75)
    vis_t = 0.56 if not finale else 0.5
    k = 0
    last_b = None
    for (b, role, v) in g_items:
        if last_b is not None and b - last_b < frac(1, 4) - frac(1, 1000):
            continue
        idx = k % npet
        kind = {"kick": TAP, "clap": FLICK, "off": DRAG, "six": DRAG}[role]
        petals[idx].note(kind, b, 0, visible=vis_t)
        if (b - b0) % 4 == 0:  # downbeat: opposite petal double
            petals[(idx + npet // 2) % npet].note(TAP, b, 0, visible=vis_t)
        k += 1 if role != "six" else 1
        last_b = b
    if finale:
        # bottom line carrying the kicks
        bot = c.line("fin_bottom", color=WHITE, y=-330, sx=0.0, speed=10.5, z=3)
        bstart = B(bar0 + 2)  # joins once the caption has faded
        c.tl(bot, "alpha").jump(bstart - 1, 255).wait(b1 - 0.5).to(b1, 0, "linear")
        c.tl(bot, "scaleX").wait(bstart - 1).to(bstart, 1.0, "expoOut")
        pulses(c, bot, "moveY", [b for b in beats if b >= bstart], -16, 0.5, "quadOut", layer=1)
        lane = Lane(-430, 430)
        sw = [it for it in groove(bar0 + 2, bar1, beat_thr=0.5, off_thr=0.7) if it[1] in ("kick", "off")]
        put_notes(bot, sw, lane, kinds={"kick": TAP, "off": DRAG},
                  xfun=lambda b, r, i: (380 * math.sin(b * math.pi / 2.0 + 0.7) if r == "off" else (-300 if i % 2 else 300)))


def scene_breath(ctx, S):
    """IV 息 Breath — bars 43..46: a warm single line turning slowly."""
    c = ctx
    b0, b1 = B(43), B(47)
    caption(c, S, b0, "息", "IV  ·  BREATH", hold=5)
    ln = c.line("breath_line", color=AMBER, sx=0.0, speed=5.5, z=2)
    a, sx, rot = c.tl(ln, "alpha"), c.tl(ln, "scaleX"), c.tl(ln, "rotate")
    a.jump(b0, 255).wait(b1 - 0.25).to(b1, 0, "linear")
    sx.wait(b0).to(b0 + 1.5, 0.30, "expoOut").wait(B(46, 2)).to(b1, 1.0, "quadIn")
    rot.wait(b0).to(B(45), 45, "sineInOut").to(B(46, 2), 0, "sineInOut")
    g = c.line("breath_glow", tex="glow.png", z=-18, color=AMBER, sx=3.0, sy=3.0)
    ga, gsx, gsy = c.tl(g, "alpha"), c.tl(g, "scaleX"), c.tl(g, "scaleY")
    ga.wait(b0).to(b0 + 2, 70, "sineOut").wait(b1 - 2).to(b1, 0, "sineIn")
    for k in range(4):
        b = B(43 + k)
        gsx.to(b + 2, 3.8, "sineInOut").to(b + 4, 3.0, "sineInOut")
        gsy.to(b + 2, 3.8, "sineInOut").to(b + 4, 3.0, "sineInOut")
    ln.note(HOLD, B(43), -200, end=B(43, 3))
    ln.note(TAP, B(43, 3), 150)
    ln.note(HOLD, B(44), 200, end=B(44, 3))
    ln.note(TAP, B(44, 3), -150)
    for s in harmonic_hits(45, 46, q=0.7, min_gap=4):
        ln.note(TAP if s % 4 == 0 else DRAG, M.step_beat(s), pitch_x(s, 320))
    # fill: rising drag stairs
    for k, s in enumerate(range(46 * 16 + 8, 47 * 16)):
        ln.note(DRAG, M.step_beat(s), -360 + k * 100)
    ln.note(FLICK, B(46, 0), 0)


def scene_pulse(ctx, S):
    """V 律 Pulse — bars 47..74: heartbeat lines over an audio-reactive equalizer."""
    c = ctx
    b0, b1 = B(47), B(75)
    caption(c, S, b0, "律", "V  ·  PULSE")
    main = c.line("pulse_main", color=CYAN, y=-250, sx=0.0, speed=8.5, z=3)
    top = c.line("pulse_top", color=ROSE, y=250, sx=0.0, speed=8.5, z=3)
    a, sx, y, rot = c.tl(main, "alpha"), c.tl(main, "scaleX"), c.tl(main, "moveY"), c.tl(main, "rotate")
    a.jump(b0, 255).wait(b1 - 0.5).to(b1, 0, "linear")
    sx.wait(b0).to(b0 + 1, 1.0, "expoOut")
    ta, tsx, ty, tr = c.tl(top, "alpha"), c.tl(top, "scaleX"), c.tl(top, "moveY"), c.tl(top, "rotate")
    ta.wait(B(50, 2)).to(B(51), 235, "sineOut").wait(b1 - 0.5).to(b1, 0, "linear")
    tsx.wait(B(50, 2)).to(B(51), 1.0, "expoOut")
    beats = [b0 + k for k in range(int(b1 - b0))]
    pulses(c, main, "moveY", beats, -14, 0.5, "quadOut", layer=1)
    pulses(c, top, "moveY", [b for b in beats if (b - b0) % 2 == 1], 14, 0.5, "quadOut", layer=1)
    # phrase 3 tilt, phrase 4 converge
    rot.wait(B(59)).to(B(59, 2), 8, "backOut")
    tr.wait(B(59)).to(B(59, 2), -8, "backOut")
    sway(rot, B(59, 2), B(67), 8, 16, 0, sign=-1)
    sway(tr, B(59, 2), B(67), 8, 16, 0, sign=1)
    rot.to(B(67), 0, "sineInOut")
    tr.to(B(67), 0, "sineInOut")
    y.wait(B(67)).to(B(73), -150, "sineInOut").to(b1, -250, "quadIn")
    ty.wait(B(67)).to(B(73), 150, "sineInOut").to(b1, 0, "quadIn")
    eq_run(c, S, b0, b1, lambda u: mix(CYAN, VIOLET, u), amax=85)
    ripples(c, S, [b for b in beats if (b - b0) % 4 == 0], lambda b: CYAN, 1.5, 2.5, 70)
    # notes
    g = groove(47, 75, beat_thr=0.5, off_thr=0.82, six_thr=1.2, fill_bars=(57, 58, 73, 74), fill_thr=0.72)
    lm, lt = Lane(-430, 430), Lane(-430, 430)
    kick = [it for it in g if it[1] == "kick"]
    clap = [it for it in g if it[1] == "clap"]
    rest = [it for it in g if it[1] in ("off", "six")]
    put_notes(main, [it for it in kick], lm, xfun=lambda b, r, i: [-300, 300, -100, 100][i % 4])
    early = [it for it in clap if it[0] < B(51)]
    late = [it for it in clap if it[0] >= B(51)]
    put_notes(main, early, lm, kinds={"clap": FLICK}, xfun=lambda b, r, i: 0)
    put_notes(top, late, lt, above=False, kinds={"clap": FLICK}, xfun=lambda b, r, i: [-220, 220][i % 2])
    # streams alternate lines by bar in the fills, else on main
    for b, role, v in rest:
        bar = int((b - 2) // 4)
        target, lane, ab = (top, lt, False) if (bar in (58, 74) and bar >= 51 and int(b * 2) % 2 == 1) else (main, lm, True)
        x = lane.put(b, 360 * math.sin(b * math.pi / 2 + 0.4))
        target.note(DRAG, b, x, above=ab)


def scene_echo(ctx, S):
    """VI 回响 Echo — bars 75..90: pendulums with ghost trails; notes leave after-images."""
    c = ctx
    b0, b1 = B(75), B(91)
    caption(c, S, b0, "回响", "VI  ·  ECHO")
    piv_y = 700
    arm = -950

    def pendulum(name, color, delay, alpha, phase, amp, z):
        pv = c.line(f"{name}_pivot", y=piv_y)
        ln = c.line(name, father=pv.index, y=arm, color=color, sx=0.0, speed=9.0, z=z)
        r = c.tl(pv, "rotate")
        r.wait(b0 + delay)
        b = frac(b0) + frac(delay)
        sgn = phase
        r.to(b + 1, sgn * amp, "sineOut")
        b += 1
        while b + 4 <= frac(b1) + frac(delay) - 1:
            sgn = -sgn
            r.to(b + 4, sgn * amp, "sineInOut")
            b += 4
        r.to(frac(b1) + frac(delay), 0, "sineInOut")
        a, sx = c.tl(ln, "alpha"), c.tl(ln, "scaleX")
        a.jump(b0, alpha).wait(b1 - 0.5).to(b1, 0, "linear")
        sx.wait(b0).to(b0 + 1, 0.42, "expoOut")
        return pv, ln

    _, p1 = pendulum("echo_a", TEAL, 0, 255, 1, 16, 4)
    pendulum("echo_a_ghost1", TEAL, frac(1, 4), 110, 1, 16, 2)
    pendulum("echo_a_ghost2", TEAL, frac(1, 2), 50, 1, 16, 1)
    pv2 = c.line("echo_b_pivot", y=piv_y)
    p2 = c.line("echo_b", father=pv2.index, y=arm, color=ROSE, sx=0.0, speed=9.0, z=4)
    r2 = c.tl(pv2, "rotate")
    r2.wait(B(83)).to(B(83, 1), -16, "sineOut")
    b = frac(B(83, 1))
    sgn = -1
    while b + 4 <= frac(b1) - 1:
        sgn = -sgn
        r2.to(b + 4, sgn * 16, "sineInOut")
        b += 4
    r2.to(b1, 0, "sineInOut")
    c.tl(p2, "alpha").jump(B(83), 240).wait(b1 - 0.5).to(b1, 0, "linear")
    c.tl(p2, "scaleX").wait(B(83)).to(B(83, 1), 0.42, "expoOut")
    c.fx("chromatic", b0, b1, power=0.0035, sampleCount=3.0)
    # notes with after-images (faster fake copies trail behind, then vanish)
    g = groove(75, 91, beat_thr=0.5, off_thr=0.82, six_thr=1.2, fill_bars=(89, 90), fill_thr=0.72)
    l1, l2 = Lane(-300, 300), Lane(-300, 300)
    for i, (b, role, v) in enumerate(g):
        bar = int((b - 2) // 4)
        use2 = bar >= 83 and (int(b) % 2 == 1)
        ln, lane = (p2, l2) if use2 else (p1, l1)
        kind = {"kick": TAP, "clap": FLICK, "off": DRAG, "six": DRAG}[role]
        x = lane.put(b, 250 * math.sin(b * 0.9) if role in ("off", "six") else [-180, 180][i % 2])
        if place(ln, kind, b, x, role, lane):
            continue
        if role in ("kick", "clap"):
            for spd, al in ((1.22, 105), (1.45, 50)):
                ln.note(kind, frac(b) + frac(1, 192), x, speed=spd, alpha=al, fake=True)


def scene_orbit(ctx, S):
    """VII 环 Orbit — bars 91..114: clock hands sweep, planets orbit on parented hubs."""
    c = ctx
    b0, b1 = B(91), B(115)
    caption(c, S, b0, "环", "VII  ·  ORBIT")
    minute = c.line("orbit_minute", color=GOLD, sx=0.0, speed=7.0, z=4)
    hour = c.line("orbit_hour", color=PALE, sx=0.0, sy=1.8, speed=6.0, z=3)
    sec = c.line("orbit_second", color=ROSE, sx=0.0, sy=0.6, z=2)
    for ln, length, al in ((minute, 0.19, 255), (hour, 0.11, 235), (sec, 0.25, 120)):
        c.tl(ln, "alpha").jump(b0, al).wait(b1 - 0.5).to(b1, 0, "linear")
        c.tl(ln, "scaleX").wait(b0).to(b0 + 2, length, "expoOut")
    # rotations
    mr = c.tl(minute, "rotate")
    mr.wait(b0).to(B(107), 360 * 2, "linear").to(B(113), 360 * 2 + 540, "linear").to(B(114, 3), 360 * 5, "quartIn")
    hr = c.tl(hour, "rotate")
    hr.wait(b0).to(B(113), 200, "linear").to(B(114, 3), 360, "quartIn")
    sr = c.tl(sec, "rotate")
    sr.wait(b0)
    for k in range(int(b1 - b0)):
        sr.wait(b0 + k).to(frac(b0 + k) + frac(1, 6), 30.0 * (k + 1), "backOut")
    # orbits: static rings + planets on hubs
    for k, (rad, col, per, al) in enumerate(((0.22, CYAN, 8, 60), (0.36, MAGENTA, 12, 45), (0.5, GOLD, 16, 35))):
        ring = c.line(f"orbit_ring{k}", tex="ring.png", z=-14, color=col, sx=rad * 2 * 675 / 512 / 0.94 / 0.5 * 0.5,
                      sy=rad * 2 * 675 / 512 / 0.94 / 0.5 * 0.5)
        c.tl(ring, "alpha").wait(b0).to(b0 + 4, al, "sineOut").wait(b1 - 2).to(b1, 0, "sineIn")
        hubp = c.line(f"orbit_phub{k}")
        c.tl(hubp, "rotate").wait(b0).to(b1, -360 * (b1 - b0) / (per * 4), "linear")
        pl = c.line(f"orbit_planet{k}", tex="glow.png", father=hubp.index, x=RX(rad), z=-13, color=col, sx=0.32, sy=0.32)
        c.tl(pl, "alpha").wait(b0).to(b0 + 4, 230, "sineOut").wait(b1 - 2).to(b1, 0, "sineIn")
    g = S["glow"]
    c.tl(g, "color").jump(b0 - 1, PALE)
    c.tl(g, "alpha").wait(b0).to(b0 + 4, 120, "sineOut").wait(b1 - 2).to(b1, 0, "sineIn")
    gsx, gsy = c.tl(g, "scaleX"), c.tl(g, "scaleY")
    for k in range(int((b1 - b0) // 4)):
        b = b0 + 4 * k
        gsx.wait(b).jump(b, 1.6).to(b + 3.5, 1.1, "quadOut")
        gsy.wait(b).jump(b, 1.6).to(b + 3.5, 1.1, "quadOut")
    # notes: minute hand carries the groove (both sides); hour hand gets the bar downbeats & claps from phrase 2
    g_ = groove(91, 115, beat_thr=0.5, off_thr=0.84, six_thr=1.2, fill_bars=(113, 114), fill_thr=0.74)
    lm, lh = Lane(-420, 420), Lane(-230, 230)
    for i, (b, role, v) in enumerate(g_):
        bar = int((b - 2) // 4)
        kind = {"kick": TAP, "clap": FLICK, "off": DRAG, "six": DRAG}[role]
        if bar >= 99 and (role == "clap" or (b - 2) % 4 == 0 and role == "kick" and bar % 2 == 1):
            place(hour, kind, b, lh.put(b, [-150, 150][i % 2]), role, lh, above=(i % 2 == 0))
        else:
            side = (int(b) // 2) % 2 == 0
            x = lm.put(b, (300 if side else -300) * (0.5 + 0.5 * math.cos(b * 0.7)) if role in ("off", "six") else (240 if side else -240))
            place(minute, kind, b, x, role, lm, above=side)


def scene_mirage(ctx, S):
    """VIII 幻 Mirage — bars 115..134: an invisible line, converging and materialising notes, flips."""
    c = ctx
    b0, b1 = B(115), B(135)
    caption(c, S, b0, "幻", "VIII  ·  MIRAGE")
    # three lines so each control trick lives on its own line
    l1 = c.line("mirage_funnel", color=VIOLET, y=-240, sx=1.0, speed=9.0, z=4)
    l1.control("pos", [(0, 1.0, "linear"), (120, 1.0, "linear"), (450, 2.1, "sineIn"), (1200, 3.2, "linear")])
    beam = c.line("mirage_beam", tex="beam.png", z=-8, y=-240, color=VIOLET, sx=1.6, sy=1.4)
    c.tl(beam, "alpha").wait(b0).to(b0 + 2, 120, "sineOut").wait(B(123) - 1).to(B(123), 0, "linear")
    c.tl(l1, "alpha").jump(b0, 0)  # invisible judge line
    l2 = c.line("mirage_flip", color=LILAC, y=-60, sx=0.0, speed=9.0, z=4)
    c.tl(l2, "alpha").wait(B(123) - 0.5).to(B(123), 255, "linear").wait(B(131) - 0.5).to(B(131), 0, "linear")
    c.tl(l2, "scaleX").wait(B(123) - 0.5).to(B(123), 1.0, "expoOut")
    fr = c.tl(l2, "rotate")
    fr.wait(B(123))
    for k, bar in enumerate((125, 127, 129)):
        fr.wait(B(bar) - 1).to(B(bar), 180.0 * ((k + 1) % 2), "backInOut")
    l3 = c.line("mirage_reveal", color=MAGENTA, y=-230, sx=0.0, speed=10.0, z=4)
    l3.control("alpha", [(0, 1.0, "linear"), (230, 1.0, "linear"), (440, 0.0, "sineIn"), (2000, 0.0, "linear")])
    c.tl(l3, "alpha").wait(B(131) - 0.5).to(B(131), 255, "linear").wait(b1 - 0.5).to(b1, 0, "linear")
    c.tl(l3, "scaleX").wait(B(131) - 0.5).to(B(131), 1.0, "expoOut")
    c.fx("noise", b0, b1, power=0.0025, seed=81.0)
    for k, (col, size, turn, al) in enumerate(((VIOLET, 1.25, 90, 55), (MAGENTA, 0.9, -135, 45), (LILAC, 0.6, 180, 40))):
        fr_ = c.line(f"mirage_frame{k}", tex="frame.png", z=-16, y=40, rot=45, color=col, sx=size, sy=size)
        c.tl(fr_, "alpha").wait(b0).to(b0 + 4, al, "sineOut").wait(b1 - 4).to(b1, 0, "sineIn")
        c.tl(fr_, "rotate").wait(b0).to(b1, 45 + turn, "linear")
        fsx, fsy = c.tl(fr_, "scaleX"), c.tl(fr_, "scaleY")
        for j in range(5):
            bb_ = b0 + 16 * j
            fsx.wait(bb_).to(bb_ + 8, size * 1.08, "sineInOut").to(bb_ + 16, size, "sineInOut")
            fsy.wait(bb_).to(bb_ + 8, size * 1.08, "sineInOut").to(bb_ + 16, size, "sineInOut")
    for bar in (115, 123, 125, 127, 129, 131):
        c.fx("glitch", B(bar) - 0.5, B(bar) + 0.5, power=0.05, rate=0.85, speed=14.0, blockCount=26.0, colorRate=0.012)
    # notes
    g = groove(115, 135, beat_thr=0.5, off_thr=0.82, six_thr=1.2, fill_bars=(133, 134), fill_thr=0.72)
    lanes = {1: Lane(-300, 300), 2: Lane(-400, 400), 3: Lane(-420, 420)}
    flip_bars = {B(125), B(127), B(129)}
    for i, (b, role, v) in enumerate(g):
        kind = {"kick": TAP, "clap": FLICK, "off": DRAG, "six": DRAG}[role]
        if b < B(123):
            place(l1, kind, b, lanes[1].put(b, 220 * math.sin(b * 1.1)), role, lanes[1])
        elif b < B(131):
            if any(abs(b - fb) <= 1 for fb in flip_bars):
                continue
            place(l2, kind, b, lanes[2].put(b, 300 * math.sin(b * 0.8) if role in ("off", "six") else [-260, 260][i % 2]), role, lanes[2])
        else:
            place(l3, kind, b, lanes[3].put(b, 330 * math.cos(b * 1.3)), role, lanes[3])


def scene_zenith(ctx, S):
    """IX 极 Zenith — bars 135..150: a rotating six-armed star in shifting colours."""
    c = ctx
    b0, b1 = B(135), B(151)
    caption(c, S, b0, "极", "IX  ·  ZENITH")
    hub = c.line("zen_hub")
    hr = c.tl(hub, "rotate")
    hr.wait(b0).to(B(143), 90, "linear").to(B(150), 360, "quadIn").to(b1, 450, "expoOut")
    arms = []
    for k in range(6):
        ln = c.line(f"zen_arm{k}", father=hub.index, rot=30 * k, sx=0.0, speed=8.0, color=hsv(k / 6, 0.45, 1.0), z=3)
        a, sx = c.tl(ln, "alpha"), c.tl(ln, "scaleX")
        for j in range(8):
            pair = j % 3
            on = k in (pair, pair + 3)
            bb_ = B(135 + 2 * j)
            a.wait(bb_ - 0.25 if j else bb_).to(bb_ if j else bb_ + EPSB, 255 if on else 105, "linear")
        sx.wait(b0).to(b0 + 1 + k * 0.25, 0.26, "expoOut").wait(b1 - 1).to(b1, 0.0, "expoIn")
        a.wait(b1 - 0.1).to(b1, 0, "linear")
        col = c.tl(ln, "color")
        for j in range(int((b1 - b0) // 2)):
            bb_ = b0 + 2 * j
            col.wait(bb_).to(bb_ + 2, hsv(k / 6 + (j + 1) * 0.06, 0.45, 1.0), "linear")
        arms.append(ln)
    eq_run(c, S, b0, b1, lambda u: hsv(u * 0.85, 0.5, 1.0), amax=95)
    for bar in range(135, 151, 4):
        c.fx("fisheye", B(bar), B(bar) + 1.5, power=kfv((B(bar), -0.05, "quadOut"), (B(bar) + 1.5, 0.0, "linear")))
    ripples(c, S, [B(bar) for bar in range(135, 151)], lambda b: hsv((b % 16) / 16, 0.45, 1.0), 1.7, 2.0, 110)
    g = groove(135, 151, beat_thr=0.5, off_thr=0.7, six_thr=1.05, fill_bars=(142, 149, 150), fill_thr=0.7)
    lanes = [Lane(-260, 260) for _ in range(6)]
    for i, (b, role, v) in enumerate(g):
        bar = int((b - 2) // 4)
        pair = (bar // 2) % 3
        k = pair if (int(b) % 2 == 0) else pair + 3
        kind = {"kick": TAP, "clap": FLICK, "off": DRAG, "six": DRAG}[role]
        side = (i % 2 == 0)
        x = (240 if side else -240) if role in ("kick", "clap") else 230 * math.sin(b * 1.2)
        place(arms[k], kind, b, lanes[k].put(b, x), role, lanes[k], above=(int(b * 2) % 2 == 0))


def scene_memory(ctx, S):
    """X 忆 Memory — bars 151..158: the Ascent remembered in grey; colour returns at the end."""
    c = ctx
    b0, b1 = B(151), B(159)
    caption(c, S, b0 + 1, "忆", "X  ·  MEMORY", hold=5)
    c.fx("grayscale", b0, b1, factor=kfv((b0, 0.0, "quadOut"), (b0 + 1, 1.0, "linear"), (B(157), 1.0, "quadIn"), (b1, 0.0, "linear")))
    c.fx("vignette", B(153), b1, extend=kfv((B(153), 0.25, "linear"), (b1, 0.6, "linear")),
         radius=kfv((B(153), 15.0, "quadIn"), (b1, 3.4, "linear")), color=[0.0, 0.0, 0.0, 1.0])
    ln = c.line("memory_line", color=PALE, y=-280, sx=0.0, speed=7.0, z=3)
    a, sx, y, sp, rot = (c.tl(ln, p) for p in ("alpha", "scaleX", "moveY", "speed", "rotate"))
    a.jump(b0, 255).wait(b1 - 0.25).to(b1, 0, "linear")
    sx.wait(b0).to(b0 + 2, 1.0, "expoOut")
    y.wait(B(152)).to(B(158, 2), -50, "quadIn")
    sp.wait(B(152)).to(B(158), 12.0, "linear")
    rot.wait(B(158)).to(B(158, 2.75), 360, "expoIn").jump(B(158, 2.75) + EPSB, 0)
    c.tl(S["curtain"], "alpha").wait(B(155)).to(B(158, 3), 130, "quadIn").jump(b1, 0)
    lane = Lane(-420, 420)
    items = []
    for bar in range(152, 159):
        for i in range(16):
            s = bar * 16 + i
            v = max(M.perc(s), M.harm(s))
            b = M.step_beat(s)
            if bar <= 153 and i % 4 == 0:
                items.append((b, "kick", v))
            elif 154 <= bar <= 155 and (i % 4 == 0 or (i % 2 == 0 and v > 0.6)):
                items.append((b, "kick" if i % 4 == 0 else "off", v))
            elif 156 <= bar <= 157 and (i % 4 == 0 or v > 0.5 or i % 2 == 0):
                items.append((b, "kick" if i % 4 == 0 else "six", v))
    put_notes(ln, items, lane, xfun=lambda b, r, i: (320 * math.sin(b * math.pi / 2) if r != "kick" else (-250 if i % 2 else 250)))
    for k in range(10):
        ln.note(DRAG, B(158) + frac(k, 4), -380 * math.cos(k * 0.9))
    ln.note(HOLD, B(158, 3), 0, end=B(158, 3.75))


def scene_coda(ctx, S):
    """XII 尾声 Coda — bars 168..176: everything comes home to a single point."""
    c = ctx
    b0 = B(168)
    end = B(176, 2)
    caption(c, S, b0, "尾声", "XII  ·  CODA")
    flash(c, S, b0, peak=180, dur=2.0)
    ln = c.line("coda_line", color=PALE, y=-120, sx=1.0, speed=5.0, z=3)
    a, sx, y = c.tl(ln, "alpha"), c.tl(ln, "scaleX"), c.tl(ln, "moveY")
    a.jump(b0, 255)
    y.wait(B(172)).to(B(174), 0, "sineInOut")
    sx.wait(B(172)).to(B(174), 0.34, "sineInOut").wait(B(174)).to(B(174, 3), 0.0, "expoIn")
    a.wait(B(174, 3)).to(B(174, 3.25), 0, "linear")
    dot = c.line("coda_dot", tex="glow.png", z=4, color=PALE, sx=0.0, sy=0.0)
    da, dsx, dsy = c.tl(dot, "alpha"), c.tl(dot, "scaleX"), c.tl(dot, "scaleY")
    da.wait(B(174, 2.5)).to(B(174, 3), 255, "linear").wait(B(175, 2)).to(end, 0, "sineIn")
    dsx.wait(B(174, 2.5)).to(B(174, 3), 0.7, "expoOut").to(end, 0.25, "sineIn")
    dsy.wait(B(174, 2.5)).to(B(174, 3), 0.7, "expoOut").to(end, 0.25, "sineIn")
    fin = c.line("coda_fin", z=50, y=-60, color=PALE, sx=0.5, sy=0.5)
    fin.ev("text", B(175), B(175, 2), "", "fin.")
    c.tl(fin, "alpha").wait(B(175)).to(B(175, 1), 200, "sineOut").wait(B(176, 1)).to(end + 2, 0, "sineIn")
    c.fx("vignette", B(174), end + 4, extend=kfv((B(174), 0.25, "linear"), (end + 4, 1.0, "linear")),
         radius=kfv((B(174), 15.0, "quadIn"), (end + 4, 1.2, "linear")), color=[0.0, 0.0, 0.0, 1.0])
    # the moon returns (full circle)
    for key, al, sc in (("moon", 50, 1.0), ("moonglow", 36, 2.6)):
        mo = S[key]
        c.tl(mo, "moveY").wait(b0).to(b0 + EPSB, 40, "linear")
        c.tl(mo, "scaleX").wait(b0).to(b0 + EPSB, sc, "linear").to(end, sc * 0.6, "sineIn")
        c.tl(mo, "scaleY").wait(b0).to(b0 + EPSB, sc, "linear").to(end, sc * 0.6, "sineIn")
        c.tl(mo, "alpha").wait(b0).to(b0 + 8, al, "sineInOut").wait(B(175)).to(end, 0, "sineIn")
    # stars return softly
    for k in range(10):
        st = c.line(f"coda_star{k}", tex="glow.png", z=-25, x=R.uniform(-600, 600), y=R.uniform(-380, 420),
                    color=mix(PALE, GOLD, R.random()), sx=0.15, sy=0.15)
        c.tl(st, "alpha").wait(b0 + R.uniform(0, 8)).to(b0 + 10, R.randint(40, 90), "sineOut").wait(B(175)).to(end, 0, "sineIn")
    lane = Lane(-380, 380)
    items = []
    for bar in range(168, 172):
        for i in (0, 8):
            s = bar * 16 + i
            if max(M.perc(s), M.harm(s)) > 0.4:
                items.append((M.step_beat(s), "kick", 1.0))
        for s in harmonic_hits(bar, bar + 1, q=0.85, min_gap=4):
            if s % 8 != 0:
                items.append((M.step_beat(s), "off", 1.0))
    items.sort(key=lambda t: t[0])
    put_notes(ln, items, lane, xfun=lambda b, r, i: pitch_x(int((b - 2) * 4), 300) if r == "off" else [-200, 200][i % 2])
    ln.note(HOLD, B(173), -150, end=B(173, 1.5))
    ln.note(TAP, B(173, 2), 150)
    ln.note(TAP, B(174), 0)


def halo(ctx, parent, factor=0.42, height=0.62):
    """soft glow beam that follows a judge line (child texture line, alpha/scale/colour cloned)."""
    h = ctx.c.line(f"{parent.name}_halo", texture="beam.png", z=parent.z - 1, father=parent.index, cover=True)
    def clone(prop, scale=1.0, default=None, kind="f"):
        tr = parent.ext.get(prop) if prop in ("scaleX", "scaleY", "color") else parent.layers[0].get(prop)
        segs = tr.segs if tr is not None else []
        if not segs:
            if default is not None:
                h.ev(prop, 0, EPSB, default, default)
            return
        for b0, b1, v0, v1, e in sorted(segs, key=lambda x: (x[0], x[1])):
            if kind == "f":
                h.ev(prop, b0, b1, v0 * scale, v1 * scale, e)
            else:
                h.ev(prop, b0, b1, v0, v1, e)
    clone("alpha", factor)
    clone("scaleX", 3.955, default=3.955)
    h.ev("scaleY", 0, EPSB, height, height)
    clone("color", kind="c", default=WHITE)
    for p in ("moveX", "moveY", "rotate"):
        h.ev(p, 0, EPSB, 0.0, 0.0)
    return h


def washes(ctx, S):
    w = S["wash"]
    a, col = ctx.tl(w, "alpha"), ctx.tl(w, "color")
    plan = [(B(0), B(27), ICE, 14), (B(27), B(34), VIOLET, 22), (B(34), B(43), MAGENTA, 18), (B(43), B(47), AMBER, 26),
            (B(47), B(75), CYAN, 12), (B(75), B(91), TEAL, 16), (B(91), B(115), GOLD, 12), (B(115), B(135), VIOLET, 22),
            (B(135), B(151), ROSE, 14), (B(159), B(168), GOLD, 18), (B(168), B(176), ICE, 12)]
    for b0, b1, c_, al in plan:
        col.jump(b0 - 1, c_)
        a.wait(b0 - 1).to(b0, al, "sineOut").wait(b1 - 1).to(b1, 0, "sineIn")


def make():
    ctx = Ctx()
    S = shared(ctx)
    main = scene_prelude(ctx, S)
    scene_ascent(ctx, S, main)
    scene_bloom(ctx, S, finale=False)
    scene_breath(ctx, S)
    scene_pulse(ctx, S)
    scene_echo(ctx, S)
    scene_orbit(ctx, S)
    scene_mirage(ctx, S)
    scene_zenith(ctx, S)
    scene_memory(ctx, S)
    scene_bloom(ctx, S, finale=True)
    scene_coda(ctx, S)
    # main line leaves after the ascent
    ctx.tl(main, "alpha").wait(B(34) - 0.1).to(B(34), 0, "linear")
    washes(ctx, S)
    for ln in list(ctx.c.lines):
        if ln.name in ("prelude_main", "prelude_top", "breath_line", "pulse_main", "pulse_top", "echo_a", "echo_b",
                       "orbit_minute", "mirage_flip", "mirage_reveal", "memory_line", "fin_bottom", "coda_line"):
            halo(ctx, ln)
    return ctx.c, INFO
