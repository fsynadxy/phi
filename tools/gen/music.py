"""Music analysis data for the generator (beats are RPE beats: beat k == analysis beat k, bar n starts at 2+4n)."""
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("CHART_DATA", os.path.join(HERE, "..", "data"))
_S = np.load(os.path.join(DATA, "steps.npz"))
KEYS = ["low_p", "lmid_p", "high_p", "mid_h", "lmid_h", "mid_p", "high_h", "low_h"]
S = {k: _S[k] for k in KEYS if k in _S.files}
NSTEP = len(S["low_p"])
PITCH = _S["pitch_cent"]


def B(bar, beat=0.0):
    """RPE beat of (bar, beat-in-bar)."""
    return 2 + 4 * bar + beat


def step_beat(s):
    return 2 + s / 4


def bar_steps(bar):
    return range(bar * 16, bar * 16 + 16)


def val(key, s):
    return float(S[key][s]) if 0 <= s < NSTEP else 0.0


def perc(s):
    return max(val("low_p", s), val("lmid_p", s), 0.85 * val("high_p", s))


def harm(s):
    return max(val("mid_h", s), 0.9 * val("lmid_h", s))


def sal(s, wp=1.0, wh=1.0):
    return max(wp * perc(s), wh * harm(s))


def local_norm(arr_fn, bar0, bar1):
    """values for steps in [bar0,bar1) normalised by that region's 95th percentile."""
    st = list(range(bar0 * 16, bar1 * 16))
    v = np.array([arr_fn(s) for s in st])
    q = np.percentile(v, 95) + 1e-9
    return st, v / q


# ------------------------------------------------------------- visualizer spectrum (per 8th note)
_VIS = os.path.join(DATA, "vis8.npz")


def _compute_vis(nb=16):
    import soundfile as sf
    y, sr = sf.read(os.environ["SONG_WAV"], dtype="float32")  # mono 22050 Hz wav of the song
    spb = 60 / 123.0
    ph = 0.3290
    n8 = int((len(y) / sr - ph) / (spb / 2))
    edges = np.geomspace(40, 10000, nb + 1)
    nfft = 4096
    win = np.hanning(nfft).astype(np.float32)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    out = np.zeros((n8, nb), np.float32)
    for i in range(n8):
        t = ph + i * spb / 2
        a = int(t * sr)
        seg = y[a:a + nfft]
        if len(seg) < nfft:
            seg = np.pad(seg, (0, nfft - len(seg)))
        mag = np.abs(np.fft.rfft(seg * win))
        for b in range(nb):
            m = (freqs >= edges[b]) & (freqs < edges[b + 1])
            out[i, b] = mag[m].mean()
    db = 20 * np.log10(out + 1e-6)
    lo = np.percentile(db, 20, axis=0)
    hi = np.percentile(db, 99, axis=0)
    norm = np.clip((db - lo) / (hi - lo + 1e-9), 0, 1)
    np.savez_compressed(_VIS, v=norm)
    return norm


VIS = np.load(_VIS)["v"] if os.path.exists(_VIS) else _compute_vis()


def vis(beat, band):
    """spectrum energy (0..1) for the 8th note starting at RPE beat `beat`."""
    i = int(round(beat * 2))
    if 0 <= i < len(VIS):
        return float(VIS[i, band])
    return 0.0


# ------------------------------------------------------------- sections (bars)
SECTIONS = [
    ("prelude", 0, 27), ("ascent", 27, 34), ("bloom", 34, 43), ("breath", 43, 47), ("pulse", 47, 75),
    ("echo", 75, 91), ("orbit", 91, 115), ("mirage", 115, 135), ("zenith", 135, 151), ("memory", 151, 159),
    ("finale", 159, 168), ("coda", 168, 177),
]
