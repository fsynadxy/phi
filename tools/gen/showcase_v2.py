"""华鸟风月 — showcase v2 ("暴力版"): same structure and song, every dimension pushed harder.

Extra devices compared to v1:
  * a root "camera" line that every scene line hangs from -> whole-screen shake / tilt / spin
  * the four characters of the title slammed onto the screen at the four biggest drops
  * denser charting (16th streams, doubles, 32nd runs), higher and discontinuous flow speed
    (freeze-then-rush), teleporting / snapping lines, strobe washes, per-bar shockwaves
"""
import math
import random

import showcase as base
from chartlib import DRAG, EPSB, FLICK, HOLD, TAP, frac, hsv, mix
from showcase import (AMBER, BLACK, CYAN, GOLD, ICE, LILAC, MAGENTA, PALE, ROSE, TEAL, VIOLET, WHITE, Lane, RX, RY,
                      groove, harmonic_hits, kfv, pitch_x, place, pulses)
import music as M

B = M.B
R = random.Random(20261109)

INFO = dict(base.INFO)
INFO.update({
    "level": "SP Lv.!?",
    "difficulty": 16.0,
    "tip": "观赏谱 · 暴力版 · 建议开启 Autoplay 观看",
    "tags": ["观赏谱", "showcase", "autoplay", "暴力版"],
    "intro": "华鸟风月 · 暴力版：同一首歌，所有方面都加码。",
})
RED = (255, 70, 90)


# ------------------------------------------------------------------ devices
def shared2(ctx):
    S = {}
    S["cam"] = cam = ctx.line("camera")  # invisible root: everything hangs from it
    S["curtain"] = ctx.line("curtain", tex="white.png", z=-40, color=BLACK, sx=24, sy=13.5)
    S["blackout"] = ctx.line("blackout", tex="white.png", z=55, color=BLACK, sx=24, sy=13.5)
    S["flash"] = ctx.line("flash", tex="white.png", z=60, color=WHITE, sx=24, sy=13.5)
    S["wash"] = ctx.line("colour_wash", tex="white.png", z=-35, color=BLACK, sx=24, sy=13.5)
    S["strobe"] = ctx.line("strobe", tex="white.png", z=-34, color=WHITE, sx=24, sy=13.5)
    S["eq"] = [ctx.line(f"eq{i}", tex="eqbar.png", z=-20, x=RX(-0.94 + i * 0.125), y=-450, color=CYAN, sx=2.2,
                        sy=0.0, father=cam.index) for i in range(16)]
    S["eqtop"] = [ctx.line(f"eqtop{i}", tex="eqbar.png", z=-20, x=RX(0.94 - i * 0.125), y=450, rot=180, color=CYAN,
                           sx=2.2, sy=0.0, father=cam.index) for i in range(16)]
    S["rings"] = [ctx.line(f"ripple{i}", tex="ring.png", z=-10, color=GOLD, sx=0.3, sy=0.3, father=cam.index)
                  for i in range(4)]
    S["glow"] = ctx.line("core_glow", tex="glow.png", z=-12, color=GOLD, sx=1.5, sy=1.5, father=cam.index)
    S["rain"] = ctx.line("rain", y=-600, speed=13.0)  # off-screen catcher for decorative fake notes
    return S


def L(ctx, S, name, **kw):
    """scene line hanging from the camera."""
    kw.setdefault("father", S["cam"].index)
    return ctx.line(name, **kw)


def shake(ctx, S, beats, amp=10.0, rot=1.0, dur=0.3):
    cam = S["cam"]
    pulses(ctx, cam, "moveX", beats, lambda b: R.choice((-1, 1)) * amp * R.uniform(0.6, 1.0), dur, "quadOut", layer=1)
    pulses(ctx, cam, "moveY", beats, lambda b: R.choice((-1, 1)) * amp * R.uniform(0.6, 1.0), dur, "quadOut", layer=1)
    if rot:
        pulses(ctx, cam, "rotate", beats, lambda b: R.choice((-1, 1)) * rot, dur * 1.4, "quadOut", layer=1)


def strobe(ctx, S, beats, colors, amp=70, dur=0.5):
    st = S["strobe"]
    col = ctx.tl(st, "color")
    for k, b in enumerate(sorted(beats)):
        col.jump(b, colors[k % len(colors)])
    pulses(ctx, st, "alpha", beats, amp, dur, "quadOut", layer=0)


def flash(ctx, S, b, peak=255, dur=1.0, color=WHITE):
    base.flash(ctx, S, b, peak=peak, dur=dur, color=color, ease="expoOut")


def blackout(ctx, S, b0, b1):
    a = ctx.tl(S["blackout"], "alpha")
    a.jump(b0, 255).wait(b1).jump(b1, 0)


def slam(ctx, S, b, text, scale=5.2, color=WHITE, life=3.0, y=40):
    ln = ctx.line(f"slam_{text}", z=-6, y=y, color=color, sx=scale * 1.7, sy=scale * 1.7, father=S["cam"].index)
    ln.ev("text", 0, EPSB, text, text)
    a, sx, sy = ctx.tl(ln, "alpha"), ctx.tl(ln, "scaleX"), ctx.tl(ln, "scaleY")
    a.jump(b, 255).to(frac(b) + frac(life), 0, "quadIn")
    for t in (sx, sy):
        t.wait(b).to(frac(b) + frac(1, 2), scale, "expoOut").to(frac(b) + frac(life), scale * 1.12, "linear")
    return ln


def rain(ctx, S, b0, b1, per_beat=2, alpha=70):
    ln = S["rain"]
    b = float(b0)
    while b < b1:
        for _ in range(per_beat):
            t = b + R.random()
            if t < b1:
                ln.note(R.choice((DRAG, DRAG, TAP, FLICK)), frac(t) + frac(1, 96), R.uniform(-620, 620), alpha=alpha,
                        fake=True, speed=R.uniform(0.8, 1.3))
        b += 1


def wash_plan(ctx, S, plan):
    w = S["wash"]
    a, col = ctx.tl(w, "alpha"), ctx.tl(w, "color")
    for b0, b1, c_, al in plan:
        col.jump(b0 - 1, c_)
        a.wait(b0 - 1).to(b0, al, "sineOut").wait(b1 - 1).to(b1, 0, "sineIn")


def chroma_track(ctx, b0, b1, strong=0.024, weak=0.012, rest=0.003, step=1.0):
    pts = []
    k = 0
    b = float(b0)
    while b < b1 - 1e-6:
        pts.append((b, strong if k % 4 == 0 else weak, "quadOut"))
        pts.append((b + step * 0.9, rest, "linear"))
        b += step
        k += 1
    pts.append((b1, 0.0, "linear"))
    ctx.fx("chromatic", b0, b1, power=kfv(*pts), sampleCount=6.0)


def shockwaves(ctx, beats, life=1.6, width=0.12):
    for b in beats:
        ctx.fx("shockwave", b, b + life, progress=kfv((b, 0.02, "quadOut"), (b + life, 1.0, "linear")), width=width,
               distortion=0.8, expand=10.0)


def pixel_burst(ctx, b, size=28.0, dur=0.75):
    ctx.fx("pixel", b, b + dur, size=kfv((b, size, "quadOut"), (b + dur, 1.0, "linear")))


def glitch(ctx, b0, b1, power=0.07):
    ctx.fx("glitch", b0, b1, power=power, rate=0.9, speed=18.0, blockCount=24.0, colorRate=0.016)


ROLE = {"kick": TAP, "clap": FLICK, "off": DRAG, "six": DRAG}


# ================================================================== scenes
def prelude(ctx, S):
    c = ctx
    title = c.line("title_open", z=-6, y=70, color=WHITE, sx=2.6, sy=2.6, father=S["cam"].index)
    title.ev("text", 0, EPSB, "华  鸟  风  月", "华  鸟  风  月")
    c.tl(title, "alpha").jump(B(0), 255).wait(B(1)).to(B(2, 2), 0, "quadIn")
    c.tl(title, "scaleX").wait(B(0)).to(B(0, 0.5), 2.2, "expoOut").to(B(2, 2), 2.5, "linear")
    c.tl(title, "scaleY").wait(B(0)).to(B(0, 0.5), 2.2, "expoOut").to(B(2, 2), 2.5, "linear")
    flash(c, S, B(0), 255, 2.0)
    shockwaves(c, [B(0)], 2.0, 0.1)
    pixel_burst(c, B(0), 22, 1.0)

    main = L(c, S, "v2_main", color=PALE, y=-220, sx=0.0, speed=9.0, z=3)
    top = L(c, S, "v2_top", color=ROSE, y=230, sx=0.0, speed=9.0, z=3)
    c.tl(main, "alpha").jump(B(0), 255)
    c.tl(main, "scaleX").wait(B(0)).to(B(0, 1), 1.0, "expoOut")
    ta = c.tl(top, "alpha")
    ta.jump(B(8), 240)
    c.tl(top, "scaleX").wait(B(8)).to(B(8, 0.5), 1.0, "expoOut")
    # teleports on the phrase grid
    my, mr = c.tl(main, "moveY"), c.tl(main, "rotate")
    spots = [(4, -140, 9), (8, -250, -6), (12, -170, 12), (16, -230, 0)]
    for bar, y, r in spots:
        my.wait(B(bar)).to(B(bar, 0.25), y, "backOut")
        mr.wait(B(bar)).to(B(bar, 0.25), r, "backOut")
    # phrase 3: violent opposite sways every two beats
    tr = c.tl(top, "rotate")
    for k in range(16):
        b = B(16) + 2 * k
        amp = 14 if k % 2 == 0 else -14
        mr.wait(b).to(b + 2, amp, "quadInOut")
        tr.wait(b).to(b + 2, -amp, "quadInOut")
    my.wait(B(24)).to(B(26), 0, "expoIn")
    c.tl(top, "moveY").wait(B(24)).to(B(26), 0, "expoIn")
    mr.wait(B(24)).to(B(26), 0, "quadOut")
    tr.wait(B(24)).to(B(26), 0, "quadOut")
    ta.wait(B(26) - 0.5).to(B(26), 0, "linear")
    c.tl(main, "color").wait(B(24)).to(B(27), VIOLET, "linear")
    shake(c, S, [B(bar, k) for bar in range(8, 24) for k in range(4)], 5, 0.4, 0.25)
    chroma_track(c, B(8), B(27), 0.012, 0.006, 0.0015, 1.0)
    rain(c, S, B(16), B(27), 2, 60)
    # notes
    lm, lt = Lane(-430, 430), Lane(-430, 430)
    g = groove(0, 27, beat_thr=0.45, off_thr=0.62, six_thr=0.95, fill_bars=(23, 24, 25, 26), fill_thr=0.6)
    for i, (b, role, v) in enumerate(g):
        bar = int((b - 2) // 4)
        kind = ROLE[role]
        if bar < 8:
            if role in ("kick", "clap"):
                place(main, TAP, b, lm.put(b, [-260, 260, -90, 90][i % 4]), "kick", lm)
            elif role == "off":
                main.note(DRAG, b, lm.put(b, pitch_x(int((b - 2) * 4), 360)))
        elif bar < 16:
            if role in ("kick", "clap"):
                place(main, kind, b, lm.put(b, [-280, 280][i % 2]), role, lm)
            else:
                top.note(DRAG, b, lt.put(b, 340 * math.sin(b * 1.3)), above=False)
        else:
            if role in ("kick", "clap"):
                main.note(kind, b, lm.put(b, -240 if i % 2 else 240))
                if (b - 2) % 2 == 0:
                    top.note(TAP, b, lt.put(b, 240 if i % 2 else -240), above=False)
            else:
                (main if i % 2 else top).note(DRAG, b, (lm if i % 2 else lt).put(b, 380 * math.sin(b * math.pi / 2)),
                                              above=bool(i % 2))
    main.note(FLICK, B(26, 3.5), 0)
    return main


def ascent(ctx, S, main):
    c = ctx
    b0, b1 = B(27), B(34)
    mirror = c.line("v2_mirror", father=main.index, rot=180, sx=1.0, speed=1.0, color=VIOLET)
    c.tl(mirror, "alpha").jump(b0, 0)  # invisible: carries notes from the other side
    y, sp, rot = c.tl(main, "moveY"), c.tl(main, "speed"), c.tl(main, "rotate")
    y.wait(b0).to(b0 + 1, -90, "expoOut").wait(B(28)).to(B(33, 2), 0, "quadIn")
    sp.wait(b0).to(B(33, 3), 14.5, "linear")
    msp = c.tl(mirror, "speed")
    msp.wait(b0).jump(b0, 10.0).to(B(33, 3), 14.5, "linear")
    rot.wait(B(28)).to(B(31), 360, "quadIn").to(B(33, 2.75), 360 * 5, "expoIn").jump(B(33, 2.75) + EPSB, 0)
    c.fx("vignette", b0, b1, extend=kfv((b0, 0.25, "linear"), (b1, 0.7, "linear")),
         radius=kfv((b0, 15.0, "quadIn"), (b1, 2.6, "linear")))
    c.fx("pixel", B(31), B(33, 3), size=kfv((B(31), 1.0, "quadIn"), (B(33, 3), 7.0, "linear")))
    glitch(c, B(33), B(33, 3), 0.05)
    c.tl(S["curtain"], "alpha").wait(b0).to(B(33, 2), 140, "quadIn").jump(b1, 0)
    blackout(c, S, B(33, 3), b1)
    beats = [B(27) + k for k in range(16)] + [B(31) + frac(k, 2) for k in range(16)] + [B(33) + frac(k, 4) for k in range(11)]
    amp_of = {}
    for b in beats:
        amp_of[b] = 4 + 16 * (float(b) - b0) / (b1 - b0)
    pulses(c, S["cam"], "moveX", beats, lambda b: R.choice((-1, 1)) * amp_of[frac(b)], 0.25, "quadOut", layer=1)
    pulses(c, S["cam"], "moveY", beats, lambda b: R.choice((-1, 1)) * amp_of[frac(b)], 0.25, "quadOut", layer=1)
    for k in range(10):
        x = -620 + k * 135 + R.uniform(-40, 40)
        st = L(c, S, f"streak{k}", tex="pillar.png", z=-15, x=x, y=-700, rot=180, color=LILAC, sx=0.6, sy=1.4)
        a, yy = c.tl(st, "alpha"), c.tl(st, "moveY")
        a.wait(b0).to(b0 + 1, 90, "sineOut").wait(b1 - 0.5).to(b1, 0, "linear")
        b = frac(b0) + frac(R.randint(0, 3), 4)
        per = frac(1)
        while b + per <= b1:
            yy.jump(b, -760).to(b + per, 760, "quadIn")
            b += per
            per = frac(1, 2) if b >= B(31) else per
            per = frac(1, 4) if b >= B(33) else per
    lane = Lane(-260, 260)
    for bar in range(27, 33):
        for i in range(16):
            s = bar * 16 + i
            b = M.step_beat(s)
            v = max(M.perc(s), M.harm(s))
            if i % 4 == 0:
                x = lane.put(b, -240 if i % 8 else 240)
                main.note(TAP, b, x)
                if bar >= 30:
                    mirror.note(TAP, b, x)  # mirror line is flipped: same x lands on the opposite side
            elif i % 2 == 0 or (bar >= 29 and v > 0.45) or bar >= 31:
                (mirror if (bar >= 31 and i % 2) else main).note(DRAG, b, lane.put(b, 250 * math.sin(b * math.pi)))
    for k in range(22):  # 32nd run spiral
        b = B(33) + frac(k, 8)
        (main if k % 2 == 0 else mirror).note(DRAG, b, 250 * math.cos(k * 0.55))


def bloom(ctx, S, finale=False):
    c = ctx
    bar0, bar1 = (159, 168) if finale else (34, 43)
    b0, b1 = B(bar0), B(bar1)
    tag = "v2fin" if finale else "v2bloom"
    slam(c, S, b0, "月" if finale else "华", 5.4, GOLD if finale else WHITE)
    flash(c, S, b0, 255, 1.5, WHITE)
    pixel_burst(c, b0, 30, 0.75)
    c.fx("radialBlur", b0, b0 + 1.5, power=kfv((b0, 0.06, "quadOut"), (b0 + 1.5, 0.0, "linear")), sampleCount=12.0)
    shockwaves(c, [B(b) for b in range(bar0, bar1)] + ([B(b, 2) for b in range(bar0, bar1)] if finale else []), 1.4)
    chroma_track(c, b0, b1, 0.03 if finale else 0.026, 0.014, 0.004, 0.5 if finale else 1.0)
    for bb in range(bar0 + 2, bar1, 2):
        c.fx("radialBlur", B(bb), B(bb) + 0.75, power=kfv((B(bb), 0.03, "quadOut"), (B(bb) + 0.75, 0.0, "linear")), sampleCount=8.0)
    glitch(c, B(bar1 - 1, 2), b1, 0.08)
    beats = [b0 + k for k in range(int(b1 - b0))]
    strobe(c, S, beats, [MAGENTA, GOLD] if not finale else [MAGENTA, CYAN, GOLD, WHITE], 80 if finale else 65, 0.45)
    shake(c, S, beats if not finale else [b0 + frac(k, 2) for k in range(int(b1 - b0) * 2)], 14, 1.4, 0.28)
    hub = L(c, S, f"{tag}_hub")
    hr = c.tl(hub, "rotate")
    ang = 0
    for k, bb in enumerate(range(bar0, bar1 - 1)):
        ang += 135 if k % 2 == 0 else -90
        hr.wait(B(bb)).to(B(bb, 1), ang, "expoOut")
    hr.wait(B(bar1 - 1)).to(b1, ang + 720, "expoIn")
    npet = 12 if finale else 8
    rho = 0.30
    petals = []
    cols = [GOLD, MAGENTA, CYAN, WHITE] if finale else [GOLD, MAGENTA]
    for k in range(npet):
        phi = 360.0 * k / npet + 90
        p = c.line(f"{tag}_petal{k}", father=hub.index, x=RX(rho * math.cos(math.radians(phi))),
                   y=RY(rho * math.sin(math.radians(phi))), rot=-(phi + 90), color=cols[k % len(cols)], sx=0.0,
                   speed=6.0, z=4)
        c.tl(p, "alpha").jump(b0, 255).wait(b1 - 0.25).to(b1, 0, "linear")
        c.tl(p, "scaleX").wait(b0).to(b0 + 0.5, 0.045, "backOut")
        pulses(c, p, "moveX", beats, RX(0.05 * math.cos(math.radians(phi))), 0.5, "quadOut", layer=1)
        pulses(c, p, "moveY", beats, RY(0.05 * math.sin(math.radians(phi))), 0.5, "quadOut", layer=1)
        petals.append(p)
    blades = []
    for k in range(2):
        bl = c.line(f"{tag}_blade{k}", father=hub.index, rot=90 * k, color=WHITE if k == 0 else ROSE, sx=0.0,
                    speed=10.0, z=5)
        c.tl(bl, "alpha").jump(b0, 235).wait(b1 - 0.25).to(b1, 0, "linear")
        c.tl(bl, "scaleX").wait(b0).to(b0 + 0.75, 0.42, "expoOut")
        blades.append(bl)
    g = S["glow"]
    c.tl(g, "color").jump(b0 - 0.5, WHITE if finale else GOLD)
    c.tl(g, "alpha").wait(b0 - 0.5).to(b0, 170, "linear").wait(b1 - 1).to(b1, 0, "linear")
    gx, gy = c.tl(g, "scaleX"), c.tl(g, "scaleY")
    for b in beats:
        gx.wait(b).jump(b, 1.7).to(b + 0.8, 0.9, "quadOut")
        gy.wait(b).jump(b, 1.7).to(b + 0.8, 0.9, "quadOut")
    base.ripples(c, S, beats, lambda b: (GOLD if int(b) % 2 else MAGENTA), 2.0, 1.2, 160)
    base.eq_run(c, S, b0, b1, lambda u: hsv(0.9 + 0.25 * u, 0.6, 1.0), amax=95, hmax=2.4)
    if finale:
        base.eq_run(c, {"eq": S["eqtop"]}, b0, b1, lambda u: hsv(0.5 + 0.3 * u, 0.6, 1.0), amax=95, hmax=2.4)
    gr = groove(bar0, bar1, beat_thr=0.4, off_thr=0.55, six_thr=0.8 if finale else 0.9, fill_bars=(bar1 - 2, bar1 - 1), fill_thr=0.55)
    lanes = [Lane(-320, 320), Lane(-320, 320)]
    k = 0
    for i, (b, role, v) in enumerate(gr):
        kind = ROLE[role]
        if role in ("kick", "clap"):
            j = i % 2
            x = (310 if (i // 2) % 2 else -310) if j == 0 else (260 if (i // 2) % 2 else -260)
            blades[j].note(kind, b, lanes[j].put(b, x), above=(i % 3 != 0))
            if (b - 2) % 2 == 0:  # double on 1 and 3
                blades[1 - j].note(TAP, b, lanes[1 - j].put(b, -x), above=(i % 3 == 0))
        else:
            petals[k % npet].note(kind, b, 0, visible=0.42)
            k += 5 if finale else 3
    if finale:
        bot = L(c, S, "v2fin_bottom", color=WHITE, y=-330, sx=0.0, speed=13.0, z=3)
        c.tl(bot, "alpha").jump(b0, 255).wait(b1 - 0.5).to(b1, 0, "linear")
        c.tl(bot, "scaleX").wait(b0).to(b0 + 0.5, 1.0, "expoOut")
        pulses(c, bot, "moveY", beats, -24, 0.4, "quadOut", layer=1)
        lane = Lane(-450, 450)
        for (b, role, v) in groove(bar0, bar1, beat_thr=0.4, off_thr=0.5, six_thr=0.75, fill_bars=(bar1 - 1,), fill_thr=0.5):
            if role in ("off", "six") and b < B(bar1 - 1):
                bot.note(DRAG, b, lane.put(b, 420 * math.sin(b * math.pi / 2 + 0.5)))
        rain(c, S, b0, b1, 3, 70)
        cam_r = c.tl(S["cam"], "rotate")
        cam_r.wait(B(bar1 - 1)).to(b1, 360, "expoIn").jump(b1 + EPSB, 0)


def breath(ctx, S):
    c = ctx
    b0, b1 = B(43), B(47)
    ln = L(c, S, "v2_breath", color=AMBER, sx=0.0, speed=6.5, z=2)
    a, sx, rot, sp = c.tl(ln, "alpha"), c.tl(ln, "scaleX"), c.tl(ln, "rotate"), c.tl(ln, "speed")
    a.jump(b0, 255).wait(b1 - 0.25).to(b1, 0, "linear")
    sx.wait(b0).to(b0 + 1, 0.33, "expoOut").wait(B(46, 2)).to(b1, 1.0, "quadIn")
    rot.wait(b0).to(B(44, 2), 90, "quadInOut").wait(B(45)).to(B(45, 0.5), 0, "expoOut")
    # freeze, then everything rushes in
    sp.wait(B(44, 2)).jump(B(44, 2), 0.0).wait(B(45)).jump(B(45), 30.0).wait(B(45, 0.5)).jump(B(45, 0.5), 8.0)
    c.tl(S["curtain"], "alpha").wait(B(44, 2)).to(B(44, 2.25), 110, "linear").wait(B(45)).jump(B(45), 0)
    c.fx("grayscale", B(44, 2), B(45), factor=0.85)
    flash(c, S, B(45), 200, 0.75, AMBER)
    shockwaves(c, [B(45)], 1.2)
    glitch(c, B(46, 2), b1, 0.06)
    lane = Lane(-420, 420)
    ln.note(HOLD, B(43), -220, end=B(43, 3))
    ln.note(TAP, B(43, 1), 220)
    ln.note(TAP, B(43, 2), -40)
    ln.note(HOLD, B(44), 220, end=B(44, 2))
    for s in harmonic_hits(45, 46, q=0.55, min_gap=2):
        b = M.step_beat(s)
        if b < B(45, 0.75):
            continue
        ln.note(TAP if s % 4 == 0 else DRAG, b, lane.put(b, pitch_x(s, 360)))
    for k in range(4):
        ln.note(TAP, B(45) + frac(k, 8), -300 + 200 * k)
    for k, s in enumerate(range(46 * 16, 47 * 16)):
        ln.note(DRAG if s % 4 else TAP, M.step_beat(s), -420 + k * 56)
    ln.note(FLICK, B(46, 3.75), 0)


def pulse(ctx, S):
    c = ctx
    b0, b1 = B(47), B(75)
    slam(c, S, b0, "鸟", 5.2, CYAN)
    flash(c, S, b0, 230, 1.0)
    pixel_burst(c, b0, 24, 0.5)
    hub = L(c, S, "v2_box_hub")
    sides = []
    # (name, local x, local y, rpe rot, half-length scaleX, colour)
    spec = [("bottom", 0, RY(-0.38), 0, 0.127, CYAN), ("top", 0, RY(0.38), 180, 0.127, ROSE),
            ("left", RX(-0.38), 0, 90, 0.127, VIOLET), ("right", RX(0.38), 0, -90, 0.127, GOLD)]
    for k, (nm, x, y, r, sxv, col) in enumerate(spec):
        ln = c.line(f"v2_box_{nm}", father=hub.index, x=x, y=y, rot=r, color=col, sx=0.0, speed=8.0, z=3)
        c.tl(ln, "alpha").jump(b0 + (0 if k < 2 else 16), 255).wait(b1 - 0.25).to(b1, 0, "linear")
        c.tl(ln, "scaleX").wait(b0 + (0 if k < 2 else 16)).to(b0 + (0.5 if k < 2 else 16.5), sxv, "expoOut")
        sides.append(ln)
    hr = c.tl(hub, "rotate")
    for k, bar in enumerate(range(59, 67)):
        hr.wait(B(bar)).to(B(bar, 0.5), 90 * (k + 1) * (1 if k % 4 < 2 else 1), "backOut")
    hr.wait(B(67)).to(B(73), 720 + 720, "linear").to(b1, 720 + 720 + 450, "expoIn")
    beats = [b0 + k for k in range(int(b1 - b0))]
    for ln, (nm, x, y, r, sxv, col) in zip(sides, spec):
        d = 18
        if nm in ("bottom", "top"):
            pulses(c, ln, "moveY", beats, -d if nm == "bottom" else d, 0.4, "quadOut", layer=1)
        else:
            pulses(c, ln, "moveX", beats, -d if nm == "left" else d, 0.4, "quadOut", layer=1)
    base.eq_run(c, S, b0, b1, lambda u: mix(CYAN, VIOLET, u), amax=90, hmax=2.3)
    base.eq_run(c, {"eq": S["eqtop"]}, B(51), b1, lambda u: mix(ROSE, GOLD, u), amax=80, hmax=2.0)
    shake(c, S, beats, 9, 0.9, 0.25)
    strobe(c, S, [b for b in beats if (b - b0) % 2 == 1], [CYAN, ROSE], 45, 0.4)
    chroma_track(c, b0, b1, 0.016, 0.009, 0.002, 1.0)
    shockwaves(c, [B(b) for b in range(47, 75, 4)], 1.5)
    for fb in (57, 73):
        glitch(c, B(fb, 2), B(fb + 1, 0), 0.06)
        glitch(c, B(fb + 1, 2), B(fb + 2), 0.08)
    gr = groove(47, 75, beat_thr=0.42, off_thr=0.62, six_thr=0.95, fill_bars=(57, 58, 73, 74), fill_thr=0.58)
    lanes = [Lane(-200, 200) for _ in range(4)]
    for i, (b, role, v) in enumerate(gr):
        bar = int((b - 2) // 4)
        kind = ROLE[role]
        if role == "kick":
            place(sides[0], TAP, b, lanes[0].put(b, [-190, 190, -60, 60][i % 4]), "kick", lanes[0])
            if bar >= 51 and (b - 2) % 4 == 0:
                sides[1].note(TAP, b, lanes[1].put(b, [190, -190][i % 2]))
        elif role == "clap":
            j = 2 + (i % 2) if bar >= 51 else 1
            sides[j].note(FLICK, b, lanes[j].put(b, [-120, 120][i % 2]))
        else:
            j = [1, 2, 0, 3][(i + bar) % 4] if bar >= 51 else (1 if role == "off" else 0)
            sides[j].note(DRAG, b, lanes[j].put(b, 190 * math.sin(b * 1.7)))


def echo(ctx, S):
    c = ctx
    b0, b1 = B(75), B(91)
    flash(c, S, b0, 200, 0.75, TEAL)
    shockwaves(c, [b0, B(83)], 1.5)
    pends = []
    for k, (col, arm) in enumerate(((TEAL, -950), (ROSE, -1050), (GOLD, -880))):
        start = b0 if k == 0 else (B(79) if k == 1 else B(83))
        sgn0 = 1 if k % 2 == 0 else -1
        for ghost, lag, al in ((False, 0, 250), (True, frac(1, 3), 90)):
            pv = L(c, S, f"v2_echo_pivot{k}{'g' if ghost else ''}", y=700)
            ln = c.line(f"v2_echo{k}{'_ghost' if ghost else ''}", father=pv.index, y=arm, color=col, sx=0.0,
                        speed=10.0, z=2 if ghost else 4)
            c.tl(ln, "alpha").jump(start, al).wait(b1 - 0.5).to(b1, 0, "linear")
            c.tl(ln, "scaleX").wait(start).to(start + 0.5, 0.36, "expoOut")
            r = c.tl(pv, "rotate")
            b = frac(start) + lag
            sgn = sgn0
            r.wait(b).to(b + 1 + k, sgn * 24, "sineOut")
            b += 1 + k
            while b + 4 <= frac(b1) - 1:
                sgn = -sgn
                r.to(b + 4, sgn * 24, "sineInOut")
                b += 4
            r.to(frac(b1) + lag, 0, "quadIn")
            if not ghost:
                pends.append(ln)
    beats = [b0 + k for k in range(int(b1 - b0))]
    shake(c, S, beats, 7, 0.8, 0.25)
    chroma_track(c, b0, b1, 0.014, 0.008, 0.005, 1.0)
    strobe(c, S, [b for b in beats if (b - b0) % 4 == 0], [TEAL, ROSE, GOLD], 55, 1.0)
    glitch(c, B(89, 2), B(91), 0.07)
    gr = groove(75, 91, beat_thr=0.42, off_thr=0.62, six_thr=0.95, fill_bars=(89, 90), fill_thr=0.58)
    lanes = [Lane(-280, 280) for _ in range(3)]
    for i, (b, role, v) in enumerate(gr):
        bar = int((b - 2) // 4)
        avail = 1 if bar < 79 else (2 if bar < 83 else 3)
        j = i % avail
        kind = ROLE[role]
        x = lanes[j].put(b, 240 * math.sin(b * 1.1) if role in ("off", "six") else [-190, 190][i % 2])
        if place(pends[j], kind, b, x, role, lanes[j]):
            continue
        if role in ("kick", "clap"):
            for spd, al in ((1.2, 120), (1.4, 70), (1.6, 35)):
                pends[j].note(kind, frac(b) + frac(1, 192), x, speed=spd, alpha=al, fake=True)


def orbit(ctx, S):
    c = ctx
    b0, b1 = B(91), B(115)
    flash(c, S, b0, 200, 0.75, GOLD)
    shockwaves(c, [b0, B(99), B(107)], 1.5)
    minute = L(c, S, "v2_minute", color=GOLD, sx=0.0, speed=8.5, z=4)
    hour = L(c, S, "v2_hour", color=PALE, sx=0.0, sy=2.0, speed=7.5, z=3)
    sec = L(c, S, "v2_second", color=RED, sx=0.0, sy=0.6, z=2)
    for ln, length, al in ((minute, 0.2, 255), (hour, 0.12, 240), (sec, 0.26, 150)):
        c.tl(ln, "alpha").jump(b0, al).wait(b1 - 0.5).to(b1, 0, "linear")
        c.tl(ln, "scaleX").wait(b0).to(b0 + 1, length, "expoOut")
    mr, hr, sr = c.tl(minute, "rotate"), c.tl(hour, "rotate"), c.tl(sec, "rotate")
    mr.wait(b0).to(B(107), 360 * 8, "linear").to(B(113), 360 * 8 - 540, "quadInOut").to(B(114, 3), 360 * 12, "expoIn")
    hr.wait(b0).to(B(113), -720, "linear").to(B(114, 3), 0, "expoIn")
    sr.wait(b0)
    for k in range(int(b1 - b0) * 2):
        sr.wait(frac(b0) + frac(k, 2)).to(frac(b0) + frac(k, 2) + frac(1, 8), 22.5 * (k + 1), "backOut")
    for k, (rad, col, per) in enumerate(((0.22, CYAN, 2), (0.36, MAGENTA, 3), (0.5, GOLD, 4))):
        ring = L(c, S, f"v2_oring{k}", tex="ring.png", z=-14, color=col, sx=rad * 675 / 240.6, sy=rad * 675 / 240.6)
        c.tl(ring, "alpha").wait(b0).to(b0 + 2, 70, "sineOut").wait(b1 - 2).to(b1, 0, "sineIn")
        hubp = L(c, S, f"v2_ophub{k}")
        c.tl(hubp, "rotate").wait(b0).to(b1, -360 * (b1 - b0) / (per * 4), "linear")
        pl = c.line(f"v2_oplanet{k}", tex="glow.png", father=hubp.index, x=RX(rad), z=-13, color=col, sx=0.36, sy=0.36)
        c.tl(pl, "alpha").wait(b0).to(b0 + 2, 240, "sineOut").wait(b1 - 2).to(b1, 0, "sineIn")
    beats = [b0 + k for k in range(int(b1 - b0))]
    base.ripples(c, S, [b for b in beats if (b - b0) % 2 == 0], lambda b: GOLD, 1.6, 2.0, 110)
    shake(c, S, beats, 6, 0.8, 0.25)
    strobe(c, S, [b for b in beats if (b - b0) % 2 == 1], [GOLD, WHITE], 40, 0.4)
    chroma_track(c, b0, b1, 0.012, 0.007, 0.002, 1.0)
    glitch(c, B(113, 2), B(115), 0.07)
    gr = groove(91, 115, beat_thr=0.42, off_thr=0.62, six_thr=0.95, fill_bars=(105, 106, 113, 114), fill_thr=0.58)
    lm, lh = Lane(-325, 325), Lane(-250, 250)
    for i, (b, role, v) in enumerate(gr):
        kind = ROLE[role]
        side = (int(b * 2) % 2 == 0)
        if role == "clap" or (role == "kick" and (b - 2) % 4 == 0):
            place(hour, kind, b, lh.put(b, [-170, 170][i % 2]), role, lh, above=(i % 2 == 0))
            if role == "kick":
                minute.note(TAP, b, lm.put(b, [320, -320][i % 2]), above=not (i % 2 == 0))
        else:
            x = (320 if side else -320) * (0.45 + 0.55 * abs(math.cos(b * 0.7))) if role in ("off", "six") else (250 if side else -250)
            place(minute, kind, b, lm.put(b, x), role, lm, above=side)


def mirage(ctx, S):
    c = ctx
    b0, b1 = B(115), B(135)
    flash(c, S, b0, 210, 0.75, VIOLET)
    c.fx("noise", b0, b1, power=0.006, seed=81.0)
    lines = []
    for k, col in enumerate((VIOLET, MAGENTA)):
        ln = L(c, S, f"v2_tele{k}", color=col, sx=0.0, speed=11.0, z=4)
        c.tl(ln, "alpha").jump(b0, 255).wait(b1 - 0.25).to(b1, 0, "linear")
        c.tl(ln, "scaleX").wait(b0).to(b0 + 0.25, 0.3, "expoOut")
        lines.append(ln)
    spots = [(-160, -200, 0), (170, -120, 18), (0, -230, -14), (-120, 40, 180), (150, -60, 200), (0, -250, 8),
             (-200, -150, -25), (60, 60, 160), (180, -220, 12), (-60, -90, 195), (0, 0, 90), (0, -180, -8)]
    jumps = {0: [], 1: [b0 - 1]}
    c.tl(lines[1], "moveX").jump(b0 - 1, -spots[0][0])
    c.tl(lines[1], "moveY").jump(b0 - 1, spots[0][1] - 40)
    for k in range(int(b1 - b0)):
        b = b0 + k
        j = k % 2  # the two lines teleport on alternate beats
        ln = lines[j]
        x, y, r = spots[(k * 5 + j * 7) % len(spots)]
        if j == 1:
            x, y = -x, y - 40
        c.tl(ln, "moveX").jump(b, x)
        c.tl(ln, "moveY").jump(b, y)
        c.tl(ln, "rotate").jump(b, r)
        jumps[j].append(b)
        c.fx("glitch", b - 0.1, b + 0.2, power=0.08 if j == 0 else 0.05, rate=1.0, speed=24.0, blockCount=20.0, colorRate=0.02)
    pulses(c, S["cam"], "moveX", [b0 + 2 * k for k in range(int((b1 - b0) // 2))], lambda b: R.choice((-1, 1)) * 16, 0.3, "quadOut", layer=1)
    beats = [b0 + k for k in range(int(b1 - b0))]
    strobe(c, S, beats, [VIOLET, MAGENTA, WHITE], 50, 0.35)
    rain(c, S, b0, b1, 2, 55)
    for k in range(3):
        fr_ = L(c, S, f"v2_mframe{k}", tex="frame.png", z=-16, y=40, rot=45, color=(VIOLET, MAGENTA, LILAC)[k],
                sx=(1.3, 0.95, 0.6)[k], sy=(1.3, 0.95, 0.6)[k])
        c.tl(fr_, "alpha").wait(b0).to(b0 + 2, 60, "sineOut").wait(b1 - 2).to(b1, 0, "sineIn")
        c.tl(fr_, "rotate").wait(b0).to(b1, 45 + (360, -540, 720)[k], "linear")
    gr = groove(115, 135, beat_thr=0.4, off_thr=0.55, six_thr=0.85, fill_bars=(133, 134), fill_thr=0.55)
    lanes = [Lane(-260, 260), Lane(-260, 260)]
    spb = 60 / 123
    for i, (b, role, v) in enumerate(gr):
        since = [b - max(jb for jb in jumps[j] if jb <= b) for j in (0, 1)]
        j = 0 if since[0] >= since[1] else 1
        if since[j] < 0.75:
            continue
        kind = ROLE[role]
        lines[j].note(kind, b, lanes[j].put(b, 230 * math.sin(b * 1.9)), visible=since[j] * spb - 0.02)


def zenith(ctx, S):
    c = ctx
    b0, b1 = B(135), B(151)
    slam(c, S, b0, "风", 5.4, TEAL)
    flash(c, S, b0, 240, 1.0)
    pixel_burst(c, b0, 26, 0.6)
    hub = L(c, S, "v2_zen_hub")
    c.tl(hub, "rotate").wait(b0).to(B(143), 360, "linear").to(B(150), 360 * 4, "quadIn").to(b1, 360 * 4 + 90, "expoOut")
    arms = []
    for k in range(12):
        ln = c.line(f"v2_zen{k}", father=hub.index, rot=15 * k, sx=0.0, speed=10.0, color=hsv(k / 12, 0.5, 1.0), z=3)
        a = c.tl(ln, "alpha")
        for j in range(16):
            bb = B(135 + j)
            on = (k % 3) == (j % 3)
            a.wait(bb - 0.125 if j else bb).to(bb if j else bb + EPSB, 255 if on else 70, "linear")
        a.wait(b1 - 0.1).to(b1, 0, "linear")
        c.tl(ln, "scaleX").wait(b0).to(b0 + 0.5 + k * 0.08, 0.28, "expoOut").wait(b1 - 1).to(b1, 0.0, "expoIn")
        col = c.tl(ln, "color")
        for j in range(int(b1 - b0)):
            col.jump(b0 + j, hsv(k / 12 + j * 0.11, 0.55, 1.0))
        arms.append(ln)
    beats = [b0 + k for k in range(int(b1 - b0))]
    base.eq_run(c, S, b0, b1, lambda u: hsv(u * 0.9, 0.55, 1.0), amax=95, hmax=2.4)
    base.eq_run(c, {"eq": S["eqtop"]}, b0, b1, lambda u: hsv(0.45 + u * 0.9, 0.55, 1.0), amax=85, hmax=2.0)
    for bar in range(135, 151):
        c.fx("fisheye", B(bar), B(bar) + 1, power=kfv((B(bar), -0.07, "quadOut"), (B(bar) + 1, 0.0, "linear")))
    for bar in range(137, 151, 2):
        c.fx("radialBlur", B(bar, 2), B(bar, 2.75), power=kfv((B(bar, 2), 0.025, "quadOut"), (B(bar, 2.75), 0.0, "linear")), sampleCount=8.0)
    chroma_track(c, b0, b1, 0.022, 0.012, 0.003, 1.0)
    shake(c, S, beats, 11, 1.2, 0.25)
    strobe(c, S, beats, [hsv(i / 7, 0.6, 1.0) for i in range(7)], 55, 0.4)
    base.ripples(c, S, beats, lambda b: hsv((b % 12) / 12, 0.5, 1.0), 1.9, 1.3, 120)
    glitch(c, B(149, 2), B(151), 0.08)
    gr = groove(135, 151, beat_thr=0.4, off_thr=0.55, six_thr=0.85, fill_bars=(142, 149, 150), fill_thr=0.55)
    lanes = [Lane(-270, 270) for _ in range(12)]
    for i, (b, role, v) in enumerate(gr):
        bar = int((b - 2) // 4)
        on = [k for k in range(12) if k % 3 == (bar - 135) % 3]
        k = on[i % 4]
        kind = ROLE[role]
        x = (250 if i % 2 else -250) if role in ("kick", "clap") else 240 * math.sin(b * 1.3)
        place(arms[k], kind, b, lanes[k].put(b, x), role, lanes[k], above=(int(b * 2) % 2 == 0))
        if role == "kick" and (b - 2) % 2 == 0:
            k2 = on[(i + 2) % 4]
            arms[k2].note(TAP, b, lanes[k2].put(b, -x), above=(int(b * 2) % 2 == 1))


def memory(ctx, S):
    c = ctx
    b0, b1 = B(151), B(159)
    c.fx("grayscale", b0, b1, factor=kfv((b0, 1.0, "linear"), (B(157), 1.0, "quadIn"), (b1, 0.0, "linear")))
    c.fx("vignette", B(153), b1, extend=kfv((B(153), 0.25, "linear"), (b1, 0.7, "linear")),
         radius=kfv((B(153), 15.0, "quadIn"), (b1, 2.8, "linear")))
    c.fx("pixel", B(156), B(158, 3), size=kfv((B(156), 1.0, "quadIn"), (B(158, 3), 6.0, "linear")))
    ln = L(c, S, "v2_memory", color=PALE, y=-110, sx=0.0, speed=9.0, z=3)
    mir = c.line("v2_memory_mirror", father=ln.index, rot=180, speed=9.0, color=PALE)
    c.tl(mir, "alpha").jump(b0, 0)
    a, sx, y, sp, rot = (c.tl(ln, p) for p in ("alpha", "scaleX", "moveY", "speed", "rotate"))
    a.jump(b0, 255).wait(b1 - 0.25).to(b1, 0, "linear")
    sx.wait(b0).to(b0 + 1, 1.0, "expoOut")
    y.wait(B(152)).to(B(158, 2), 0, "quadIn")
    sp.wait(B(152)).to(B(158, 3), 15.0, "linear")
    c.tl(mir, "speed").wait(B(152)).to(B(158, 3), 15.0, "linear")
    rot.wait(B(154)).to(B(156), 360, "quadIn").to(B(158, 2.75), 360 * 5, "expoIn").jump(B(158, 2.75) + EPSB, 0)
    c.tl(S["curtain"], "alpha").wait(B(155)).to(B(158, 2), 140, "quadIn").jump(b1, 0)
    blackout(c, S, B(158, 3), b1)
    beats = [B(152) + frac(k, 2) for k in range(24)] + [B(155) + frac(k, 4) for k in range(48)]
    amp = {frac(b): 3 + 15 * (float(b) - b0) / (b1 - b0) for b in beats}
    pulses(c, S["cam"], "moveX", beats, lambda b: R.choice((-1, 1)) * amp[frac(b)], 0.2, "quadOut", layer=1)
    pulses(c, S["cam"], "moveY", beats, lambda b: R.choice((-1, 1)) * amp[frac(b)], 0.2, "quadOut", layer=1)
    rain(c, S, B(153), B(158, 3), 3, 50)
    lane = Lane(-260, 260)
    for bar in range(152, 158):
        for i in range(16):
            s = bar * 16 + i
            b = M.step_beat(s)
            v = max(M.perc(s), M.harm(s))
            if i % 4 == 0:
                x = lane.put(b, -240 if i % 8 else 240)
                ln.note(TAP, b, x)
                if bar >= 155:
                    mir.note(TAP, b, x)
            elif i % 2 == 0 or bar >= 155 or (bar >= 154 and v > 0.5):
                (mir if (bar >= 156 and i % 2) else ln).note(DRAG, b, lane.put(b, 250 * math.sin(b * math.pi)))
    for k in range(22):
        (ln if k % 2 == 0 else mir).note(DRAG, B(158) + frac(k, 8), -250 * math.cos(k * 0.55))


def coda(ctx, S):
    c = ctx
    b0 = B(168)
    end = B(176, 2)
    flash(c, S, b0, 255, 2.0)
    shockwaves(c, [b0], 2.5, 0.15)
    c.fx("radialBlur", b0, b0 + 2, power=kfv((b0, 0.05, "quadOut"), (b0 + 2, 0.0, "linear")), sampleCount=12.0)
    # debris: shards of every line fly outward
    for k in range(28):
        ang = R.uniform(0, 360)
        dist = R.uniform(0.6, 1.3)
        sh = L(c, S, f"v2_shard{k}", color=R.choice((GOLD, MAGENTA, CYAN, WHITE, ROSE, TEAL)), sx=R.uniform(0.02, 0.06),
               rot=R.uniform(0, 360), z=2)
        c.tl(sh, "alpha").jump(b0, 255).wait(b0 + 2).to(b0 + 6, 0, "quadIn")
        c.tl(sh, "moveX").wait(b0).to(b0 + 6, RX(dist * math.cos(math.radians(ang))), "expoOut")
        c.tl(sh, "moveY").wait(b0).to(b0 + 6, RY(dist * math.sin(math.radians(ang))), "expoOut")
        c.tl(sh, "rotate").wait(b0).to(b0 + 6, R.uniform(360, 1080) * R.choice((-1, 1)), "expoOut")
    ln = L(c, S, "v2_coda", color=PALE, y=-120, sx=0.0, speed=6.0, z=3)
    a, sx, y = c.tl(ln, "alpha"), c.tl(ln, "scaleX"), c.tl(ln, "moveY")
    a.wait(b0 + 3).to(b0 + 4, 255, "sineOut")
    sx.wait(b0 + 3).to(b0 + 5, 1.0, "expoOut").wait(B(172)).to(B(174), 0.34, "sineInOut").wait(B(174)).to(B(174, 1), 0.0, "expoIn")
    y.wait(B(172)).to(B(174), 0, "sineInOut")
    a.wait(B(174, 1)).to(B(174, 1.25), 0, "linear")
    flash(c, S, B(174), 255, 4.0)
    shockwaves(c, [B(174)], 3.0, 0.15)
    t = c.line("title_end", z=-6, y=40, color=WHITE, sx=2.4, sy=2.4)
    t.ev("text", 0, EPSB, "华  鸟  风  月", "华  鸟  风  月")
    c.tl(t, "alpha").wait(B(174)).to(B(174, 1), 255, "expoOut").wait(B(175, 2)).to(end + 2, 0, "sineIn")
    c.tl(t, "scaleX").wait(B(174)).to(end + 2, 2.7, "linear")
    c.tl(t, "scaleY").wait(B(174)).to(end + 2, 2.7, "linear")
    c.fx("vignette", B(174), end + 4, extend=kfv((B(174), 0.25, "linear"), (end + 4, 1.0, "linear")),
         radius=kfv((B(174), 15.0, "quadIn"), (end + 4, 1.2, "linear")))
    lane = Lane(-400, 400)
    for bar in range(169, 173):
        for i in range(0, 16, 2):
            s = bar * 16 + i
            if max(M.perc(s), M.harm(s)) > 0.45:
                b = M.step_beat(s)
                ln.note(TAP if i % 4 == 0 else DRAG, b, lane.put(b, pitch_x(s, 330) if i % 4 else [-220, 220][(s // 4) % 2]))
    ln.note(HOLD, B(173), -200, end=B(173, 1.5))
    ln.note(TAP, B(173), 200)
    ln.note(FLICK, B(173, 2), 0)
    ln.note(TAP, B(174), -150)
    ln.note(TAP, B(174), 150)


def make():
    ctx = base.Ctx()
    ctx.c.meta = dict(INFO, id="claude-showcase-v2")
    S = shared2(ctx)
    main = prelude(ctx, S)
    ascent(ctx, S, main)
    bloom(ctx, S, finale=False)
    breath(ctx, S)
    pulse(ctx, S)
    echo(ctx, S)
    orbit(ctx, S)
    mirage(ctx, S)
    zenith(ctx, S)
    memory(ctx, S)
    bloom(ctx, S, finale=True)
    coda(ctx, S)
    ctx.tl(main, "alpha").wait(B(34) - 0.1).to(B(34), 0, "linear")
    wash_plan(ctx, S, [(B(0), B(27), ICE, 16), (B(27), B(34), VIOLET, 30), (B(34), B(43), MAGENTA, 26),
                       (B(43), B(47), AMBER, 30), (B(47), B(75), CYAN, 18), (B(75), B(91), TEAL, 22),
                       (B(91), B(115), GOLD, 18), (B(115), B(135), VIOLET, 30), (B(135), B(151), ROSE, 20),
                       (B(159), B(168), GOLD, 26)])
    for ln in list(ctx.c.lines):
        if ln.name in ("v2_main", "v2_top", "v2_breath", "v2_minute", "v2_memory", "v2fin_bottom", "v2_coda",
                       "v2_box_bottom", "v2_box_top", "v2_echo0", "v2_echo1", "v2_echo2", "v2_tele0", "v2_tele1"):
            base.halo(ctx, ln, factor=0.5)
    return ctx.c, INFO
