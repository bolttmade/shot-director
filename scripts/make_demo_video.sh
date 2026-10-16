#!/usr/bin/env bash
# Build the demo video draft: free and local, spends no Comfy credits, posts nothing.
#   scripts/make_demo_video.sh                 # everything -> $DEMO_OUT/shot-director-demo.mp4 (default ./demo)
#   DEMO_OUT=/workspace/comfy/demo scripts/make_demo_video.sh
#   scripts/make_demo_video.sh capture previs  # re-run one stage (cards | tts | capture [--only a,b] | assemble)
# Needs: python3, ffmpeg, google-chrome/chromium, network (once: piper voice download, and the live Space for one beat).
set -euo pipefail
cd "$(dirname "$0")/.."
export DEMO_OUT="${DEMO_OUT:-$PWD/demo}"
mkdir -p "$DEMO_OUT/voices"
# 1) playwright (screen capture) in a throwaway venv, Pillow comes with it
if [ ! -x /tmp/shots/bin/python ]; then python3 -m venv /tmp/shots && /tmp/shots/bin/pip install -q playwright pillow; fi
# 2) piper (offline TTS) + one voice model (downloaded once; kept out of git)
if [ ! -x /tmp/tts/bin/python ]; then python3 -m venv /tmp/tts && /tmp/tts/bin/pip install -q piper-tts; fi
V="$DEMO_OUT/voices/en_US-lessac-medium.onnx"
if [ ! -s "$V" ]; then
  base=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium
  curl -sL -o "$V" "$base/en_US-lessac-medium.onnx" && curl -sL -o "$V.json" "$base/en_US-lessac-medium.onnx.json"
fi
export PIPER_PY=/tmp/tts/bin/python PIPER_VOICE="$V"
# the app venv (ffmpeg/pytest/app deps) is the repo's .venv
[ -x .venv/bin/python ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
stage="${1:-all}"; shift || true
/tmp/shots/bin/python scripts/demo_video.py "$stage" "$@"
if [ "$stage" = all ] || [ "$stage" = assemble ]; then
  ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height -of default=nw=1 "$DEMO_OUT/shot-director-demo.mp4"
fi
