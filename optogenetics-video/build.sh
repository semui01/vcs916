#!/usr/bin/env bash
# Rebuild the whole video: VO → timeline → frames → score/SFX → final mp4s.
# needs: python3 (kokoro-onnx soundfile scipy numpy), node + playwright, ffmpeg
# KOKORO_DIR must hold kokoro-v1.0.onnx + voices-v1.0.bin (github.com/thewh1teagle/kokoro-onnx releases)
set -euo pipefail
cd "$(dirname "$0")"
: "${KOKORO_DIR:?set KOKORO_DIR}"; WORK=${WORK:-build}; mkdir -p vo "$WORK" out
python3 tts.py "$KOKORO_DIR" am_michael 1.22
echo "window.TL = $(cat timeline.json);" > timeline.js
node render.js video "$WORK" 4 30
ffmpeg -y -loglevel error -f concat -safe 0 -i "$WORK/segs.txt" -c copy "$WORK/video_raw.mp4"
python3 audio.py "$WORK/cues.json" timeline.json vo "$WORK/mix.wav"
python3 audio.py "$WORK/cues.json" timeline.json vo "$WORK/mix_novo.wav" --no-vo
for v in "mix:hijacked-light_optogenetics_1080x1920.mp4" "mix_novo:hijacked-light_NO-VO_music-sfx-only.mp4"; do
  ffmpeg -y -loglevel error -i "$WORK/video_raw.mp4" -i "$WORK/${v%%:*}.wav" -map 0:v -map 1:a -c:v libx264 -preset slow -crf 17 \
    -pix_fmt yuv420p -movflags +faststart -af "loudnorm=I=-14:TP=-1:LRA=11" -c:a aac -b:a 256k -shortest "out/${v#*:}"
done
