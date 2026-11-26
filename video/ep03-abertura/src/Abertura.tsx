import React, { useMemo } from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import TL from "../data/timeline.json";
import TY from "../data/typing.json";
import TOK from "../data/tokens.json";
import { useFontsReady } from "./fonts";
import { ASC, F0, LINE_H, Layout, makeLayout } from "./layout";
import { C, FONT } from "./theme";

// ---------------------------------------------------------------------------
// Parâmetros de composição (px de tela, 1080 × 1920)
// ---------------------------------------------------------------------------
const W = 1080;
const S_FINAL = TL.camera.pushScale;  // escala da câmera ao fim da aproximação
const ANCHOR_Y = 720;                 // altura, na tela, da letra de referência (linha do meio)
const GAP_FINAL = 20;                 // vão entre fragmentos, já na escala final
const PAD_FINAL = 7;                  // folga horizontal da caixa de cada fragmento
const FIELD_PAD_X = 88;               // margens do campo de texto (px de cena)
const FIELD_PAD_TOP = 64;
const FIELD_PAD_BOTTOM = 132;         // inclui a linha do botão de enviar
const CAPTION_BOTTOM = 1430;          // base do bloco de legenda (acima da interface inferior do Reels)
const CAPTION_W = 820;                // coluna central, longe dos botões da direita

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const easeInOut = Easing.bezier(0.42, 0, 0.58, 1);
const easeOut = Easing.bezier(0.16, 1, 0.3, 1);
const pushEase = Easing.bezier(0.4, 0, 0.1, 1);

const lerp = (t: number, t0: number, t1: number, v0: number, v1: number, easing = easeInOut) =>
  interpolate(t, [t0, t1], [v0, v1], { ...clamp, easing });

// ---------------------------------------------------------------------------
// Câmera: escala em torno da letra de referência (ponto fixo da travessia)
// ---------------------------------------------------------------------------
const cameraScale = (t: number) => {
  const { driftEnd, driftScale, pushStart, pushEnd, pushScale } = TL.camera;
  if (t < pushStart) {
    // abre já em movimento: aproximação lenta que assenta quando a digitação para
    return interpolate(t, [0, driftEnd], [1, driftScale], { ...clamp, easing: Easing.out(Easing.sin) });
  }
  // aproximação em escala logarítmica (velocidade aparente constante de um dolly)
  const p = interpolate(t, [pushStart, pushEnd], [0, 1], { ...clamp, easing: pushEase });
  return Math.exp(Math.log(driftScale) + (Math.log(pushScale) - Math.log(driftScale)) * p);
};

// ---------------------------------------------------------------------------
// Geometria derivada do layout
// ---------------------------------------------------------------------------
type Geo = ReturnType<typeof makeGeo>;
const makeGeo = (L: Layout) => {
  const gapScene = GAP_FINAL / S_FINAL;
  const padScene = PAD_FINAL / S_FINAL;
  // extensão do bloco no modo tokens (com vãos abertos)
  let left = 0, right = 0;
  for (const r of L.runs) {
    const x = r.x + r.idxInLine * gapScene;
    left = Math.min(left, x - padScene - (r.hangingSpace ? L.spaceW : 0));
    right = Math.max(right, x + r.w + padScene);
  }
  const center = (left + right) / 2;
  // a letra de referência fica fixa na tela; o bloco termina centralizado na escala final
  const anchorScreenX = W / 2 - S_FINAL * (center - L.anchor.x);
  const textLeft = anchorScreenX - L.anchor.x;
  const anchorYInGlyph = 0.36 * F0; // centro óptico de "l" acima da linha de base
  const baseline = (line: number) => ANCHOR_Y + anchorYInGlyph + (line - 1) * LINE_H;
  return {
    gapScene, padScene, textLeft, baseline,
    anchor: { x: anchorScreenX, y: ANCHOR_Y },
    boxTop: (line: number) => baseline(line) - 0.86 * F0,
    boxBottom: (line: number) => baseline(line) + 0.35 * F0,
  };
};

// ---------------------------------------------------------------------------
// Digitação
// ---------------------------------------------------------------------------
const typedCount = (frame: number, fps: number) => {
  let n = TY.pretyped;
  for (const k of TY.keys) {
    if (k.kind === "dead") continue;
    if (Math.ceil(k.t * fps - 1e-6) <= frame) n++;
  }
  return n;
};

const caretPos = (L: Layout, count: number) => {
  const last = count - 1;
  if (L.wrapSpaces.includes(last)) {
    const line = L.wrapSpaces.indexOf(last);
    return { line, x: L.prefixW(line, L.lines[line].length) + L.spaceW };
  }
  let line = 0;
  for (let i = 0; i < 3; i++) if (last >= L.lineStart[i]) line = i;
  return { line, x: L.prefixW(line, last - L.lineStart[line] + 1) };
};

const caretOpacity = (t: number) => {
  const { lastKeyHoldUntil, offUntil, fadeOutStart, fadeOutEnd } = TL.caret;
  if (t >= fadeOutStart) return lerp(t, fadeOutStart, fadeOutEnd, 1, 0);
  if (t >= lastKeyHoldUntil && t < offUntil) return 0; // a única piscada, na pausa de "nem letras"
  return 1;
};

// ---------------------------------------------------------------------------
// Cena (tudo o que está "na tela" e se move com a câmera)
// ---------------------------------------------------------------------------
const Scene: React.FC<{ L: Layout; G: Geo; t: number; frame: number; fps: number }> = ({ L, G, t, frame, fps }) => {
  const s = cameraScale(t);
  const count = typedCount(frame, fps);
  const { pushStart, pushEnd } = TL.camera;
  const fieldOpacity = lerp(t, pushStart + 0.12, pushEnd - 0.1, 1, 0);
  const gp = lerp(t, TL.tokens.gapsStart, TL.tokens.gapsEnd, 0, 1);

  const fieldLeft = G.textLeft - FIELD_PAD_X;
  const fieldRight = G.textLeft + L.fieldTextW + FIELD_PAD_X;
  const fieldTop = G.baseline(0) - ASC * F0 - FIELD_PAD_TOP;
  const fieldBottom = G.baseline(2) + 0.25 * F0 + FIELD_PAD_BOTTOM;

  const caret = caretPos(L, count);
  const tokenAppear = (k: number) =>
    interpolate(t, [TL.tokens.boxesStart + k * TL.tokens.boxStagger, TL.tokens.boxesStart + k * TL.tokens.boxStagger + 0.2], [0, 1], { ...clamp, easing: easeOut });

  // caixas por fragmento (um fragmento pode ter um run só; aqui todos têm)
  const boxes = L.runs.map((r) => {
    const x = G.textLeft + r.x + r.idxInLine * G.gapScene * gp;
    const left = x - G.padScene - (r.hangingSpace ? L.spaceW : 0);
    const right = x + r.w + G.padScene;
    return { r, x, left, right, top: G.boxTop(r.line), bottom: G.boxBottom(r.line), p: tokenAppear(r.token) };
  });

  return (
    <AbsoluteFill
      style={{
        transformOrigin: `${G.anchor.x}px ${G.anchor.y}px`,
        transform: `scale(${s})`,
      }}
    >
      {/* campo de mensagem genérico (sem marca), dissolve quando a câmera entra na frase */}
      <div
        style={{
          position: "absolute",
          left: fieldLeft,
          top: fieldTop,
          width: fieldRight - fieldLeft,
          height: fieldBottom - fieldTop,
          borderRadius: 34,
          background: C.field,
          border: `2px solid ${C.fieldBorder}`,
          boxShadow: "0 30px 80px rgba(0,0,0,0.35)",
          opacity: fieldOpacity,
        }}
      >
        <div
          style={{
            position: "absolute",
            right: 30,
            bottom: 28,
            width: 76,
            height: 76,
            borderRadius: 38,
            background: "#2B3138",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <svg width="34" height="34" viewBox="0 0 24 24" fill="none">
            <path d="M12 19V5M5.5 11.5 12 5l6.5 6.5" stroke="#AEB6BF" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      {/* caixas dos fragmentos (atrás das letras) */}
      {boxes.map(({ r, left, right, top, bottom, p }) => (
        <div
          key={`box-${r.token}-${r.line}`}
          style={{
            position: "absolute",
            left,
            top,
            width: right - left,
            height: bottom - top,
            borderRadius: 0.14 * F0,
            background: `rgba(${C.cyanRGB}, ${0.11 * p})`,
            border: `${2 / 1}px solid rgba(${C.cyanRGB}, ${0.92 * p})`,
            transform: `scale(${0.93 + 0.07 * p})`,
            transformOrigin: "50% 50%",
            boxSizing: "border-box",
          }}
        />
      ))}

      {/* marcas de espaço: o espaço faz parte do fragmento seguinte */}
      {boxes
        .filter(({ r }) => r.hangingSpace || r.text.startsWith(" "))
        .map(({ r, x, p }) => {
          const sx = r.hangingSpace ? x - L.spaceW : x;
          const mw = L.spaceW * 0.7;
          return (
            <div
              key={`sp-${r.token}`}
              style={{
                position: "absolute",
                left: sx + (L.spaceW - mw) / 2,
                top: G.baseline(r.line) - 0.12 * F0,
                width: mw,
                height: 0.12 * F0,
                borderLeft: `2px solid rgba(${C.cyanRGB}, ${0.8 * p})`,
                borderRight: `2px solid rgba(${C.cyanRGB}, ${0.8 * p})`,
                borderBottom: `2px solid rgba(${C.cyanRGB}, ${0.8 * p})`,
                boxSizing: "border-box",
              }}
            />
          );
        })}

      {/* letras: cada fragmento é um run de texto corrido; só a parte já digitada aparece */}
      {boxes.map(({ r, x }) => {
        const visible = Math.max(0, Math.min(r.text.length, count - r.start));
        if (visible === 0) return null;
        return (
          <div
            key={`run-${r.token}-${r.line}`}
            style={{
              position: "absolute",
              left: x,
              top: G.baseline(r.line) - ASC * F0,
              fontFamily: FONT.screen,
              fontWeight: 500,
              fontSize: F0,
              lineHeight: `${1.2 * F0}px`,
              whiteSpace: "pre",
              color: C.ink,
              fontKerning: "normal",
            }}
          >
            {r.text.slice(0, visible)}
          </div>
        );
      })}

      {/* cursor */}
      <div
        style={{
          position: "absolute",
          left: G.textLeft + caret.x + 3,
          top: G.baseline(caret.line) - 0.8 * F0,
          width: 0.06 * F0,
          height: 0.98 * F0,
          borderRadius: 2,
          background: C.ink,
          opacity: caretOpacity(t),
        }}
      />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Vidro: reflexo suave e vinheta. Somem enquanto a câmera atravessa a superfície.
// ---------------------------------------------------------------------------
const Glass: React.FC<{ t: number }> = ({ t }) => {
  const { pushStart, pushEnd } = TL.camera;
  const reflection = lerp(t, pushStart, pushStart + 0.6, 1, 0);
  const vignette = lerp(t, pushStart, pushEnd, 1, 0.45);
  const drift = interpolate(t, [0, pushStart], [0, -24], clamp); // reflexo desliza de leve com a câmera
  return (
    <>
      <AbsoluteFill
        style={{
          opacity: reflection,
          background:
            "linear-gradient(116deg, rgba(255,255,255,0) 16%, rgba(255,255,255,0.045) 33%, rgba(255,255,255,0.012) 44%, rgba(255,255,255,0) 56%)," +
            "radial-gradient(ellipse 70% 40% at 18% 6%, rgba(190,215,235,0.07), rgba(0,0,0,0) 70%)",
          transform: `translateX(${drift}px)`,
        }}
      />
      <AbsoluteFill
        style={{
          opacity: vignette,
          background: "radial-gradient(ellipse 80% 62% at 50% 40%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)",
        }}
      />
    </>
  );
};

// granulação estática muito leve: evita faixas no gradiente depois da compressão
const Grain: React.FC = () => (
  <AbsoluteFill style={{ opacity: 0.05, mixBlendMode: "overlay" }}>
    <svg width="100%" height="100%">
      <filter id="g">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="3" stitchTiles="stitch" />
        <feColorMatrix type="saturate" values="0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#g)" />
    </svg>
  </AbsoluteFill>
);

// ---------------------------------------------------------------------------
// Legendas e título
// ---------------------------------------------------------------------------
export const Highlighted: React.FC<{ text: string; word?: string }> = ({ text, word }) => {
  if (!word || !text.includes(word)) return <>{text}</>;
  const i = text.indexOf(word);
  return (
    <>
      {text.slice(0, i)}
      <span style={{ color: C.cyan }}>{word}</span>
      {text.slice(i + word.length)}
    </>
  );
};

// Blocos colados trocam por corte seco (nunca dois textos sobrepostos no mesmo lugar);
// só há fusão quando a legenda nasce ou termina num trecho sem legenda.
export const Captions: React.FC<{ t: number }> = ({ t }) => {
  const fade = 0.1;
  const caps = TL.captions;
  return (
    <>
      {caps.map((c, i) => {
        const joinedBefore = i > 0 && Math.abs(caps[i - 1].out - c.in) < 0.001;
        const joinedAfter = i < caps.length - 1 && Math.abs(caps[i + 1].in - c.out) < 0.001;
        const start = joinedBefore || c.in === 0 ? c.in : c.in - 0.033;
        if (t < start || t >= c.out) return null;
        const fadeIn = joinedBefore || c.in === 0 ? 1 : lerp(t, c.in - 0.033, c.in + 0.067, 0, 1);
        const fadeOut = joinedAfter ? 1 : lerp(t, c.out - fade, c.out, 1, 0);
        const o = Math.min(fadeIn, fadeOut);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: (W - CAPTION_W) / 2,
              width: CAPTION_W,
              bottom: 1920 - CAPTION_BOTTOM,
              textAlign: "center",
              fontFamily: FONT.caption,
              fontWeight: 700,
              fontSize: 58,
              lineHeight: 1.2,
              color: "#F5F7F9",
              textShadow: "0 2px 14px rgba(0,0,0,0.6)",
              opacity: o,
            }}
          >
            {c.lines.map((line, j) => (
              <div key={j}>
                <Highlighted text={line} word={(c as { highlight?: string }).highlight} />
              </div>
            ))}
          </div>
        );
      })}
    </>
  );
};

export const Title: React.FC<{ t: number }> = ({ t }) => (
  <div
    style={{
      position: "absolute",
      left: (W - 900) / 2,
      width: 900,
      bottom: 1920 - CAPTION_BOTTOM - 6,
      textAlign: "center",
      fontFamily: FONT.title,
      fontWeight: 700,
      fontSize: 86,
      lineHeight: 1.1,
      letterSpacing: "-0.02em",
      color: C.ink,
    }}
  >
    {TL.title.parts.map((p, i) => {
      const fo = (TL.title as { fadeOut?: number[] }).fadeOut;
      const o = lerp(t, p.in - 0.033, p.in + 0.17, 0, 1, easeOut) * (fo ? 1 - lerp(t, fo[0], fo[1], 0, 1) : 1);
      const y = lerp(t, p.in - 0.033, p.in + 0.25, 16, 0, easeOut);
      return (
        <div key={i} style={{ opacity: o, transform: `translateY(${y}px)` }}>
          <Highlighted text={p.text} word={(p as { highlight?: string }).highlight} />
        </div>
      );
    })}
  </div>
);

const TokenLabel: React.FC<{ t: number; G: Geo }> = ({ t, G }) => {
  const o = lerp(t, TL.tokens.labelIn, TL.tokens.labelIn + 0.3, 0, 1);
  const y = G.anchor.y + S_FINAL * (G.boxBottom(2) - G.anchor.y) + 40;
  return (
    <div
      style={{
        position: "absolute",
        top: y,
        left: 0,
        width: W,
        textAlign: "center",
        fontFamily: FONT.caption,
        fontWeight: 500,
        fontSize: 36,
        letterSpacing: "0.01em",
        color: C.dim,
        opacity: o,
      }}
    >
      tokenizador {TOK.tokenizer} (OpenAI) · {TOK.count} tokens ·{" "}
      <span
        style={{
          display: "inline-block",
          width: 16,
          height: 9,
          margin: "0 6px 0 4px",
          borderLeft: `2px solid ${C.cyan}`,
          borderRight: `2px solid ${C.cyan}`,
          borderBottom: `2px solid ${C.cyan}`,
          opacity: 0.85,
        }}
      />
      espaço
    </div>
  );
};

// ---------------------------------------------------------------------------
// Som: voz original intacta; teclas; ambiente que perde presença ao entrar na tela
// ---------------------------------------------------------------------------
const Sound: React.FC = () => {
  const { fps, durationInFrames } = useVideoConfig();
  const { pushStart, pushEnd } = TL.camera;
  const sala = (f: number) => {
    const t = f / fps;
    return Math.min(lerp(t, 0, 0.12, 0, 1), lerp(t, pushStart, pushEnd, 1, 0));
  };
  const tela = (f: number) => {
    const t = f / fps;
    return Math.min(lerp(t, pushStart, pushEnd, 0, 1), lerp(f, durationInFrames - 8, durationInFrames - 1, 1, 0));
  };
  return (
    <>
      <Audio src={staticFile(TL.audio.file)} trimBefore={Math.round(TL.audio.trimBeforeSec * fps)} />
      <Audio src={staticFile("sfx/teclas.wav")} />
      <Audio src={staticFile("sfx/ambiente-sala.wav")} volume={sala} />
      <Audio src={staticFile("sfx/ambiente-tela.wav")} volume={tela} />
    </>
  );
};

// ---------------------------------------------------------------------------
export const Abertura: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ready = useFontsReady();
  const t = frame / fps;
  const L = useMemo(() => (ready ? makeLayout() : null), [ready]);
  const G = useMemo(() => (L ? makeGeo(L) : null), [L]);

  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Sound />
      {L && G ? (
        <>
          <Scene L={L} G={G} t={t} frame={frame} fps={fps} />
          <Glass t={t} />
          <Grain />
          <TokenLabel t={t} G={G} />
          <Captions t={t} />
          <Title t={t} />
        </>
      ) : null}
    </AbsoluteFill>
  );
};
