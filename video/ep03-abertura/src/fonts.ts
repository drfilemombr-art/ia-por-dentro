import { useEffect, useState } from "react";
import { continueRender, delayRender, staticFile } from "remotion";

// Fontes locais (pasta public/fonts, licença OFL) para que cada acento seja renderizado
// com a mesma fonte em qualquer máquina, sem depender de rede.
const FACES: Array<[string, string, string]> = [
  ["Figtree", "fonts/figtree-latin-500-normal.woff2", "500"],
  ["Figtree", "fonts/figtree-latin-600-normal.woff2", "600"],
  ["Figtree", "fonts/figtree-latin-700-normal.woff2", "700"],
  ["Space Grotesk", "fonts/space-grotesk-latin-700-normal.woff2", "700"],
];

let loaded: Promise<void> | null = null;
const loadAll = () => {
  if (!loaded) {
    loaded = Promise.all(
      FACES.map(async ([family, file, weight]) => {
        const face = new FontFace(family, `url(${staticFile(file)}) format("woff2")`, { weight });
        await face.load();
        (document.fonts as unknown as { add: (f: FontFace) => void }).add(face);
      }),
    ).then(() => undefined);
  }
  return loaded;
};

export const useFontsReady = () => {
  const [ready, setReady] = useState(false);
  const [handle] = useState(() => delayRender("Carregando fontes"));
  useEffect(() => {
    loadAll()
      .then(() => {
        setReady(true);
        continueRender(handle);
      })
      .catch((err) => {
        console.error(err);
      });
  }, [handle]);
  return ready;
};
