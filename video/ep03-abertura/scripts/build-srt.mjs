// Gera o SRT a partir de data/timeline.json (mesmos tempos das legendas queimadas).
// A pergunta final entra como um bloco único: no vídeo ela é título e legenda ao mesmo tempo.
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
const TL = JSON.parse(readFileSync(new URL("../data/timeline.json", import.meta.url), "utf8"));
const ts = (s) => {
  const ms = Math.round(s * 1000);
  const p = (n, w = 2) => String(n).padStart(w, "0");
  return `${p(Math.floor(ms / 3600000))}:${p(Math.floor(ms / 60000) % 60)}:${p(Math.floor(ms / 1000) % 60)},${p(ms % 1000, 3)}`;
};
const blocks = TL.captions.map((c) => ({ in: c.in, out: c.out, text: c.lines.join("\n") }));
blocks.push({ in: TL.title.parts[0].in, out: TL.title.out, text: TL.title.parts.map((p) => p.text).join("\n") });
const srt = blocks.map((b, i) => `${i + 1}\n${ts(b.in)} --> ${ts(b.out)}\n${b.text}\n`).join("\n");
mkdirSync(new URL("../out/", import.meta.url), { recursive: true });
writeFileSync(new URL("../out/ep03-abertura.srt", import.meta.url), srt);
writeFileSync(new URL("../legendas/ep03-abertura.srt", import.meta.url), srt);
process.stdout.write(srt);
