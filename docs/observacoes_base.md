# Considerações sobre a base — o que o diagnóstico revelou

Escrito depois de rodar `notebooks/00_diagnostico.ipynb` e
`notebooks/01_cobertura_amostral.ipynb` sobre os 16 arquivos da ANP
(2019-01 a 2026-01) e o recorte AL + gasolina (`precos_al.parquet`,
30.091 linhas, 2019-01-02 a 2026-08-26, 5 municípios).

---

## O que está sólido

- **Esquema estável.** As 16 colunas são idênticas nos 16 arquivos, do mais
  antigo ao mais recente. A armadilha de "nomes de coluna que mudam de ano para
  ano" não apareceu em 2019+; o `normalizar_nome` + `RENOMEAR` do `load.py`
  cobre o que precisa (7 colunas renomeadas de fato, 4 sem mapa).
- **Preços plausíveis.** Nenhuma das 30.091 linhas foi rejeitada pela validação.
  `valor_venda` vai de R$ 3,50 (2020) a R$ 8,59 (2022); a média sobe de forma
  coerente com a inflação de combustível (4,58 → 6,78 de 2019 a 2026). Sem
  outlier absurdo.
- **Passo semanal limpo.** Mediana de 7 dias exatos entre semanas de referência.
- **Latência pequena (1 medição).** A coleta mais recente na base em 2026-09-03
  é de 2026-08-26 → dado mais novo com 8 dias. Medido contra o dia do download,
  logo é um teto (≤ 8 dias). Não confirmei se é estável; a premissa do CLAUDE.md
  é "~1 a 2 semanas".

## Riscos e limitações — em ordem de gravidade

### 1. A amostra do interior é fina e intermitente (o problema principal)

Só existem 5 municípios: Maceió e mais quatro do interior (Arapiraca, Delmiro
Gouveia, Palmeira dos Índios, Rio Largo).

| Município | postos/semana (mediana) | semanas presentes (de 387) |
|---|---|---|
| Maceió | 19 | 385 — quase contínuo |
| Arapiraca | 14 | 371 |
| Delmiro Gouveia | 7 | 314 |
| Rio Largo | 7 | 285 |
| Palmeira dos Índios | 8 | 238 |

- **Palmeira dos Índios e Rio Largo ficam fora da amostra o ano de 2021 inteiro**
  (64 e 53 semanas seguidas sem nenhum posto). Delmiro Gouveia, metade de 2021.
- Semanas com **1 ou 2 postos** existem no interior — média simples nessas
  semanas não significa nada.
- Só **Maceió** pode ser tratado como série contínua e confiável no período todo.

### 2. Quebra de amostragem em 2023

A ANP reconfigurou a pesquisa: Maceió **cai de ~24 para ~19 postos/semana** e
Arapiraca **sobe de 13 para 15**, os dois no início de 2023. Isso é uma quebra
estrutural na contagem de postos — e possivelmente na média de preço, se os
postos que saíram de Maceió não eram um recorte aleatório. **Checar se a série
de preço médio de Maceió tem degrau em 2023 antes de usar 2019–2022 como treino.**

### 3. `valor_compra` acaba em 17/08/2020

92,81% nulo, com corte exato em 2020-08-17 — é ausência estrutural, não dado
faltante. Qualquer análise de margem de distribuição ou de repasse
distribuidora→bomba só vale até meados de 2020. Não imputar.

### 4. `bandeira` mistura épocas da mesma empresa

13 valores, com três pares/trios que são a mesma companhia em momentos
diferentes:

- **VIBRA (6.569) = VIBRA ENERGIA (3.530) = PETROBRAS DISTRIBUIDORA S.A. (2.381)**
- **ALE (114) = ALESAT (403)**

Sem um de-para, a série por bandeira e o teste da H2 (branca × bandeirada) saem
enviesados — a mesma empresa aparece como três concorrentes. O de-para é
obrigatório e pequeno (~3 renomeações). `BRANCA` (8.704 linhas, 29%) é a maior
categoria e é posto sem bandeira — boa base para a H2.

### 5. Gasolina comum e aditivada estão juntas no recorte

O filtro pega `GASOLINA` e `GASOLINA ADITIVADA`. A aditivada é mais cara na média
(R$ 6,28 × R$ 5,74 na comum). Se um posto reporta só uma das duas numa semana, a
"média do posto" oscila conforme o produto, não conforme o preço. **Decidir**:
modelar só comum, ou modelar as duas separadas.

### 6. Julho/2026 está vazio — costura entre dois arquivos

`ca-2026-01.zip` cobre jan–30/jun/2026; `ultimas-4-semanas-gasolina-etanol.csv`
cobre 03–26/ago/2026. **Julho inteiro fica de fora** — o semestre 2026-02 ainda
não foi publicado e o arquivo de "últimas semanas" só guarda 4 semanas. Esse
buraco deve fechar sozinho quando `ca-2026-02.zip` sair. As 4 últimas semanas da
série (agosto) vêm logo depois de um vazio de um mês — cuidado ao montar os lags.

(Verificado: **não há duplicação** entre os dois arquivos — 0 linhas repetidas
por (cnpj, produto, data_coleta), as datas não se sobrepõem.)

### 7. Download instável — resolvido

O servidor da ANP derrubou a conexão várias vezes no meio de arquivos grandes
(`ChunkedEncodingError` / `IncompleteRead`). O `src/download.py` ganhou retry
(4 tentativas, espera crescente), escrita num `.part` que só é renomeado quando
o arquivo vem inteiro (confere o `Content-Length`), e trata 404 como "semestre
ainda não publicado". Rodar de novo retoma de onde parou.

## Decisões que o diagnóstico força

- **Alvo mais defensável:** preço médio semanal de **Maceió** (série densa e
  contínua). É o maior município da amostra — **43,5% das 30.091 linhas** — e o
  único sem buracos longos.
- **Interior:** modelar de 2022/2023 em diante, ou assumir baixa confiança em
  2019–2021.
- **Agregação por município-semana:** usar mediana ou exigir um número mínimo de
  postos na semana; nunca média simples.
- **Baseline de persistência honesto:** pela latência medida (~1 semana, ver
  acima), ao prever a semana N o dado mais recente disponível é o da semana
  N-1 ou N-2 já publicada, não o "de agora". O baseline é "preço = última
  semana publicada".
- **Split temporal sempre** (já no CLAUDE.md) — e as estatísticas de
  normalização só sobre o treino.

## Ainda não verificado

- Qual arquivo exige encoding latin-1 (o `load.py` tem o fallback, mas não
  confirmei que ele dispara).
- Se algum posto troca de CNPJ mantendo o local (inflaria a contagem de
  entradas/saídas de postos).
- Se a média de preço de Maceió tem degrau em 2023 junto com o corte de amostra.
- Teste da H1 (assimetria Maceió × interior) e da H2 (branca mais barata).
- Métrica-alvo do modelo (erro máximo aceitável) — ainda não definida.
