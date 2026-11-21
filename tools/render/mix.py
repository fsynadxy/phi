"""Mix the soundtrack for the rendered video: music + autoplay hitsounds + result-screen music.

usage: python mix.py <meta.json> <song.ogg> <assets_dir> <out.wav> [sfx_volume] [ending_volume]
Times in meta.json are on the renderer's clock; frame k shows clock time (k + 0.5) / fps, so audio is shifted
by half a frame to sit on the frames' presentation times.
"""
import json
import subprocess
import sys

import numpy as np

SR = 48000
meta = json.load(open(sys.argv[1]))
song, assets, out = sys.argv[2], sys.argv[3], sys.argv[4]
v_sfx = float(sys.argv[5]) if len(sys.argv) > 5 else 0.55
v_end = float(sys.argv[6]) if len(sys.argv) > 6 else 0.6


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


fps = meta["fps"]
shift = -0.5 / fps
n_frames = meta["frames_written"]
total = n_frames / fps
buf = np.zeros((int(total * SR) + SR, 2), np.float32)


def place(t, clip, vol=1.0):
    i = int(round((t + shift) * SR))
    if i >= len(buf):
        return
    if i < 0:
        clip, i = clip[-i:], 0
    n = min(len(clip), len(buf) - i)
    buf[i:i + n] += clip[:n] * vol


music = load(song)
t0 = meta["music_start"]
place(t0, music, 0.82)
sfx = [load(f"{assets}/{k}.ogg") for k in ("click", "drag", "flick")]
off = meta["chart_offset"]
for t, kind in meta["notes"]:
    place(t0 + t + off, sfx[kind], v_sfx)
if meta["ending_start"] < 1e300:
    end = load(f"{assets}/ending.ogg")
    te = meta["ending_start"]
    fade_len = int(1.5 * SR)
    end_seg = end[: max(0, int((total - te) * SR))].copy()
    if len(end_seg) > fade_len:
        end_seg[-fade_len:] *= np.linspace(1, 0, fade_len)[:, None]
    place(te, end_seg, v_end)
buf = buf[: int(total * SR)]
peak = float(np.abs(buf).max())
import soundfile as sf  # float WAV; the final encode runs a look-ahead limiter (ffmpeg alimiter)

sf.write(out, buf, SR, subtype="FLOAT")
print(f"mixed {total:.2f}s, music at {t0:.3f}s, {len(meta['notes'])} hitsounds, peak {peak:.2f}")
