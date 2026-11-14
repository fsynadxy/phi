"""Smallest complete Phira chart built with chartlib: one judge line, 16 notes of every kind, one shader.

usage:
  python tools/gen/build.py out --variant example_minimal --song song.ogg --pez example.pez
  python tools/gen/validate.py out          # must print errors=0 before you ship anything

Copy this file and edit make(); see docs/PHIRA_CHART_GUIDE.md for the rules behind every line.
"""
from chartlib import DRAG, EPSB, FLICK, HOLD, TAP, Chart

BPM = 120.0
OFFSET_MS = 0  # music time (ms) at which beat 0 of the chart plays; MP3 needs about +25 on top (decoder delay)

INFO = {
    "name": "Example", "difficulty": 10.0, "level": "IN Lv.10", "charter": "me", "composer": "someone",
    "illustrator": "me", "chart": "chart.json", "format": "rpe", "music": "song.ogg",
    "illustration": "illustration.jpg", "previewStart": 0.0, "previewEnd": 20.0, "aspectRatio": 1.7777778,
    "backgroundDim": 0.6, "lineLength": 6.0, "offset": 0.0, "tip": "", "tags": [], "intro": "",
    "holdPartialCover": False, "noteUniformScale": False, "forceAspectRatio": False,
    "useRpe170Speed": False, "useAttachUiFix": True,  # always write the last two: otherwise Phira prompts on import
}


def make():
    c = Chart(OFFSET_MS, dict(INFO, id="example"), bpm=BPM)
    ln = c.line("judge")
    # every track gets a keyframe at beat 0 (a line with no alpha events is invisible; notes need speed from beat 0)
    for prop, v in (("moveX", 0.0), ("moveY", -250.0), ("rotate", 0.0), ("alpha", 255.0), ("speed", 8.0)):
        ln.ev(prop, 0, EPSB, v, v)
    for k in range(16):
        x = (-300, -100, 100, 300)[k % 4]
        if k % 8 == 7:
            ln.note(HOLD, k + 2, x, end=k + 3)
        else:
            ln.note((TAP, TAP, FLICK, DRAG)[k % 4], k + 2, x)
    c.effect("vignette", 0, 20, {"extend": 0.2, "radius": 18.0})  # never give a colour var as floats
    return c, INFO


def assets(out):
    from PIL import Image
    Image.new("RGB", (1920, 1080), (20, 24, 40)).save(f"{out}/illustration.jpg")
