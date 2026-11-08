"""Cut the four footage clips of the 新宿决战 chart out of the reference MAD video.

usage: python cut_clips.py <video file (BV1dGTu66Eo4, any resolution)> <out_dir> [song.ogg [video audio]]

The video's soundtrack runs 0.5595 s ahead of the song (measured by cross-correlation of the two
recordings over 40 s, no drift up to the end). If song.ogg is given, the lag is re-measured against the
video's soundtrack (or against a separate audio file, for DASH downloads whose video stream has no sound).
Clips are cut on the chart's beats (153.6 BPM, beat 0 at 0.2935 s of the song), scaled to 1280x720,
H.264 yuv420p without audio, and run 0.1 s longer than their segment so Phira never shows a gap.
"""
import os
import subprocess
import sys

SPB = 60 / 153.6
PHASE = 0.2935
SEGMENTS = {"clip_a": (73, 82), "clip_b": (105, 113), "clip_c": (144, 154), "clip_d": (216, 238.6)}


def measure_lag(video, song):
    import numpy as np
    import soundfile as sf
    from scipy.signal import correlate

    def mono(path):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "22050", "-f", "f32le", "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.float32)
    v, s = mono(video), mono(song)
    sr = 22050
    n = sr * 40
    c = correlate(v[:n + sr * 2], s[:n], mode="valid", method="fft")
    return int(np.argmax(c)) / sr


def main():
    video, out = sys.argv[1], sys.argv[2]
    lag = measure_lag(sys.argv[4] if len(sys.argv) > 4 else video, sys.argv[3]) if len(sys.argv) > 3 else 0.5594557823129251
    print(f"video leads the song by {lag:.4f} s")
    os.makedirs(out, exist_ok=True)
    for name, (b0, b1) in SEGMENTS.items():
        t0 = PHASE + b0 * SPB + lag
        dur = (b1 - b0) * SPB + 0.1
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.4f}", "-i", video, "-t", f"{dur:.4f}", "-an",
                        "-vf", "scale=1280:720:flags=lanczos,unsharp=5:5:0.6:5:5:0.0,format=yuv420p",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-profile:v", "high", "-level", "4.0",
                        "-g", "30", "-movflags", "+faststart", "-map_metadata", "-1", os.path.join(out, name + ".mp4")],
                       check=True)
        print(f"{name}: beats {b0}-{b1}, video {t0:.3f}s + {dur:.3f}s")


if __name__ == "__main__":
    main()
