// Tokeniza a frase da abertura com o encoding o200k_base (OpenAI), usando js-tiktoken,
// e confere se a junção dos fragmentos reconstrói o texto original byte a byte.
import { writeFileSync } from "node:fs";
import { Tiktoken } from "js-tiktoken/lite";
import o200k_base from "js-tiktoken/ranks/o200k_base";
import { readFileSync } from "node:fs";
const pkg = JSON.parse(readFileSync(new URL("../node_modules/js-tiktoken/package.json", import.meta.url), "utf8"));

const TEXT = "paciente em ventilação mecânica";
const enc = new Tiktoken(o200k_base);
const ids = enc.encode(TEXT);
const dec = new TextDecoder("utf-8", { fatal: true });

// Decodifica cada id isoladamente; se algum fragmento não for UTF-8 válido sozinho
// (byte parcial de caractere acentuado), o decoder "fatal" acusa.
const pieces = ids.map((id) => {
  const text = enc.decode([id]);
  return { id, text };
});
const joined = pieces.map((p) => p.text).join("");
const bytesOk = Buffer.from(joined, "utf8").equals(Buffer.from(TEXT, "utf8"));
const roundTrip = enc.decode(ids) === TEXT;
// Checagem extra: cada fragmento sozinho é UTF-8 completo (nenhum acento partido ao meio).
const allWhole = pieces.every((p) => !p.text.includes("�"));

const out = {
  text: TEXT,
  tokenizer: "o200k_base",
  library: `js-tiktoken@${pkg.version}`,
  note: "Encoding o200k_base da OpenAI (o tiktoken o associa ao GPT-4o). Claude e Gemini usam tokenizadores próprios; a divisão deles pode ser diferente.",
  count: ids.length,
  pieces,
  checks: { joinedEqualsText: bytesOk, decodeRoundTrip: roundTrip, noBrokenCharacters: allWhole },
};
writeFileSync(new URL("../data/tokens.json", import.meta.url), JSON.stringify(out, null, 2) + "\n");
console.log(JSON.stringify(out, null, 2));
if (!bytesOk || !roundTrip || !allWhole) { console.error("FALHA NA CONFERÊNCIA"); process.exit(1); }
