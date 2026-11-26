// EP03 · abertura cinematográfica (v2).
// Imagem: Blender/Cycles (blender/cena.py) → public/frames/fNNNN.png.
// Aqui: legendas, título-pergunta, rótulos científicos e mixagem, nos mesmos tempos da narração.
import React from "react";
import { AbsoluteFill, Audio, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig, Easing } from "remotion";
import TL from "../data/timeline.json";
import TOK from "../data/tokens.json";
import { useFontsReady } from "./fonts";
import { Captions, Title } from "./Abertura";
import { C, FONT } from "./theme";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const fade = (t: number, a: number, b: number) => interpolate(t, [a, b], [0, 1], { ...clamp, easing: Easing.bezier(0.16, 1, 0.3, 1) });

// Tempos da imagem (iguais a blender/cena.py)
const PUSH0 = 7.08, PUSH1 = 8.15;

const Label: React.FC<{ top: number; opacity: number; children: React.ReactNode; size?: number }> = ({ top, opacity, children, size = 30 }) => (
  <div
    style={{
      position: "absolute", top, left: 90, width: 900, textAlign: "center",
      fontFamily: FONT.caption, fontWeight: 500, fontSize: size, lineHeight: 1.3,
      color: "#9AA4AE", letterSpacing: "0.01em", opacity,
      textShadow: "0 1px 8px rgba(0,0,0,0.8)",
    }}
  >
    {children}
  </div>
);

// `from`: quadro absoluto da linha do tempo do episódio em que esta composição começa.
// Todas as trilhas são cortadas no mesmo ponto, então voz, efeitos e imagem continuam alinhados.
const Sound: React.FC<{ from: number; fadeEnd: boolean }> = ({ from, fadeEnd }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const v = (f: number, a: number, b: number) => interpolate((f + from) / fps, [a, b], [0, 1], clamp);
  const end = (f: number) => (fadeEnd ? 1 - interpolate(f, [durationInFrames - 8, durationInFrames - 1], [0, 1], clamp) : 1);
  return (
    <>
      <Audio src={staticFile(TL.audio.file)} trimBefore={from} />
      <Audio src={staticFile("sfx/teclas.wav")} trimBefore={from} />
      <Audio src={staticFile("sfx/ambiente-sala.wav")} trimBefore={from} volume={(f) => Math.min(v(f, 0, 0.12), 1 - v(f, PUSH0, PUSH1 - 0.1))} />
      <Audio src={staticFile("sfx/ambiente-tela.wav")} trimBefore={from} volume={(f) => Math.min(v(f, PUSH0, PUSH1 - 0.1), end(f))} />
      <Audio src={staticFile("sfx/transicao-fragmentos.wav")} trimBefore={from} />
    </>
  );
};

export type CinemaProps = { from?: number; fadeEnd?: boolean; seam?: number | null };

export const Cinema: React.FC<CinemaProps> = ({ from = 0, fadeEnd = true, seam = null }) => {
  const frame = useCurrentFrame() + from;
  const { fps } = useVideoConfig();
  const ready = useFontsReady();
  const t = frame / fps;
  const scrim = 1 - interpolate(t, [PUSH0, PUSH1], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Sound from={from} fadeEnd={fadeEnd} />
      <Img src={staticFile(`frames/f${String(frame).padStart(4, "0")}.png`)} style={{ width: 1080, height: 1920 }} />
      {/* véu escuro só atrás da legenda enquanto a mesa está em quadro (legibilidade sobre o teclado) */}
      <AbsoluteFill
        style={{
          opacity: 0.85 * scrim,
          background: "radial-gradient(ellipse 62% 9% at 50% 71%, rgba(0,0,0,0.62), rgba(0,0,0,0) 100%)",
        }}
      />
      {ready ? (
        <>
          <Label top={196} opacity={fade(t, 8.0, 8.35)} size={26}>
            <span style={{ letterSpacing: "0.16em", color: C.cyan, fontWeight: 600 }}>ILUSTRAÇÃO</span>
            {"  ·  "}tokenizador {TOK.tokenizer} (OpenAI)
          </Label>
          <Label top={236} opacity={fade(t, 8.7, 9.1)} size={26}>
            Claude, Gemini e outros modelos usam tokenizadores próprios
          </Label>
          <Label top={1146} opacity={fade(t, 8.6, 8.95)}>
            fragmento <span style={{ color: C.cyan }}>→</span> ID no vocabulário
          </Label>
          <Captions t={t} />
          <Title t={t} />
          {/* prévia de revisão: marca discreta no quadro da emenda (não existe no trecho limpo) */}
          {seam !== null && frame >= seam && frame < seam + 3 ? (
            <div style={{ position: "absolute", top: 40, right: 40, fontFamily: FONT.caption, fontSize: 24, color: "#E5B85C" }}>emenda · q{seam}</div>
          ) : null}
        </>
      ) : null}
    </AbsoluteFill>
  );
};
