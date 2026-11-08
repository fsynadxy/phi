"""Build the Phira chart folder (and optionally the importable .pez).

usage:
  python tools/gen/build.py <out_dir> [--song song.mp3] [--cover cover.jpg] [--pez out.pez]

The folder receives chart.json / extra.json / info.yml / textures / illustration.
Without --song the music file is left out (the repo does not ship the audio).
"""
import argparse
import os
import shutil
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from chartlib import dump  # noqa: E402


def build(out, song=None, cover=None):
    import showcase

    os.makedirs(out, exist_ok=True)
    # textures + illustration (deterministic)
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "assets.py"), out], check=True)
    chart, info = showcase.make()
    dump(chart.to_json(), os.path.join(out, info["chart"]))
    dump(chart.extra_json(), os.path.join(out, "extra.json"))
    with open(os.path.join(out, "info.yml"), "w", encoding="utf-8") as f:
        yaml.safe_dump(info, f, allow_unicode=True, sort_keys=False)
    if song:
        shutil.copy(song, os.path.join(out, info["music"]))
    if cover:
        from PIL import Image

        im = Image.open(cover).convert("RGB")
        if im.width > 1920:
            im = im.resize((1920, round(im.height * 1920 / im.width)), Image.LANCZOS)
        im.save(os.path.join(out, info["illustration"]), quality=92)
    print(f"built {out}: lines={len(chart.lines)} notes={chart.note_count()} effects={len(chart.effects)}")
    return info


def pack(folder, pez):
    import zipfile

    with zipfile.ZipFile(pez, "w") as z:
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            method = zipfile.ZIP_DEFLATED if name.endswith((".json", ".yml")) else zipfile.ZIP_STORED
            z.write(path, arcname=name, compress_type=method)
    print(f"packed {pez} ({os.path.getsize(pez) / 1e6:.1f} MB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--song")
    ap.add_argument("--pez")
    ap.add_argument("--cover")
    a = ap.parse_args()
    build(a.out, a.song, a.cover)
    if a.pez:
        if not a.song:
            sys.exit("--pez needs --song (a chart package must contain its music)")
        pack(a.out, a.pez)
