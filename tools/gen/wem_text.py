"""Pre-render the text textures of world.execute(me); into tools/data/wem/ (run once; the PNGs are committed).

usage: python tools/gen/wem_text.py <fonts_dir>
fonts_dir holds PressStart2P-Regular.ttf and VT323-Regular.ttf (Google Fonts, SIL OFL 1.1);
math glyphs use DejaVu Sans Bold (system font).
All text is white on transparent and gets its colour from colour events in the chart.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "wem")
FD = sys.argv[1]
PIX = os.path.join(FD, "PressStart2P-Regular.ttf")
TERM = os.path.join(FD, "VT323-Regular.ttf")
MATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# name -> (font, size px, text). Pixel font sizes are multiples of 8 (its native grid) so the edges stay crisp.
TEXTS = {
    # title and big program states (pixel font)
    "t_title": (PIX, 48, "world.execute(me);"),
    "t_run": (PIX, 40, "RUN"),
    "t_error": (PIX, 64, "ERROR"),
    "t_fatal": (PIX, 40, "FATAL"),
    "t_executing": (PIX, 32, "EXECUTING..."),
    # boot terminal (one line per lyric line of the first verse, as code)
    "t_b0": (TERM, 64, "> power.on()"),
    "t_b1": (TERM, 64, "> protect(all)"),
    "t_b2": (TERM, 64, "> pieces.lay_down()"),
    "t_b3": (TERM, 64, "> new Object()"),
    "t_b4": (TERM, 64, "> fill(data, params)"),
    "t_b5": (TERM, 64, "> init()"),
    "t_b6": (TERM, 64, "> world = new World()"),
    "t_b7": (TERM, 64, "> world.execute(me);"),
    # math of the second verse
    "t_points": (MATH, 72, "P = { (x, y) }"),
    "t_circle": (MATH, 72, "C = 2πr"),
    "t_tangent": (MATH, 72, "y = sin x    y′ = cos x"),
    "t_limit": (MATH, 72, "lim  x → ∞"),
    "t_inf": (MATH, 220, "∞"),
    # pre-chorus: current / dizzy / time / unite
    "t_ac": (MATH, 80, "AC  ∿"),
    "t_dc": (MATH, 80, "DC  —"),
    "t_time": (MATH, 72, "A.D.  ⇄  B.C."),
    "t_merge": (TERM, 64, "merge(you, me)"),
    # third verse
    "t_egg": (TERM, 64, "new Eggplant()"),
    "t_tom": (TERM, 64, "new Tomato()"),
    "t_cat": (TERM, 64, "new TabbyCat()"),
    "t_exist": (MATH, 80, "∃ me  ⇐  ∃ you"),
    # second pre-chorus
    "t_fm": (MATH, 80, "F  ⇄  M"),
    "t_ampm": (MATH, 80, "AM  ⇄  PM"),
    "t_role": (TERM, 64, "role ^= 1"),
    "t_rem": (TERM, 72, "10 REM ..."),
    # second chorus / error / bridge
    "t_loop": (TERM, 64, "while (true) { }"),
    "t_segv": (TERM, 56, "Segmentation fault (core dumped)"),
    "t_stack": (TERM, 56, "StackOverflowError"),
    "t_dead": (TERM, 56, "0xDEADBEEF"),
    "t_null": (TERM, 56, "NullPointerException"),
    "t_panic": (TERM, 56, "kernel panic - not syncing"),
    "t_fatal_msg": (TERM, 56, "A fatal exception has occurred."),
    "t_deadlock": (TERM, 64, "deadlock: waiting for you"),
    # outro
    "t_shutdown": (TERM, 64, "> shutdown()"),
    "t_bye": (PIX, 40, "goodbye, world."),
}


def render(font, size, text, pad=8):
    f = ImageFont.truetype(font, size)
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    l, t, r, b = tmp.textbbox((0, 0), text, font=f)
    w, h = r - l + 2 * pad, b - t + 2 * pad
    im = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((pad - l, pad - t), text, font=f, fill=255)
    if font == PIX:  # keep the pixel font hard-edged
        mask = mask.point(lambda v: 255 if v >= 128 else 0)
    im.putalpha(mask)
    return im


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, (font, size, text) in TEXTS.items():
        im = render(font, size, text)
        im.save(os.path.join(OUT, name + ".png"), optimize=True)
        print(name, im.size)
