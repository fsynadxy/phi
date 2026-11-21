"""Source separation with Demucs (htdemucs): writes vocals / drums / bass / other as 22.05 kHz mono wavs.

usage: python wem_separate.py <song.ogg> <workdir>
"""
import sys

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model

src, W = sys.argv[1], sys.argv[2]
torch.set_num_threads(4)
model = get_model("htdemucs")
model.eval()
import subprocess

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "f32le", "-ac", "2", "-ar", str(model.samplerate), "-"],
                     check=True, capture_output=True).stdout
wav = torch.from_numpy(np.frombuffer(raw, np.float32).reshape(-1, 2).T.copy())
ref = wav.mean(0)
wav = (wav - ref.mean()) / ref.std()
with torch.no_grad():
    out = apply_model(model, wav[None], device="cpu", shifts=1, split=True, overlap=0.25, progress=False)[0]
out = out * ref.std() + ref.mean()
import librosa

for name, x in zip(model.sources, out):
    mono = x.mean(0).numpy()
    mono = librosa.resample(mono, orig_sr=model.samplerate, target_sr=22050)
    sf.write(f"{W}/stem_{name}.wav", mono, 22050)
    print(name, float(np.sqrt((mono ** 2).mean())))
