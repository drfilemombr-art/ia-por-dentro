"""Revisão automática do MP4 da abertura (requer ffmpeg, Pillow, numpy, soundfile).

Uso: python3 scripts/revisar-quadros.py out/ep03-abertura.mp4 public/audio/narracao.mp3

1. Letra de referência: mede, em cada quadro, o centro do traço do "l" de "ventilação"
   na altura da âncora e acusa qualquer deslocamento maior que 1 px.
2. Saltos: lista as maiores diferenças entre quadros consecutivos na área da frase.
3. Legendas: lista os quadros em que a área de legenda/título muda.
4. Voz: ganho e atraso da narração no MP4 em relação ao arquivo original.
"""
import subprocess, sys, tempfile, os
import numpy as np
from PIL import Image, ImageChops, ImageStat
import soundfile as sf

mp4, ref = sys.argv[1], sys.argv[2]
ANCHOR_X, ANCHOR_Y = 472.5, 720  # posição da âncora na tela (ver makeGeo em src/Abertura.tsx)
tmp = tempfile.mkdtemp()
subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp4, "-vsync", "0", f"{tmp}/f%03d.png"], check=True)
frames = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
L = lambda i: Image.open(f"{tmp}/{frames[i]}").convert("L")

def stroke_center(im, y, x0):
    row = np.array(im.crop((0, y, im.width, y + 1))).ravel() > 150
    runs, x = [], 0
    while x < len(row):
        if row[x]:
            s = x
            while x < len(row) and row[x]: x += 1
            runs.append((s, x - 1))
        x += 1
    r = min(runs, key=lambda r: abs((r[0] + r[1]) / 2 - x0))
    return (r[0] + r[1]) / 2, r[1] - r[0] + 1

l_typed = 100  # quadro em que o "l" é digitado (data/typing.json, 3,331 s)
xs = [stroke_center(L(i), ANCHOR_Y, ANCHOR_X) for i in range(l_typed, len(frames))]
dev = max(abs(x - xs[0][0]) for x, _ in xs)
print(f"[âncora] quadros {l_typed}-{len(frames)-1}: x de {min(x for x,_ in xs)} a {max(x for x,_ in xs)} px "
      f"(desvio máx {dev:.1f} px); traço {xs[0][1]} → {xs[-1][1]} px")

diffs = []
prev = L(0)
for i in range(1, len(frames)):
    cur = L(i); d = ImageChops.difference(cur, prev)
    diffs.append((i, ImageStat.Stat(d.crop((0, 300, 1080, 1100))).mean[0], ImageStat.Stat(d.crop((0, 1200, 1080, 1460))).mean[0]))
    prev = cur
print("[saltos] maiores variações na área da frase:", ", ".join(f"q{i}:{a:.1f}" for i, a, _ in sorted(diffs, key=lambda x: -x[1])[:6]))
print("[legendas] trocas na área inferior:", " ".join(f"q{i}" for i, _, c in diffs if c > 0.5))

wav = f"{tmp}/mix.wav"; refw = f"{tmp}/ref.wav"
subprocess.run(["ffmpeg", "-loglevel", "error", "-i", mp4, "-vn", "-ar", "44100", "-af", "pan=mono|c0=c0", wav], check=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-i", ref, "-t", "11.2", "-ac", "1", "-ar", "44100", refw], check=True)
m, sr = sf.read(wav); v, _ = sf.read(refw); n = min(len(m), len(v)); m, v = m[:n], v[:n]
lag = max(range(-441, 442), key=lambda k: np.dot(m[max(0, k):n + min(0, k)], v[max(0, -k):n - max(0, k)]))
print(f"[voz] atraso {lag} amostras ({lag/sr*1000:.1f} ms); ganho {20*np.log10(np.dot(m, v)/np.dot(v, v)):+.2f} dB")
