#!/usr/bin/env bash
# Record a Phira chart with the real engine, offline, frame by frame (1080p60, 4x MSAA) and mix the song
# with the game's hitsounds on the engine's own timeline.
#
#   JL_WORK=<dir> PHIRA=<phira checkout> tools/render/render.sh <chart.pez> <out.mp4>
#
# Needs: a Rust toolchain, Xvfb + Mesa (llvmpipe), ffmpeg, libasound2-dev, libwayland-dev; python numpy + soundfile.
# Without a sound card Phira needs a null ALSA device (written to ~/.asoundrc below).
set -euo pipefail
PEZ=$1; OUT=$2; HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$JL_WORK"; rm -rf "$JL_WORK/unpacked" "$JL_WORK/rassets"
python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$PEZ" "$JL_WORK/unpacked"
mkdir -p "$JL_WORK/rassets" && cp -r "$PHIRA"/assets/* "$JL_WORK/rassets/"   # fonts, note skin, hitsounds
[ -f "$JL_WORK/rassets/font.ttf" ] || cp "$JL_WORK/rassets/bold.ttf" "$JL_WORK/rassets/font.ttf"
grep -q nullsink ~/.asoundrc 2>/dev/null || printf 'pcm.nullsink { type null }\npcm.!default { type plug slave { pcm "nullsink" rate 48000 channels 2 format S16_LE } }\n' >> ~/.asoundrc
cp -r "$HERE/jl-render" "$PHIRA/" && grep -q '"jl-render"' "$PHIRA/Cargo.toml" || sed -i 's/    "phira-monitor",/    "phira-monitor",\n    "jl-render",/' "$PHIRA/Cargo.toml"
(cd "$PHIRA" && cargo build --release -p jl-render)
BIN=$PHIRA/target/release/jl-render
# The loading card switches to the game on frame 169 and the music starts on frame 212 (3.533 s): see mix.py.
FRAMES=${FRAMES:-17900}; HALF=$((FRAMES / 2))
xvfb-run -a $BIN "$JL_WORK/rassets" "$JL_WORK/unpacked" "$JL_WORK/part1.mp4" 1920 1080 60 0 $HALF 4 17 &
sleep 3
xvfb-run -a $BIN "$JL_WORK/rassets" "$JL_WORK/unpacked" "$JL_WORK/part2.mp4" 1920 1080 60 $HALF $((FRAMES - HALF)) 4 17 &
wait
JL_WORK=$JL_WORK python3 "$HERE/mix.py" $FRAMES 0.6
printf "file '%s'\nfile '%s'\n" "$JL_WORK/part1.mp4" "$JL_WORK/part2.mp4" > "$JL_WORK/parts.txt"
END=$(python3 -c "print($FRAMES / 60 - 1)")
ffmpeg -y -f concat -safe 0 -i "$JL_WORK/parts.txt" -i "$JL_WORK/mix.wav" -map 0:v -map 1:a -c:v copy \
  -af "volume=0.75,alimiter=limit=0.89:attack=5:release=50:level=disabled,afade=t=out:st=$END:d=1" \
  -c:a aac -b:a 320k -shortest -movflags +faststart "$OUT"
