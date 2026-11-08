"""MAD song: grid at 153.6 BPM, downbeat phase, per-beat features, SSM/novelty, stops & impacts.

usage: python mad_stage3.py <work> [bpm]   (reads mono22k.wav and bands.npz, writes beatfeat.npz and grid.json)
"""
import sys, json
import numpy as np
import soundfile as sf
import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d

W = sys.argv[1]
BPM = float(sys.argv[2]) if len(sys.argv) > 2 else 153.6  # 走过漫漫时空: 160
per = 60 / BPM
y, sr = sf.read(f"{W}/mono22k.wav", dtype="float32")
dur = len(y) / sr
Bd = np.load(f"{W}/bands.npz")
fps = float(Bd["fps"])
full = Bd["flux_full"]
n = len(full)
envc = full / np.percentile(full, 99.9)


def gscore(ph, env):
    ts = ph + per * np.arange(0, (n / fps - ph) / per)
    return np.interp(ts * fps, np.arange(n), env).mean()


phs = np.arange(0.0, per, 0.0005)
PH = float(phs[int(np.argmax([gscore(p, envc) for p in phs]))])
nb = int((dur - PH) / per) + 1
bt = PH + per * np.arange(nb)
print(f"BPM {BPM} phase {PH:.4f} beats {nb} last {bt[-1]:.2f}")

hop = 512
C = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop, bins_per_octave=36)
Mf = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=20)
fr = np.clip(librosa.time_to_frames(np.concatenate([bt, [dur]]), sr=sr, hop_length=hop), 0, C.shape[1] - 1)
Cs = librosa.util.sync(C, fr, aggregate=np.median)[:, :nb]
Ms = librosa.util.sync(Mf, fr, aggregate=np.mean)[:, :nb]


def bandmean(key, t0, t1):
    a, b = int(t0 * fps), int(t1 * fps)
    return float(Bd[key][a:b].mean()) if b > a else 0.0


def bandmax(key, t0, t1):
    a, b = int(t0 * fps), int(t1 * fps)
    return float(Bd[key][a:b].max()) if b > a else 0.0


low = np.array([bandmean("rms_low", t, t + per) for t in bt])
mid = np.array([bandmean("rms_mid", t, t + per) for t in bt])
hi = np.array([bandmean("rms_high", t, t + per) for t in bt])
onl = np.array([bandmax("flux_low", t - 0.02, t + 0.06) for t in bt])
onf = np.array([bandmax("flux_full", t - 0.02, t + 0.06) for t in bt])
for arr in (low, mid, hi, onl, onf):
    arr /= np.percentile(arr, 98) + 1e-9
Cn = Cs / (np.linalg.norm(Cs, axis=0, keepdims=True) + 1e-9)
chg = np.r_[0, 1 - (Cn[:, 1:] * Cn[:, :-1]).sum(0)]
for k in range(4):
    sel = np.arange(k, nb, 4)
    print(f"phase {k}: chroma-chg {chg[sel].mean():.3f} lowOn {onl[sel].mean():.3f} fullOn {onf[sel].mean():.3f} hi {hi[sel].mean():.3f}")
for k in range(8):
    sel = np.arange(k, nb, 8)
    print(f"2-bar phase {k}: chroma-chg {chg[sel].mean():.3f} fullOn {onf[sel].mean():.3f}")

F = np.vstack([Cn, (Ms - Ms.mean(1, keepdims=True)) / (Ms.std(1, keepdims=True) + 1e-9) * 0.35])
F = F / (np.linalg.norm(F, axis=0, keepdims=True) + 1e-9)
Fs = uniform_filter1d(F, 4, axis=1)
SSM = Fs.T @ Fs


def novelty(S, L):
    k = np.ones((2 * L, 2 * L)); k[:L, L:] = -1; k[L:, :L] = -1
    g = np.exp(-((np.arange(2 * L) - L + 0.5) ** 2) / (2 * (L / 2) ** 2))
    k *= np.outer(g, g)
    P = np.pad(S, L, mode="edge")
    return np.array([(P[i:i + 2 * L, i:i + 2 * L] * k).sum() for i in range(len(S))])


nov = novelty(SSM, 8)
# stops: near-silent stretches (full-band rms)
r = Bd["rms_full"]
rs = uniform_filter1d(r, int(0.03 * fps))
thr = np.percentile(rs, 50) * 0.18
quiet = rs < thr
stops = []
i = 0
while i < len(quiet):
    if quiet[i]:
        j = i
        while j < len(quiet) and quiet[j]:
            j += 1
        if (j - i) / fps > 0.06:
            stops.append((i / fps, j / fps))
        i = j
    else:
        i += 1
print("stops (s):", [(round(a, 3), round(b, 3), round((a - PH) / per, 2), round((b - PH) / per, 2)) for a, b in stops])
np.savez_compressed(f"{W}/beatfeat.npz", bt=bt, low=low, mid=mid, hi=hi, onl=onl, onf=onf, chg=chg, nov=nov, ssm=SSM)
json.dump({"bpm": BPM, "phase": PH, "nbeats": int(nb)}, open(f"{W}/grid.json", "w"))
print("beat table (beat, t, low, mid, hi, onsetFull, chordChg, novelty):")
for k in range(nb):
    print(f"{k:3d} {bt[k]:6.2f} L{low[k]:4.2f} M{mid[k]:4.2f} H{hi[k]:4.2f} O{onf[k]:4.2f} C{chg[k]:.2f} N{nov[k]:5.1f} " + "#" * int(onf[k] * 10))
fig, axs = plt.subplots(2, 1, figsize=(16, 20), gridspec_kw={"height_ratios": [4, 1]})
axs[0].imshow(SSM, cmap="magma", origin="lower", vmin=np.percentile(SSM, 30))
axs[0].set_xticks(np.arange(0, nb, 16)); axs[0].set_yticks(np.arange(0, nb, 16)); axs[0].grid(alpha=0.3, color="cyan")
axs[1].plot(nov); axs[1].plot(low * nov.max(), alpha=0.5); axs[1].plot(hi * nov.max(), alpha=0.5)
axs[1].set_xticks(np.arange(0, nb, 8)); axs[1].grid(alpha=0.3)
plt.tight_layout(); plt.savefig(f"{W}/ssm.png", dpi=50)
