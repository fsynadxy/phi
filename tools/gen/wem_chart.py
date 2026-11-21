"""world.execute(me); (Mili) — a showcase chart for Phira, in the cover's glitch / pixel-art look.

The song is about a program created to love the one who runs it; its first verse is literally a boot
sequence, its second a geometry lesson, and it ends in errors. The chart follows the lyrics as a program:

    0-32    BOOT       verse 1 over the intro beat: power on, protect, pieces, object, data, init, world, title
    32-64   RUN        instrumental hook: the cover's ring, wings and power button come alive, two lines trade beats
    64-96   GEOMETRY   points -> constellation, a circle rolling out its circumference, notes on sine tangents,
                       a point tracing infinity, walls closing in (limits)
    96-128  CURRENT    AC (the line oscillates) / DC, a blinding flash, a dizzy camera, time running backwards
                       (notes rewind), two lines uniting into one point
    128-160 CHORUS     the full cover palette, call and response between a bottom and a top line
    160-192 OBJECTS    eggplant, tomato, tabby cat, and a single haloed line for "the only god"
    192-224 SWITCH     two lines swapping places, day / night, roles, then a dreamy blur; the EXECUTE? dialog
    224-288 EXECUTE    red alarm, a cage of bars (while (true)), error pop-ups, the HUD turns red
    288-320 ERROR      instrumental: glitch, error cascades, a teleporting line, a blue crash screen, reboot
    320-352 DEADLOCK   grey memories: tiles of the cover drifting, a pixel heart beating, then it stops
    352-416 FINAL      the cover assembles from its tiles, the title, everything at once
    416-458 SHUTDOWN   objects deleted one by one, the cover powers off like a CRT, "goodbye, world."

Beat k = beat k of the song (130 BPM, beat 0 at 0.2205 s); bars start on beats 0 mod 4.
"""
import math
import os
import random
from fractions import Fraction as F

import madlib as ML
import wem_assets
from chartlib import Chart, DRAG, EPSB, FLICK, HOLD, TAP, frac
from madlib import TL
from wem_lib import (BLUE, CRIMSON, CYAN, GOLD, INK, JL, MAGENTA, NEON, NIGHT, ORANGE, PALE, PINK, PURPLE, PX, RED,
                     SKY, TEAL, TERM, VIOLET, WHITE, YELLOW, Music, Notes, Stage, hsv, merge, mix)

BPM = 130.0
OFFSET_MS = 220
END = 458

INFO = {
    "name": "world.execute(me);",
    "difficulty": 13.0,
    "level": "SP Lv.?",
    "charter": "Claude",
    "composer": "Mili",
    "illustrator": "未知（封面由用户提供）",
    "chart": "chart.json",
    "format": "rpe",
    "music": "song.ogg",
    "illustration": "illustration.jpg",
    "previewStart": 59.3,
    "previewEnd": 74.0,
    "aspectRatio": 1.7777778,
    "backgroundDim": 0.5,
    "lineLength": 6.0,
    "offset": 0.0,
    "tip": "> world.execute(me);  建议开启 Autoplay 观看；特效较多，设备较弱时可关闭特效",
    "tags": ["观赏谱", "showcase", "Mili", "world.execute(me);", "glitch"],
    "intro": "Mili《world.execute(me);》观赏谱：把歌词当成一段程序来演——开机、建模、几何课、交流电、副歌、报错、死锁、关机。",
    "holdPartialCover": False,
    "noteUniformScale": False,
    "forceAspectRatio": False,
    "useRpe170Speed": False,
    "useAttachUiFix": True,
}

R = random.Random(20161205)
B0 = -260.0  # main line height


# ------------------------------------------------------------------ texture helpers
def T(name):
    return name if "." in name else name + ".png"


def size(name):
    return ML.TEXPX[T(name)]


def tex_h(name, w):
    pw, ph = size(name)
    return w * ph / pw


def anim(e, b0, b1, ease="linear", **vals):
    """animate the given properties from b0 to b1 (each one held at its last value until b0)."""
    b0 = frac(b0)
    for p in vals:
        kf = e.kf[p]
        if kf.k[-1][0] < b0:
            kf.add(b0, kf.k[-1][1], "linear")
    e.at(b1, ease, **vals)
    return e


def txt(sh, name, x, y, h, b0, b1, col=WHITE, a=255, z=20, fade=F(1, 4), left=False):
    """a text texture of height h (physical) centred at (x, y) (or with its left edge at x)."""
    pw, ph = size(name)
    w = h * pw / ph
    cx = x + w / 2 if left else x
    e = sh.tex(T(name), cx, y, w, h, color=col, alpha=0 if fade else a, z=z, start=b0, end=b1)
    if fade:
        e.at(frac(b0) + fade, "quadOut", alpha=a)
        if frac(b1) - fade > frac(b0) + fade:
            e.at(frac(b1) - fade, alpha=a)
            e.at(b1, "quadIn", alpha=0)
    return e


LABEL_X, LABEL_Y = -720.0, 382.0  # top left, clear of the pause button, the combo counter (top centre) and the score


def label(sh, name, h, b0, b1, col=WHITE, a=255, z=20):
    """a section caption: left-aligned at the top left of the screen"""
    return txt(sh, name, LABEL_X, LABEL_Y, h, b0, b1, col, a, z=z, left=True)


def typed(sh, name, nchar, x_left, y, h, b0, dur, b_end, col, panel, z=20, cursor=True):
    """terminal typing: the text is uncovered character by character by a panel-coloured mask."""
    pw, ph = size(name)
    w = h * pw / ph
    k = h / ph
    pad = 8 * k
    cw = (w - 2 * pad) / nchar
    b0, dur = frac(b0), frac(dur)
    sh.tex(T(name), x_left + w / 2, y, w, h, color=col, z=z, start=b0, end=b_end)
    right = x_left + w + 2
    m = sh.tex("white.png", (x_left + right) / 2, y, right - x_left + 4, h + 6, color=panel, z=z + 1, start=b0,
               end=b0 + dur + F(1, 16))
    cur = sh.tex("white.png", x_left + pad + cw * 0.45, y - h * 0.05, cw * 0.85, h * 0.62, color=col, z=z + 2,
                 start=b0, end=b0 + dur + F(3, 2)) if cursor else None
    for i in range(1, nchar + 1):
        t = b0 + dur * i / nchar
        left = x_left + pad + cw * i
        prev = left - cw
        m.at(t, x=(prev + right) / 2, w=right - prev + 4)
        m.at(t, x=(left + right) / 2, w=max(0.5, right - left + 4))
        if cur:
            cur.at(t, x=prev + cw * 0.45)
            cur.at(t, x=left + cw * 0.45)
    if cur:  # blink after typing
        for j in range(3):
            t = b0 + dur + F(j, 2)
            cur.at(t, alpha=255)
            cur.at(t, alpha=0)
            cur.at(t + F(1, 4), alpha=0)
            cur.at(t + F(1, 4), alpha=255)
    return w


def pop(sh, name, x, y, w, b0, b1, col=WHITE, a=255, z=30, rot=0.0, t_in=F(3, 8), t_out=F(1, 4), ease="backOut",
        close=True):
    h = tex_h(name, w)
    b0, b1 = frac(b0), frac(b1)
    e = sh.tex(name, x, y, w * 0.2, h * 0.2, rot=rot, color=col, alpha=0, z=z, start=b0, end=b1)
    e.at(b0 + t_in, ease, w=w, h=h, alpha=a)
    if close:
        shut(e, b1, w, h, a, t_out)
    return e


def shut(e, b1, w, h, a=255, t_out=F(1, 4)):
    b1 = frac(b1)
    e.at(b1 - t_out, w=w, h=h, alpha=a)
    e.at(b1, "quadIn", w=w * 0.05, h=h * 1.1, alpha=0)


def flash(sh, b, col=WHITE, a=230, dur=1, z=60):
    b = frac(b)
    e = sh.tex("white.png", 0, 0, 1800, 1050, color=col, alpha=a, z=z, start=b, end=b + frac(dur))
    e.at(b + frac(dur), "quadOut", alpha=0)
    return e


def panel(sh, x0, y0, x1, y1, b0, b1, col=INK, a=235, z=18, t=F(1, 4)):
    e = sh.tex("white.png", (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, 1, color=col, alpha=a, z=z, start=b0, end=b1)
    e.at(frac(b0) + t, "expoOut", h=y1 - y0)
    if frac(b1) - t > frac(b0) + t:
        e.at(frac(b1) - t, h=y1 - y0)
    e.at(b1, "expoIn", h=1)
    return e


def stroke(sh, x1, y1, x2, y2, b0, b1, col=WHITE, th=6.0, a=255, z=0):
    return sh.seg((x1, y1), (x2, y2), thick=th, color=col, alpha=a, z=z, start=b0, end=b1)


def grow(sh, x1, y1, x2, y2, b0, dur, b1, col=WHITE, th=6.0, a=255, z=0, out=F(1, 4)):
    """a stroke drawn from (x1, y1) towards (x2, y2) over `dur` beats, faded out over the last `out` beats"""
    ang = -math.degrees(math.atan2(y2 - y1, x2 - x1))
    half = math.hypot(x2 - x1, y2 - y1) / 2
    b0, b1 = frac(b0), frac(b1)
    e = sh.line(x1, y1, ang, 0.5, th, col, a, z=z, start=b0, end=b1)
    e.at(b0 + frac(dur), "quadOut", x=(x1 + x2) / 2, y=(y1 + y2) / 2, w=half)
    if b1 - frac(out) > b0 + frac(dur):
        e.at(b1 - frac(out), alpha=a)
    e.at(b1, "quadIn", alpha=0)
    return e


def bounce(jl, beats, y, depth=12.0, sgn=1):
    """a speaker-cone kick: down right after each beat, back at rest before the next one."""
    for b in beats:
        b = frac(b)
        jl.to(b, b + F(1, 8), "quadOut", y=y - sgn * depth)
        jl.to(b + F(1, 8), b + F(5, 8), "quadInOut", y=y)


# ------------------------------------------------------------------ note helpers
def auto_flicks(ev, gap=F(1)):
    """phrase ends: a short syllable followed by a gap of at least `gap` beats"""
    out = []
    for i, e in enumerate(ev):
        nxt = ev[i + 1]["b"] if i + 1 < len(ev) else e["b"] + 9
        if nxt - e["b"] >= gap and e.get("sus", 0) < F(3, 4):
            out.append(e["b"])
    return out


def phrase_starts(ev, gap=F(1)):
    out = []
    for i, e in enumerate(ev):
        prv = ev[i - 1]["b"] if i else e["b"] - 9
        if e["b"] - prv >= gap and e["b"].denominator == 1:
            out.append(e["b"])
    return out


def fill(base, extra, gap=F(1, 2)):
    """add the extra events that are at least `gap` from every base event"""
    bs = [e["b"] for e in base]
    out = list(base)
    for e in extra:
        if all(abs(e["b"] - b) >= gap for b in bs):
            out.append(e)
    return sorted(out, key=lambda e: e["b"])


def cut(ev, *ranges):
    """drop events inside the given [b0, b1) ranges"""
    return [e for e in ev if not any(frac(a) <= e["b"] < frac(b) for a, b in ranges)]


def ev_at(beats, w=0.8, src="d"):
    return [{"b": frac(b), "w": w, "p": 62.0, "sus": F(0), "src": src} for b in beats]


# ------------------------------------------------------------------ the chart
class World:
    def __init__(self, c):
        self.c = c
        self.S = Stage(c)
        self.m = Music()
        self.N = Notes()
        self.cam = self.S.cam.index
        self.A = JL(c, "A", z=10, father=self.cam, y=0, alpha=0, speed=8.0, color=WHITE, sx=0.0)
        self.B = JL(c, "B", z=9, father=self.cam, y=260, rot=180, alpha=0, speed=9.0, color=PINK)
        self.sh = self.S.eng.shot(0, END)

    # ---------------------------------------------------------------- 0-32 BOOT
    def boot(self):
        S, sh, A, N, m = self.S, self.sh, self.A, self.N, self.m
        # CRT look for the whole boot: scanlines over everything
        e = sh.tex("scan.png", 0, 0, 1600, 900, color=WHITE, alpha=140, z=70, start=0, end=34)
        e.at(32, alpha=140)
        e.at(34, "quadOut", alpha=0)
        # power LED, then the line switches on like a CRT
        led = sh.tex("glow.png", 0, 0, 10, color=TERM, alpha=0, z=12, start=EPSB, end=F(5, 2))
        led.at(F(1, 4), "quadOut", w=90, h=90, alpha=255)
        led.at(1, w=70, h=70, alpha=255)
        led.at(F(3, 2), "expoOut", w=260, h=40, alpha=255)
        led.at(F(5, 2), "quadOut", w=40, h=20, alpha=0)
        A.at(1, a=255, sy=5.0, col=TERM)
        A.to(1, F(3, 2), "expoOut", sx=1.0)
        A.to(1, 2, "quadOut", sy=1.0)
        A.to(F(3, 2), 3, "quadOut", col=WHITE)
        flash(sh, 1, TERM, 55, F(3, 4))
        S.chroma(1, 0.02, 1)
        # terminal panel (top left), one line per bar
        panel(sh, -790, 52, -95, 440, F(1, 2), 32, INK, 240, z=18)
        rows = [("t_b0", 12), ("t_b1", 14), ("t_b2", 19), ("t_b3", 14), ("t_b4", 20), ("t_b5", 6), ("t_b6", 21),
                ("t_b7", 20)]
        for i, (name, n) in enumerate(rows):
            typed(sh, name, n, -770, 412 - 47 * i, 43, 4 * i + F(1, 4), F(3, 2) if n < 16 else 2, 32, TERM, INK)
        # bar 1: protect(all) -- a frame draws itself around the screen
        corners = [(-770, 425), (770, 425), (770, -425), (-770, -425)]
        for k in range(4):
            (x1, y1), (x2, y2) = corners[k], corners[(k + 1) % 4]
            b = 4 + F(k, 2)
            grow(sh, x1, y1, x2, y2, b, F(1, 2), 32 + F(1, 2), TERM, 5, 220, z=14, out=F(1, 2))
        # the line drops to its place in the gap of bar 1
        A.to(F(27, 4), F(31, 4), "quartInOut", y=B0)
        # bar 2: pieces laid down onto the line, bar 3: they gather into an object
        pcs = []
        times = [8, F(17, 2), 9, F(39, 4), F(41, 4), F(21, 2), 11, F(23, 2)]
        cols = [CYAN, PINK, NEON, YELLOW, VIOLET, ORANGE, CYAN, MAGENTA]
        for k, (b, col) in enumerate(zip(times, cols)):
            x = -420 + 120 * k
            p = sh.tex("white.png", x, 520, 46, 46, rot=45, color=col, z=11, start=b - F(1, 2), end=F(29, 2))
            p.at(b, "quadIn", y=B0 + 30, rot=0)
            p.at(b + F(1, 4), "quadOut", y=B0 + 52)
            p.at(b + F(1, 2), "bounceOut", y=B0 + 30)
            pcs.append((p, x))
        for k, (p, x) in enumerate(pcs):
            a = k / 8 * 2 * math.pi
            p.at(12, y=B0 + 30, x=x, rot=0)
            p.at(13, "quartInOut", x=150 * math.cos(a), y=110 + 150 * math.sin(a), rot=180)
            p.at(14, "linear", x=150 * math.cos(a + 1.2), y=110 + 150 * math.sin(a + 1.2), rot=360)
            anim(p, 14, F(29, 2), "expoIn", x=0, y=110, w=10, h=10, rot=540)
        obj = pop(sh, "power.png", 0, 110, 200, F(29, 2), 32, TERM, 255, z=12, t_in=F(1, 2), close=False)
        flash(sh, F(29, 2), TERM, 120, F(1, 2))
        S.shock(F(29, 2), 0.5, 0.62, F(3, 2), 0.06, 0.6, p0=0.1)
        for b in range(16, 28, 2):  # the object breathes with the kick
            obj.at(b, w=200, h=200)
            obj.at(b + F(1, 4), "quadOut", w=214, h=214)
            obj.at(b + F(1, 1), "quadIn", w=200, h=200)
        obj.at(F(57, 2), w=200, h=200, x=0, y=110)
        obj.at(30, "quartInOut", x=560, y=300, w=150, h=150)
        obj.at(32, x=560, y=300, w=150, h=150)
        # bar 4: fill(data, params) -- data rain
        for k, x in enumerate((-660, -330, 0, 330, 660)):
            for j in range(2):
                b = 16 + F(k, 4) + 4 * j
                d = sh.tex("binary.png", x + 60 * j, 1260, 300, color=TERM, alpha=0, z=-40, start=b, end=b + 6)
                d.at(b + 1, alpha=110)
                d.at(b + 6, "linear", y=-1260, alpha=60)
        # bar 5: init() -- a setup window with a progress bar
        win_w = 560
        sc = win_w / 128
        wy = 120
        pop(sh, "win_load.png", 0, wy, win_w, 20, 24, WHITE, 255, z=30)
        x_left = -win_w / 2 + 9 * sc
        bar_w = 110 * sc
        bar_y = wy + (24 - 32) * sc
        bar = sh.tex("white.png", x_left, bar_y, 0.1, 9 * sc, color=TERM, z=31, start=F(41, 2), end=F(95, 4))
        prog = [(F(41, 2), 0.0), (21, 0.22), (F(43, 2), 0.38), (22, 0.55), (F(45, 2), 0.71), (23, 0.86), (F(47, 2), 1.0)]
        for b, f in prog[1:]:
            bar.at(b, "quadOut", x=x_left + bar_w * f / 2, w=max(0.1, bar_w * f))
        # bar 6: world = new World() -- the grid
        g = sh.tex("grid.png", 0, -40, 400, color=TEAL, alpha=0, z=-50, start=24, end=34)
        g.at(25, "expoOut", w=1900, h=tex_h("grid.png", 1900), alpha=150)
        anim(g, 32, 33, "quadOut", w=2600, h=tex_h("grid.png", 2600), alpha=0)
        S.bgc(24, (10, 18, 30), 2)
        # bar 7: the title, a glitch, the cover flickers in, run
        panel(sh, -470, 230, 470, 330, 28, 32, INK, 250, z=24)
        typed(sh, "t_title", 18, -440, 280, 52, 28, F(5, 2), 32, YELLOW, INK, z=25)
        S.glitch(30, F(61, 2), 0.06, 0.9, 12)
        S.glitch(31, 32, 0.1, 1.0, 16)
        for b, name, a in ((F(121, 4), "cover_px24.jpg", 180), (F(245, 8), "cover_px8.jpg", 220), (F(63, 2), "cover_full.jpg", 255)):
            e = sh.tex(name, 0, 0, 1600, 900, color=WHITE, alpha=a, z=-60, start=b, end=b + F(1, 8) if b < 31 else F(127, 4))
            if b == F(63, 2):
                e.at(F(127, 4), "quadIn", alpha=0)
        # ---- notes: the first verse on the line (centre for bar 0-1, then low)
        ev = cut(m.vocal(2, 32, 0.3), (F(27, 4), F(31, 4)), (F(29, 2) - F(1, 8), F(29, 2) + F(1, 8)))
        ev = fill(ev, m.drums(8, 32, kick=0.5), F(1, 2))
        N.place(ev, A, zone=(110, 470), flicks=auto_flicks(ev, F(3, 2)), chord_at=[16, 24], seed=1)
        A.at(F(29, 2), spd=8.5)
        A.at(28, spd=9.0)

    # ---------------------------------------------------------------- 32-64 RUN (instrumental hook)
    def run(self):
        S, sh, A, B, N, m = self.S, self.sh, self.A, self.B, self.N, self.m
        flash(sh, 32, WHITE, 210, 1)
        S.shock(32, 0.5, 0.5, 2, 0.12, 0.9)
        S.chroma(32, 0.03, 2)
        S.hud_in(32, 33)
        S.bgc(32, (20, 14, 46), 1)
        for k, col in enumerate([(26, 12, 54), (10, 22, 50), (30, 10, 44)]):
            S.bgc(40 + 8 * k, col, 2, "sineInOut")
        # the cover's ring, wings and power button
        ring = sh.tex("ring_cover.png", 0, 70, 100, color=WHITE, alpha=0, z=-20, start=32, end=64)
        ring.at(33, "expoOut", w=760, h=760, alpha=230, rot=90)
        ring.at(62, "linear", rot=90 + 270)
        anim(ring, 63, 64, "expoIn", w=60, h=60, alpha=0, rot=420)
        wl = sh.tex("wing_l.png", 0, 90, 10, color=WHITE, alpha=0, z=-18, start=32, end=64)
        wr = sh.tex("wing_r.png", 0, 90, 10, color=WHITE, alpha=0, z=-18, start=32, end=64)
        W_ = 640
        H_ = tex_h("wing_r.png", W_)
        for e, s in ((wl, -1), (wr, 1)):
            e.at(F(65, 2), "backOut", x=s * 330, w=W_, h=H_, alpha=255, rot=-s * 10)
            for b in range(33, 62):
                e.at(b, h=H_, rot=-s * 10)
                e.at(b + F(1, 2), "quadOut", h=H_ * 0.84, rot=-s * 2)
                e.at(b + 1, "quadIn", h=H_, rot=-s * 10)
            e.at(63, x=s * 330, alpha=255)
            e.at(64, "expoIn", x=s * 900, alpha=0)
        pw = sh.tex("power.png", 560, 300, 150, color=TERM, alpha=255, z=-16, start=32, end=64)
        pw.at(33, "quartInOut", x=0, y=70, w=170, h=170)
        pw.at(33, color=WHITE)
        for b in range(33, 63):
            pw.at(b, w=170, h=170, color=CYAN if b % 2 else PINK)
            pw.at(b + F(1, 4), "quadOut", w=196, h=196)
            pw.at(b + 1, "quadIn", w=170, h=170)
        pw.at(64, "expoIn", w=0, h=0, alpha=0)
        # emoji windows pop on the phrase ends
        spots = [(-560, 250), (560, 250), (-560, -20), (560, -20)]
        faces = ["face_smile.png", "face_laugh.png", "face_angry.png", "face_smile.png", "face_dizzy.png",
                 "face_laugh.png", "face_smile.png", "face_laugh.png"]
        for k in range(8):
            b = 35 + 4 * k
            x, y = spots[k % 4]
            pop(sh, "win_blank.png", x, y, 300, b, b + 3, WHITE, 255, z=30, rot=R.uniform(-4, 4))
            pop(sh, faces[k], x, y - 14, 110, b + F(1, 8), b + 3 - F(1, 16), WHITE, 255, z=31)
        label(sh, "t_run", 49, 32, 40, TERM, 255, z=20)
        # lines: A on the kicks (bottom), B on the off-beats (top, upside down); they swap halfway
        A.at(32, col=CYAN, spd=9.0)
        bounce(A, [b for b in range(33, 47)], B0, 10)
        B.at(32, a=0, y=250, col=PINK)
        B.to(32, 33, "quadOut", a=255)
        for b in range(32, 64):  # every downbeat the camera dips
            if b % 4 == 0:
                S.cam_to(b, b + F(1, 8), "quadOut", y=-10)
                S.cam_to(b + F(1, 8), b + 1, "quadInOut", y=0)
        # swap at 47.5-48: A goes to the top (flipped), B to the bottom
        A.to(F(95, 2), 48, "quartInOut", y=250, rot=180)
        B.to(F(95, 2), 48, "quartInOut", y=B0, rot=360)
        B.at(48, rot=0)
        A.to(F(127, 2), 64, "quartInOut", y=B0, rot=360)
        A.at(64, rot=0)
        B.to(F(127, 2), 64, "quartInOut", y=260, rot=180, a=0)
        kick = [{"b": F(b), "w": 1.0, "p": 62.0, "sus": F(0), "src": "k"} for b in range(32, 64)]
        off = [{"b": F(b) + F(1, 2), "w": 0.8, "p": 62.0, "sus": F(0), "src": "s"} for b in range(32, 63)]
        fills = []
        for b in (39, 47, 55, 63):
            fills += [{"b": F(b) + F(k, 4), "w": 0.7, "p": 60.0 + 3 * k, "sus": F(0), "src": "h"} for k in range(4)]
        kick = [e for e in kick if e["b"] not in (39, 47, 55, 63, 48)]
        off = [e for e in off if e["b"] not in (F(79, 2), F(95, 2), F(111, 2), F(127, 2))]
        lo = [e for e in kick if e["b"] < 48]
        hi = [e for e in off if e["b"] < 48]
        N.place(lo, A, zone=(200, 520), seed=3, xfun=lambda e, h, i: (-1) ** i * (260 + 120 * ((i // 2) % 3)))
        N.place(hi, B, zone=(160, 420), seed=4, xfun=lambda e, h, i: (-1) ** (i + 1) * (180 + 100 * ((i // 2) % 3)))
        N.place([e for e in kick if e["b"] >= 48], B, seed=5, xfun=lambda e, h, i: (-1) ** i * (260 + 120 * ((i // 2) % 3)))
        N.place([e for e in off if e["b"] >= 48], A, seed=6, xfun=lambda e, h, i: (-1) ** (i + 1) * (180 + 100 * ((i // 2) % 3)))
        for k, b in enumerate((39, 47, 55, 63)):
            line = A if b < 48 else B
            xs = [-450, -300, -150, 0] if k % 2 == 0 else [450, 300, 150, 0]
            for j in range(4):
                if b == 63 and j == 3:
                    continue
                N.add(line if b != 47 else A, F(b) + F(j, 4), xs[j], TAP if j == 0 else DRAG)
        N.add(B, 48, -380, FLICK)
        N.add(B, 48, 380, FLICK)
        B.at(40, col=MAGENTA)
        A.at(48, col=PINK)
        B.at(48, col=CYAN)

    # ---------------------------------------------------------------- 64-96 GEOMETRY
    def geometry(self):
        S, sh, A, N, m, c = self.S, self.sh, self.A, self.N, self.m, self.c
        A.at(64, col=WHITE, a=255, spd=9.0)
        S.bgc(64, (8, 16, 30), 1)
        # -- points -> dimension (64-72)
        label(sh, "t_points", 56, 64, 72, CYAN, 230)
        ev = m.vocal(64, 72, 0.3)
        dots = []
        for k, e in enumerate(ev):
            x, y = R.uniform(-640, 640), R.uniform(-60, 340)
            col = (CYAN, PINK, YELLOW, NEON)[k % 4]
            d = sh.tex("glow.png", x, y, 8, color=col, alpha=0, z=-10, start=e["b"], end=72)
            d.at(min(e["b"] + F(1, 4), F(287, 4)), "backOut", w=70, h=70, alpha=255)
            if e["b"] + F(1, 4) < F(143, 2):
                d.at(F(143, 2), w=70, h=70, alpha=255)
            d.at(72, "quadIn", w=10, h=10, alpha=0)
            dots.append((x, y, e["b"]))
        for k in range(len(dots) - 1):
            (x1, y1, b1), (x2, y2, b2) = dots[k], dots[k + 1]
            b = max(b2, F(68)) + F(k % 4, 8)
            if b >= 71:
                continue
            grow(sh, x1, y1, x2, y2, b, F(1, 4), 72, PALE, 3, 150, z=-11, out=F(1, 2))
        g = sh.tex("grid.png", 0, 140, 1900, color=CYAN, alpha=0, z=-30, start=68, end=72)
        g.at(69, "quadOut", alpha=60)
        g.at(72, "quadIn", alpha=0)
        N.place(ev, A, zone=(110, 520), flicks=auto_flicks(ev), chord_at=[64], seed=11)
        # -- circle -> circumference (72-80)
        label(sh, "t_circle", 63, 72, 80, VIOLET, 240)
        ring = sh.tex("ring_cover.png", 0, 90, 60, color=WHITE, alpha=0, z=-20, start=72, end=80)
        ring.at(73, "expoOut", w=560, h=560, alpha=230, rot=-60)
        ring.at(F(151, 2), "linear", rot=-60 + 315)
        r = 92.0
        anim(ring, F(151, 2), 76, "quartInOut", x=-700, y=B0 + r, w=2 * r / 0.98, h=2 * r / 0.98, rot=-60 + 360)
        xr1 = 700.0
        roll = (xr1 + 700) / r * 180 / math.pi
        ring.at(F(319, 4), "linear", x=xr1, rot=-60 + 360 + roll)
        anim(ring, F(319, 4), 80, "quadIn", x=xr1 + 40, alpha=0, w=0, h=0)
        trail = sh.tex("white.png", -750, B0 + 2, 1, 10, color=VIOLET, alpha=255, z=11, start=76, end=F(161, 2))
        trail.at(F(319, 4), "linear", x=(-800 + xr1) / 2, w=xr1 + 800)
        anim(trail, 80, F(161, 2), "quadIn", alpha=0, h=2)
        # 12-gon spinning inside the ring (children of a hub line)
        hub = JL(c, "hub12", z=-19, father=self.cam, x=0, y=90, alpha=0, speed=0.0)
        hub.to(72, 76, "linear", rot=360)
        segs = []
        for k in range(12):
            a = k / 12 * 2 * math.pi
            rad = 200
            sx, sy = rad * math.cos(a), rad * math.sin(a)
            ln = c.line(f"poly{k}", texture="white.png", z=-19, father=hub.ln.index, rot_with_father=True)
            half = rad * math.sin(math.pi / 12)
            for p, v in (("moveX", sx * PX), ("moveY", sy), ("rotate", -math.degrees(a) - 90), ("alpha", 0.0),
                         ("scaleX", 2 * half / (64 * ML.TEXK)), ("scaleY", 5 / (64 * ML.TEXK))):
                ln.ev(p, 0, EPSB, v, v)
            ln.ev("color", 0, EPSB, PALE, PALE)
            ln.ev("alpha", 72 + F(k, 12), 73 + F(k, 12), 0.0, 220.0, "quadOut")
            ln.ev("alpha", F(151, 2), 76, 220.0, 0.0, "quadIn")
            segs.append(ln)
        ev = m.vocal(72, 80, 0.3)
        N.place(ev, A, zone=(110, 500), flicks=auto_flicks(ev), seed=12)
        # -- sine wave and its tangents (80-88): the notes sit on the tangents
        label(sh, "t_tangent", 56, 80, 88, PINK, 230)
        A.to(F(319, 4), 80, "quadIn", a=0)
        wave = sh.tex("sine.png", 0, -110, 1700, 260, color=PINK, alpha=0, z=-25, start=79, end=88)
        wave.at(80, alpha=50)
        wave.at(87, alpha=50)
        wave.at(88, alpha=0)
        Y0, AMP, LAM, PER = -110.0, 115.0, 1280.0, F(4)
        tilt = math.degrees(math.atan(AMP * 2 * math.pi / LAM))
        xs = [-640 + 160 * k for k in range(9)]
        T = []
        for k, x in enumerate(xs):
            col = mix(CYAN, PINK, k / 8)
            ph = 2 * math.pi * x / LAM
            y_at = lambda t, ph=ph: Y0 + AMP * math.sin(ph - 2 * math.pi * (t - 80) / float(PER))
            r_at = lambda t, ph=ph: -tilt * math.cos(ph - 2 * math.pi * (t - 80) / float(PER))
            ln = JL(c, f"tan{k}", z=8, father=self.cam, x=x, y=y_at(79), rot=r_at(79), alpha=0, speed=7.5,
                    color=col, sx=70 / 2400)
            ln.to(79, 80, "quadOut", a=255)
            self._sine_track(ln, "y", 79, F(177, 2), lambda t, ph=ph: math.sin(ph - 2 * math.pi * (t - 80) / float(PER)),
                             Y0, AMP, PER, ph)
            self._sine_track(ln, "rot", 79, F(177, 2), lambda t, ph=ph: math.sin(ph + math.pi / 2 - 2 * math.pi * (t - 80) / float(PER)),
                             0.0, -tilt, PER, ph + math.pi / 2)
            ln.to(88, F(177, 2), "quadIn", a=0)
            T.append(ln)
        ev = m.vocal(80, 88, 0.3)
        ev = fill(ev, ev_at([82, 87 + F(3, 4)], 0.8), F(1, 2))
        order = [1, 3, 5, 7, 6, 4, 2, 4, 6, 8, 6, 4, 3, 2, 1]
        for i, e in enumerate(ev):
            k = order[i % len(order)]
            kind, end = TAP, None
            if e.get("sus", 0) >= F(3, 4):
                kind, end = HOLD, e["b"] + min(F(2), e["sus"])
            N.add(T[k], e["b"], 0.0, kind, end)
        A.at(F(175, 2), y=B0, rot=0)
        A.to(F(175, 2), 88, "quadOut", a=255)
        # -- infinity and limits (88-96)
        label(sh, "t_limit", 59, 88, 96, YELLOW, 230)
        inf = sh.tex("t_inf.png", 0, 120, 620, color=YELLOW, alpha=0, z=-30, start=88, end=94)
        inf.at(89, alpha=70)
        inf.at(93, alpha=70)
        inf.at(94, alpha=0)
        dot = sh.tex("glow.png", 0, 120, 80, color=WHITE, alpha=0, z=-28, start=88, end=94)
        dot.at(F(353, 4), alpha=255)
        steps = 48
        for k in range(steps + 1):
            t = 2 * math.pi * k / steps * 2
            a = 300
            den = 1 + math.sin(t) ** 2
            x, y = a * math.cos(t) / den, a * math.sin(t) * math.cos(t) / den
            dot.at(F(353, 4) + F(k, steps) * F(19, 4), "linear", x=x, y=120 + y * 0.92)
        dot.at(94, "quadIn", alpha=0)
        for s_ in (-1, 1):
            wall = sh.tex("white.png", s_ * 840, 0, 14, 900, color=RED, alpha=255, z=12, start=92, end=96)
            wall.at(93, "expoOut", x=s_ * 600)
            for b in (94, 95):
                wall.at(b, x=s_ * 600, w=14)
                wall.at(b + F(1, 8), "quadOut", x=s_ * 585, w=20)
                wall.at(b + F(1, 2), "quadIn", x=s_ * 600, w=14)
            wall.at(F(191, 2), x=s_ * 600)
            wall.at(96, "expoIn", x=s_ * 950, w=2)
        A.to(92, 93, "expoOut", sx=600 / 2400)
        A.to(F(191, 2), 96, "expoIn", sx=1.0)
        ev = m.vocal(88, 96, 0.3)
        N.place([e for e in ev if e["b"] < 92], A, zone=(110, 520), flicks=auto_flicks(ev), seed=13)
        N.place([e for e in ev if e["b"] >= 92], A, zone=(90, 460), flicks=auto_flicks(ev), seed=14)

    def _sine_track(self, ln, k, b0, b1, f, base, amp, per, ph):
        """value(t) = base + amp*sin(ph - 2pi(t-80)/per) written with sine easings between extremes."""
        b0, b1 = frac(b0), frac(b1)
        quarter = per / 4
        # extremes: ph - 2pi(t-80)/per = pi/2 + n pi  ->  t = 80 + (ph - pi/2 - n pi) * per / 2pi
        ext = []
        for n in range(-12, 12):
            t = 80 + (ph - math.pi / 2 - n * math.pi) * float(per) / (2 * math.pi)
            if float(b0) < t < float(b1):
                ext.append(F(t).limit_denominator(96))
        ext.sort()
        pts = [b0] + ext + [b1]
        val = lambda t: base + amp * math.sin(ph - 2 * math.pi * (float(t) - 80) / float(per))
        ln.at(b0, **{k: val(b0)})
        for a, b in zip(pts, pts[1:]):
            if b <= a:
                continue
            # full half-wave between two extremes: sineInOut; partial ones: clipped sineInOut
            va, vb = val(a), val(b)
            ln.to(a, b, self._sine_clip(a, b, ext, per), **{k: vb})

    @staticmethod
    def _sine_clip(a, b, ext, per):
        half = per / 2
        if a in ext and b in ext:
            return "sineInOut"
        # the half wave containing [a, b]
        if a in ext:
            e0 = a
        elif b in ext:
            e0 = b - half
        else:
            e0 = a - half / 2
        left = float((a - e0) / half)
        right = float((b - e0) / half)
        left, right = max(0.0, left), min(1.0, right)
        if right - left < 1e-3:
            return "linear"
        from chartlib import EASE
        return (EASE["sineInOut"], left, right)

    # ---------------------------------------------------------------- 96-128 CURRENT
    def current(self):
        S, sh, A, B, N, m = self.S, self.sh, self.A, self.B, self.N, self.m
        Y = -230.0
        A.to(95, 96, "quadInOut", y=Y)
        A.at(96, col=YELLOW)
        S.bgc(96, (22, 20, 8), F(1, 2))
        wave = sh.tex("sine.png", 0, 80, 1800, 300, color=YELLOW, alpha=0, z=-25, start=96, end=104)
        wave.at(F(193, 2), alpha=150)
        for b in range(96, 100):
            wave.at(b, h=300)
            wave.at(b + F(1, 4), "sineOut", h=360)
            wave.at(b + F(3, 4), "sineInOut", h=220)
            wave.at(b + 1, "sineIn", h=300)
        wave.at(100, h=300, color=YELLOW)
        wave.at(F(201, 2), "expoOut", h=8, color=CYAN)
        wave.at(104, alpha=150)
        label(sh, "t_ac", 61, 96, 100, YELLOW, 255)
        label(sh, "t_dc", 61, 100, 104, CYAN, 255)
        # AC: the line swings through its rest position on every 8th
        AMP = 46
        A.to(96, F(385, 4), "sineOut", y=Y + AMP)
        b = F(385, 4)
        sgn = -1
        while b + F(1, 2) <= 100 - F(1, 4):
            A.to(b, b + F(1, 2), "sineInOut", y=Y + sgn * AMP)
            b += F(1, 2)
            sgn = -sgn
        A.to(b, 100, "sineIn", y=Y)
        A.at(100, col=CYAN)
        # blind my vision: a white-out between phrases
        flash(sh, 102, WHITE, 250, F(3, 2), z=65)
        # dizzy (104-112): camera sways, fisheye breathes, dizzy faces orbit
        S.sway(104, 112, 12, 2)
        S.fxk("fisheye", 104, 112, {"power": [(104, 0.0, "linear"), (106, -0.12, "sineInOut"), (108, 0.0, "sineInOut"),
                                             (110, -0.12, "sineInOut"), (112, 0.0, "sineInOut")]})
        S.bgc(104, (28, 10, 40), 1)
        A.at(104, col=PINK)
        for k in range(4):
            f = sh.tex("face_dizzy.png", 0, 0, 120, color=WHITE, alpha=0, z=-10, start=104, end=112)
            for j in range(33):
                t = F(104) + F(j, 4)
                a = 2 * math.pi * (j / 16 + k / 4)
                f.at(t, "linear", x=430 * math.cos(a), y=120 + 220 * math.sin(a), rot=j * 22.5, alpha=220 if 0 < j < 32 else 0)
        # A.D. <-> B.C. (112-120): the clock runs backwards and the notes rewind
        label(sh, "t_time", 61, 112, 120, PALE, 255)
        S.bgc(112, (10, 14, 24), 1)
        A.at(112, col=PALE)
        clock = sh.tex("clock.png", 0, 90, 80, color=PALE, alpha=0, z=-25, start=112, end=120)
        clock.at(113, "expoOut", w=560, h=560, alpha=120)
        clock.at(119, w=560, h=560, alpha=120)
        clock.at(120, "expoIn", w=40, h=40, alpha=0)
        for L, th_, spd in ((180, 9, -360), (240, 5, -1440)):
            hand = stroke(sh, 0, 90, 0, 90 + L, 112, 120, PALE, th_, 220, z=-24)
            hand.kf["x"].add(112, 0)
            for j in range(1, 33):
                t = F(112) + F(j, 4)
                a = math.radians(spd * j / 32)
                hand.at(t, "linear", x=L / 2 * math.sin(a), y=90 + L / 2 * math.cos(a), rot=math.degrees(a) - 90)
        for t0 in (F(229, 2), F(237, 2)):  # rewind windows
            A.at(t0, spd=-11.0)
            A.at(t0 + F(1, 2), spd=16.0)
            A.at(t0 + 1, spd=9.0)
            S.chroma(t0, 0.025, 1)
            S.glitch(t0, t0 + F(1, 2), 0.05, 1.0, 10)
            flash(sh, t0, CYAN, 80, F(1, 2))
        # unite (120-128): a bottom and a top line close in and become one
        A.to(119, 120, "quadOut", y=B0)
        A.at(120, col=CYAN)
        B.at(119, y=320, rot=180, col=PINK, a=0)
        B.to(119, 120, "quadOut", a=255, y=260)
        A.to(120, 126, "sineInOut", y=-70)
        B.to(120, 126, "sineInOut", y=70)
        A.to(126, 127, "quartInOut", y=0)
        B.to(126, 127, "quartInOut", y=0, rot=360, a=0)
        B.at(127, rot=0)
        S.bgc(120, (16, 10, 30), 2)
        label(sh, "t_merge", 49, 121, 127, PALE, 230)
        A.to(127, F(255, 2), "expoIn", sx=0.004, sy=3.0, col=WHITE)
        core = sh.tex("glow.png", 0, 0, 10, color=WHITE, alpha=0, z=12, start=127, end=F(257, 2))
        core.at(F(255, 2), "expoIn", w=180, h=180, alpha=255)
        core.at(128, w=60, h=60)
        core.at(F(257, 2), "expoOut", w=900, h=900, alpha=0)
        # ---- notes
        ev = m.vocal(96, 104, 0.3)
        ev = cut(ev, (F(203, 2), F(207, 2)))
        N.place(ev, A, zone=(120, 520), flicks=auto_flicks(ev), seed=21)
        ev = m.vocal(104, 112, 0.3)
        ev = fill(ev, m.drums(104, 112, kick=0.5), F(1, 2))
        N.place(ev, A, zone=(110, 420), flicks=auto_flicks(ev), seed=22)
        ev = cut(m.vocal(112, 120, 0.3), (F(229, 2), F(231, 2) + F(1, 8)), (F(237, 2), F(239, 2) + F(1, 8)))
        N.place(ev, A, zone=(120, 500), seed=23)
        ev = cut(m.vocal(120, 127, 0.3), (F(251, 2), 127))
        N.place(ev, lambda e, i: A if (e["b"] - 120) % 4 < 2 else B, zone=(120, 480), seed=24)
        N.add(A, F(251, 2), 0, HOLD, F(253, 2))

    # ---------------------------------------------------------------- 128-160 CHORUS
    def chorus(self):
        S, sh, A, B, N, m = self.S, self.sh, self.A, self.B, self.N, self.m
        flash(sh, 128, WHITE, 210, 1)
        S.shock(128, 0.5, 0.5, 2, 0.12, 0.9)
        S.chroma(128, 0.03, 2)
        A.to(128, F(257, 2), "expoOut", sx=1.0, sy=1.0)
        A.to(128, 129, "quartInOut", y=B0)
        A.at(128, col=CYAN, spd=10.0)
        B.at(128, y=270, rot=180, col=PINK, spd=10.0)
        B.to(128, 129, "quartOut", a=255)
        S.bgc(128, (30, 12, 62), F(1, 2))
        S.bga(128, 175, 1)  # let the blurred cover glow through
        S.bga(159, 255, 1)
        for k, col in enumerate([(18, 10, 52), (40, 12, 58), (12, 20, 60)]):
            S.bgc(136 + 8 * k, col, 2, "sineInOut")
        ring = sh.tex("ring_cover.png", 0, 40, 60, color=WHITE, alpha=0, z=-20, start=128, end=160)
        ring.at(129, "expoOut", w=860, h=860, alpha=210, rot=-90)
        ring.at(159, "linear", rot=-90 - 360)
        anim(ring, 159, 160, "expoIn", w=1800, h=1800, alpha=0, rot=-90 - 380)
        W_ = 600
        H_ = tex_h("wing_r.png", W_)
        for s_, name in ((-1, "wing_l.png"), (1, "wing_r.png")):
            e = sh.tex(name, 0, 60, 10, color=WHITE, alpha=0, z=-18, start=128, end=160)
            e.at(F(257, 2), "backOut", x=s_ * 380, w=W_, h=H_, alpha=255, rot=-s_ * 12)
            for b in range(129, 159):
                e.at(b, h=H_, rot=-s_ * 12)
                e.at(b + F(1, 2), "quadOut", h=H_ * 0.82, rot=-s_ * 3)
                e.at(b + 1, "quadIn", h=H_, rot=-s_ * 12)
            anim(e, 159, 160, "expoIn", x=s_ * 1000, alpha=0)
        pw = sh.tex("power.png", 0, 40, 10, color=WHITE, alpha=0, z=-16, start=128, end=160)
        pw.at(129, "backOut", w=180, h=180, alpha=255)
        for b in range(129, 160):
            pw.at(b, w=180, h=180, color=(CYAN, PINK, YELLOW, NEON)[b % 4])
            pw.at(b + F(1, 4), "quadOut", w=210, h=210)
            pw.at(b + 1, "quadIn", w=180, h=180)
        for b in (136, 144, 152):
            S.shock(b, 0.5, 0.52, F(3, 2), 0.08, 0.7, p0=0.12)
        for b in range(130, 160, 2):
            S.chroma(b, 0.012, F(1, 2))
        # hearts float up, windows pop at phrase ends
        for k in range(16):
            b = 129 + 2 * k
            x = R.uniform(-700, 700)
            h = sh.tex("heart.png", x, -520, 70, color=WHITE, alpha=230, z=-12, start=b, end=b + 4)
            h.at(b + 4, "linear", y=520, x=x + R.uniform(-120, 120), rot=R.uniform(-40, 40))
        for k, b in enumerate((131, 135, 139, 143, 147, 151, 155)):
            x, y = (-590, 280) if k % 2 == 0 else (590, 280)
            pop(sh, "win_blank.png", x, y, 260, b, b + F(5, 2), WHITE, 255, z=30)
            pop(sh, ("face_laugh.png", "face_smile.png")[k % 2], x, y - 12, 96, b + F(1, 8), b + F(5, 2) - F(1, 16), WHITE, 255, z=31)
        # 144-152: the two lines tilt into a V and back
        bounce(A, range(129, 160), B0)
        bounce(B, range(129, 160), 270, sgn=-1)
        A.to(144, 146, "sineInOut", rot=-7)
        B.to(144, 146, "sineInOut", rot=187)
        A.to(150, 152, "sineInOut", rot=0)
        B.to(150, 152, "sineInOut", rot=180)
        for b in range(152, 160):
            A.at(b, col=(CYAN, YELLOW)[b % 2])
            B.at(b, col=(PINK, VIOLET)[b % 2])
        # ---- notes: "If I can" (bottom) / "if I can" (top) / the rest (bottom)
        ev = m.vocal(128, 160, 0.3)
        ev = fill(ev, m.drums(128, 160, kick=0.4), F(1, 4))
        top = lambda e: 2 <= (e["b"] - 128) % 8 < 3
        N.place(ev, lambda e, i: B if top(e) else A, zone=(120, 520), flicks=auto_flicks(ev), chord_at=[128, 136, 144, 152],
                seed=31)
        A.to(158, 160, "quadIn", spd=10.0)

    # ---------------------------------------------------------------- 160-192 OBJECTS
    def objects(self):
        S, sh, A, B, N, m = self.S, self.sh, self.A, self.B, self.N, self.m
        B.to(160, 161, "quadIn", a=0)
        A.at(160, spd=9.0)
        scenes = [(160, "eggplant.png", "t_egg", (52, 22, 88), (196, 150, 255), (600, 210)),
                  (168, "tomato.png", "t_tom", (78, 14, 24), (255, 150, 150), (-600, 210)),
                  (176, "cat.png", "t_cat", (90, 46, 12), (255, 200, 120), (0, 230))]
        for b0, icon, text, bg, col, (x, y) in scenes:
            S.bgc(b0, bg, F(1, 2))
            A.at(b0, col=col)
            e = sh.tex(icon, x + (900 if x > 0 else -900 if x < 0 else 0), y + (0 if x else 500), 260, color=WHITE,
                       alpha=255, z=-10, start=b0, end=b0 + 8)
            e.at(b0 + 1, "bounceOut", x=x, y=y)
            for b in range(b0 + 1, b0 + 7):
                e.at(b, w=260, h=tex_h(icon, 260), rot=0)
                e.at(b + F(1, 4), "quadOut", w=290, h=tex_h(icon, 260) * 0.9, rot=8 if b % 2 else -8)
                e.at(b + 1, "quadIn", w=260, h=tex_h(icon, 260), rot=0)
            anim(e, b0 + 7, b0 + 8, "backIn", y=y + 600 if x == 0 else y, x=x * 2 if x else 0)
            label(sh, text, 54, b0, b0 + 8, col, 240)
        # the cat purrs: the line trembles
        for b in range(176, 184, 2):
            for j in range(8):
                t = F(b) + F(j, 16)
                A.to(t, t + F(1, 16), "linear", y=B0 + (3 if j % 2 == 0 else -3))
        A.to(184, F(737, 4), "linear", y=B0)
        # the only god: one line, a halo, rays, existence
        S.bgc(184, (40, 34, 14), 1)
        A.at(184, col=GOLD)
        A.to(184, 186, "quadOut", sy=2.2)
        glow = sh.tex("glow.png", 0, 40, 100, color=GOLD, alpha=0, z=-30, start=184, end=192)
        glow.at(186, "quadOut", w=1500, h=1500, alpha=120)
        glow.at(191, alpha=120)
        glow.at(192, "quadIn", alpha=0)
        halo = sh.tex("ring.png", 0, 90, 60, 18, color=GOLD, alpha=0, z=-12, start=184, end=192)
        halo.at(185, "expoOut", w=440, h=130, alpha=255)
        for b in range(185, 191):
            halo.at(b, y=90)
            halo.at(b + F(1, 2), "sineInOut", y=108)
            halo.at(b + 1, "sineInOut", y=90)
        anim(halo, 191, 192, "expoIn", w=0, h=0, alpha=0)
        for k in range(12):
            a0 = k * 30
            ray = sh.line(0, 90, a0, 10, 6, GOLD, 0, z=-31, start=184, end=192)
            ray.at(186, "quadOut", w=820, alpha=90)
            ray.at(191, "linear", rot=a0 + 60)
            anim(ray, 191, 192, "quadIn", alpha=0, w=1000)
        label(sh, "t_exist", 56, 184, 192, GOLD, 255)
        A.to(F(383, 2), 192, "quadIn", sy=1.0)
        # ---- notes
        ev = m.vocal(160, 192, 0.3)
        ev = fill(ev, m.drums(160, 192, kick=0.5), F(1, 2))
        purr = [e for e in ev if 176 <= e["b"] < 184]
        rest = [e for e in ev if not 176 <= e["b"] < 184]
        N.place([e for e in rest if e["b"] < 176], A, zone=(110, 520), flicks=auto_flicks(rest), chord_at=[160, 168], seed=41)
        N.place(purr, A, zone=(110, 460), seed=42, drag_runs=True)
        N.place([e for e in rest if e["b"] >= 184], A, zone=(90, 420), flicks=auto_flicks(rest), seed=43)

    # ---------------------------------------------------------------- 192-224 SWITCH
    def switch(self):
        S, sh, A, B, N, m = self.S, self.sh, self.A, self.B, self.N, self.m
        Y1, Y2 = -150.0, -330.0
        A.at(192, col=PINK, rot=0)
        A.to(192, 193, "quadOut", y=Y1)
        B.at(192, y=Y2 - 60, rot=0, col=SKY, a=0, spd=9.0)
        B.to(192, 193, "quadOut", y=Y2, a=255)
        S.bgc(192, (24, 16, 40), 1)
        label(sh, "t_fm", 61, 192, 200, PALE, 240)
        # F <-> M: the lines trade places every two beats
        up = True
        for b in range(193, 199, 2):
            A.to(b, b + 1, "sineInOut", y=Y2 if up else Y1)
            B.to(b, b + 1, "sineInOut", y=Y1 if up else Y2)
            up = not up
        A.to(199, 200, "sineInOut", y=Y1)
        B.to(199, 200, "sineInOut", y=Y2)
        # AM <-> PM: day and night every two beats, a sun / moon arcs over
        label(sh, "t_ampm", 61, 200, 208, PALE, 240)
        for k, b in enumerate(range(200, 208, 2)):
            S.bgc(b, (70, 110, 170) if k % 2 == 0 else (8, 10, 34), F(1, 2), "sineInOut")
            body = sh.tex("disc.png", -760, 0, 120, color=YELLOW if k % 2 == 0 else PALE, alpha=255, z=-30, start=b, end=b + 2)
            for j in range(1, 9):
                t = F(b) + F(j, 4)
                a = math.pi * j / 8
                body.at(t, "linear", x=-760 * math.cos(a), y=-40 + 380 * math.sin(a))
        # role ^= 1: only one line is "on" each bar
        label(sh, "t_role", 54, 208, 216, PALE, 240)
        S.bgc(208, (20, 12, 34), 1)
        for b in range(208, 216, 4):
            on, off = (A, B) if (b // 4) % 2 == 0 else (B, A)
            on.at(b, a=255)
            off.at(b, a=70)
        # 10 REM: dream (216-224)
        S.bgc(216, (30, 16, 52), 2)
        label(sh, "t_rem", 59, 216, 222, VIOLET, 230)
        A.at(216, a=255)
        B.at(216, a=255)
        A.to(216, 220, "sineInOut", y=-200, rot=-4)
        B.to(216, 220, "sineInOut", y=-300, rot=5, a=150)
        S.fxk("radialBlur", 216, 222, {"power": [(216, 0.0, "linear"), (218, 0.012, "sineInOut"), (222, 0.0, "sineInOut")]},
              centerX=0.5, centerY=0.5, sampleCount=6)
        S.fx("vignette", 216, 224, extend=0.35, radius=12.0)
        A.to(220, 222, "sineInOut", y=B0, rot=0)
        B.to(220, 222, "quadIn", a=0, y=-420, rot=0)
        # the dialog: EXECUTE ME? -- the cursor clicks YES on the last beat
        win = pop(sh, "win_exec.png", 0, 90, 600, 221, 224, WHITE, 255, z=40)
        sc = 600 / 128
        yes_x, yes_y = -300 + 34 * sc, 90 + (36 - 59) * sc
        cur = sh.tex("cursor.png", 520, -200, 70, color=WHITE, alpha=0, z=42, start=F(443, 2), end=224)
        cur.at(222, alpha=255)
        cur.at(223, "quartInOut", x=yes_x + 26, y=yes_y - 30)
        anim(cur, 223, F(447, 2), "quadIn", w=58, h=tex_h("cursor.png", 58))
        cur.at(F(895, 4), "quadOut", w=70, h=tex_h("cursor.png", 70))
        flash(sh, F(447, 2), RED, 120, F(1, 2), z=43)
        A.to(222, 224, "quadIn", spd=12.0)
        S.chroma(223, 0.02, 1)
        # ---- notes
        ev = m.vocal(192, 216, 0.3)
        ev = fill(ev, m.drums(192, 216, kick=0.5), F(1, 2))
        role = lambda e: A if ((int(e["b"]) // 4) % 2 == 0) else B
        N.place([e for e in ev if e["b"] < 200], lambda e, i: A if i % 2 == 0 else B, zone=(110, 500),
                flicks=auto_flicks(ev), chord_at=[192], seed=51)
        N.place([e for e in ev if 200 <= e["b"] < 208], A, zone=(110, 500), flicks=auto_flicks(ev), seed=52)
        N.place([e for e in ev if e["b"] >= 208], lambda e, i: role(e), zone=(110, 500), flicks=auto_flicks(ev), seed=53)
        ev = m.vocal(216, 223, 0.3)
        N.place(cut(ev, (F(443, 2), 223)), A, zone=(110, 420), seed=54)
        N.add(A, F(447, 2), -200, FLICK)
        N.add(A, F(447, 2), 200, FLICK)

    # ---------------------------------------------------------------- 224-288 EXECUTE
    def execute(self):
        S, sh, A, B, N, m = self.S, self.sh, self.A, self.B, self.N, self.m
        S.shock(224, 0.5, 0.45, 2, 0.12, 1.0)
        flash(sh, 224, RED, 200, 1)
        A.at(224, col=RED, spd=10.5, sy=1.0)
        S.hud_to(224, 225, "quadOut", col=(255, 120, 130))
        for b in range(224, 240):
            S.bgc(b, (70, 6, 16) if b % 2 == 0 else (16, 4, 8), 0)
            S.bgc(b, (34, 4, 10) if b % 2 == 0 else (10, 2, 6), F(3, 4), "quadOut")
        blink = sh.tex("t_executing.png", LABEL_X + 200, LABEL_Y, 400, color=RED, alpha=255, z=20, start=224, end=240)
        for b in range(224, 240):
            blink.at(b, alpha=255)
            blink.at(b + F(1, 2), alpha=255)
            blink.at(b + F(1, 2), alpha=40)
            blink.at(b + 1, alpha=40)
        for b in range(224, 240, 4):
            S.chroma(b, 0.02, 1)
            S.shake(b, 14, F(1, 2), 6, seed=b)
        # 240-256: the cage -- while (true) { }
        S.bgc(240, (20, 6, 12), 1)
        label(sh, "t_loop", 56, 240, 256, PALE, 255)
        for k in range(9):
            x = -720 + 180 * k
            bar = sh.tex("white.png", x, 1000, 12, 900, color=PALE, alpha=200, z=13, start=240 + F(k, 8), end=258)
            bar.at(241 + F(k, 8), "bounceOut", y=0)
            bar.at(256, y=0)
            bar.at(258, "backIn", y=-1000)
        A.to(240, 242, "sineInOut", y=-200)
        A.to(254, 256, "sineInOut", y=B0)
        # 256-288: call and response again, glitches creeping in
        B.at(256, y=270, rot=180, col=PALE, a=0, spd=10.5)
        B.to(256, 257, "quadOut", a=255)
        S.bgc(256, (12, 4, 10), 1)
        for b in range(256, 288, 4):
            S.glitch(b, b + F(1, 4), 0.04 + (b - 256) / 32 * 0.04, 1.0, 10)
        for k, b in enumerate(range(272, 288)):
            x, y = R.uniform(-560, 560), R.uniform(-40, 320)
            pop(sh, "win_error.png", x, y, 300, b, min(b + 3, 288), WHITE, 255, z=32 + k % 3, rot=R.uniform(-6, 6))
        S.hud_to(272, 280, "linear", col=(255, 60, 70))
        for b in range(280, 288):
            S.hud_to(b, b + F(1, 4), "linear", x=R.uniform(-30, 30), y=R.uniform(-16, 16))
        S.hud_to(288, 288, x=0, y=0)
        # ---- notes
        ev = m.vocal(224, 240, 0.3)
        ev = fill(ev, m.drums(224, 240, kick=0.4), F(1, 4))
        N.place(ev, A, zone=(120, 540), flicks=auto_flicks(ev), chord_at=[224, 232], seed=61)
        ev = m.vocal(240, 256, 0.3)
        ev = fill(ev, m.drums(240, 256, kick=0.5), F(1, 2))
        N.place(ev, A, zone=(110, 520), flicks=auto_flicks(ev), chord_at=[240, 248], seed=62)
        ev = m.vocal(256, 288, 0.3)
        ev = fill(ev, m.drums(256, 288, kick=0.4), F(1, 4))
        top = lambda e: (e["b"] - 256) % 8 >= 4
        N.place(ev, lambda e, i: B if top(e) else A, zone=(120, 520), flicks=auto_flicks(ev), chord_at=[256, 264, 272, 280],
                seed=63)
        B.to(F(575, 2), 288, "quadIn", a=0)

    # ---------------------------------------------------------------- 288-320 ERROR
    def error(self):
        S, sh, A, B, N, m = self.S, self.sh, self.A, self.B, self.N, self.m
        S.shock(288, 0.5, 0.5, 2, 0.14, 1.0)
        flash(sh, 288, RED, 230, 1)
        e = sh.tex("t_error.png", 0, 60, 900, color=RED, alpha=255, z=45, start=288, end=290)
        e.at(F(577, 2), w=900, h=tex_h("t_error.png", 900))
        e.at(290, "expoIn", w=2400, h=tex_h("t_error.png", 2400), alpha=0)
        S.glitch(288, 304, 0.035, 0.6, 7)
        S.fx("chromatic", 288, 304, sampleCount=3, power=0.006)
        for b in range(288, 304):
            S.bgc(b, (60, 0, 10) if b % 2 == 0 else (6, 0, 4), 0)
        # cascade of error windows
        for k in range(14):
            b = 288 + F(k, 2) + 1
            pop(sh, "win_error.png", -520 + 70 * k, 330 - 34 * k, 320, b, 297, WHITE, 255, z=30 + k, t_in=F(1, 8))
        msgs = ["t_segv", "t_stack", "t_null", "t_dead", "t_panic", "t_segv", "t_null", "t_stack"]
        for k, name in enumerate(msgs):
            b = 296 + k
            txt(sh, name, R.uniform(-240, 240), R.uniform(-60, 360), 58, b, b + F(3, 4), (PALE, RED, YELLOW)[k % 3], 255,
                z=33, fade=0)
        # the line teleports between beats
        pos = [(0, B0, 0), (-220, -180, -12), (240, -280, 10), (-120, -120, 6), (180, -220, -8), (0, -300, 0),
               (-260, -240, 12), (200, -160, -10)]
        for k, b in enumerate(range(289, 303, 2)):
            x, y, r_ = pos[(k + 1) % len(pos)]
            A.at(F(b) + F(1, 4), x=x, y=y, rot=r_, col=(RED, PALE)[k % 2])
        A.at(F(1213, 4), x=0, y=B0, rot=0, col=WHITE)
        S.hud_to(288, 288, col=(255, 60, 70))
        for b in range(288, 304, 1):
            S.hud_to(b, b + F(1, 2), "linear", x=R.uniform(-40, 40), y=R.uniform(-20, 20), rot=R.uniform(-6, 6))
        # 304-312: crash screen
        S.bgc(304, (0, 0, 168), 0)
        S.hud_to(304, 304, a=0, x=0, y=0, rot=0)
        txt(sh, "t_fatal", 0, 300, 85, 304, 312, WHITE, 255, z=20, fade=0)
        txt(sh, "t_fatal_msg", 0, 180, 56, F(609, 2), 312, WHITE, 255, z=20, fade=0)
        txt(sh, "t_dead", 0, 110, 49, 305, 312, WHITE, 200, z=20, fade=0)
        A.at(304, col=WHITE)
        # 312-320: reboot
        S.bgc(312, INK, 0)
        e = sh.tex("white.png", -700, 300, 26, 44, color=TERM, alpha=255, z=20, start=312, end=316)
        for j in range(8):
            e.at(F(312) + F(j, 2), alpha=255)
            e.at(F(312) + F(j, 2) + F(1, 4), alpha=255)
            e.at(F(312) + F(j, 2) + F(1, 4), alpha=0)
            e.at(F(312) + F(j, 2) + F(1, 2), alpha=0)
        pop(sh, "win_load.png", 0, 120, 520, 314, 319, WHITE, 255, z=30)
        sc = 520 / 128
        x_left = -260 + 9 * sc
        bar = sh.tex("white.png", x_left, 120 - 8 * sc, 0.1, 9 * sc, color=TERM, z=31, start=315, end=F(1275, 4))
        bar.at(318, "quartInOut", x=x_left + 110 * sc / 2, w=110 * sc)
        S.hud_to(316, 318, "quadOut", a=255, col=(200, 200, 200))
        A.at(312, col=TERM)
        # ---- notes: the beat, glitchy 16ths on the fills
        d = m.drums(288, 320, kick=0.45, snare=0.6)
        d = [e for e in d if (e["b"] >= 304 or e["b"] % 1 == 0) and not (294 <= e["b"] < 295 or 302 <= e["b"] < 303)]
        N.place([e for e in d if e["b"] < 304], A, zone=(160, 500), seed=71,
                xfun=lambda e, h, i: (-1 if h == 0 else 1) * (200 + 220 * ((i * 7) % 3) / 2))
        N.place([e for e in d if 304 <= e["b"] < 312], A, zone=(200, 460), seed=72)
        N.place([e for e in d if e["b"] >= 312], A, zone=(160, 460), seed=73)
        for b in (294, 302):
            for j in range(4):
                N.add(A, F(b) + F(j, 4), (-1) ** (b // 8) * (420 - 140 * j), TAP if j == 0 else DRAG)

    # ---------------------------------------------------------------- 320-352 DEADLOCK
    def deadlock(self):
        S, sh, A, N, m = self.S, self.sh, self.A, self.N, self.m
        S.bgc(320, (26, 26, 30), 2)
        S.hud_to(320, 322, "quadOut", col=WHITE)
        A.at(320, col=WHITE, spd=8.5)
        S.fxk("grayscale", 320, 352, {"factor": [(320, 0.0, "linear"), (322, 0.9, "quadOut"), (344, 0.9, "linear"),
                                                 (352, 0.0, "quadIn")]})
        panel(sh, -750, 300, -205, 380, 320, 344, INK, 220, z=18)
        typed(sh, "t_deadlock", 25, -730, 340, 44, F(641, 2), 3, 344, PALE, INK, z=20)
        # memory fragments: tiles of the cover drifting
        tw, th = size("tile_00.jpg")
        for k in range(10):
            r_, c_ = R.randrange(4), R.randrange(6)
            name = f"tile_{r_}{c_}.jpg"
            b = 321 + 2 * k
            x, y = R.uniform(-650, 650), R.uniform(-150, 260)
            t = sh.tex(name, x, y - 120, tw * ML.TEXK * 0.8, color=WHITE, alpha=0, z=-40, start=b, end=b + 10, rot=R.uniform(-15, 15))
            t.at(b + 2, "quadOut", alpha=110)
            t.at(b + 8, alpha=110)
            t.at(b + 10, "quadIn", alpha=0, y=y + 160, rot=R.uniform(-30, 30))
        heart = sh.tex("heart.png", 0, 70, 160, color=WHITE, alpha=0, z=-8, start=320, end=352)
        heart.at(322, "quadOut", alpha=230)
        for b in range(322, 344):
            heart.at(b, w=160, h=tex_h("heart.png", 160))
            heart.at(b + F(1, 8), "quadOut", w=196, h=tex_h("heart.png", 196))
            heart.at(b + F(1, 2), "quadIn", w=160, h=tex_h("heart.png", 160))
        heart.at(348, w=160, h=tex_h("heart.png", 160), color=WHITE)
        heart.at(350, "quadIn", w=120, h=tex_h("heart.png", 120), color=(120, 120, 130))
        heart.at(F(703, 2), "expoIn", w=4, h=4, alpha=0)
        # build: the line speeds up and the world folds into the centre
        A.to(344, 352, "quadIn", spd=11.0)
        A.to(350, F(703, 2), "expoIn", sx=0.01, y=0)
        S.sway(344, 350, 4, 2)
        core = sh.tex("glow.png", 0, 0, 10, color=WHITE, alpha=0, z=12, start=350, end=F(705, 2))
        core.at(F(703, 2), "expoIn", w=200, h=200, alpha=255)
        core.at(352, w=80, h=80)
        core.at(F(705, 2), "expoOut", w=1600, h=1600, alpha=0)
        # ---- notes: the bridge melody, gentle
        ev = cut(m.vocal(320, 350, 0.5, min_gap=F(1, 2)), (F(699, 2), 352))
        N.place(ev, A, zone=(110, 480), flicks=auto_flicks(ev), seed=81)

    # ---------------------------------------------------------------- 352-416 FINAL
    def final(self):
        S, sh, A, B, N, m = self.S, self.sh, self.A, self.B, self.N, self.m
        flash(sh, 352, WHITE, 255, F(3, 2))
        S.shock(352, 0.5, 0.5, 2, 0.14, 1.0)
        S.chroma(352, 0.035, 2)
        A.at(352, x=0, y=0, col=CYAN, spd=10.5)
        A.to(352, F(705, 2), "expoOut", sx=1.0)
        A.to(352, 354, "quartInOut", y=B0)
        S.bgc(352, (10, 10, 22), F(1, 2))
        # the cover assembles from its tiles (352-354), then stays dimmed behind the lines
        tw, th = size("tile_00.jpg")
        wphys, hphys = tw * ML.TEXK, th * ML.TEXK
        for r_ in range(4):
            for c_ in range(6):
                x = -800 + wphys * (c_ + 0.5)
                y = 450 - hphys * (r_ + 0.5)
                b = 352 + F((r_ * 6 + c_) * 3 % 24, 16)
                sx_, sy_ = R.uniform(-1300, 1300), R.choice((-1, 1)) * R.uniform(600, 900)
                t = sh.tex(f"tile_{r_}{c_}.jpg", sx_, sy_, wphys * 0.4, rot=R.uniform(-120, 120), color=WHITE, alpha=0,
                           z=-60, start=b, end=354 + F(1, 8))
                t.at(b + F(1, 8), alpha=255)
                t.at(354, "expoOut", x=x, y=y, w=wphys + 1, h=hphys + 1, rot=0)
        cov = sh.tex("cover_full.jpg", 0, 0, 1600, 900, color=WHITE, alpha=255, z=-61, start=354, end=386)
        cov.at(356, "quadOut", alpha=82)
        cov.at(383, alpha=82)
        for y_ in (B0, 270):
            band = sh.tex("white.png", 0, y_, 1800, 1, color=INK, alpha=170, z=-55, start=355, end=384)
            band.at(356, "expoOut", h=74)
            band.at(F(767, 2), h=74)
            band.at(384, "quadIn", h=1, alpha=0)
        A.to(355, 356, "quadOut", sy=1.6)
        A.to(383, 384, "quadIn", sy=1.0)
        cov.at(384, "quadIn", alpha=255)
        cov.at(F(769, 2), alpha=255)
        anim(cov, F(769, 2), 386, "expoIn", w=2600, h=1460, alpha=0, rot=8)
        for b in (360, 368, 376):
            S.shock(b, 0.5, 0.5, F(3, 2), 0.08, 0.7, p0=0.12)
        for b in range(353, 384, 2):
            S.chroma(b, 0.01, F(1, 2))
        B.at(354, y=270, rot=180, col=PINK, a=0, spd=10.5)
        B.to(354, 355, "quadOut", a=255)
        B.to(355, 356, "quadOut", sy=1.6)
        B.to(383, 384, "quadIn", sy=1.0)
        for b in range(356, 384):
            A.at(b, col=hsv((b - 356) / 16, 0.65, 1.0))
            B.at(b, col=hsv((b - 356) / 16 + 0.5, 0.6, 1.0))
        # 384: the title over the full cover, then it shatters
        S.glitch(384, 385, 0.08, 1.0, 14)
        panel(sh, -520, -10, 520, 130, 384, F(771, 2), INK, 200, z=40)
        t = sh.tex("t_title.png", 0, 60, 960, color=YELLOW, alpha=0, z=41, start=384, end=F(771, 2))
        t.at(F(1537, 4), "quadOut", alpha=255)
        t.at(385, alpha=255)
        t.at(F(771, 2), "expoIn", w=1800, h=tex_h("t_title.png", 1800), alpha=0)
        flash(sh, 386, WHITE, 230, 1)
        S.shock(386, 0.5, 0.5, 2, 0.14, 1.0)
        # 386-416: everything at once
        S.bgc(386, (24, 10, 54), F(1, 2))
        S.bga(386, 175, 1)
        S.bga(415, 255, 1)
        ring = sh.tex("ring_cover.png", 0, 40, 60, color=WHITE, alpha=0, z=-20, start=386, end=416)
        ring.at(387, "expoOut", w=900, h=900, alpha=220, rot=0)
        ring.at(414, "linear", rot=540)
        anim(ring, 414, 416, "expoIn", w=2000, h=2000, alpha=0, rot=600)
        W_ = 620
        H_ = tex_h("wing_r.png", W_)
        for s_, name in ((-1, "wing_l.png"), (1, "wing_r.png")):
            e = sh.tex(name, 0, 60, 10, color=WHITE, alpha=0, z=-18, start=386, end=416)
            e.at(387, "backOut", x=s_ * 400, w=W_, h=H_, alpha=255, rot=-s_ * 12)
            for b in range(387, 415):
                e.at(b, h=H_, rot=-s_ * 12)
                e.at(b + F(1, 2), "quadOut", h=H_ * 0.8, rot=-s_ * 2)
                e.at(b + 1, "quadIn", h=H_, rot=-s_ * 12)
            anim(e, 415, 416, "expoIn", x=s_ * 1100, alpha=0)
        pw = sh.tex("power.png", 0, 40, 10, color=WHITE, alpha=0, z=-16, start=386, end=416)
        pw.at(387, "backOut", w=190, h=190, alpha=255)
        for b in range(387, 416):
            pw.at(b, w=190, h=190, color=hsv(b / 8, 0.5, 1))
            pw.at(b + F(1, 4), "quadOut", w=226, h=226)
            pw.at(b + 1, "quadIn", w=190, h=190)
        for b in range(396, 416, 8):
            S.shock(b, 0.5, 0.52, F(3, 2), 0.08, 0.7, p0=0.12)
        for k in range(14):
            b = 387 + 2 * k
            x, y = R.choice(((-600, 290), (600, 290), (-600, 20), (600, 20)))
            pop(sh, "win_blank.png", x, y, 250, b, b + F(3, 2), WHITE, 255, z=30)
            pop(sh, R.choice(("face_laugh.png", "face_smile.png", "face_angry.png")), x, y - 12, 92, b + F(1, 8),
                b + F(3, 2) - F(1, 16), WHITE, 255, z=31)
        # two decorative diagonal lines turning behind everything
        for k, s_ in enumerate((-1, 1)):
            d = JL(self.c, f"diag{k}", z=-15, father=self.cam, x=0, y=40, rot=s_ * 35, alpha=0, speed=0.0,
                   color=(VIOLET, NEON)[k])
            d.to(386, 388, "quadOut", a=150)
            d.to(388, 414, "linear", rot=s_ * 35 + s_ * 360)
            d.to(414, 416, "quadIn", a=0)
        for b in range(386, 416):
            A.at(b, col=hsv((b - 386) / 12, 0.6, 1.0))
            B.at(b, col=hsv((b - 386) / 12 + 0.5, 0.55, 1.0))
        S.sway(392, 412, 5, 4)
        bounce(A, range(387, 415), B0, 10)
        bounce(B, range(387, 415), 270, 10, sgn=-1)
        A.to(412, 416, "quadIn", spd=12.0)
        B.to(412, 416, "quadIn", spd=12.0)
        B.to(F(831, 2), 416, "quadIn", a=0)
        # ---- notes: the melody is long here, so the beat carries the rest
        ev = m.vocal(352, 384, 0.3)
        ev = fill(ev, m.drums(352, 384, kick=0.4), F(1, 4))
        ev = fill(ev, ev_at([F(b) + F(1, 2) for b in range(354, 383)], 0.6, "y"), F(1, 4))
        ev = cut(ev, (352, F(1409, 4)))
        top = lambda e: (e["b"] - 352) % 8 >= 4
        N.place(ev, lambda e, i: B if top(e) else A, zone=(120, 540), flicks=auto_flicks(ev), chord_at=[360, 368, 376],
                seed=91)
        ev = m.vocal(386, 416, 0.3)
        ev = fill(ev, m.drums(386, 416, kick=0.4), F(1, 4))
        ev = fill(ev, ev_at([F(b) + F(1, 2) for b in range(386, 415)], 0.6, "y"), F(1, 4))
        for b in (391, 399, 407):  # 16th runs into each phrase
            ev = [e for e in ev if not b + F(1, 2) <= e["b"] < b + 1]
            ev += [{"b": F(b) + F(1, 2) + F(j, 4), "w": 0.8, "p": 60.0 + 4 * j, "sus": F(0), "src": "h"} for j in range(2)]
        ev.sort(key=lambda e: e["b"])
        N.place(ev, lambda e, i: B if (e["b"] - 386) % 8 >= 4 else A, zone=(120, 540), flicks=auto_flicks(ev),
                chord_at=[392, 400, 408], seed=92)
        N.add(A, 384, -300, FLICK)
        N.add(A, 384, 300, FLICK)

    # ---------------------------------------------------------------- 416-458 SHUTDOWN
    def shutdown(self):
        S, sh, A, N, m = self.S, self.sh, self.A, self.N, self.m
        flash(sh, 416, WHITE, 200, 1)
        A.at(416, col=WHITE, spd=9.0, rot=0)
        S.bgc(416, NIGHT, 1)
        S.bgc(424, INK, 4)
        panel(sh, -760, 270, -300, 380, F(833, 2), 444, INK, 230, z=18)
        typed(sh, "t_shutdown", 12, -735, 325, 52, 417, F(3, 2), 444, TERM, INK)
        # objects deleted one per bar
        objs = [("ring_cover.png", 0, 60, 520, 416, 424), ("wing_l.png", -330, 80, 420, 416, 428),
                ("wing_r.png", 330, 80, 420, 416, 428), ("power.png", 0, 60, 150, 416, 432)]
        for name, x, y, w, b0, b1 in objs:
            e = sh.tex(name, x, y, w, color=WHITE, alpha=0, z=-18, start=b0, end=b1)
            e.at(417, "quadOut", alpha=200)
            e.at(b1 - 1, alpha=200, x=x, y=y)
            anim(e, b1 - 1, b1 - F(1, 2), "quadOut", x=x * 1.05, y=y + 20, color=RED)
            anim(e, b1 - F(1, 2), b1, "expoIn", w=w * 0.02, h=tex_h(name, w) * 1.2, alpha=0)
        # uninstall: the bar runs back to zero
        pop(sh, "win_load.png", 0, 120, 520, 432, 440, WHITE, 255, z=30)
        sc = 520 / 128
        x_left = -260 + 9 * sc
        bar = sh.tex("white.png", x_left + 110 * sc / 2, 120 - 8 * sc, 110 * sc, 9 * sc, color=RED, z=31, start=F(865, 2), end=439)
        for k in range(1, 9):
            b = F(865, 2) + F(k, 2) * F(3, 4)
            f = 1 - k / 8
            bar.at(b, "quadOut", x=x_left + 110 * sc * f / 2, w=max(0.1, 110 * sc * f))
        S.hud_out(436, 440)
        # the last picture, then a CRT power-off
        cov = sh.tex("cover_full.jpg", 0, 0, 1600, 900, color=WHITE, alpha=0, z=-30, start=440, end=449)
        cov.at(441, "quadOut", alpha=255)
        cov.at(446, alpha=255, h=900, w=1600)
        anim(cov, 446, F(893, 2), "expoIn", h=5, w=1600, color=(230, 240, 255))
        cov.at(F(895, 2), "expoIn", h=4, w=2)
        cov.at(449, "quadIn", alpha=0)
        dot = sh.tex("glow.png", 0, 0, 2, color=WHITE, alpha=0, z=-29, start=F(895, 2), end=450)
        dot.at(448, "quadOut", w=70, h=70, alpha=255)
        dot.at(450, "quadIn", w=8, h=8, alpha=0)
        A.to(444, 446, "quadOut", y=0, a=120)
        A.to(446, F(893, 2), "expoIn", sx=1.0, a=255)
        A.to(F(893, 2), F(895, 2), "expoIn", sx=0.0)
        A.at(F(895, 2), a=0)
        S.fx("vignette", 440, 449, extend=0.3, radius=14.0)
        S.fx("chromatic", 446, 448, sampleCount=3, power=0.008)
        txt(sh, "t_bye", 0, 0, 49, 450, 457, PALE, 255, z=20, fade=F(1, 2))
        # ---- notes: the outro beat thins out
        d = m.drums(416, 444, kick=0.45)
        d = fill(d, [e for e in m.synths(416, 444, 0.6, 2) if e["b"] % 1 == F(1, 2)], F(1, 2))
        d = [e for e in d if not (e["b"] >= 432 and e["b"] % 2 == 1) and e["b"] < 440]
        N.place(d, A, zone=(160, 480), seed=101)
        N.add(A, 440, 0, HOLD, 444)

    # ----------------------------------------------------------------
    def build(self):
        self.boot()
        self.run()
        self.geometry()
        self.current()
        self.chorus()
        self.objects()
        self.switch()
        self.execute()
        self.error()
        self.deadlock()
        self.final()
        self.shutdown()
        self.S.eng.bake()
        return self.N.write()


_SIZES = {}


def ensure_sizes():
    if not _SIZES:
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            _SIZES.update(wem_assets.save_all(d, os.environ.get("WEM_COVER")))
    ML.register_textures(_SIZES)


def make():
    ensure_sizes()
    c = Chart(OFFSET_MS, dict(INFO, id="claude-world-execute-me"), bpm=BPM, compact=True)
    w = World(c)
    n = w.build()
    print(f"notes: {n}, lines: {len(c.lines)}, effects: {len(c.effects)}")
    return c, INFO


def assets(out):
    _SIZES.update(wem_assets.save_all(out, os.environ.get("WEM_COVER")))
    ML.register_textures(_SIZES)
