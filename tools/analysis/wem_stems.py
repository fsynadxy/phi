"""Per-16th features from the Demucs stems: vocal syllables + pitch, drum hits (kick/snare/hats), synth onsets.

usage: python wem_stems.py <work>   (reads stem_*.wav + grid.json, writes stems.npz and stems.txt)
"""
import json
import sys

import librosa
import numpy as np
import soundfile as sf
from scipy.signal import find_peaks

W = sys.argv[1]
G = json.load(open(f"{W}/grid.json"))
BPM, PH = G["bpm"], G["phase"]
per = 60.0 / BPM
sr = 22050
hop = 128
fps = sr / hop


def load(name):
    y, s = sf.read(f"{W}/stem_{name}.wav", dtype="float32")
    assert s == sr
    return y


voc, drm, oth, bas = load("vocals"), load("drums"), load("other"), load("bass")
dur = len(voc) / sr
nstep = int((dur - PH) / (per / 4)) + 1
step_t = PH + np.arange(nstep) * per / 4


def band_flux(y, lo, hi, nfft=1024):
    S = np.abs(librosa.stft(y, n_fft=nfft, hop_length=hop))
    f = librosa.fft_frequencies(sr=sr, n_fft=nfft)
    m = (f >= lo) & (f < hi)
    L = np.log1p(100 * S[m])
    D = np.diff(L, axis=1, prepend=L[:, :1])
    D[D < 0] = 0
    e = D.mean(0)
    rms = np.sqrt((S[m] ** 2).mean(0))
    return e, rms


def at_steps(env, w0=-0.015, w1=0.04, fn=np.max):
    out = np.zeros(nstep)
    for i, t in enumerate(step_t):
        a, b = max(0, int((t + w0) * fps)), min(len(env), int((t + w1) * fps))
        out[i] = fn(env[a:b]) if b > a else 0.0
    return out


def norm(a, q=99):
    return np.clip(a / (np.percentile(a, q) + 1e-9), 0, 2)


# ---- drums: kick (40-120 Hz), snare (150-400 + 2-5k), hats (7-11k)
kick_e, _ = band_flux(drm, 30, 120)
snare_e, _ = band_flux(drm, 180, 2500)
hat_e, _ = band_flux(drm, 6000, 11000)
kick, snare, hat = (norm(at_steps(e)) for e in (kick_e, snare_e, hat_e))
# ---- synths / other: onset strength
oth_e, oth_r = band_flux(oth, 150, 6000)
synth = norm(at_steps(oth_e))
bass_e, bass_r = band_flux(bas, 30, 300)
bassn = norm(at_steps(bass_e))
# ---- vocals: presence, syllable onsets, pitch
v_on_env = librosa.onset.onset_strength(y=voc, sr=sr, hop_length=hop, fmax=6000)
v_rms = librosa.feature.rms(y=voc, frame_length=1024, hop_length=hop)[0]
f0, vflag, vprob = librosa.pyin(voc, fmin=140, fmax=1200, sr=sr, frame_length=2048, hop_length=hop * 2,
                                resolution=0.1, switch_prob=0.02)
vm = np.where(vflag, librosa.hz_to_midi(np.nan_to_num(f0, nan=1.0)), np.nan)
vm = np.repeat(vm, 2)[: len(v_rms)]
pres_th = np.percentile(v_rms, 60) * 0.35
v_pres = at_steps((v_rms > pres_th).astype(float), 0.0, per / 4, np.mean)
v_level = norm(at_steps(v_rms, 0.0, per / 4, np.mean), 98)
v_on = norm(at_steps(v_on_env), 99)
pitch = np.full(nstep, np.nan)
for i, t in enumerate(step_t):
    a, b = int((t + 0.01) * fps), int((t + per / 4) * fps)
    seg = vm[a:b]
    ok = ~np.isnan(seg)
    if b > a and ok.sum() >= max(2, (b - a) // 3):
        pitch[i] = float(np.median(seg[ok]))
# syllables: onset peaks while the voice is present, plus pitch jumps inside a sustained phrase
pk, _ = find_peaks(v_on_env, height=np.percentile(v_on_env, 75), distance=int(0.09 * fps))
syl = np.zeros(nstep)
for p in pk:
    t = p / fps
    i = int(round((t - PH) / (per / 4)))
    if 0 <= i < nstep and abs(step_t[i] - t) < per / 8 + 0.01:
        a = int(t * fps)
        if v_rms[a:a + int(0.08 * fps)].max(initial=0) > pres_th * 1.5:
            syl[i] = max(syl[i], v_on_env[p])
syl = norm(syl, 98) * (syl > 0)
for i in range(1, nstep):
    if syl[i] == 0 and not np.isnan(pitch[i]) and not np.isnan(pitch[i - 1]) and abs(pitch[i] - pitch[i - 1]) >= 1.5:
        syl[i] = 0.35
np.savez_compressed(f"{W}/stems.npz", step_t=step_t, kick=kick, snare=snare, hat=hat, synth=synth, bass=bassn,
                    v_pres=v_pres, v_level=v_level, v_on=v_on, syl=syl, pitch=np.nan_to_num(pitch), T0=PH, per=per)

C = " .:-=+*#%@"


def row(a):
    return "".join(C[min(9, int(x * 6))] for x in a)


with open(f"{W}/stems.txt", "w") as f:
    f.write("bar | kick | snare | hat | synth | vocal syl (pitch letter=a:C4..) \n")
    for bar in range(nstep // 16):
        s = slice(bar * 16, bar * 16 + 16)
        vv = ""
        for i in range(bar * 16, bar * 16 + 16):
            if syl[i] > 0.2:
                vv += "abcdefghijklmnopqrstuvwxyz"[int(np.clip((pitch[i] if not np.isnan(pitch[i]) else 60) - 60, 0, 25))].upper()
            elif v_pres[i] > 0.5:
                vv += "~"
            else:
                vv += "."
        f.write(f"{bar:3d} {row(kick[s])} {row(snare[s])} {row(hat[s])} {row(synth[s])} {vv}\n")
print("steps", nstep, "syllables", int((syl > 0.2).sum()))
