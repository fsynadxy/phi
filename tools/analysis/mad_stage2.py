"""Stage 2: precise beat grid (BPM + phase), drift check, band onsets (chunked, low memory).

usage: python mad_stage2.py <work>/mono22k.wav <work>/bands.npz <work>/grid.json
"""
import sys, json, gc
import numpy as np
import soundfile as sf

wav = sys.argv[1]
y, sr = sf.read(wav, dtype="float32")
if y.ndim > 1:
    y = y.mean(axis=1)
assert sr == 22050, sr
hop = 64
nfft = 2048
fps = sr / hop
freqs = np.fft.rfftfreq(nfft, 1 / sr)
bands = {"low": (20, 150), "mid": (150, 2500), "high": (5000, 11025), "full": (20, 11025)}
win = np.hanning(nfft).astype(np.float32)

nfr = 1 + (len(y) - nfft) // hop if len(y) >= nfft else 1
ypad = np.concatenate([np.zeros(nfft // 2, np.float32), y, np.zeros(nfft, np.float32)])
nfr = 1 + (len(ypad) - nfft) // hop
out = {k: np.zeros(nfr, np.float32) for k in bands}
rmsb = {k: np.zeros(nfr, np.float32) for k in bands}
prev = None
chunk = 4096
for c0 in range(0, nfr, chunk):
    c1 = min(nfr, c0 + chunk)
    idx = np.arange(c0, c1)[:, None] * hop + np.arange(nfft)[None, :]
    frames = ypad[idx] * win
    S = np.abs(np.fft.rfft(frames, axis=1)).astype(np.float32)
    L = np.log1p(100 * S)
    if prev is None:
        prevL = L[:1]
    else:
        prevL = prev
    D = np.diff(np.vstack([prevL, L]), axis=0)
    D[D < 0] = 0
    for k, (lo, hi) in bands.items():
        m = (freqs >= lo) & (freqs < hi)
        out[k][c0:c1] = D[:, m].mean(axis=1)
        rmsb[k][c0:c1] = np.sqrt((S[:, m] ** 2).mean(axis=1))
    prev = L[-1:]
    del frames, S, L, D, idx
    gc.collect()
n = nfr
t = np.arange(n) / fps
np.savez_compressed(sys.argv[2], fps=fps, **{f"flux_{k}": v for k, v in out.items()}, **{f"rms_{k}": v for k, v in rmsb.items()})
print("frames", n, "fps", fps)

full = out["full"]
envc = full / np.percentile(full, 99.9)

def grid_score(bpm, phase, env, t0=0, t1=None):
    per = 60.0 / bpm
    t1 = t1 if t1 is not None else n / fps
    k0 = np.ceil((t0 - phase) / per)
    ts = phase + per * np.arange(k0, (t1 - phase) / per)
    fr = ts * fps
    return np.interp(fr, np.arange(n), env).mean()

best = None
for bpm in np.arange(151.50, 155.50, 0.01):
    per = 60.0 / bpm
    for ph in np.arange(0, per, 0.002):
        s = grid_score(bpm, ph, envc)
        if best is None or s > best[0]:
            best = (s, bpm, ph)
print("coarse best: score %.4f bpm %.4f phase %.4f" % best)
s, bpm0, ph0 = best
best = None
for bpm in np.arange(bpm0 - 0.006, bpm0 + 0.006, 0.0005):
    per = 60.0 / bpm
    for ph in np.arange(ph0 - 0.004, ph0 + 0.004, 0.0002):
        s = grid_score(bpm, ph, envc)
        if best is None or s > best[0]:
            best = (s, bpm, ph)
print("fine best: score %.4f bpm %.4f phase %.4f" % best)
s, bpm, ph = best
for w0 in range(0, int(n / fps), 10):
    offs = np.arange(-0.03, 0.0301, 0.001)
    sc = [grid_score(bpm, ph + o, envc, w0, w0 + 10) for o in offs]
    print(f"  window {w0:3d}s best local shift {offs[int(np.argmax(sc))]*1000:+.0f} ms (peak {max(sc):.3f})")
# also: profile of the envelope around beats (sub-beat structure): average over all beats of envelope at 1/12-beat positions
per = 60.0 / bpm
for name in ["full", "low", "mid", "high"]:
    e = out[name] / np.percentile(out[name], 99.9)
    prof = []
    for k in range(24):
        prof.append(grid_score(bpm, ph + k * per / 24, e))
    print(f"subbeat profile {name:5s}:", " ".join(f"{v:.2f}" for v in prof))
json.dump({"bpm": float(bpm), "phase": float(ph)}, open(sys.argv[3], "w"))
