"""The scenes of the Just Love showcase, in order. Each function writes one stretch of the song.

Conventions: beats are chart beats (bar k = beat 3 + 4k, B(k, beat)); positions are physical units
(x -800..800, y -450..450, +y up); X is the shared context built in just_love.build().
"""
import math

from chartlib import DRAG, EPSB, FLICK, HOLD, TAP
from jl_core import (B, BLUSH, DEEP, F, GOLD, ICE, INDIGO, LAVENDER, LINE, MINT, NIGHT, PINK, PX, ROSE, SKY, SNOW, TEXK,
                     VIOLET, WHITE, Rig, mix)
from madlib import TL
from just_love import TEX, burst, caption, glow, heart_up, ring, ripple, scroll, snow, sparkle, th


# ------------------------------------------------------------------ rhythm helpers
def onsets(X, b0, b1, grid=4):
    """per-step strengths, normalised inside [b0, b1): {beat: dict(K, S, M, F, pos)}"""
    m = X.m
    f = {k: m.scale(k, b0, b1) for k in ("kick", "snare", "harm", "mid", "full", "hat")}
    out = {}
    for i in range(int(math.ceil(float(b0) * grid)), int(math.ceil(float(b1) * grid))):
        b = F(i, grid)
        h = f["harm"](b)
        near = [f["harm"](b + F(d, 4)) for d in (-2, -1, 1, 2)]
        peak = h / (sorted(near)[1] + 0.15)  # contrast against the neighbourhood
        out[b] = {"K": f["kick"](b), "S": f["snare"](b), "H": h, "P": peak, "M": f["mid"](b), "F": f["full"](b),
                  "T": f["hat"](b), "pos": (b - 3) % 4}
    return out


def pitch_map(X, b0, b1, span):
    """melody pitch -> x in [-span, span], scaled to the range the section actually uses"""
    ps = [p for p in (X.m.pitch(F(i, 4)) for i in range(int(float(b0) * 4), int(float(b1) * 4))) if p]
    if len(ps) < 8:
        return lambda b: None
    ps.sort()
    lo, hi = ps[len(ps) // 12], ps[-1 - len(ps) // 12]
    mid, half = (lo + hi) / 2, max(3.0, (hi - lo) / 2)

    def f(b):
        p = X.m.pitch(b)
        if p is None:
            return None
        return max(-1.0, min(1.0, (p - mid) / half)) * span
    return f


def pulses(X, beats, zoom=0.02, split=0.0, shake=0.0, dur=1):
    for b in beats:
        if zoom:
            X.L.punch(b, zoom, dur)
        if split:
            X.L.split.pulse(b, split, F(3, 4), "quadOut")
        if shake:
            X.G.shake(b, shake, shake * 0.03, 0.35)


# ================================================================== 0-35: the illustration, the title
def intro(X):
    G, E, L, m = X.G, X.E, X.L, X.m
    G.bgc(0, NIGHT, 255)
    G.vig(0, NIGHT, 150)
    G.hud_alpha(0, 0)
    s = E.shot(0, 35)
    # the picture arrives with the first voice (the pick-up on beat 2) and slowly opens up
    pic = s.tex("cover_wide.png", -50, -150, 2050, None, 0.0, WHITE, 0, -60, 2, 35)
    pic.at(3, "sineOut", alpha=255)
    pic.at(19, "sineInOut", x=0, y=0, w=1650, h=th("cover_wide.png", 1650))
    pic.at(35, "sineInOut", w=1720, h=th("cover_wide.png", 1720))
    G.bgc(2, NIGHT, 205, 2)
    snow(s, 0.55, 0.6, 5.0, start=2, a_in=3)
    L.frost.ramp(2, 10, 0.0, 0.35, "sineOut")
    # every chopped phrase nudges the camera; the hard stops in the audio black the picture out
    for b in m.hits("full", 3, 35, 0.55, grid=4, gap=F(1, 2)):
        L.punch(b, 0.010, F(3, 4))
        G.flash(b, SNOW, 22, F(1, 2))
    for g0, g1 in ((F(33, 4), F(17, 2)), (F(41, 4), F(21, 2)), (F(159, 8), 20), (F(221, 8), F(223, 8))):
        G.black(g0, g1, 255)
        L.punch(g1, 0.03, 1)
        G.flash(g1, SNOW, 70, F(3, 4))
        L.split.pulse(g1, 0.012, 1)
    # the title, as a lower third over the last four bars
    band = s.tex("band.png", 0, -235, 1800, 430, 0.0, NIGHT, 0, -40, 17, 35)
    band.at(20, "sineOut", alpha=252).at(33, "linear", alpha=252).at(35, "sineIn", alpha=0)
    w = 500
    t = s.tex("t_title.png", 0, -300, w, None, 0.0, SNOW, 0, 52, 19, 35)
    t.at(21, "expoOut", alpha=255, y=-288).at(33, "linear", alpha=255).at(35, "sineIn", alpha=0, y=-280)
    rule = s.tex("white.png", 0, -362, 0, 2.0, 0.0, ICE, 220, 52, 20, 35)
    rule.at(23, "expoOut", w=520).at(33, "linear", alpha=220).at(35, "sineIn", alpha=0)
    mask = s.tex("white.png", 0, -362, 0, 14, 0.0, NIGHT, 255, 53, 20, 35)
    mask.at(22, "backOut", w=52).at(33, "linear", alpha=255).at(35, "sineIn", alpha=0)
    fl = s.tex("flake_s.png", 0, -362, 0, 0, 0.0, SNOW, 255, 54, 20, 35)
    fl.at(22, "backOut", w=34, h=34).at(33, "linear", alpha=255, rot=120).at(35, "sineIn", alpha=0)
    wa, wf = 104, 240
    ta = s.tex("t_artist.png", -wf / 2 - 16, -400, wa, None, 0.0, ICE, 0, 52, 21, 35)
    ta.at(23, "sineOut", alpha=230).at(33, "linear", alpha=230).at(35, "sineIn", alpha=0)
    tf = s.tex("t_feat.png", wa / 2 + 16, -400, wf, None, 0.0, ICE, 0, 52, 21, 35)
    tf.at(23, "sineOut", alpha=230).at(33, "linear", alpha=230).at(35, "sineIn", alpha=0)
    for k, b_ in enumerate((19, 23, 27, 31)):  # a glint on each bar while the title is up
        sparkle(s, b_, (-300, 310, -220, 240)[k], (-250, -262, -330, -322)[k], 100, SNOW, 2, 55)


# ================================================================== 35-67: the picture dissolves, the line is drawn
def build_up(X):
    G, E, L, m, N, A = X.G, X.E, X.L, X.m, X.N, X.A
    s = E.shot(35, 67)
    G.flash(35, ICE, 120, 2)
    G.bgc(35, INDIGO, 225, 12)
    G.vig(35, NIGHT, 215, 8)
    G.hud_alpha(35, 255, 4)
    L.punch(35, 0.04, 2)
    L.frost.ramp(35, 63, 0.35, 0.9, "quadIn")
    L.zoom.ramp(47, 63, 1.0, 1.07, "quadIn")
    # dive into the picture
    pic = s.tex("cover_wide.png", 0, 0, 1720, None, 0.0, WHITE, 255, -60, 35, 53)
    pic.at(53, "quadIn", w=3300, h=th("cover_wide.png", 3300), y=-260, alpha=0)
    ripple(s, 35, 0, -200, 10, 900, ICE, 200, 20, 3)
    snow(s, 0.8, 0.9, 8.0, 35, 51)
    snow(s, 1.0, 1.7, 14.0, 51, 63)
    # the crystal forms behind the line
    fk = s.tex("flake_a.png", 0, 40, 180, 180, 0.0, ICE, 0, -30, 43, 63)
    fk.at(63, "quadIn", w=900, h=900, rot=-120, alpha=120)
    gl = glow(s, 0, -200, 60, SNOW, 255, 30, 35, 43)
    gl.at(39, "expoOut", w=520, h=520).at(43, "quadIn", alpha=0)
    # the line: a point of light that opens
    A.at(35, x=0, y=-200, a=255, sx=0.0, spd=7.0).to(35, 39, "quartOut", sx=0.42)
    A.to(47, 63, "quadIn", spd=10.5)
    kicks = [b for b in range(39, 63) if m.scale("kick", 35, 63)(b) > 0.25 or b >= 43]
    for k, b in enumerate(kicks):
        t = k / max(1, len(kicks) - 1)
        side = -1 if k % 2 == 0 else 1
        x = side * (520 - 330 * t)
        if (b - 3) % 4 == 0 and b >= 47:
            N.add(A, b, -abs(x), TAP)
            N.add(A, b, abs(x), TAP)
        else:
            N.add(A, b, x, TAP)
        L.punch(b, 0.008 + 0.022 * t, F(3, 4))
        ripple(s, b, x, -200, 10, 110 + 120 * t, ICE, 150, 22, 1)
    # bar 15: the kick cuts out, a vocal chop hangs in the air, toms tumble into the drop
    G.flash(63, WHITE, 255, F(1, 2), "quadOut")
    G.shake(63, 18, 0.6, 0.4)
    N.add(A, 63, 0, TAP)
    s2 = E.shot(63, 67)
    G.bgc(63, NIGHT, 250)
    L.frost.ramp(63, F(127, 2), 0.9, 0.0, "expoOut")
    L.zoom.ramp(63, F(127, 2), 1.07, 1.0, "expoOut")
    L.sat.ramp(63, F(127, 2), 1.0, 0.15, "expoOut")
    L.sat.ramp(F(129, 2), 67, 0.15, 1.0, "quadIn")
    A.to(63, 64, "expoOut", sx=0.12)
    # "Just" on the chop, "Love" on the stab
    for tex_, b, x in (("t_just.png", F(127, 2), -250), ("t_love.png", F(129, 2), 250)):
        w = 520
        t = s2.tex(tex_, x, 60, w * 1.25, None, 0.0, SNOW, 255, 56, b, 67)
        t.at(b + F(1, 2), "expoOut", w=w, h=th(tex_, w))
        t.at(F(133, 2), "linear", alpha=255).at(67, "expoIn", alpha=0, w=w * 1.5, h=th(tex_, w * 1.5))
        G.flash(b, ICE, 110, F(1, 2))
        L.punch(b, 0.05, 1)
        L.split.pulse(b, 0.02, 1)
    N.add(A, F(127, 2), -180, TAP)
    N.add(A, F(129, 2), 180, TAP)
    for k in range(4):  # the tom roll, 32nds
        b = F(129, 2) + F(k + 1, 8)
        if k < 3:
            N.add(A, b, 180 - 90 * (k + 1), DRAG)
    N.add(A, 65, -180, FLICK)
    A.to(65, 67, "quadIn", sx=0.45, y=-220)
    L.zoom.ramp(65, 67, 1.0, 1.12, "expoIn")
    L.wash.ramp(F(265, 4), 67, 0.0, 0.85, "quadIn")
    for k, b in enumerate((F(265, 4), F(133, 2), F(267, 4))):  # snare roll into the drop
        N.add(A, b, (-300, 0, 300)[k], TAP)
        sparkle(s2, b, (-300, 0, 300)[k] , -200, 220, SNOW, 1, 40)
        G.shake(b, 8 + 4 * k, 0.3, 0.2)
    glow(s2, 0, 60, 300, SNOW, 0, 30, 65, 67).at(67, "expoIn", alpha=255, w=2600, h=2600)


# ------------------------------------------------------------------ shared pieces of the drops
def shards(s, b, cx, cy, n, r0, r1, length, width, color, life=F(3, 4), z=30, a=230, phase=0.0):
    """ice needles thrown outwards from a centre (tips first)"""
    b, life = F(b), F(life)
    for k in range(n):
        ang = phase + 360.0 * k / n
        ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        e = s.tex("spike.png", cx + ca * (r0 + length / 2), cy + sa * (r0 + length / 2), width, length, 90.0 - ang, color, a, z, b, b + life)
        e.at(b + life, "expoOut", x=cx + ca * (r1 + length / 2), y=cy + sa * (r1 + length / 2), alpha=0)


def tunnel(s, b0, b1, every=1, color=ICE, a=140, z=-24, life=2, w0=50, w1=2800, spin=30.0, tex="hex.png", x=0.0, y=0.0):
    """rings rushing past the camera: one is born every `every` beats and grows off the screen"""
    b, k = F(b0), 0
    while b < F(b1):
        end = min(b + F(life), F(b1))
        e = s.tex(tex, x, y, w0, w0, 30.0 * (k % 2), color, 0, z, b, end)
        e.at(b + (end - b) * F(1, 4), "linear", alpha=a)
        e.at(end, "quadIn", w=w1, h=w1, rot=30.0 * (k % 2) + spin)
        e.at(b + (end - b) * F(3, 4), "linear", alpha=a)
        e.at(end, "linear", alpha=0)
        b += F(every)
        k += 1


def star_on(X, b, sx=0.30, color=LINE, speed=8.0, n=3, dur=F(1, 2)):
    """the crystal: n lines through the pivot, 180/n degrees apart"""
    for i in range(n):
        k = X.K[i]
        k.at(b, x=0, y=0, rot=180.0 / n * i, col=color, spd=speed, a=255, sx=0.0)
        k.to(b, F(b) + F(dur), "expoOut", sx=sx)


def star_off(X, b, dur=1, n=3):
    for i in range(n):
        X.K[i].to(b, F(b) + F(dur), "expoIn", sx=0.0)
        X.K[i].at(F(b) + F(dur), a=0)


def drum_fx(X, s, ev, kick_zoom=0.035, snare_split=0.012, cx=0.0, cy=0.0, shard=True, color=ICE):
    """camera and light reactions shared by the drops: kicks punch in, back-beats split the colours"""
    for b, o in ev.items():
        if o["K"] > 0.45:
            X.L.punch(b, kick_zoom * min(1.3, 0.6 + 0.5 * o["K"]), 1)
            X.G.shake(b, 7, 0.25, 0.3)
        if o["pos"] in (1, 3) and o["S"] > 0.35:
            X.L.split.pulse(b, snare_split, F(3, 4))
            X.G.flash(b, color, 30, F(1, 2))
            if shard:
                shards(s, b, cx, cy, 6, 60, 330, 300, 34, color, F(3, 4), 28, 170, phase=30.0 if o["pos"] == 3 else 0.0)


def melodic(o, dens):
    """is this step a note of the lead? peaks in the harmonic flux, or a steady 8th when the part is busy"""
    on8 = (o["pos"] * 2) % 1 == 0
    if o["P"] > 1.22 and o["H"] > 0.55:
        return True
    if on8 and o["H"] > {1: 9.0, 2: 0.95, 3: 0.8, 4: 0.68, 5: 0.6}[dens]:
        return True
    return False


# ------------------------------------------------------------------ turning the analysis into notes
def is_snare(o):
    return o["pos"] in (1, 3) and o["S"] > 0.35


def chart_line(X, ev, b0, b1, line, px, dens=4, kick_x=470, snare_x=130, hats=True, hat_amp=540, drums=True, holds=False,
               above=True, skip=()):
    """one horizontal line: kicks out wide, back-beats as flicks near the middle, the lead where its pitch puts it,
    hi-hats as a slow wave of drags"""
    N, m = X.N, X.m
    lane = 0
    mel = [b for b, o in ev.items() if b0 <= b < b1 and melodic(o, dens) and not (drums and is_snare(o))]
    for b, o in ev.items():
        if not b0 <= b < b1 or b in skip:
            continue
        used = []
        if drums and o["K"] > 0.45:
            lane += 1
            used.append((-1 if lane % 2 else 1) * kick_x)
            N.add(line, b, used[-1], TAP, above=above)
        if drums and is_snare(o):
            used.append(snare_x if o["pos"] == 1 else -snare_x)
            N.add(line, b, used[-1], FLICK, above=above)
        if b in mel:
            x = px(b)
            if x is None:
                x = 300 * math.sin(float(b) * 1.3)
            for u in used:
                if abs(x - u) < 200:
                    x = u - 250 if u > 0 else u + 250
            end = None
            if holds:
                nxt = min([q for q in mel if q > b] + [F(b1)])
                if nxt - b >= F(3, 2) and m.d["pitch_w"][int(float(b) * 8) + 4:int(float(nxt) * 8) - 2].mean() > 0.3:
                    end = min(nxt - F(1, 2), b + 4)
            if not N.holding(b, line):
                N.add(line, b, x, HOLD if end else TAP, end=end, above=above)
                used.append(x)
        if hats and not used and (o["pos"] * 2) % 1 == 0 and (o["T"] > 0.3 or o["F"] > 0.3) and not N.holding(b, line):
            N.add(line, b, hat_amp * math.sin(2 * math.pi * float(b - b0) / 8), DRAG, above=above)


def chart_star(X, ev, b0, b1, lines, px, dens=4, hats=True, rad=430):
    """the crystal: every hit goes to the next arm, alternating ends and sides; back-beats land on the hub"""
    N = X.N
    cyc, side = 0, 1
    n = len(lines)
    for b, o in ev.items():
        if not b0 <= b < b1:
            continue
        if is_snare(o):
            for ln in lines:
                N.add(ln, b, 0, FLICK)
            continue
        if o["K"] > 0.45:
            cyc += 1
            side = -side
            N.add(lines[cyc % n], b, side * rad, TAP, above=cyc % 2 == 0)
        elif melodic(o, dens):
            cyc += 1
            side = -side
            x = px(b)
            r = 180 + (abs(x) * 0.55 if x is not None else 120)
            N.add(lines[cyc % n], b, side * r, TAP, above=cyc % 2 == 0)
        elif hats and (o["pos"] * 2) % 1 == 0 and (o["T"] > 0.3 or o["F"] > 0.3):
            cyc += 1
            side = -side
            N.add(lines[cyc % n], b, side * 300, DRAG, above=cyc % 2 == 0)


# ================================================================== 67-195: CRYSTALLIZE
def drop1(X):
    G, E, L, m, N, A, Bt, P, K = X.G, X.E, X.L, X.m, X.N, X.A, X.Bt, X.P, X.K
    R = X.R
    N.fx = (196, 228, 255)
    ev = onsets(X, 67, 195)
    px = pitch_map(X, 67, 195, 400)
    # ---- the drop lands
    G.flash(67, WHITE, 255, 2)
    L.wash.ramp(67, 68, 0.85, 0.0, "expoOut")
    L.zoom.ramp(67, 68, 1.12, 1.0, "expoOut")
    G.shake(67, 26, 1.2, 0.5)
    G.bgc(67, INDIGO, 238)
    G.vig(67, NIGHT, 225)
    X.pre.append(("shockwave", 67, 69, {"progress": X.c.var_kfs([(67, 0.02, "quadOut"), (69, 1.0, "linear")]), "width": 0.12, "distortion": 0.8, "expand": 10.0}))
    s = E.shot(67, 131)
    caption(s, "t_ch2.png", 67, 83)
    mist = s.tex("mist.png", 100, 40, 2600, None, 0.0, SKY, 70, -50)
    mist.at(131, "linear", x=-160)
    em = s.tex("flake_a.png", 0, 30, 1500, 1500, 0.0, ICE, 150, -30)
    em.at(69, "expoOut", w=980, h=980, alpha=95)
    em.at(131, "linear", rot=-200)
    glow(s, 0, 30, 900, SKY, 60, -32)
    snow(s, 0.9, 1.5, 16.0, 67, 131)
    drum_fx(X, s, {b: o for b, o in ev.items() if b < 131})
    # ---- phase 1 (67-99): one line, the crystal turning behind it
    A.at(67, y=-220, sx=0.45, spd=10.0, a=255, rot=0)
    chart_line(X, ev, 67, 99, A, px, 4)
    for bar in range(16, 24):  # the line breathes with the bar
        A.to(B(bar), B(bar, 2), "sineInOut", rot=1.6 if bar % 2 == 0 else -1.6)
        A.to(B(bar, 2), B(bar + 1), "sineInOut", rot=0.0)
    # ---- phase 2 (99-131): the line becomes a six-armed crystal that ticks round on the back-beats
    G.flash(99, ICE, 200, 1)
    G.bgc(99, DEEP, 235, 2)
    X.pre.append(("shockwave", 99, 101, {"progress": X.c.var_kfs([(99, 0.02, "quadOut"), (101, 1.0, "linear")]), "width": 0.1, "distortion": 0.6, "expand": 10.0}))
    A.to(98, 99, "expoIn", sx=0.0, y=0)
    A.at(99, a=0)
    P.at(99, x=0, y=10, rot=0)
    star_on(X, 99, 0.30, LINE, 8.0)
    rot = 0.0
    for bar in range(24, 32):
        for beat in (1, 3):
            P.to(B(bar, beat), B(bar, beat) + F(1, 2), "expoOut", rot=rot + 30.0)
            rot += 30.0
    chart_star(X, ev, 99, 130, K[:3], px, 4)
    em.at(99, "linear", color=ICE)
    em.at(100, "quadOut", color=SNOW)
    star_off(X, 130, 1)


# ================================================================== 131-195: the break, the blizzard, the crystal again
def drop1b(X):
    G, E, L, m, N, A, Bt, P, K = X.G, X.E, X.L, X.m, X.N, X.A, X.Bt, X.P, X.K
    ev = onsets(X, 67, 195)
    px = pitch_map(X, 67, 195, 400)
    # ---- bar 32: everything lets go and sinks with the falling bass
    s = E.shot(131, 135)
    G.flash(131, SNOW, 230, 1)
    G.bgc(131, NIGHT, 245, 2)
    G.shake(131, 16, 0.6, 0.4)
    L.punch(131, 0.05, 2)
    L.roll.ramp(131, 135, 0.0, -5.0, "quadIn")
    L.roll.ramp(135, 136, -5.0, 0.0, "expoOut")
    L.sat.ramp(131, 134, 1.0, 0.35, "sineOut")
    L.sat.ramp(134, 135, 0.35, 1.0, "quadIn")
    em = s.tex("flake_a.png", 0, 30, 980, 980, -200.0, SNOW, 120, -30)
    em.at(135, "quadIn", y=-520, rot=-150.0, alpha=0)
    snow(s, 0.9, 0.5, 4.0)
    A.at(131, x=0, y=60, rot=-3.0, sx=0.0, a=255, spd=7.0).to(131, 132, "expoOut", sx=0.40)
    A.to(132, 135, "quadIn", y=-250, rot=0.0)
    N.add(A, 131, 0, TAP)
    N.add(A, F(533, 4), -150, HOLD, end=F(539, 4))  # the stuttering voice
    N.add(A, F(539, 4), 150, FLICK)
    # ---- phase 3 (135-163): blizzard: two lines, a tunnel of hexagons
    s = E.shot(135, 163)
    G.flash(135, WHITE, 240, 1)
    G.bgc(135, (30, 24, 84), 238, 1)
    X.pre.append(("shockwave", 135, 137, {"progress": X.c.var_kfs([(135, 0.02, "quadOut"), (137, 1.0, "linear")]), "width": 0.12, "distortion": 0.8, "expand": 10.0}))
    tunnel(s, 135, 163, 1, LAVENDER, 120)
    glow(s, 0, 0, 700, VIOLET, 90, -34)
    snow(s, 1.0, 2.6, 28.0)
    drum_fx(X, s, {b: o for b, o in ev.items() if 135 <= b < 163}, cx=0, cy=0, color=LAVENDER)
    A.at(135, spd=10.0, y=-250)
    Bt.at(134, x=0, y=250, rot=180, sx=0.0, spd=10.0, col=LAVENDER)
    Bt.to(134, 135, "expoOut", a=255, sx=0.45)
    chart_line(X, ev, 135, 163, A, px, 4, drums=False)
    lane = 0
    for b, o in ev.items():
        if not 135 <= b < 163:
            continue
        if is_snare(o):
            N.add(Bt, b, 0, FLICK)
        elif o["K"] > 0.45:
            lane += 1
            N.add(Bt, b, (-1 if lane % 2 else 1) * 380, TAP)
    for bar in range(33, 40):  # the two lines lean into the wind, opposite ways
        t = 2.5 if bar % 2 else -2.5
        A.to(B(bar), B(bar + 1), "sineInOut", rot=t)
        Bt.to(B(bar), B(bar + 1), "sineInOut", rot=180 - t)
    X.fx["kaleido"].add(161, 163, amount=[(161, 0.0, "quadOut"), (F(323, 2), 1.0, "linear"), (163, 1.0, "linear")], sides=6.0,
                        angle=[(161, 0.0, "linear"), (163, 60.0, "linear")], source=90.0)
    # ---- phase 4 (163-191): the crystal again, never still; the last bars fold the whole screen into it
    s = E.shot(163, 195)
    G.flash(163, WHITE, 255, 1)
    G.bgc(163, DEEP, 235, 1)
    X.pre.append(("shockwave", 163, 165, {"progress": X.c.var_kfs([(163, 0.02, "quadOut"), (165, 1.0, "linear")]), "width": 0.12, "distortion": 0.8, "expand": 10.0}))
    em = s.tex("flake_b.png", 0, 10, 1500, 1500, 0.0, ICE, 150, -30, 163, 195)
    em.at(165, "expoOut", w=1040, h=1040, alpha=100)
    em.at(191, "linear", rot=240.0)
    em.at(195, "expoIn", w=0, h=0, rot=420.0)
    glow(s, 0, 10, 1000, SKY, 70, -32, 163, 191)
    snow(s, 1.0, 1.9, 18.0, 163, 191)
    drum_fx(X, s, {b: o for b, o in ev.items() if 163 <= b < 191}, cy=10)
    A.to(162, 163, "expoIn", sx=0.0)
    A.at(163, a=0)
    Bt.to(162, 163, "expoIn", sx=0.0)
    Bt.at(163, a=0)
    P.at(163, x=0, y=10, rot=0)
    star_on(X, 163, 0.30, LINE, 8.5)
    rot = 0.0
    for bar in range(40, 47):
        d = 60.0 if bar % 2 == 0 else -60.0
        P.to(B(bar), B(bar + 1), "sineInOut", rot=rot + d * 2)
        rot += d * 2
    chart_star(X, ev, 163, 191, K[:3], px, 5)
    X.fx["kaleido"].add(179, 191, amount=[(179, 0.0, "sineOut"), (181, 0.85, "linear"), (190, 0.85, "quadIn"), (191, 0.0, "linear")],
                        sides=6.0, angle=[(179, 0.0, "linear"), (191, 90.0, "linear")], source=90.0)
    # ---- bar 47: the kick stops; toms tumble down, the crystal folds away arm by arm
    G.flash(191, SNOW, 200, 1)
    G.shake(191, 18, 0.8, 0.4)
    L.punch(191, 0.05, 2)
    G.bgc(191, NIGHT, 245, 4)
    for i in range(3):
        N.add(K[i], 191, 0, TAP)
    toms = [F(385, 2), F(771, 4), 193, F(387, 2), 194, F(389, 2)]
    P.to(191, 195, "quadOut", rot=rot + 45)
    K[2].to(192, 193, "expoIn", sx=0.0)
    K[2].at(193, a=0)
    K[1].to(193, 194, "expoIn", sx=0.0)
    K[1].at(194, a=0)
    K[0].to(194, 195, "expoIn", sx=0.0)
    K[0].at(195, a=0)
    for k, b in enumerate(toms):
        ln = K[0] if k >= 4 else (K[1] if k >= 2 else K[2])
        x = 420 - 150 * k
        N.add(ln, b, x, DRAG if k % 2 else TAP)
        sparkle(s, b, 420 - 170 * k, 250 - 90 * k, 260, SNOW, 1.5, 40)
        L.punch(b, 0.02, F(1, 2))



# ------------------------------------------------------------------ the lotus: petals on a pivot of their own
class Flower:
    RINGS = [  # petals, length, width, base radius, phase, alpha, z
        (8, 350, 156, 50, 0.0, 150, -12),
        (8, 255, 124, 26, 22.5, 180, -11),
        (6, 150, 86, 4, 0.0, 220, -10),
    ]

    def __init__(self, X, cx=0.0, cy=40.0):
        c = X.c
        self.pivot = Rig(c, "flower", X.root, cx, cy)
        self.petals = []
        for ri, (n, lp, w, r0, ph, a, z) in enumerate(self.RINGS):
            for k in range(n):
                phi = ph + 360.0 * k / n
                ln = c.line(f"petal_{ri}_{k}", texture="petal.png", z=z, father=self.pivot.index, rot_with_father=True)
                init = {"moveX": 0.0, "moveY": 0.0, "rotate": 90.0 - phi, "alpha": 0.0, "scaleX": 0.0, "scaleY": 0.0, "color": SNOW}
                tl = {}
                for prop, v in init.items():
                    ln.ev(prop, 0, EPSB, v, v)
                    tl[prop] = TL(ln, prop, v)
                self.petals.append({"ln": ln, "tl": tl, "phi": phi, "L": lp, "w": w, "r0": r0, "a": a, "ring": ri})

    @staticmethod
    def _geom(p, fl, fw):
        """line values for a petal at a fraction of its length / width (the base stays where it is)"""
        length, width = p["L"] * fl, p["w"] * fw
        r = p["r0"] * fl + length / 2
        ca, sa = math.cos(math.radians(p["phi"])), math.sin(math.radians(p["phi"]))
        return {"moveX": ca * r * PX, "moveY": sa * r, "scaleX": width / (256 * TEXK), "scaleY": length / (512 * TEXK)}

    def _move(self, p, b0, b1, fl, fw, ease):
        for prop, v in self._geom(p, fl, fw).items():
            t = p["tl"][prop]
            if b1 is None:
                t.jump(b0, v)
            else:
                t.wait(b0)
                t.to(b1, v, ease)

    def bloom(self, b, colors, dur=2, stagger=F(1, 2), twist=70.0):
        """closed bud -> open flower; the rings open from the outside in, the whole flower untwists"""
        b = F(b)
        self.pivot.at(b, rot=self.pivot.v("rot") + twist)
        self.pivot.to(b, b + F(dur) + 2 * F(stagger), "expoOut", rot=self.pivot.v("rot") - twist)
        for p in self.petals:
            st = b + F(stagger) * p["ring"]
            self._move(p, st, None, 0.06, 0.25, None)
            p["tl"]["color"].jump(st, colors[p["ring"]])
            p["tl"]["alpha"].jump(st, float(p["a"]))
            self._move(p, st, st + F(dur), 1.0, 1.0, "expoOut")

    def tint(self, b, colors, fade=1):
        for p in self.petals:
            t = p["tl"]["color"]
            t.wait(b)
            t.to(F(b) + F(fade), colors[p["ring"]], "sineInOut")

    def spin(self, b0, b1, deg, ease="linear"):
        self.pivot.to(b0, b1, ease, rot=self.pivot.v("rot") + deg)

    def alpha(self, b0, b1, k):
        for p in self.petals:
            t = p["tl"]["alpha"]
            t.wait(b0)
            t.to(b1, p["a"] * k, "sineInOut")

    def close(self, b0, b1, ease="expoIn"):
        for p in self.petals:
            self._move(p, b0, b1, 0.05, 0.2, ease)
            t = p["tl"]["alpha"]
            t.wait(b0)
            t.to(b1, 0.0, ease)

    def scatter(self, b0, b1, R):
        """the petals let go and drift down"""
        for p in self.petals:
            tx, ty, tr, ta = p["tl"]["moveX"], p["tl"]["moveY"], p["tl"]["rotate"], p["tl"]["alpha"]
            d = R.uniform(0, F(1, 1))
            for t, v, e in ((tx, tx.v + R.uniform(-260, 260) * PX, "sineOut"), (ty, ty.v - R.uniform(420, 760), "quadIn"),
                            (tr, tr.v + R.uniform(-160, 160), "sineOut"), (ta, 0.0, "quadIn")):
                t.wait(F(b0) + F(d).limit_denominator(8))
                t.to(b1, v, e)


def ring_on(X, b, R=270.0, sx=0.066, color=LINE, speed=6.0, dur=1, cx=0.0, cy=40.0, rot0=0.0):
    """six short lines as a hexagon around (cx, cy); their upper side faces the centre, so notes fly outwards"""
    b = F(b)
    X.P.at(b, x=cx, y=cy, rot=rot0)
    for i in range(6):
        phi = math.radians(90 - 60 * i)
        k = X.K[i]
        k.at(b, x=R * 0.25 * math.cos(phi), y=R * 0.25 * math.sin(phi), rot=270.0 - (90 - 60 * i), col=color, spd=speed, a=255, sx=0.0)
        k.to(b, b + F(dur), "expoOut", x=R * math.cos(phi), y=R * math.sin(phi), sx=sx)


def ring_off(X, b, dur=1, R=270.0):
    b = F(b)
    for i in range(6):
        phi = math.radians(90 - 60 * i)
        X.K[i].to(b, b + F(dur), "expoIn", sx=0.0, x=R * 1.6 * math.cos(phi), y=R * 1.6 * math.sin(phi))
        X.K[i].at(b + F(dur), a=0)


def chart_ring(X, ev, b0, b1, R=270.0, speed=6.0, hats=False):
    """drums on the hexagon: notes are born in the middle and fly out; kicks to two opposite sides, back-beats to three"""
    N = X.N
    vis = R / (speed * 120.2) * 0.96
    i, j = 0, 0
    for b, o in ev.items():
        if not b0 <= b < b1:
            continue
        if is_snare(o):
            j += 1
            for k in range(3):
                N.add(X.K[(j + 2 * k) % 6], b, 0, FLICK, vis=vis)
        elif o["K"] > 0.45:
            i += 1
            for k in (0, 3):
                N.add(X.K[(i + k) % 6], b, 0, TAP, vis=vis)
        elif hats and (o["pos"] * 2) % 1 == 0 and (o["T"] > 0.3 or o["F"] > 0.3):
            i += 1
            N.add(X.K[i % 6], b, 0, DRAG, vis=vis)


def shock(X, b, width=0.12, dist=0.8, dur=2, cx=0.5, cy=0.5):
    b = F(b)
    X.pre.append(("shockwave", b, b + F(dur), {"progress": X.c.var_kfs([(b, 0.02, "quadOut"), (b + F(dur), 1.0, "linear")]),
                                              "width": width, "distortion": dist, "expand": 10.0, "centerX": cx, "centerY": cy}))


# ================================================================== 195-227: still air, the build, the ice breaks
def breakdown(X):
    G, E, L, m, N, A, P, K = X.G, X.E, X.L, X.m, X.N, X.A, X.P, X.K
    R = X.R
    N.fx = (214, 232, 255)
    s = E.shot(195, 227)
    G.flash(195, WHITE, 255, 2)
    G.shake(195, 22, 1.0, 0.5)
    L.punch(195, 0.07, 3)
    shock(X, 195, 0.14, 0.9, 3)
    G.bgc(195, (14, 18, 46), 240, 2)
    ripple(s, 195, 0, -100, 20, 1100, ICE, 220, 20, 4)
    snow(s, 0.7, 0.45, 3.0, 195, 211)
    snow(s, 0.9, 1.2, 8.0, 211, 223)
    rose = s.tex("rose.png", 0, 40, 520, 520, 0.0, SKY, 0, -30, 195, 227)
    rose.at(199, "sineOut", alpha=80).at(211, "linear", rot=-40.0, w=640, h=640, alpha=80)
    rose.at(223, "quadIn", rot=-150.0, w=1200, h=1200, alpha=150)
    glow(s, 0, 40, 700, DEEP, 150, -32, 195, 223).at(223, "quadIn", w=1500, h=1500, color=SKY)
    for k in range(7):  # slow lights rising through the still air
        x, y0 = R.uniform(-700, 700), R.uniform(-420, 100)
        d = R.uniform(60, 190)
        bk = s.tex("bokeh.png", x, y0, d, d, 0.0, mix(SKY, LAVENDER, R.random()), 0, -26, 195 + k, 223)
        bk.at(199 + k, "sineOut", alpha=R.randint(40, 90)).at(223, "linear", y=y0 + R.uniform(160, 320), x=x + R.uniform(-60, 60), alpha=0)
    A.at(195, x=0, y=-120, rot=0, sx=0.0, a=255, spd=6.5, col=LINE).to(195, 197, "expoOut", sx=0.36)
    N.add(A, 195, 0, HOLD, end=198)
    ev = onsets(X, 195, 211)
    side = 1
    for b, o in ev.items():
        if b < 198:
            continue
        if o["K"] > 0.4 and (o["pos"] * 2) % 1 == 0 and o["pos"] % 1 != 0:  # the off-beat bass plucks
            side = -side
            N.add(A, b, side * 330, DRAG)
            ripple(s, b, side * 330, -120, 10, 120, SKY, 130, 22, 1)
        elif o["M"] > 0.55 and (o["pos"] * 4) % 2 == 0:
            N.add(A, b, 150 * math.sin(float(b) * 0.9), TAP)
            sparkle(s, b, R.uniform(-500, 500), R.uniform(60, 330), 150, SNOW, 2, 40)
    # ---- 211-223: four on the floor
    G.bgc(211, INDIGO, 235, 12)
    L.zoom.ramp(211, 223, 1.0, 1.06, "quadIn")
    L.frost.ramp(211, 223, 0.0, 0.8, "quadIn")
    A.to(211, 223, "quadIn", y=0, spd=9.5, sx=0.45)
    for k, b in enumerate(range(211, 223)):
        t = k / 11
        x = (-1 if k % 2 == 0 else 1) * (480 - 280 * t)
        if k % 4 == 0:
            N.add(A, b, -abs(x), TAP)
            N.add(A, b, abs(x), TAP)
        else:
            N.add(A, b, x, TAP)
        L.punch(b, 0.012 + 0.02 * t, F(3, 4))
        ripple(s, b, x, float(-120 + 120 * (t ** 2)), 10, 130 + 100 * t, ICE, 150, 22, 1)
    N.add(A, 215, 0, HOLD, end=F(445, 2))
    # ---- bar 55: four kick-stops; every one cracks the ice a little further, then the roll and the riser burst it
    s2 = E.shot(223, 227)
    hits = [223, F(447, 2), 224, F(449, 2)]
    X.fx["shatter"].add(223, 227, cells=5.0, seed=3.0,
                        crack=[(223, 0.0, "expoOut"), (F(1785, 8), 0.26, "linear"), (F(447, 2), 0.26, "expoOut"), (F(1789, 8), 0.48, "linear"),
                               (224, 0.48, "expoOut"), (F(1793, 8), 0.72, "linear"), (F(449, 2), 0.72, "quadOut"), (225, 1.0, "linear"), (227, 1.0, "linear")],
                        power=[(223, 0.0, "linear"), (225, 0.0, "quadIn"), (227, 0.72, "linear")])
    L.frost.ramp(223, 224, 0.8, 0.3, "expoOut")
    L.zoom.ramp(223, 223 + EPSB, 1.06, 1.0)
    L.sat.ramp(223, 223 + EPSB, 1.0, 0.25)
    L.sat.ramp(225, 227, 0.25, 1.0, "quadIn")
    G.bgc(223, (10, 14, 40), 245)
    for k, b in enumerate(hits):
        L.invert.hold(b, 1.0, F(1, 8))
        L.punch(b, 0.05 + 0.01 * k, F(1, 2))
        G.shake(b, 16 + 4 * k, 0.5, 0.3)
        w = (700, 1200, 1900, 2600)[k]
        cr = s2.tex("crack.png", 0, 0, w, None, (0.0, 180.0, 0.0, 180.0)[k], SNOW, 255, 60, b, hits[k + 1] if k < 3 else 227)
        if k == 3:
            cr.at(225, "linear", alpha=255).at(227, "quadIn", alpha=120, w=3200, h=th("crack.png", 3200))
        if k < 3:
            N.add(A, b, -230, TAP)
            N.add(A, b, 230, TAP)
    A.at(223, y=0, sx=0.45, spd=9.0)
    for k in range(4):  # the 32nd kick roll
        N.add(A, F(449, 2) + F(k, 8), -300 + 200 * k, DRAG if k else TAP)
    N.add(A, 225, 0, FLICK)
    for k in range(5):  # snare roll, 16ths
        b = F(903, 4) + F(k, 4)
        N.add(A, b, (-1 if k % 2 else 1) * (360 - 60 * k), TAP)
        G.shake(b, 8 + 3 * k, 0.3, 0.2)
    L.zoom.ramp(225, 227, 1.0, 1.10, "expoIn")
    L.wash.ramp(F(451, 2), 227, 0.0, 0.9, "quadIn")
    A.to(225, 227, "quadIn", y=-260)



# ================================================================== 227-355: BLOOM
PETAL_ICE = (ICE, LAVENDER, BLUSH)
PETAL_PINK = (PINK, BLUSH, SNOW)
PETAL_SNOW = (SNOW, ICE, BLUSH)


def chorus_fx(X, s, ev, b0, b1, cx=0.0, cy=40.0, hearts=True, color=PINK):
    """what the chorus does on its drums: kicks punch and send up a heart, back-beats glint"""
    R = X.R
    for b, o in ev.items():
        if not b0 <= b < b1:
            continue
        if o["K"] > 0.45:
            X.L.punch(b, 0.03 * min(1.3, 0.6 + 0.5 * o["K"]), 1)
            X.G.shake(b, 6, 0.2, 0.3)
            if hearts:
                heart_up(s, b, R.uniform(-620, 620), R.uniform(-300, -120), R.uniform(50, 90), mix(color, SNOW, R.uniform(0, 0.5)),
                         R.uniform(140, 260), 4, 24, 190, R.uniform(-40, 40))
        if is_snare(o):
            X.L.split.pulse(b, 0.010, F(3, 4))
            X.G.flash(b, BLUSH, 26, F(1, 2))
            ang = R.uniform(0, 360)
            rr = R.uniform(260, 420)
            sparkle(s, b, cx + rr * math.cos(math.radians(ang)), cy + rr * math.sin(math.radians(ang)) * 0.8, R.uniform(160, 260), SNOW, 1.5, 42)


def chorus(X, b0=227, last=False):
    """32 bars: the lotus opens (16 bars: one line under it), then a hexagon of lines closes round it and the
    drums fly out of the flower (16 bars)"""
    G, E, L, m, N, A, P, K = X.G, X.E, X.L, X.m, X.N, X.A, X.P, X.K
    R = X.R
    b0 = F(b0)
    mid, b1 = b0 + 64, b0 + 128
    N.fx = (255, 206, 228)
    ev = onsets(X, b0, b1)
    px = pitch_map(X, b0, b1, 430)
    fl = X.flower
    # ---- the ice bursts: white, then the flower
    G.flash(b0, WHITE, 255, 3)
    L.wash.ramp(b0, b0 + 2, 0.9, 0.0, "expoOut")
    L.zoom.ramp(b0, b0 + 2, 1.10, 1.0, "expoOut")
    L.sat.ramp(b0, b0 + 2, 1.0, 1.12, "sineOut")
    G.shake(b0, 26, 1.2, 0.5)
    shock(X, b0, 0.14, 0.9, 3, 0.5, 0.545)
    G.bgc(b0, (40, 34, 96), 232)
    G.vig(b0, (20, 14, 50), 210)
    X.fx["glow"].add(b0, b0 + 16, strength=[(b0, 1.1, "sineOut"), (b0 + 8, 0.55, "linear"), (b0 + 14, 0.55, "sineIn"), (b0 + 16, 0.0, "linear")],
                     radius=0.012, threshold=0.55)
    s = E.shot(b0, b1)
    if not last:
        caption(s, "t_ch3.png", b0, b0 + 16)
    else:
        caption(s, "t_ch7.png", b0, b0 + 16)
    rays = s.tex("rays.png", 0, 40, 600, 600, 0.0, BLUSH, 0, -40)
    rays.at(b0 + 3, "expoOut", w=2300, h=2300, alpha=74).at(b1, "linear", rot=160.0)
    glow(s, 0, 40, 200, GOLD, 255, -8, b0, b1).at(b0 + 3, "expoOut", w=330, h=330, alpha=215)
    glow(s, 0, 40, 400, PINK, 0, -42, b0, b1).at(b0 + 3, "expoOut", w=1500, h=1500, alpha=92)
    burst(s, b0, 0, 40, 14, 40, 760, 150, SNOW, R, 3, 44)
    burst(s, b0, 0, 40, 10, 30, 520, 70, PINK, R, 4, 43, "heart.png", 220)
    scroll(s, "snow_b.png", BLUSH, 150, 2100, 170, 46, b0, b1, rot=22.0)
    scroll(s, "snow_a.png", SNOW, 120, 1900, 110, -22, b0, b1, rot=12.0)
    fl.bloom(b0, PETAL_ICE if not last else PETAL_PINK, 2)
    fl.spin(b0 + 4, mid, 64.0)
    chorus_fx(X, s, ev, b0, b1)
    for q, bq in enumerate(range(int(b0), int(b1), 16)):  # every four bars the flower changes colour
        if q:
            cols = (PETAL_ICE, PETAL_PINK, PETAL_SNOW, PETAL_PINK)[q % 4] if not last else (PETAL_PINK, PETAL_SNOW, PETAL_PINK, PETAL_ICE)[q % 4]
            fl.tint(bq, cols, 2)
            ripple(s, bq, 0, 40, 60, 900, SNOW, 170, -6, 3)
            G.flash(bq, BLUSH, 70, 1)
            if q % 2 == 0:
                shock(X, bq, 0.1, 0.6, 2, 0.5, 0.545)
    # ---- first half: the line under the flower carries everything
    A.at(b0, x=0, y=-260, rot=0, sx=0.45, a=255, spd=9.5, col=LINE)
    chart_line(X, ev, b0, mid, A, px, 4, holds=True)
    for k in range(16):
        bb = b0 + 4 * k
        A.to(bb, bb + 2, "sineInOut", rot=1.4 if k % 2 == 0 else -1.4)
        A.to(bb + 2, bb + 4, "sineInOut", rot=0.0)
    # ---- second half: the hexagon; kicks and back-beats are thrown out of the flower
    G.flash(mid, WHITE, 200, 1)
    G.bgc(mid, (52, 36, 104), 230, 2)
    A.to(mid - 1, mid, "sineInOut", y=-345)
    ring_on(X, mid, 270.0, 0.066, BLUSH, 6.0, 1, 0, 40)
    fl.spin(mid, b1 - 4, -90.0)
    rot = 0.0
    for k in range(15):
        bb = mid + 4 * k
        P.to(bb, bb + 4, "linear", rot=rot + 15.0)
        rot += 15.0
    chart_ring(X, ev, mid, b1 - 4, 270.0, 6.0)
    chart_line(X, ev, mid, b1 - 4, A, px, 4, drums=False, holds=True)
    for bb in X.m.hits("kick", mid, b1 - 4, 0.45):
        ripple(s, bb, 0, 40, 60, 300, PINK, 150, -7, 1)
    return s, ev, px


def chorus1(X):
    G, E, L, m, N, A, P, K = X.G, X.E, X.L, X.m, X.N, X.A, X.P, X.K
    X.flower = Flower(X, 0, 40)
    s, ev, px = chorus(X, 227)
    fl = X.flower
    # ---- bar 87: last bar of the chorus (ring still up); bar 88: the petals let go
    chart_ring(X, ev, 351, 355, 270.0, 6.0)
    chart_line(X, ev, 351, 355, A, px, 4, drums=False)
    P.to(351, 355, "quadIn", rot=P.v("rot") + 60.0)
    ring_off(X, 355, 1)



# ------------------------------------------------------------------ the swing: a pivot far above the screen, two ropes, the seat
class Swing:
    LEN, HALF = 780.0, 380.0

    def __init__(self, X, top=640.0):
        c = X.c
        self.top = top
        self.pivot = Rig(c, "swing_pivot", X.root, 0, top)
        self.seat = X.JL(c, "swing_seat", 118, self.pivot.index, x=0, y=-self.LEN, sx=0.0, speed=6.5)
        self.ropes = []
        for sgn in (-1, 1):
            ln = c.line(f"swing_rope_{'l' if sgn < 0 else 'r'}", texture="white.png", z=100, father=self.pivot.index, rot_with_father=True)
            init = {"moveX": sgn * self.HALF * PX, "moveY": -self.LEN / 2, "rotate": 0.0, "alpha": 0.0, "scaleX": 4.0 / (64 * TEXK),
                    "scaleY": self.LEN / (64 * TEXK), "color": ICE}
            tl = {}
            for prop, v in init.items():
                ln.ev(prop, 0, EPSB, v, v)
                tl[prop] = TL(ln, prop, v)
            self.ropes.append(tl)

    def on(self, b, dur=2, color=LINE):
        b = F(b)
        self.pivot.at(b, rot=0, y=self.top + 260)
        self.pivot.to(b, b + F(dur), "expoOut", y=self.top)
        self.seat.at(b, a=255, sx=0.0, col=color).to(b, b + F(dur), "expoOut", sx=(self.HALF + 30) / 2400)
        for tl in self.ropes:
            tl["alpha"].wait(b)
            tl["alpha"].to(b + F(dur), 190.0, "sineOut")

    def swing(self, b0, b1, amp0, amp1=None, half=4):
        """pendulum from rest at b0: extremes every `half` beats, amplitude fading from amp0 to amp1"""
        amp1 = amp0 if amp1 is None else amp1
        b0, b1 = F(b0), F(b1)
        n = int((b1 - b0 - F(half, 2)) // half)
        t, sgn = b0 + F(half, 2), 1
        self.pivot.to(b0, t, "sineOut", rot=amp0)
        for k in range(n):
            a = amp0 + (amp1 - amp0) * (k + 1) / max(1, n)
            sgn = -sgn
            self.pivot.to(t, t + half, "sineInOut", rot=sgn * a)
            t += half
        self.pivot.to(t, b1, "sineInOut", rot=0.0)

    def off(self, b, dur=1):
        b = F(b)
        for tl in self.ropes:
            tl["alpha"].wait(b)
            tl["alpha"].to(b + F(dur), 0.0, "quadIn")
        self.seat.to(b, b + F(dur), "quadIn", a=0)


def night_sky(X, s, b0, b1, aurora=(MINT, LAVENDER), moon=True, a_in=4, horizon=-270.0):
    """stars, two curtains of aurora breathing against each other, a small moon, the far shore of the lake"""
    b0, b1 = F(b0), F(b1)
    st = s.tex("stars.png", 0, 60, 1900, None, 0.0, SNOW, 0, -70, b0, b1)
    st.at(b0 + a_in, "sineOut", alpha=210).at(b1, "linear", x=-70)
    for k, (col, x0, x1, w, y, a) in enumerate(((aurora[0], -160, 120, 2100, 150, 150), (aurora[1], 220, -140, 2500, 190, 110))):
        au = s.tex("aurora.png", x0, y, w, 620 + 80 * k, 0.0, col, 0, -64 + k, b0, b1)
        au.at(b0 + a_in + 2 * k, "sineOut", alpha=a)
        n = int((b1 - b0) // 8)
        for q in range(1, n + 1):
            bb = b0 + 8 * q
            if bb > b0 + a_in + 2 * k and bb < b1:
                au.at(bb, "sineInOut", alpha=a * (0.55 if (q + k) % 2 else 1.0))
        au.at(b1, "linear", x=x1)
    if moon:
        glow(s, 520, 300, 420, ICE, 0, -62, b0, b1).at(b0 + a_in, "sineOut", alpha=110)
        s.tex("disc.png", 520, 300, 84, 84, 0.0, SNOW, 0, -61, b0, b1).at(b0 + a_in, "sineOut", alpha=235)
    sh = s.tex("beam.png", 0, horizon, 2400, 26, 0.0, ICE, 0, -58, b0, b1)
    sh.at(b0 + a_in, "sineOut", alpha=120)


# ================================================================== 355-419: SWING
def swing_scene(X):
    G, E, L, m, N, A, P, K = X.G, X.E, X.L, X.m, X.N, X.A, X.P, X.K
    R = X.R
    fl = X.flower
    X.swing = sw = Swing(X)
    N.fx = (200, 236, 255)
    # ---- bar 88: the chorus lets go; petals fall, the light goes out
    s = E.shot(355, 359)
    G.flash(355, BLUSH, 200, 1)
    G.bgc(355, NIGHT, 250, 4)
    G.vig(355, NIGHT, 215, 4)
    L.sat.ramp(355, 359, 1.12, 1.0, "linear")
    L.punch(355, 0.04, 1)
    fl.scatter(355, 359, R)
    snow(s, 0.7, 0.6, 6.0)
    A.to(355, 359, "sineInOut", y=-140, sx=(Swing.HALF + 30) / 2400, spd=6.5)
    for k, bb in enumerate((355, F(711, 2), 356, F(713, 2), 357, F(715, 2), 358)):
        N.add(A, bb, (-1 if k % 2 else 1) * (300 - 36 * k), TAP if k % 3 else FLICK)
        sparkle(s, bb, R.uniform(-600, 600), R.uniform(-100, 350), 180, BLUSH, 1.5, 42)
        L.punch(bb, 0.012, F(1, 2))
    # ---- the swing over the frozen lake
    s = E.shot(359, 419)
    caption(s, "t_ch4.png", 359, 375)
    night_sky(X, s, 359, 419)
    snow(s, 0.7, 0.45, 3.0, 359, 419, a_in=3)
    X.fx["mirror"].add(359, 419, horizon=0.2, depth=2.6, ripple=0.004, tint=(170, 205, 255),
                       amount=[(359, 0.0, "sineOut"), (363, 0.6, "linear"), (417, 0.6, "sineIn"), (419, 0.0, "linear")])
    A.at(359, a=0)
    sw.on(359, 2)
    sw.swing(359, 419, 9.0, 9.0, 4)
    G.flash(359, ICE, 90, 2)
    L.punch(359, 0.03, 2)
    ev = onsets(X, 359, 419)
    px = pitch_map(X, 359, 419, 300)
    chart_line(X, ev, 359, 419, sw.seat, px, 3, kick_x=300, snare_x=110, hats=False, holds=True)
    for bar in (89, 93, 97, 100):  # the long 808 notes: the sky answers
        bb = B(bar)
        G.flash(bb, MINT, 46, 2)
        L.punch(bb, 0.025, 2)
        ripple(s, bb, 0, -270, 40, 900, MINT, 120, -56, 4)
    L.shiftY.ramp(359, 371, 0.0, 0.012, "sineInOut")
    L.shiftY.ramp(371, 375, 0.012, 0.0, "sineInOut")
    L.shiftY.ramp(375, 387, 0.0, 0.012, "sineInOut")
    L.shiftY.ramp(387, 391, 0.012, 0.0, "sineInOut")
    for bar in range(96, 104):  # second half: hearts rise from the seat
        bb = B(bar)
        heart_up(s, bb, R.uniform(-300, 300), -120, R.uniform(46, 70), mix(PINK, SNOW, 0.3), R.uniform(200, 320), 6, 24, 170, R.uniform(-60, 60))
        heart_up(s, bb + 2, R.uniform(-300, 300), -120, R.uniform(36, 56), mix(PINK, SNOW, 0.5), R.uniform(200, 320), 6, 24, 150, R.uniform(-60, 60))


# ================================================================== 419-487: PRISM
PRISM = ((186, 216, 255), (150, 255, 220), (255, 236, 170), (255, 172, 208), (190, 170, 255))


def chart_prism(X, ev, b0, b1, R=250.0, speed=6.5, dens=4):
    """everything leaves from the centre: kicks to two opposite sides, back-beats to three, the lead to the side
    its pitch class points at, hi-hats round the ring"""
    N = X.N
    vis = R / (speed * 120.2) * 0.96
    i, j, h = 0, 0, 0
    for b, o in ev.items():
        if not b0 <= b < b1:
            continue
        if is_snare(o):
            j += 1
            for k in range(3):
                N.add(X.K[(j + 2 * k) % 6], b, 0, FLICK, vis=vis)
        elif o["K"] > 0.45:
            i += 1
            for k in (0, 3):
                N.add(X.K[(i + k) % 6], b, 0, TAP, vis=vis)
        elif melodic(o, dens):
            p = X.m.pitch(b)
            side = int(round(p)) % 6 if p else (h := h + 1) % 6
            N.add(X.K[side], b, 0, TAP, vis=vis)
        elif (o["pos"] * 2) % 1 == 0 and (o["T"] > 0.3 or o["F"] > 0.3):
            h += 1
            N.add(X.K[h % 6], b, 0, DRAG, vis=vis)


def drop2(X):
    G, E, L, m, N, A, P, K = X.G, X.E, X.L, X.m, X.N, X.A, X.P, X.K
    R = X.R
    sw = X.swing
    N.fx = (230, 240, 255)
    # ---- bars 104-105: the ropes give; the seat is a judge line again and turns over
    s = E.shot(419, 427)
    G.flash(419, WHITE, 255, 2)
    G.shake(419, 22, 1.0, 0.5)
    L.punch(419, 0.06, 2)
    shock(X, 419, 0.12, 0.8, 2)
    G.bgc(419, INDIGO, 240, 4)
    snow(s, 0.9, 1.4, 12.0)
    sw.off(419, F(1, 2))
    A.at(419, x=0, y=-140, rot=0, sx=(Swing.HALF + 30) / 2400, a=255, spd=8.0, col=LINE)
    A.to(419, 421, "expoOut", y=0, sx=0.45)
    for bb, xs, kind in ((419, (-260, 260), TAP), (F(841, 2), (0,), TAP), (422, (-200,), TAP), (F(845, 2), (200,), FLICK),
                         (423, (-260, 260), TAP), (F(849, 2), (0,), FLICK), (F(853, 2), (0,), TAP)):
        for x in xs:
            N.add(A, bb, x, kind)
        L.punch(bb, 0.03, 1)
        sparkle(s, bb, R.uniform(-500, 500), R.uniform(-200, 300), 260, SNOW, 1.5, 42)
    G.flash(423, WHITE, 230, 1)
    G.shake(423, 20, 0.8, 0.4)
    L.roll.ramp(423, 427, 0.0, -6.0, "quadIn")
    L.roll.ramp(427, 428, -6.0, 0.0, "expoOut")
    A.to(423, 425, "expoOut", rot=180.0)
    A.to(425, 427, "expoIn", sx=0.0, rot=360.0)
    A.at(427, a=0, rot=0)
    L.zoom.ramp(425, 427, 1.0, 1.1, "expoIn")
    L.wash.ramp(F(853, 2), 427, 0.0, 0.8, "quadIn")
    # ---- the prism: a hexagon of lines; light leaves the centre in colours
    ev = onsets(X, 427, 483)
    s = E.shot(427, 487)
    caption(s, "t_ch5.png", 427, 443)
    G.flash(427, WHITE, 255, 2)
    L.wash.ramp(427, 428, 0.8, 0.0, "expoOut")
    L.zoom.ramp(427, 428, 1.1, 1.0, "expoOut")
    G.shake(427, 26, 1.2, 0.5)
    shock(X, 427, 0.14, 0.9, 2)
    G.bgc(427, (16, 16, 50), 244)
    ring_on(X, 427, 250.0, 0.061, SNOW, 6.5, 1, 0, 0)
    snow(s, 0.8, 1.6, 20.0, 427, 483)
    core = glow(s, 0, 0, 260, WHITE, 255, -8, 427, 483)
    rays = s.tex("rays.png", 0, 0, 1900, 1900, 0.0, SNOW, 90, -40, 427, 483)
    rays.at(483, "linear", rot=-300.0)
    hexm = s.tex("hex.png", 0, 0, 2 * 250 / 0.9, 2 * 250 / 0.9, 30.0, SNOW, 0, -9, 427, 483)
    L.split.ramp(427, 429, 0.0, 0.006, "sineOut")
    L.split.ramp(481, 483, 0.006, 0.0, "sineIn")
    rot = 0.0
    for q in range(14):  # two bars a colour; the ring turns, changing direction with the colour
        bb = 427 + 4 * q
        col = PRISM[(q // 2) % 5]
        d = 60.0 if (q // 2) % 2 == 0 else -60.0
        P.to(bb, bb + 4, "linear", rot=rot + d)
        rot += d
        if q % 2 == 0:
            for k in K:
                k.at(bb, col=mix(col, WHITE, 0.25))
            core.at(bb, "linear", color=core.kf["color"].value(bb)).at(bb + 1, "quadOut", color=mix(col, WHITE, 0.5))
            rays.at(bb, "linear", color=rays.kf["color"].value(bb)).at(bb + 1, "quadOut", color=col)
            G.bgc(bb, mix((16, 16, 50), col, 0.16), 244, 1)
            tunnel(s, bb, bb + 8, 1, col, 110, -24, 2, 60, 2900, 30.0)
            if q:
                G.flash(bb, col, 120, 1)
    for b, o in ev.items():
        if o["K"] > 0.45:
            L.punch(b, 0.035 * min(1.3, 0.6 + 0.5 * o["K"]), 1)
            G.shake(b, 7, 0.25, 0.3)
            ripple(s, b, 0, 0, 40, 250, SNOW, 190, -7, 1)
        if is_snare(o):
            L.split.pulse(b, 0.022, F(3, 4))
            G.flash(b, SNOW, 34, F(1, 2))
            shards(s, b, 0, 0, 6, 270, 620, 260, 30, SNOW, F(3, 4), 28, 150, phase=float(P.v("rot")) % 60)
    chart_prism(X, ev, 427, 483, 250.0, 6.5, 4)
    X.fx["kaleido"].add(457, 459, amount=[(457, 0.0, "quadOut"), (F(915, 2), 1.0, "linear"), (459, 1.0, "linear")], sides=6.0,
                        angle=[(457, 0.0, "linear"), (459, 60.0, "linear")], source=90.0)
    X.fx["kaleido"].add(467, 483, amount=[(467, 0.0, "sineOut"), (469, 0.7, "linear"), (481, 0.7, "quadIn"), (483, 0.0, "linear")],
                        sides=6.0, angle=[(467, 0.0, "linear"), (483, -120.0, "linear")], source=30.0)
    # ---- bar 120: the light folds back into a point
    G.flash(483, WHITE, 230, 1)
    G.shake(483, 20, 0.8, 0.4)
    L.punch(483, 0.05, 2)
    P.to(483, 487, "quadIn", rot=rot + 120.0)
    for i in range(6):
        phi = math.radians(90 - 60 * i)
        K[i].to(483, 487, "expoIn", x=0, y=0, sx=0.0)
        K[i].at(487, a=0)
    for k, (bb, n_) in enumerate(((483, 6), (484, 2), (F(969, 2), 3), (F(971, 2), 2), (F(973, 2), 3), (F(1947, 4), 6))):
        for q in range(n_):
            N.add(K[(k + q * (6 // n_)) % 6], bb, 0, FLICK if n_ == 3 else TAP, vis=0.25)
        L.punch(bb, 0.025, F(1, 2))
    L.wash.ramp(486, 487, 0.0, 1.0, "expoIn")
    glow(s, 0, 0, 300, WHITE, 255, 30, 483, 487).at(487, "expoIn", w=2800, h=2800)


SCENES = [intro, build_up, drop1, drop1b, breakdown, chorus1, swing_scene, drop2]
