"""Stage 3: beat-synchronous features, downbeat phase, novelty & self-similarity."""
import sys, json
import numpy as np
import librosa
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d

SP = sys.argv[1]
y, sr = sf.read(f"{SP}/work/mono22k.wav", dtype="float32")
B = np.load(f"{SP}/work/bands.npz")
fps = float(B["fps"])
BPM = 123.0
per = 60.0 / BPM
# best phase for exact 123
full = B["flux_full"]; envc = full / np.percentile(full, 99.9)
n = len(full)
def grid_score(phase, env, sub=0.0):
    ts = phase + sub + per * np.arange(0, (n / fps - phase) / per)
    return np.interp(ts * fps, np.arange(n), env).mean()
phs = np.arange(0.30, 0.36, 0.0005)
sc = [grid_score(p, envc) for p in phs]
PH = float(phs[int(np.argmax(sc))])
print(f"phase for 123.000: {PH:.4f}")
dur = len(y) / sr
nb = int((dur - PH) / per) + 1
beat_t = PH + per * np.arange(nb)
print("beats", nb, "last", beat_t[-1])

hop = 512
C = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop, bins_per_octave=36)
M = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=20)
R = librosa.feature.rms(y=y, hop_length=hop)[0]
fr = librosa.time_to_frames(np.concatenate([beat_t, [dur]]), sr=sr, hop_length=hop)
fr = np.clip(fr, 0, C.shape[1] - 1)
Cs = librosa.util.sync(C, fr, aggregate=np.median)[:, :nb]
Ms = librosa.util.sync(M, fr, aggregate=np.mean)[:, :nb]
Rs = librosa.util.sync(R[None, :], fr, aggregate=np.mean)[0, :nb]

def bandsum(name, t0, t1):
    a = int(t0 * fps); b = int(t1 * fps)
    return float(B[name][a:b].mean()) if b > a else 0.0
low_on = np.array([bandsum("flux_low", t - 0.03, t + 0.06) for t in beat_t])
mid_on = np.array([bandsum("flux_mid", t - 0.03, t + 0.06) for t in beat_t])
hi_on = np.array([bandsum("flux_high", t - 0.03, t + 0.06) for t in beat_t])
lowr = np.array([bandsum("rms_low", t, t + per) for t in beat_t])
hir = np.array([bandsum("rms_high", t, t + per) for t in beat_t])
midr = np.array([bandsum("rms_mid", t, t + per) for t in beat_t])

# chroma change between consecutive beats
Cn = Cs / (np.linalg.norm(Cs, axis=0, keepdims=True) + 1e-9)
chg = np.r_[0, 1 - (Cn[:, 1:] * Cn[:, :-1]).sum(0)]
for ph4 in range(4):
    sel = np.arange(ph4, nb, 4)
    print(f"bar phase {ph4}: chroma-change {chg[sel].mean():.4f} low_on {low_on[sel].mean():.4f} mid_on {mid_on[sel].mean():.4f} hi_on {hi_on[sel].mean():.4f}")
for ph8 in range(8):
    sel = np.arange(ph8, nb, 8)
    print(f"2bar phase {ph8}: chroma-change {chg[sel].mean():.4f}")

# feature matrix & SSM
F = np.vstack([Cn * 1.0, (Ms - Ms.mean(1, keepdims=True)) / (Ms.std(1, keepdims=True) + 1e-9) * 0.35])
F = F / (np.linalg.norm(F, axis=0, keepdims=True) + 1e-9)
Fsm = uniform_filter1d(F, 4, axis=1)
SSM = Fsm.T @ Fsm
def novelty(S, L):
    k = np.ones((2 * L, 2 * L)); k[:L, L:] = -1; k[L:, :L] = -1
    g = np.exp(-((np.arange(2 * L) - L + 0.5) ** 2) / (2 * (L / 2) ** 2))
    k = k * np.outer(g, g)
    N = len(S); out = np.zeros(N)
    P = np.pad(S, L, mode="edge")
    for i in range(N):
        out[i] = (P[i:i + 2 * L, i:i + 2 * L] * k).sum()
    return out
nov16 = novelty(SSM, 8)
nov32 = novelty(SSM, 16)
energy = Rs / Rs.max()
np.savez_compressed(f"{SP}/work/beatfeat.npz", beat_t=beat_t, chroma=Cs, mfcc=Ms, rms=Rs, low_on=low_on, mid_on=mid_on, hi_on=hi_on,
                    lowr=lowr, midr=midr, hir=hir, chg=chg, nov16=nov16, nov32=nov32, ssm=SSM)
json.dump({"bpm": BPM, "phase": PH, "nbeats": int(nb)}, open(f"{SP}/work/grid.json", "w"))

# peaks of novelty
from scipy.signal import find_peaks
pk, pr = find_peaks(nov16, distance=12, prominence=np.percentile(nov16, 80) * 0.3)
order = np.argsort(pr["prominences"])[::-1][:40]
print("novelty16 peaks (beat idx, time, prom):")
for i in sorted(pk[order]):
    print(f"  beat {i:4d} t={beat_t[i]:7.2f} bar={i/4:6.2f} nov={nov16[i]:.2f}")

fig, axs = plt.subplots(2, 1, figsize=(24, 30), gridspec_kw={"height_ratios": [4, 1]})
axs[0].imshow(SSM, cmap="magma", origin="lower", vmin=np.percentile(SSM, 30))
axs[0].set_xticks(np.arange(0, nb, 32)); axs[0].set_yticks(np.arange(0, nb, 32))
axs[0].grid(alpha=0.25, color="cyan")
axs[1].plot(nov16, label="nov16"); axs[1].plot(nov32, label="nov32")
axs[1].plot(energy * nov16.max(), label="rms", alpha=0.6)
axs[1].plot(hir / hir.max() * nov16.max(), label="high rms", alpha=0.6)
axs[1].set_xticks(np.arange(0, nb, 32)); axs[1].grid(alpha=0.3); axs[1].legend()
plt.tight_layout(); plt.savefig(f"{SP}/work/ssm.png", dpi=50)
print("saved")
