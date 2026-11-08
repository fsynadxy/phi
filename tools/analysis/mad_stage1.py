"""MAD song: alignment check, overview figure, tempo candidates.

usage: python mad_stage1.py <work>   (<work>/mono22k.wav = song.ogg decoded to 22.05 kHz mono,
       <work>/mono22k_src.wav = the original m4a decoded the same way)
"""
import sys
import numpy as np
import soundfile as sf
import librosa
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import uniform_filter1d
from scipy.signal import correlate

W = sys.argv[1]
y, sr = sf.read(f"{W}/mono22k.wav", dtype="float32")
y2, _ = sf.read(f"{W}/mono22k_src.wav", dtype="float32")
n = min(len(y), len(y2), sr * 30)
c = correlate(y[:n], y2[:n], mode="full", method="fft")
lag = np.argmax(c) - (n - 1)
print(f"ogg vs m4a lag: {lag} samples ({lag / sr * 1000:.2f} ms)")
dur = len(y) / sr
print(f"duration {dur:.3f}s")

hop = 128
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
fps = sr / hop
t = np.arange(len(oenv)) / fps
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=hop)[0]
S = librosa.feature.melspectrogram(y=y, sr=sr, hop_length=256, n_mels=96)
SdB = librosa.power_to_db(S, ref=np.max)

env = oenv / (np.percentile(oenv, 99.5) + 1e-9)
def comb(bpm):
    per = 60.0 / bpm * fps
    best = 0
    for ph in np.linspace(0, per, 64, endpoint=False):
        idx = np.arange(ph, len(env) - 1, per)
        best = max(best, np.interp(idx, np.arange(len(env)), env).mean())
    return best
cands = np.arange(60, 220, 0.5)
sc = np.array([comb(b) for b in cands])
order = np.argsort(sc)[::-1]
print("tempo candidates:", [(float(cands[i]), round(float(sc[i]), 3)) for i in order[:12]])
tg = librosa.feature.tempo(onset_envelope=oenv, sr=sr, hop_length=hop, aggregate=None)
step = int(5 * fps)
print("local tempo per 5s:", [round(float(np.median(tg[i:i + step])), 1) for i in range(0, len(tg), step)])

fig, axs = plt.subplots(3, 1, figsize=(30, 11), sharex=True)
axs[0].imshow(SdB, origin="lower", aspect="auto", extent=[0, dur, 0, 96], cmap="magma")
axs[1].plot(t, rms, lw=0.4)
axs[1].plot(t, uniform_filter1d(rms, int(fps)), lw=1.5, color="r")
axs[2].plot(t, oenv, lw=0.4)
for ax in axs:
    ax.set_xticks(np.arange(0, dur, 2))
    ax.grid(alpha=0.35)
plt.tight_layout()
plt.savefig(f"{W}/overview.png", dpi=55)
print("saved overview")
