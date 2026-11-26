// Sintetiza os efeitos da abertura (sem bibliotecas, sem bancos de som externos):
//   public/sfx/teclas.wav          — uma tecla por evento de data/typing.json (pressão + fundo de curso + soltura)
//   public/sfx/ambiente-sala.wav   — tom de sala de plantão: ar-condicionado + monitores distantes
//   public/sfx/ambiente-tela.wav   — o mesmo ambiente abafado (passa-baixa), usado depois que a câmera entra na tela
// Todos em 48 kHz, 16 bits, estéreo, com a duração exata da abertura.
import { readFileSync, writeFileSync } from "node:fs";
const TL = JSON.parse(readFileSync(new URL("../data/timeline.json", import.meta.url), "utf8"));
const TY = JSON.parse(readFileSync(new URL("../data/typing.json", import.meta.url), "utf8"));
const SR = 48000;
const N = Math.round(TL.durationSec * SR);

let seed = 7741;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
const noise = () => rnd() * 2 - 1;
const db = (d) => 10 ** (d / 20);

// Biquad RBJ
function biquad(type, f0, Q) {
  const w = (2 * Math.PI * f0) / SR, c = Math.cos(w), s = Math.sin(w), a = s / (2 * Q);
  let b0, b1, b2, a0, a1, a2;
  if (type === "lp") { b0 = (1 - c) / 2; b1 = 1 - c; b2 = (1 - c) / 2; a0 = 1 + a; a1 = -2 * c; a2 = 1 - a; }
  if (type === "hp") { b0 = (1 + c) / 2; b1 = -(1 + c); b2 = (1 + c) / 2; a0 = 1 + a; a1 = -2 * c; a2 = 1 - a; }
  if (type === "bp") { b0 = a; b1 = 0; b2 = -a; a0 = 1 + a; a1 = -2 * c; a2 = 1 - a; }
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  return (x) => { const y = (b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0; x2 = x1; x1 = x; y2 = y1; y1 = y; return y; };
}
const filt = (buf, ...fs) => { for (const f of fs) for (let i = 0; i < buf.length; i++) buf[i] = f(buf[i]); return buf; };

// Reverb curto: convolução com ruído de decaimento exponencial (esparsa, rápida o bastante para 11 s).
function reverb(buf, rt, wet, lp) {
  const len = Math.round(rt * SR), ir = new Float32Array(len), f = biquad("lp", lp, 0.7);
  for (let i = 0; i < len; i++) ir[i] = f(noise()) * Math.exp((-6.9 * i) / len);
  let e = 0; for (const v of ir) e += v * v; const g = wet / Math.sqrt(e);
  const out = Float32Array.from(buf);
  const step = 4; // IR decimado para custo baixo; suficiente para cauda difusa
  for (let i = 0; i < buf.length; i++) {
    const x = buf[i]; if (Math.abs(x) < 1e-5) continue;
    for (let k = 0; k < len && i + k < out.length; k += step) out[i + k] += x * ir[k] * g * Math.sqrt(step);
  }
  return out;
}

// ---------- Teclas ----------
function addKey(buf, t, kind, gainDb) {
  const A = db(gainDb), i0 = Math.round(t * SR);
  const burst = (at, dur, fc, q, amp) => {
    const f = biquad("bp", fc, q), n = Math.round(dur * 8 * SR);
    for (let n2 = 0; n2 < n; n2++) { const i = at + n2; if (i < 0 || i >= buf.length) continue; buf[i] += f(noise()) * Math.exp(-n2 / (dur * SR)) * amp; }
  };
  const body = (at, f0, dur, amp) => {
    const n = Math.round(dur * 7 * SR); let ph = 0;
    for (let n2 = 0; n2 < n; n2++) { const i = at + n2; if (i >= buf.length) break; const fr = f0 * (1 - 0.12 * n2 / n); ph += (2 * Math.PI * fr) / SR; buf[i] += Math.sin(ph) * Math.exp(-n2 / (dur * SR)) * amp; }
  };
  const space = kind === "space";
  burst(i0, 0.0022, 2400 + rnd() * 1400, 1.1, A * 2.2);                                   // contato
  body(i0, space ? 125 + rnd() * 20 : 190 + rnd() * 120, space ? 0.028 : 0.014, A * 0.42); // corpo da tecla
  burst(i0 + Math.round((0.004 + rnd() * 0.005) * SR), 0.0014, 4600 + rnd() * 1500, 1.4, A * 1.1); // fundo de curso
  const rel = i0 + Math.round((space ? 0.12 : 0.075 + rnd() * 0.035) * SR);
  burst(rel, 0.0018, 3200 + rnd() * 1500, 1.2, A * 0.7);                                   // soltura
  body(rel, 260 + rnd() * 80, 0.008, A * 0.12);
}
const keys = new Float32Array(N);
for (const k of TY.keys) {
  let g = -29 + (rnd() * 3 - 1.5);
  if (k.kind === "space") g += 1.5;
  if (k.kind === "dead") g -= 1.0;
  addKey(keys, k.t, k.kind, g);
}
const keysWet = reverb(keys, 0.22, 0.22, 3500);

// ---------- Ambiente ----------
function pink(n) {
  const out = new Float32Array(n); let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < n; i++) { const w = noise();
    b0 = 0.99886 * b0 + w * 0.0555179; b1 = 0.99332 * b1 + w * 0.0750759; b2 = 0.969 * b2 + w * 0.153852;
    b3 = 0.8665 * b3 + w * 0.3104856; b4 = 0.55 * b4 + w * 0.5329522; b5 = -0.7616 * b5 - w * 0.016898;
    out[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11; b6 = w * 0.115926; }
  return out;
}
const rms = (b) => { let s = 0; for (const v of b) s += v * v; return Math.sqrt(s / b.length); };
const norm = (b, targetDb) => { const g = db(targetDb) / (rms(b) || 1); for (let i = 0; i < b.length; i++) b[i] *= g; return b; };

function roomChannel(beepPan) {
  const room = filt(pink(N), biquad("hp", 120, 0.7), biquad("lp", 3200, 0.7));
  norm(room, -45);
  // ar-condicionado: grave, com leve oscilação lenta
  const hvac = filt(pink(N), biquad("lp", 220, 0.7), biquad("lp", 220, 0.7), biquad("hp", 40, 0.7));
  norm(hvac, -50);
  for (let i = 0; i < N; i++) hvac[i] *= 1 + 0.15 * Math.sin((2 * Math.PI * i) / (SR * 3.7));
  // dois monitores multiparamétricos distantes (bipe de pulso), atrás de uma parede
  const beeps = new Float32Array(N);
  const monitor = (period, phase, freq, levelDb) => {
    for (let t = phase; t < TL.durationSec; t += period) {
      const i0 = Math.round(t * SR), n = Math.round(0.07 * SR);
      for (let k = 0; k < n && i0 + k < N; k++) {
        const env = Math.min(1, k / (0.004 * SR)) * Math.min(1, (n - k) / (0.012 * SR));
        beeps[i0 + k] += Math.sin((2 * Math.PI * freq * k) / SR) * env * db(levelDb);
      }
    }
  };
  monitor(0.78, 0.35, 932, -37 + beepPan);
  monitor(0.92, 0.61, 784, -42 - beepPan);
  const beepsFar = reverb(filt(beeps, biquad("lp", 1700, 0.7), biquad("hp", 300, 0.7)), 0.7, 0.9, 2500);
  for (let i = 0; i < N; i++) beepsFar[i] *= 0.55;
  const out = new Float32Array(N);
  for (let i = 0; i < N; i++) out[i] = room[i] + hvac[i] + beepsFar[i];
  return out;
}
const ambL = roomChannel(1.5), ambR = roomChannel(-1.5);
const muffle = (b) => { const o = Float32Array.from(b); filt(o, biquad("lp", 380, 0.7), biquad("lp", 380, 0.7)); for (let i = 0; i < N; i++) o[i] *= db(-8); return o; };
const telaL = muffle(ambL), telaR = muffle(ambR);

// ---------- WAV ----------
function writeWav(path, L, R) {
  const n = L.length, buf = Buffer.alloc(44 + n * 4);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * 4, 4); buf.write("WAVE", 8); buf.write("fmt ", 12);
  buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22); buf.writeUInt32LE(SR, 24);
  buf.writeUInt32LE(SR * 4, 28); buf.writeUInt16LE(4, 32); buf.writeUInt16LE(16, 34); buf.write("data", 36); buf.writeUInt32LE(n * 4, 40);
  let peak = 0;
  for (let i = 0; i < n; i++) {
    const l = Math.max(-1, Math.min(1, L[i])), r = Math.max(-1, Math.min(1, R[i]));
    peak = Math.max(peak, Math.abs(l), Math.abs(r));
    buf.writeInt16LE(Math.round(l * 32767), 44 + i * 4); buf.writeInt16LE(Math.round(r * 32767), 46 + i * 4);
  }
  writeFileSync(new URL(path, import.meta.url), buf);
  console.log(path, "pico", (20 * Math.log10(peak)).toFixed(1), "dBFS; RMS", (20 * Math.log10(rms(L))).toFixed(1), "dBFS");
}
// ---------- Travessia e fragmentos ----------
// Ar da aproximação: ruído com banda que sobe enquanto a câmera entra na tela.
const V = TL.voice;
const trans = new Float32Array(N);
{
  const t0 = 7.08, t1 = 8.15; let bpf = null; let lastFc = 0;
  for (let i = Math.round(t0 * SR); i < Math.min(N, Math.round(t1 * SR)); i++) {
    const p = (i / SR - t0) / (t1 - t0);
    const fc = 260 * Math.pow(2200 / 260, p);
    if (!bpf || Math.abs(fc - lastFc) > 20) { bpf = biquad("bp", fc, 0.9); lastFc = fc; }
    const env = Math.sin(Math.PI * Math.min(1, p * 1.15)) ** 2;
    trans[i] = bpf(noise()) * env * db(-31);
  }
}
// Fragmentos: um toque curto e vítreo por token, na entrada da placa (afinação sobe levemente).
const tok = new Float32Array(N);
for (let k = 0; k < 7; k++) {
  const t = V.tokensWord + k * 0.085 + 0.05, i0 = Math.round(t * SR), f0 = 1760 * Math.pow(1.045, k);
  for (let n = 0; n < 0.25 * SR && i0 + n < N; n++) {
    const tt = n / SR, env = Math.exp(-tt / 0.045) * Math.min(1, n / (0.0015 * SR));
    tok[i0 + n] += (Math.sin(2 * Math.PI * f0 * tt) + 0.45 * Math.sin(2 * Math.PI * f0 * 2.76 * tt) * Math.exp(-tt / 0.02)) * env * db(-36);
  }
}
const tokWet = reverb(tok, 0.6, 0.35, 6000);
// Tensão antes da pergunta: um grave que cresce na pausa e se recolhe quando a voz volta em "Mas".
const swell = new Float32Array(N);
{
  const a = 8.38, b = V.mas - 0.02, c = V.mas + 0.30;
  for (let i = Math.round(a * SR); i < Math.min(N, Math.round(c * SR)); i++) {
    const t = i / SR;
    const env = t < b ? ((t - a) / (b - a)) ** 2 : Math.max(0, 1 - (t - b) / (c - b)) ** 1.5;
    const x = Math.sin(2 * Math.PI * 73.4 * t) + 0.5 * Math.sin(2 * Math.PI * 146.8 * t) + 0.25 * Math.sin(2 * Math.PI * 220.2 * t);
    swell[i] = Math.tanh(x * 1.3) * env * db(-30);
  }
}
const fxL = new Float32Array(N), fxR = new Float32Array(N);
for (let i = 0; i < N; i++) { const v = trans[i] + tokWet[i] + swell[i]; fxL[i] = v; fxR[i] = v; }
writeWav("../public/sfx/transicao-fragmentos.wav", fxL, fxR);

// teclas: leve abertura estéreo (mono quase centrado, digitação à frente)
writeWav("../public/sfx/teclas.wav", keysWet, keysWet);
writeWav("../public/sfx/ambiente-sala.wav", ambL, ambR);
writeWav("../public/sfx/ambiente-tela.wav", telaL, telaR);
