"""Just Love (feat. PSYQUI): everything the chart generator needs, on the song's own grid.

usage: python -u tools/analysis/jl_steps.py <song.wav 44.1 kHz stereo> <out_dir>      (out_dir: tools/data/justlove)

Grid (measured, not assumed): 160.000 BPM, no drift.  High-band transients folded over one beat rise at
15.5 ms, so beat b of the chart sounds at 0.0155 + 0.375 * b seconds (the long-window spectral flux used
for the earlier charts leads the real transient by ~25 ms, which is why this one is measured in the
time domain).  The drums are a two-step break (snare on 2 and 4), which puts bar k on beat 3 + 4k; the
first sound of the song is the pick-up on beat 2.

Writes steps.npz with one value per 32nd note (8 per beat) and grid.json.  Runs in about two minutes.
"""
import json
import sys
import time

import librosa
import numpy as np
import soundfile as sf
from scipy.ndimage import median_filter, uniform_filter1d
from scipy.signal import butter, sosfiltfilt

BPM, PHASE, BAR0 = 160.0, 0.0155, 3
PER = 60.0 / BPM
SUB = 8  # steps per beat
T0 = time.time()


def log(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


wav, out = sys.argv[1], sys.argv[2]
y2, sr = sf.read(wav, dtype="float32")
assert sr == 44100
mono = y2.mean(axis=1).astype(np.float64)
dur = len(mono) / sr
nbeat = int((dur - PHASE) / PER)
nstep = nbeat * SUB
st = PHASE + np.arange(nstep) * PER / SUB
log(f"loaded {dur:.2f}s, {nbeat} beats, {nstep} steps")


def bp(lo, hi):
    if lo is None:
        sos = butter(4, hi, btype="low", fs=sr, output="sos")
    elif hi is None:
        sos = butter(4, lo, btype="high", fs=sr, output="sos")
    else:
        sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    return sosfiltfilt(sos, mono)


BANDS = {"sub": (None, 120), "low": (120, 500), "mid": (500, 3000), "pres": (3000, 8000), "air": (8000, None)}
E = {k: np.maximum(uniform_filter1d(bp(*v) ** 2, int(sr * 0.004)), 0.0) for k, v in BANDS.items()}
FULL = np.maximum(uniform_filter1d(mono ** 2, int(sr * 0.004)), 0.0)
CS = {k: np.concatenate([[0.0], np.cumsum(v)]) for k, v in E.items()}
CS["full"] = np.concatenate([[0.0], np.cumsum(FULL)])
log("band envelopes")


def win(key, t, a, b):
    """mean energy of a band over [t+a, t+b) (cumulative sums: O(1))"""
    c = CS[key]
    i0 = np.clip(((t + a) * sr).astype(int), 0, len(c) - 1)
    i1 = np.clip(((t + b) * sr).astype(int), 0, len(c) - 1)
    return (c[i1] - c[i0]) / np.maximum(i1 - i0, 1)


def rise(key, pre, post):
    """log energy step across each grid point, weighted by how loud the hit is"""
    a, b = win(key, st, *pre), win(key, st, *post)
    return np.maximum(0.0, np.log10((b + 1e-8) / (a + 1e-8))) * np.sqrt(b)


def norm(a, q=99.0):
    return (a / (np.percentile(a, q) + 1e-12)).astype(np.float32)


kick = norm(rise("sub", (-0.040, -0.004), (0.004, 0.050)))
body = norm(rise("low", (-0.030, -0.003), (0.000, 0.030)))
snare = norm(rise("pres", (-0.030, -0.003), (0.000, 0.030)))
hat = norm(rise("air", (-0.020, -0.003), (0.000, 0.015)))
mid = norm(rise("mid", (-0.030, -0.003), (0.000, 0.030)))
full = norm(rise("full", (-0.030, -0.003), (0.000, 0.030)))
lev = {k: np.sqrt(win(k, st, 0.0, PER / SUB)) for k in E}
lev_full = np.sqrt(win("full", st, 0.0, PER / SUB))
ref = np.percentile(lev_full, 90)
silent = lev_full < ref * 0.05
log("drum onsets, levels")
del E, FULL, CS

# ---- harmonic / percussive split (chunked, below 6 kHz), melody line ---------------------------------
y22 = librosa.resample(mono.astype(np.float32), orig_sr=sr, target_sr=22050)
hop = 256
fps = 22050 / hop
freqs = np.fft.rfftfreq(2048, 1 / 22050)
keep = freqs < 6000
seg = int(20.0 * fps) * hop
pad = int(1.5 * fps) * hop
hflux, pflux = [], []
for s0 in range(0, len(y22), seg):
    a, b = max(0, s0 - pad), min(len(y22), s0 + seg + pad)
    S = np.abs(librosa.stft(y22[a:b], n_fft=2048, hop_length=hop))[keep]
    Hm, Pm = librosa.decompose.hpss(S, kernel_size=(13, 25), margin=1.0)
    f0 = (s0 - a) // hop
    f1 = f0 + (min(seg, len(y22) - s0) + hop - 1) // hop
    fk = freqs[keep]
    for M, lo, hi, dst in ((Hm, 300, 3000, hflux), (Pm, 150, 6000, pflux)):
        m = (fk >= lo) & (fk < hi)
        L = np.log1p(40 * M[m])
        d = np.diff(L, axis=1, prepend=L[:, :1])
        d[d < 0] = 0
        dst.append(d.mean(0)[f0:f1])
hflux, pflux = np.concatenate(hflux), np.concatenate(pflux)
log("hpss")


def at(env, a=-0.016, b=0.045):
    i0 = np.clip(((st + a) * fps).astype(int), 0, len(env) - 1)
    i1 = np.clip(((st + b) * fps).astype(int) + 1, 1, len(env))
    return np.array([env[p:q].max() if q > p else 0.0 for p, q in zip(i0, i1)])


harm = norm(at(hflux), 99.5)
perc = norm(at(pflux), 99.5)

# melody: salience with harmonic summation on a constant-Q transform; a median over time removes drum hits
chop = 256
C = np.abs(librosa.cqt(y22, sr=22050, hop_length=chop, fmin=librosa.note_to_hz("C2"), n_bins=84 * 2, bins_per_octave=24)).astype(np.float32)
cfps = 22050 / chop
log("cqt")
Cm = median_filter(C, size=(1, 7))
lo_bin, hi_bin = 24 * 2 + 14, 24 * 4 + 10  # G4 .. F6: the lead / vocal register seen in the spectrogram
sal = np.zeros((hi_bin - lo_bin, C.shape[1]), np.float32)
for h, w in ((1, 1.0), (2, 0.6), (3, 0.35)):
    shf = int(round(24 * np.log2(h)))
    hi = min(C.shape[0], hi_bin + shf)
    sal[: hi - lo_bin - shf] += w * Cm[lo_bin + shf:hi]
pitch_fr = lo_bin + sal.argmax(0)
strength_fr = sal.max(0) / (np.percentile(sal.max(0), 95) + 1e-9)


def pitch_at(t):
    i0, i1 = int((t + 0.02) * cfps), min(int((t + PER / 4 + 0.01) * cfps), len(pitch_fr))
    if i1 <= i0:
        return 0.0, 0.0
    vals, cnt = np.unique(pitch_fr[i0:i1], return_counts=True)
    return float(vals[cnt.argmax()]) / 2.0 + 36.0, float(strength_fr[i0:i1].mean())  # MIDI note number


pp = np.array([pitch_at(t) for t in st])
# sub-bass pitch (the 808 glides): strongest bin below ~125 Hz
Cl = C[: 24 * 2 - 8]
sub_pitch_fr = Cl.argmax(0) / 2.0 + 36.0
sub_lvl_fr = Cl.max(0) / (np.percentile(Cl.max(0), 95) + 1e-9)


def sub_at(t):
    i0, i1 = int(t * cfps), min(int((t + PER / 4) * cfps) + 1, len(sub_pitch_fr))
    if i1 <= i0:
        return 0.0, 0.0
    return float(np.median(sub_pitch_fr[i0:i1])), float(sub_lvl_fr[i0:i1].mean())


sb = np.array([sub_at(t) for t in st])
log("melody, sub bass")

# spectrum for a visualiser: 16 log bands per 16th note, each normalised over the song
edges = np.geomspace(45, 5900, 17)
S2 = np.abs(librosa.stft(y22, n_fft=2048, hop_length=hop))[keep]
fk = freqs[keep]
masks = [(fk >= edges[b]) & (fk < edges[b + 1]) for b in range(16)]
n16 = nstep // 2
vis = np.zeros((n16, 16), np.float32)
w16 = max(2, int(PER / 4 * fps))
for i in range(n16):
    f0 = int(st[i * 2] * fps)
    mag = S2[:, f0:f0 + w16].mean(1) if f0 < S2.shape[1] else np.zeros(S2.shape[0])
    for b in range(16):
        vis[i, b] = mag[masks[b]].mean()
db = 20 * np.log10(vis + 1e-6)
p25, p99 = np.percentile(db, 25, axis=0), np.percentile(db, 99, axis=0)
vis = np.clip((db - p25) / (p99 - p25 + 1e-9), 0, 1).astype(np.float32)
log("visualiser bands")

np.savez_compressed(
    f"{out}/steps.npz", kick=kick, body=body, snare=snare, hat=hat, mid=mid, full=full, harm=harm, perc=perc,
    pitch=pp[:, 0].astype(np.float32), pitch_w=pp[:, 1].astype(np.float32),
    sub_pitch=sb[:, 0].astype(np.float32), sub_lvl=sb[:, 1].astype(np.float32),
    lev=(lev_full / ref).astype(np.float32), silent=silent, vis=vis,
    **{f"lev_{k}": (v / (np.percentile(v, 95) + 1e-12)).astype(np.float32) for k, v in lev.items()})
json.dump({"bpm": BPM, "phase": PHASE, "bar0": BAR0, "sub": SUB, "nbeat": int(nbeat), "duration": round(dur, 3)},
          open(f"{out}/grid.json", "w"))
log(f"wrote {out}/steps.npz")
