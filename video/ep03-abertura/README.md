# IA por Dentro · EP03 · abertura

## v2: reconstrução cinematográfica (Blender/Cycles + Remotion)

**Arquitetura híbrida.** `blender/cena.py` (Python + `bpy` 5.3, Cycles em CPU) renderiza toda a
imagem física e 3D. A composição `Cinema` do Remotion (`src/Cinema.tsx`) põe por cima as
legendas, o título-pergunta e os rótulos científicos, e mixa o som. Os dois leem os mesmos tempos
(`data/timeline.json`, `data/typing.json`, `data/tokens.json`), então imagem, legenda e voz não
se desencontram.

```bash
pip install bpy fonttools brotli                  # Blender como módulo Python (3.13)
python3 blender/cena.py --samples 12 --out out/frames   # 336 quadros PNG (≈ 30–40 s cada em 4 núcleos)
ln -sfn ../out/frames public/frames
npm run sfx && npx remotion render src/index.ts Cinema out/ep03-abertura-cinema.mp4
```

### O que deixava a v1 com cara de interface animada
- Tudo era plano: retângulos CSS, gradiente de "reflexo" e vinheta desenhados, nenhuma luz real.
- O zoom era uma escala 2D: sem paralaxe, profundidade de campo nem motion blur.
- Faltava um mundo físico: nem mesa, nem teclado, nem monitor, nem fonte de luz.
- As caixas dos tokens eram contornos chapados, sem volume, material ou sombra.

### Storyboard (tempos da narração)
| Plano | Tempo | Câmera / ótica | Luz | Ação |
|---|---|---|---|---|
| 1 · Mãos fora de quadro, teclado | 0–2,7 s | 35 mm, baixa, rente ao teclado, f/1.8, foco nas teclas | monitor 7200 K sobre as teclas; prática 3100 K à esquerda; corredor em bokeh | as teclas afundam no ritmo exato da digitação (ABNT2, tecla morta em ã/â) |
| 2 · Rack focus + grua | 1,2–5,9 s | sobe e avança até a tela em ângulo leve; o foco passa das teclas para o texto (f/2.8) | idem | "paciente em ventilação mecânica" surge na tela |
| 3 · Pausa | 5,9–7,08 s | parada | idem | digitação para em "nem"; o cursor pisca uma vez |
| 4 · Travessia | 7,08–8,15 s | dolly-in até o macro, de ângulo leve para frontal, f/5.6, motion blur 180° | a tela apaga; entram luz-chave rasante 5200 K, recorte azul e preenchimento, ligados só aos fragmentos (light linking) | as letras deixam de ser pixels e ganham volume |
| 5 · Tokenização | 7,82–8,55 s | quase parada | idem | 7 placas de vidro fumê emergem atrás das letras, cada uma acendendo seu filete ciano (a fronteira do token); os vãos se abrem |
| 6 · IDs | 8,42–9,2 s | desacelera | idem | o ID real de cada fragmento desce da placa por um filete |
| 7 · Pergunta | 8,94–11,2 s | desacelera até parar em 10,6 s | idem | título-legenda "Mas, afinal, o que é um token?" |

### Fidelidade científica
Os fragmentos e IDs vêm do o200k_base, verificados (ver "Tokenização"). A cena separa
texto (pixels na tela), tokens (placas) e IDs (números), e não mostra embeddings. A travessia é
metáfora, e o rótulo "ILUSTRAÇÃO" está na tela. Outro rótulo avisa que Claude, Gemini e outros
modelos usam tokenizadores próprios.

### Limitações encontradas
- **Sem GPU:** Cycles em 4 núcleos de CPU, cerca de 30–40 s por quadro em 1080 × 1920 com
  12 amostras e denoiser OIDN. O master em 2160 × 3840 levaria por volta de 4× isso (mais de
  12 h), então a entrega é em 1080 × 1920 nativo, sem upscale.
- **Sem acesso a Poly Haven, ambientCG ou bibliotecas de modelos:** não há HDRI nem texturas
  PBR escaneadas. Madeira, alumínio escovado, PBT do teclado, borracha e aço são materiais
  procedurais.
- **Sem mãos humanas:** não dá para fazê-las com qualidade fotográfica aqui. Seguindo o pedido,
  o plano usa teclado e tela, sem humano artificial.
- **Subpixels:** a máscara RGB de subpixels existe, mas só acende quando cada pixel da tela ocupa
  9 pixels ou mais do vídeo, para evitar moiré. Neste trajeto ela quase não aparece.
- **Sem volumetria:** neblina e luz volumétrica foram descartadas pelo custo em CPU.

## v1: prova de edição da abertura (2D)

Composição em [Remotion](https://www.remotion.dev/) da abertura de **"Afinal, o que é um token?"**.
O trecho vai da primeira palavra da narração até logo depois de "Mas, afinal, o que é um token?":
**11,2 s, 336 quadros, 1080 × 1920, 30 fps, H.264 + AAC 320 kbps.**

> **Sem clipe de vídeo na pasta.** A pasta tinha só o roteiro e o MP3. Por isso esta versão segue
> a alternativa combinada: abre direto na frase e no cursor, em tela cheia. A passagem
> "mesa real → dentro da frase" ainda **não foi testada com imagem filmada**. Veja
> [Quando houver o clipe](#quando-houver-o-clipe-da-mão-e-do-monitor).

## Como rodar

```bash
npm install
# coloque a narração original em public/audio/narracao.mp3 (fica fora do git)
npm run audio     # cópia dual-mono, ganho 1,0 (ver "Voz")
npm run sfx       # sintetiza teclas e ambiente em public/sfx/
npm run studio    # edição/preview
npm run render    # out/ep03-abertura.mp4
npm run srt       # out/ep03-abertura.srt e legendas/ep03-abertura.srt
npm run revisar   # checagens automáticas do MP4 (Python: Pillow, numpy, soundfile)
```

Se o Remotion não encontrar um Chrome, passe `--browser-executable=<caminho do chrome-headless-shell>`.

## Onde editar

| O quê | Arquivo |
|---|---|
| Tempos medidos, legendas, título, câmera, fragmentos | `data/timeline.json` |
| Cronograma das teclas (gerado, editável) | `data/typing.json` ← `scripts/build-typing.mjs` |
| Fragmentos do tokenizador + conferência | `data/tokens.json` ← `scripts/tokenize.mjs` |
| Layout da frase (quebra de linha, letra de referência) | `src/layout.ts` |
| Cena, câmera, legendas, título, mixagem | `src/Abertura.tsx` |
| Cores e fontes | `src/theme.ts`, `public/fonts/` (OFL) |

## Montagem guiada pela voz

Tempos medidos na gravação com envelope RMS de 5 ms, conferidos com dois reconhecedores
(Parakeet TDT v3 e Whisper turbo, ambos via sherpa-onnx, rodando localmente).

| Momento na fala | Tempo | Quadro | Ação |
|---|---|---|---|
| "Quando…" (1ª palavra) | 0,075 s | 2 | Abre em movimento: "pa" já digitado, cursor avançando |
| última tecla ("a" de "mecânica") | 6,08 s | 183 | A digitação termina |
| "nem letras" | 6,12 s | 184 | Nenhuma tecla depois disso; o cursor pisca uma vez na pausa (6,63–6,97 s) |
| pausa real | 6,87–7,17 s | 206–215 | Quadro parado |
| "Eles leem tokens" | 7,17 s | 215 | Aproximação (início suave em 7,10 s) até 8,05 s; o campo de texto dissolve e as bordas saem pelos lados |
| "tokens" | 7,82 s | 235 | As caixas dos fragmentos entram na ordem de leitura; os vãos abrem até 8,55 s |
| "Mas, afinal," | 8,94 s | 269 | Título-legenda, linha 1 (imagem já estável) |
| "o que é um token?" | 9,745 s | 293 | Título-legenda, linha 2 |
| fim da pergunta | 10,79 s | 324 | — |
| corte | 11,20 s | 336 | A frase seguinte ("No episódio 1…") começa em 11,278 s |

**Letra de referência da travessia:** o **"l" de "ventilação"** (último caractere do fragmento
" ventil"). Ela é o ponto fixo da escala da câmera e não se move quando os vãos abrem.
No MP4, o centro do traço fica entre x = 472,0 e 472,5 px do quadro 100 (quando é digitado)
ao 335, enquanto o traço engrossa de 9 para 15 px.

## Tokenização (conferida)

- Tokenizador: **o200k_base** (OpenAI), via `js-tiktoken@1.0.21`. A biblioteca associa esse
  encoding ao GPT-4o, GPT-4.1, o1 e GPT-5 (`getEncodingNameForModel`).
- `"paciente em ventilação mecânica"` → **7 tokens**:
  `pac` · `iente` · `␣em` · `␣ventil` · `ação` · `␣mec` · `ânica`
  (IDs 77915, 5707, 863, 46936, 3890, 52737, 104028).
- Reunidos, os fragmentos reproduzem o texto byte a byte, com espaços e acentos; nenhum
  fragmento corta um caractere acentuado ao meio (`checks` em `data/tokens.json`).
- Conferência independente com `gpt-tokenizer@3.4.0`: mesmos IDs.
- Claude e Gemini usam tokenizadores próprios. A divisão deles pode ser outra, por isso o rótulo
  na tela nomeia o tokenizador.
- O espaço pertence ao fragmento seguinte. Na tela ele aparece como a marca ⎵ dentro da caixa;
  no início de linha, a marca fica pendurada à esquerda.

## Legendas

Figtree 700, 58 px, até duas linhas, coluna central de 820 px (x 130–950) com a base em
y = 1430. Assim ficam acima da interface inferior do Reels e longe dos botões da direita.
As margens de segurança do Reels são aproximadas: confira num celular antes de publicar.
Blocos colados trocam por corte seco, nunca dois textos sobrepostos. A pergunta final aparece
uma vez só, como título no lugar da legenda (Space Grotesk 700, 86 px). O destaque em ciano é
um por bloco ("tokens", "token").

## Som

- **Voz:** o MP3 original não sofre nenhum processamento. O FFmpeg (usado pelo Remotion) converte
  mono em estéreo a −3 dB por canal. Para evitar isso, `npm run audio` só copia o canal mono
  nos dois lados, com ganho 1,0. No MP4: atraso 0 ms, ganho −0,02 dB, pico −3,5 dBFS (original:
  −3,6), −17,8 LUFS integrado.
- **Teclas:** sintetizadas, uma por evento de `data/typing.json`, com o teclado ABNT2: "ã" e "â"
  têm o clique da tecla morta antes da letra. Ficam discretas: pico de cerca de −25 dBFS, uns 22 dB abaixo do pico da voz.
- **Ambiente:** tom de sala de plantão (ar-condicionado e dois monitores distantes, atrás de uma
  parede), também sintetizado. Na aproximação (7,10–8,05 s) ele cruza para uma versão abafada.
  Acima de 500 Hz, a faixa que um alto-falante de celular reproduz, o ambiente cai cerca de 30 dB.
- Sem vinheta, sem trilha, sem efeito na revelação dos fragmentos.

## Revisão quadro a quadro (MP4 final)

1. **Inserção do texto:** a quebra de linha é a de uma caixa de texto real. A largura do campo
   foi calculada para quebrar em "paciente em / ventilação / mecânica", então nenhuma palavra
   salta de linha durante a digitação. O cursor fica depois do espaço no fim da linha, e "ç", "ã"
   e "â" aparecem corretos.
2. **Travessia:** a letra de referência fica no mesmo pixel (desvio ≤ 0,5 px). A variação entre
   quadros cresce e cai de forma contínua (pico no quadro 222), sem saltos isolados. O texto
   continua nítido no meio do movimento, porque é rasterizado de novo a cada quadro.
3. **Entrada de "tokens":** a primeira caixa surge no quadro 235 (7,83 s), com a palavra começando
   em 7,82 s. A última termina em 8,53 s. Não há texto duplicado.

Na área de legenda, as trocas caem nos quadros 69, 123, 184 e 215 (cortes secos no início das
falas). A fusão de saída vai de 255 a 256 e o título entra em 268–272 e 292–296.

## Para ouvir antes de aprovar

- **"Eles leem tokens" (7,17–8,40 s):** o Whisper transcreveu "leem" e o Parakeet, "lê". O
  final nasal é fraco (7,66–7,81 s, cerca de −45 dBFS). A legenda segue "leem", que é o que o
  roteiro pede e o que o envelope sugere. Vale escutar esse trecho.
- Nenhuma imprecisão científica relevante nessa abertura. "Nenhum deles lê palavras, nem letras"
  é uma simplificação aceitável: um token pode coincidir com uma palavra inteira (aqui, "␣em"),
  e o próprio vídeo mostra isso.

## Quando houver o clipe da mão e do monitor

Ainda não foi implementado nem testado. O que a composição precisaria:

**Clipe (filmagem ou geração externa)**: 9:16, de preferência 2160 × 3840, 30 fps, **9 s**.
- *Enquadramento:* plano fechado em ângulo leve (cerca de 15–20° na lateral, um pouco de cima).
  Dedos e teclado no terço inferior, a tela no terço médio-superior. **Os quatro cantos da área
  de tela ficam visíveis o tempo todo**, para o corner-pin.
- *Tela:* grafite uniforme (#1D2126), **sem nenhum texto**, porque o texto entra na edição.
  Sem reflexos fortes cruzando a área onde as letras vão ficar.
- *Ação:* digitação contínua de 0 a 6,1 s. Depois, a mão repousa e fica parada até o fim.
- *Câmera:* dolly-in lento e constante, sem tremor nem rotação.
- *Luz:* noite. A luz fria do monitor ilumina os dedos e a mesa, com sombra visível sob a mão.
  Ao fundo, ambiente hospitalar fora de foco (bokeh quente), sem pessoas identificáveis e sem logos.
- *Quadro inicial:* dedos em movimento sobre as teclas, tela inteira visível.
- *Quadro final:* mão parada, câmera mais próxima, os quatro cantos da tela ainda no quadro.

**Integração:**
1. Rastrear os quatro cantos da tela por quadro (Mocha, After Effects ou Blender) e exportar JSON.
2. Renderizar a mesma `Scene` dentro de uma homografia (`matrix3d`) presa a esses cantos.
3. Em "Eles", interpolar o quadrilátero rastreado até a tela frontal, mantendo o "l" fixo,
   e tirar o clipe quando a borda sair do quadro.
4. Alternativa, se a inserção não ficar boa: plano da mão até uma tecla, corte seco no som dessa
   tecla para o detalhe frontal (esta composição).

## Arquivos fora do git

`public/audio/` (narração por clone de voz), `public/sfx/` (recriado por `npm run sfx`) e `out/`
(MP4, SRT, quadros) não vão para o repositório, que é público.
