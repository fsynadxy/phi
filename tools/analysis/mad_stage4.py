"""Stage 4: 16th-grid onset matrices (perc/harm split by band) + pitch-ish descriptor per onset.

usage: python mad_stage4.py <work>   (reads grid.json and mono22k.wav, writes steps.npz)
"""
import sys, json, gc
import numpy as np
import soundfile as sf
import librosa

W = sys.argv[1]
G = json.load(open(f"{W}/grid.json"))
BPM = G["bpm"]; PH = G["phase"]; per = 60 / BPM
FIRST = 0
T0 = PH + FIRST * per          # time of bar 0
y, sr = sf.read(f"{W}/mono22k.wav", dtype="float32")
dur = len(y) / sr
nbar = int((dur - T0) / (4 * per)) + 1
nstep = nbar * 16
step_t = T0 + np.arange(nstep) * per / 4

hop = 128
fps = sr / hop
# HPSS on STFT in chunks (memory friendly)
nfft = 2048
H_env = {}
P_env = {}
bands = {"low": (20, 160), "lmid": (160, 600), "mid": (600, 2500), "high": (2500, 11025)}
freqs = np.fft.rfftfreq(nfft, 1 / sr)
chunk_s = 20.0
seg = int(round(chunk_s * sr / hop)) * hop
pad = int(round(2.0 * sr / hop)) * hop
outs = {f"{k}_{c}": [] for k in bands for c in ("h", "p")}
pitch_frames = []
prevL = None
for s0 in range(0, len(y), seg):
    a = max(0, s0 - pad); b = min(len(y), s0 + seg + pad)
    S = librosa.stft(y[a:b], n_fft=nfft, hop_length=hop)
    Hm, Pm = librosa.decompose.hpss(np.abs(S), kernel_size=(17, 31), margin=1.0)
    f0 = (s0 - a) // hop
    f1 = f0 + (min(seg, len(y) - s0) + hop - 1) // hop if s0 + seg >= len(y) else f0 + seg // hop
    for comp, Mx in (("h", Hm), ("p", Pm)):
        L = np.log1p(50 * Mx)
        D = np.diff(L, axis=1, prepend=L[:, :1]); D[D < 0] = 0
        for k, (lo, hi) in bands.items():
            m = (freqs >= lo) & (freqs < hi)
            outs[f"{k}_{comp}"].append(D[m][:, f0:f1].mean(0))
    # harmonic pitch descriptor: chroma-ish weighted log-frequency centroid over 150-2500Hz of harmonic part
    m = (freqs >= 150) & (freqs < 2500)
    Hh = Hm[m][:, f0:f1]
    lf = np.log2(freqs[m] / 440.0) * 12 + 69
    w = Hh ** 2
    cent = (w * lf[:, None]).sum(0) / (w.sum(0) + 1e-9)
    # dominant pitch (argmax of harmonic spectrum, with harmonic summation light)
    pk = lf[np.argmax(Hh, axis=0)]
    pitch_frames.append(np.vstack([cent, pk]))
    del S, Hm, Pm; gc.collect()
env = {k: np.concatenate(v) for k, v in outs.items()}
pitch = np.concatenate(pitch_frames, axis=1)
n = min(len(v) for v in env.values())
for k in env:
    env[k] = env[k][:n] / (np.percentile(env[k][:n], 99.5) + 1e-9)

def sample(e, t, w0=-0.012, w1=0.035):
    a = int((t + w0) * fps); b = int((t + w1) * fps)
    a = max(a, 0); b = min(b, len(e))
    return float(e[a:b].max()) if b > a else 0.0

M = {k: np.array([sample(env[k], t) for t in step_t]) for k in env}
P = np.array([[float(np.median(pitch[i, max(0, int((t + 0.02) * fps)):int((t + 0.09) * fps)])) if int((t + 0.09) * fps) < pitch.shape[1] else 0 for t in step_t] for i in range(2)])
np.savez_compressed(f"{W}/steps.npz", step_t=step_t, T0=T0, per=per, nbar=nbar, pitch_cent=P[0], pitch_pk=P[1], **M)
print("bars", nbar, "steps", nstep, "T0", T0)

for bar in range(nbar):
    def row(k):
        v = M[k][bar * 16:(bar + 1) * 16]
        return "".join(" .:-=+*#%@"[min(9, int(x * 6))] for x in v)
    print(f"{bar:3d} | " + " | ".join(row(k) for k in ["low_p", "lmid_p", "high_p", "mid_h"]))
