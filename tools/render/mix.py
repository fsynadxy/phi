import json, sys
from collections import defaultdict
import numpy as np, soundfile as sf
import os
S = os.environ["JL_WORK"]  # holds unpacked/ (the unpacked .pez) and rassets/ (the engine assets)
SR, FPS, T0, OFF, SPB = 44100, 60, 212 / 60, 0.016, 60 / 160
FRAMES = int(sys.argv[1])
SFX_VOL = float(sys.argv[2])
length = FRAMES / FPS
out = np.zeros((int(length * SR) + SR, 2), np.float32)
music, sr = sf.read(f"{S}/unpacked/song.ogg", dtype="float32", always_2d=True)
assert sr == SR
i0 = round(T0 * SR)
n = min(len(music), len(out) - i0)
out[i0:i0 + n] += music[:n]
clips = {}
for k, name in ((1, "click"), (2, "click"), (3, "flick"), (4, "drag")):
    c, csr = sf.read(f"{S}/rassets/{name}.ogg", dtype="float32", always_2d=True)
    assert csr == SR
    clips[k] = np.repeat(c, 2, axis=1) if c.shape[1] == 1 else c
ch = json.load(open(f"{S}/unpacked/chart.json"))
hits = defaultdict(int)
for ln in ch["judgeLineList"]:
    for nt in ln.get("notes", []):
        if nt["isFake"]:
            continue
        b = nt["startTime"][0] + nt["startTime"][1] / nt["startTime"][2]
        hits[(round(b * SPB, 6), nt["type"])] += 1
for (t, k), cnt in hits.items():
    p = round((T0 + OFF + t) * SR)
    c = clips[k] * SFX_VOL * (1.0 if cnt == 1 else 1.3)
    m = min(len(c), len(out) - p)
    if m > 0:
        out[p:p + m] += c[:m]
out = out[:int(length * SR)]
print("hitsound events", len(hits), "peak before limiting", float(np.abs(out).max()))
sf.write(f"{S}/mix.wav", out, SR, subtype="FLOAT")
