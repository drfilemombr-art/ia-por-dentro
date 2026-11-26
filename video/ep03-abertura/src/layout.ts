// Layout da frase digitada, calculado com as métricas reais da fonte (canvas.measureText).
//
// Modo editor: o campo tem largura tal que a quebra automática de linha cai em
// "paciente em / ventilação / mecânica" (o espaço da quebra fica pendurado no fim da linha,
// como em qualquer caixa de texto). Assim nenhuma palavra salta de linha durante a digitação.
//
// Modo tokens: as mesmas letras, nos mesmos lugares, recebem caixas por fragmento
// (saída real do o200k_base). Os espaços pertencem ao fragmento seguinte; nos inícios
// de linha o espaço aparece pendurado à esquerda, dentro da caixa do fragmento.
import tokensData from "../data/tokens.json";
import { FONT } from "./theme";

export const F0 = 97;               // corpo do texto no plano da tela (px de cena)
export const LINE_H = 1.32 * F0;    // entrelinha folgada: as caixas de fragmento não se tocam
export const ASC = 0.95;            // métricas verticais da Figtree (fontBoundingBox, em em)
export const DESC = 0.25;

export type Run = {
  token: number;        // índice do fragmento
  line: number;         // 0, 1, 2
  text: string;         // texto visível nesta linha (pode começar com espaço, ex. " em")
  start: number;        // índice do primeiro caractere de `text` na frase
  x: number;            // posição no modo editor (relativa à margem esquerda do texto)
  w: number;            // largura do run
  idxInLine: number;    // ordem do fragmento dentro da linha (para abrir os vãos)
  hangingSpace: boolean; // o fragmento começa com o espaço que, no editor, ficou no fim da linha anterior
};

export type Layout = {
  text: string;
  lines: string[];
  lineStart: number[];   // índice do 1º caractere de cada linha na frase
  wrapSpaces: number[];  // índices dos espaços de quebra
  fieldTextW: number;    // largura útil do campo (garante a quebra natural)
  runs: Run[];
  spaceW: number;
  prefixW: (line: number, chars: number) => number; // largura dos `chars` primeiros caracteres da linha
  anchor: { line: number; x: number; char: string; index: number }; // letra de referência
};

export const makeLayout = (): Layout => {
  const ctx = document.createElement("canvas").getContext("2d")!;
  ctx.font = `500 ${F0}px "${FONT.screen}"`;
  const m = (s: string) => ctx.measureText(s).width;

  const text: string = tokensData.text;
  const lines = ["paciente em", "ventilação", "mecânica"];
  const lineStart = [0, 12, 23];
  const wrapSpaces = [11, 22];
  if (lines.join(" ") !== text) throw new Error("linhas não reconstroem a frase");

  // Faixa de largura em que o navegador quebraria exatamente nesses pontos:
  // cabe "paciente em", não cabe "paciente em v"; cabe "ventilação", não cabe "ventilação m".
  const minW = Math.max(m(lines[0]), m(lines[1]), m(lines[2]));
  const maxW = Math.min(m("paciente em v"), m("ventilação m"));
  if (!(minW < maxW)) throw new Error("quebra natural impossível neste corpo de fonte");
  const fieldTextW = (minW + maxW) / 2;

  const runs: Run[] = [];
  let pos = 0;
  tokensData.pieces.forEach((p: { text: string }, token: number) => {
    const t0 = pos, t1 = pos + p.text.length;
    pos = t1;
    for (let line = 0; line < 3; line++) {
      const ls = lineStart[line], le = ls + lines[line].length;
      let a = Math.max(t0, ls), b = Math.min(t1, le);
      if (a >= b) continue;
      const hangingSpace = wrapSpaces.includes(t0) && a === ls && t0 === ls - 1;
      const runText = text.slice(a, b);
      const lineText = lines[line];
      const endInLine = b - ls;
      const w = m(runText);
      const x = m(lineText.slice(0, endInLine)) - w; // respeita o kerning do texto corrido
      runs.push({ token, line, text: runText, start: a, x, w, idxInLine: 0, hangingSpace });
    }
  });
  for (let line = 0; line < 3; line++) {
    runs.filter((r) => r.line === line).forEach((r, i) => (r.idxInLine = i));
  }

  // Checagem: os runs + espaços de quebra reconstroem a frase, caractere por caractere.
  const rebuilt = [...text].map(() => "");
  runs.forEach((r) => [...r.text].forEach((c, i) => (rebuilt[r.start + i] = c)));
  wrapSpaces.forEach((i) => (rebuilt[i] = " "));
  if (rebuilt.join("") !== text) throw new Error("runs não reconstroem a frase");

  const prefixW = (line: number, chars: number) => m(lines[line].slice(0, chars));

  // Letra de referência da travessia: o "l" de "ventilação" (último caractere do fragmento " ventil").
  // Ela é o ponto fixo da aproximação e não se move quando os vãos entre fragmentos se abrem.
  const anchorIndex = text.indexOf("ventil") + 5;
  const aLine = 1, inLine = anchorIndex - lineStart[1];
  const anchorX = prefixW(1, inLine) + m(text[anchorIndex]) / 2;

  return {
    text, lines, lineStart, wrapSpaces, fieldTextW, runs,
    spaceW: m(" "), prefixW,
    anchor: { line: aLine, x: anchorX, char: text[anchorIndex], index: anchorIndex },
  };
};
