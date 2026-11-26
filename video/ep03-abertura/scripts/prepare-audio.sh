#!/usr/bin/env bash
# Prepara a narração para o Remotion sem alterar a voz:
# decodifica o MP3 original e copia o canal mono nos dois lados, com ganho 1,0.
# (O upmix padrão do FFmpeg coloca o mono a −3 dB em cada canal; isto evita essa perda.)
set -euo pipefail
cd "$(dirname "$0")/.."
ffmpeg -hide_banner -loglevel error -y -i public/audio/narracao.mp3 \
  -af "pan=stereo|c0=c0|c1=c0" -c:a pcm_s24le public/audio/narracao-dual-mono.wav
echo "public/audio/narracao-dual-mono.wav pronto"
