# EP03 · mapa da narração gravada × caderno de direção

Gravação: `narracao.mp3` (ElevenLabs, 2:41,96). Transcrição com Parakeet TDT v3 e Whisper turbo
(sherpa-onnx). Bordas de fala medidas com envelope de 10 ms. Os tempos de início vêm do
reconhecedor, que costuma adiantar 0,1–0,2 s, e precisam ser refinados por bloco antes da montagem.

**A voz gravada segue o roteiro original de Filemom, não as falas sugeridas pelo caderno.** Pela
regra do caderno, a montagem usa a voz gravada e as diferenças ficam sinalizadas abaixo.
Qualquer regravação depende da sua aprovação.

| Bloco | Entrada → saída (s) | O que foi dito (resumo) |
|---|---|---|
| Abertura | 0,00 → 11,20 | "Quando você escreve… Mas, afinal, o que é um token?" |
| 1 · Das palavras aos números | 11,20 → 19,37 | "No episódio 1, vimos que a IA faz contas com números, mas você escreve palavras. Quem faz essa tradução é o **token**." |
| 2 · O olhar do médico | 19,37 → ≈ 39,1 | "Pense em como a gente lê termos médicos. Taquicardia… Antes de tudo, um programa chamado tokenizador **corta o texto em pedaços que aparecem muito**. Esses pedaços são os tokens." |
| 3 · Uma frase em português | ≈ 39,1 → ≈ 56,5 | "Veja a frase… Palavras comuns costumam virar um token só. **Palavras longas ou raras viram dois ou três pedaços.** … uns quatro caracteres." |
| 4 · O idioma muda a conta | ≈ 56,5 → ≈ 75,9 | "Outras línguas costumam gastar mais. Um estudo de Oxford mostrou que o tokenizador do ChatGPT usava cerca de **uma vez e meia** mais tokens… em italiano… E cada empresa tem o seu tokenizador…" |
| 5 · Do token ao vetor | ≈ 75,9 → ≈ 88,6 | "Depois, cada token vira um número, a sua posição num dicionário. E esse número **vira** uma lista com milhares de outros números, que **carrega o significado**. Tokens de sentido parecido ficam perto uns dos outros." |
| 6 · Como a frase avança | ≈ 88,6 → ≈ 103,0 | igual ao caderno |
| 7 · Quanto cabe de uma vez | ≈ 103,0 → ≈ 123,3 | "…Quantos tokens o modelo enxerga de uma vez? **Hoje**, Claude, ChatGPT e Gemini têm modelos que chegam a cerca de um milhão… uns oito romances. **O que passa do limite, o modelo não vê.**" |
| 8 · Custo e letras | ≈ 123,3 → ≈ 141,0 | "**Preço e energia são contados por token**, e os modelos que raciocinam… gastam tokens que você nem vê. … contar as letras de uma palavra pode ser difícil para ela." |
| 9 · A sigla no plantão | ≈ 141,0 → ≈ 155,1 | "…A sigla IC… **O token é o mesmo**, e quem decide o sentido é o contexto. Escreva de forma clara e completa." |
| 10 · O posto | ≈ 155,1 → 161,96 | "No próximo episódio, como a IA escolhe a próxima palavra? Siga o perfil e salve para rever depois." |

## Imprecisões a corrigir (sugestões curtas de regravação)

1. **Bloco 1:** "Quem faz essa tradução é o token." Quem traduz é o **tokenizador**; o token é o
   resultado. → *"Quem faz essa tradução é o tokenizador."*
2. **Bloco 4:** "uma vez e meia… tokenizador do ChatGPT". O caderno diz ≈ 1,6×. **Não consegui
   verificar o número** (openreview.net bloqueado aqui). Antes de exibir qualquer número, confira
   na tabela de Petrov et al. (2023) qual tokenizador e qual valor valem para o italiano. → *"…um
   estudo de Oxford encontrou, no tokenizador avaliado, cerca de [valor conferido] vez a
   quantidade de tokens em italiano…"*
3. **Bloco 5:** "esse número vira uma lista… que carrega o significado". O ID **seleciona** uma
   linha da tabela de embeddings; o vetor não "carrega o significado" sozinho, as relações são
   aprendidas. → *"Esse número aponta para uma lista de valores, chamada vetor. Nessa
   representação, o modelo aprende relações entre os tokens."*
4. **Bloco 7:** "Hoje… cerca de um milhão" é um dado que envelhece. Confira os modelos vigentes
   na data de publicação. "O que passa do limite, o modelo não vê" pode sugerir que o app apaga o
   começo da conversa; o caderno pede cuidado com isso. → *"O modelo só recebe o que entra no
   contexto daquela resposta."*
5. **Bloco 8:** "Preço e energia são contados por token". As APIs cobram por token, mas energia
   não é contada nem cobrada por token. → *"Em muitas APIs, você paga pelos tokens de entrada e
   de saída…"*
6. **Bloco 9:** "O token é o mesmo". Isso depende do tokenizador e do que vem antes (espaço,
   pontuação). O ponto clínico é que a **escrita** é a mesma. → *"A escrita é a mesma. O sentido
   depende do contexto."*

Até a decisão sobre regravar, as legendas reproduzem o que foi dito.
