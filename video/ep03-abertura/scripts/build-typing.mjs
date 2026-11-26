// Gera o cronograma de digitação (data/typing.json) de forma determinística.
// Teclado ABNT2: "ç" tem tecla própria; "ã" = tecla morta "~" + "a"; "â" = Shift + "~" (tecla morta) + "a".
// A última letra cai antes de "nem" (6,12 s), para que a parada da digitação coincida com a palavra.
import { readFileSync, writeFileSync } from "node:fs";
const TL = JSON.parse(readFileSync(new URL("../data/timeline.json", import.meta.url), "utf8"));
const TEXT = "paciente em ventilação mecânica";
const PRETYPED = 2;          // "pa" já está na tela no quadro 0: a abertura começa em movimento
const FIRST_KEY = 0.12;      // primeira tecla audível
const LAST_KEY = 6.08;       // última letra (quadro 182/183), antes de "nem" em 6,12 s

let seed = 20261126;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 2 ** 32);
const DEAD = { "ã": "~", "â": "^" };

const chars = [...TEXT];
const weights = [];
for (let i = PRETYPED; i < chars.length; i++) {
  const c = chars[i], prev = chars[i - 1];
  let w = 0.13 + rnd() * 0.06;                 // dentro da palavra
  if (c === " ") w = 0.16 + rnd() * 0.05;      // barra de espaço
  if (prev === " ") w = 0.24 + rnd() * 0.08;   // início de palavra nova
  if (DEAD[c]) w += 0.10;                      // tempo da tecla morta
  if (i === 12) w += 0.10;                     // pequena hesitação antes de "ventilação"
  weights.push(w);
}
const total = weights.reduce((a, b) => a + b, 0) - weights[0];
const span = LAST_KEY - FIRST_KEY;
let t = FIRST_KEY;
const keys = [];
for (let k = 0; k < weights.length; k++) {
  if (k > 0) t += (weights[k] / total) * span;
  const i = PRETYPED + k, c = chars[i];
  if (DEAD[c]) keys.push({ t: +(t - 0.11).toFixed(3), kind: "dead", key: DEAD[c], charIndex: null });
  keys.push({ t: +t.toFixed(3), kind: c === " " ? "space" : "char", key: c, charIndex: i });
}
const out = { text: TEXT, pretyped: PRETYPED, fps: TL.fps, keys };
writeFileSync(new URL("../data/typing.json", import.meta.url), JSON.stringify(out, null, 1) + "\n");
console.log(keys.map((k) => `${k.t.toFixed(3)} f${Math.round(k.t * 30)} ${k.kind} ${JSON.stringify(k.key)}`).join("\n"));
