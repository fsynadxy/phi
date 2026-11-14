"""Preview a built package with the real effect shaders (Phira's presets and the chart's own GLSL), run in
headless Chromium through glfx.js.

usage:  RESPACK=<phira>/assets/respack PHIRA_SRC=<phira checkout> python tools/gen/jl_preview.py <pkg> <out.png> <beats,...> [cols] [width]
        beats may be written as bar:beat with --bars (bar k starts on beat 3 + 4k for Just Love)
Without PHIRA_SRC the preset shaders fall back to the numpy emulation in preview.py and custom shaders are skipped.
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preview  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PRESET_FILES = {"chromatic": "chromatic.glsl", "circleBlur": "circle_blur.glsl", "fisheye": "fisheye.glsl", "glitch": "glitch.glsl",
                "grayscale": "grayscale.glsl", "noise": "noise.glsl", "pixel": "pixel.glsl", "radialBlur": "radial_blur.glsl",
                "shockwave": "shockwave.glsl", "vignette": "vignette.glsl"}


class GLChart(preview.Chart):
    gl = None

    def _start(self):
        self.tmp = tempfile.mkdtemp(prefix="glfx")
        self.gl = subprocess.Popen(["node", os.path.join(HERE, "glfx.js"), "serve"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    def _shader_path(self, sh):
        if sh.startswith("/"):
            return os.path.join(self.pkg, sh[1:])
        src = os.environ.get("PHIRA_SRC")
        return os.path.join(src, "prpr", "src", "core", "shaders", PRESET_FILES[sh]) if src else None

    def _effects(self, canvas, t):
        if not os.environ.get("PHIRA_SRC"):
            return super()._effects(canvas, t)
        passes = []
        for ef in self.extra.get("effects", []):
            if not (self.sec(ef["start"]) <= t < self.sec(ef["end"])):
                continue
            uni = {}
            for k, v in self._effect_vars(ef, t).items():
                if isinstance(v, (list, tuple)):
                    uni[k] = [float(x) / 255 for x in v] if len(v) == 4 else [float(x) for x in v]
                else:
                    uni[k] = float(v)
            passes.append({"shader": self._shader_path(ef["shader"]), "uniforms": uni, "time": t})
        if not passes:
            return canvas
        if self.gl is None:
            self._start()
        src, dst = os.path.join(self.tmp, "in.png"), os.path.join(self.tmp, "out.png")
        canvas.convert("RGB").save(src)
        self.gl.stdin.write(json.dumps({"width": canvas.width, "height": canvas.height, "input": src, "output": dst, "passes": passes}) + "\n")
        self.gl.stdin.flush()
        ans = self.gl.stdout.readline().strip()
        if ans != "done":
            raise RuntimeError(f"glfx: {ans}")
        return Image.open(dst).convert("RGBA")

    def close(self):
        if self.gl:
            self.gl.stdin.close()
            self.gl.wait(timeout=20)


def parse_beats(spec, bars):
    out = []
    for tok in spec.split(","):
        if bars and ":" in tok:
            bar, beat = tok.split(":")
            out.append(3 + 4 * float(bar) + float(beat))
        elif bars:
            out.append(3 + 4 * float(tok))
        else:
            out.append(float(tok))
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    bars = "--bars" in sys.argv
    pkg, out, spec = args[0], args[1], args[2]
    cols = int(args[3]) if len(args) > 3 else 4
    W = int(args[4]) if len(args) > 4 else 480
    ch = GLChart(pkg)
    beats = parse_beats(spec, bars)
    labels = [f"b{b:.2f} bar {(b - 3) / 4:.2f} {b * ch.spb:.1f}s" for b in beats]
    preview.sheet(ch, [b * ch.spb for b in beats], out, cols, W, labels=labels)
    ch.close()
    print("saved", out)
