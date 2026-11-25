# Canvas de catalogação de dados — Preço da gasolina em AL

Fonte dos números: `notebooks/00_diagnostico.ipynb` (executado em 2026-09-03),
sobre `data/raw/` e `data/processed/precos_al.parquet`. Cada afirmação abaixo
traz o número que a sustenta; onde não há evidência, está escrito
"não verificado".

---

## 1. Fonte & Identidade

- **Origem:** ANP — Série Histórica de Preços de Combustíveis (dados abertos).
  `https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis`
- **Coleta:** pesquisa de campo **amostral** — nem todo posto é visitado toda
  semana. Mediana de postos/semana: Maceió 19, Arapiraca 14, Palmeira dos Índios 8,
  Delmiro Gouveia 7, Rio Largo 7 (notebook 01).
- **Arquivos na base:** 16 em `data/raw/` (semestrais de 2019-01 a 2026-01;
  2026-02 ainda não publicado — HTTP 404).
- **Recorte do projeto:** UF = AL, produto começando com "GASOLINA"
  (comum + aditivada) → **30.091 linhas**, **5 municípios** (ARAPIRACA,
  DELMIRO GOUVEIA, MACEIO, PALMEIRA DOS INDIOS, RIO LARGO; saída do `load.py`).
- **Licença/uso:** dados abertos; obrigação de citar a fonte (CLAUDE.md).

## 2. Natureza & Formato

- **Formato muda em 2022:** `.csv` solto até 2021-02, `.zip` de 2022-02 em
  diante; 2022-01 vem como `precos-semestrais-ca.zip` (nome fora do padrão).
  Confirmado na listagem de `data/raw/`.
- **Parsing:** separador `;`, decimal `,` (30.091 valores de venda convertidos
  para float sem erro). Encoding lido com fallback utf-8 → latin-1 no `load.py`;
  qual arquivo exige latin-1: **não verificado**.
- **Esquema:** 16 colunas, **idênticas** no arquivo antigo (`ca-2019-01.csv`) e
  no recente (`ca-2026-01.zip`) — 0 colunas com nome divergente entre eles.
- **Tipos (parquet, 18 colunas após `load.py`):** 14 texto, 2 data
  (`data_coleta`, `semana`), 2 float (`valor_venda`, `valor_compra`).
  No arquivo bruto da ANP todas as 16 vêm como texto.
- **Grão:** 1 linha = 1 preço de 1 produto em 1 posto numa data de coleta.
- **Volume:** `data/raw/` ≈ **536 MB** (CSV 2019–2021 ~40–90 MB cada;
  ZIP 2022–2026 ~7–17 MB). Parquet do recorte AL: **0,24 MB**.
- **Nacional vs. recorte:** `ca-2026-01` tem 422.418 linhas nacionais →
  2.529 em AL+gasolina (0,60%). `ca-2019-01`: 496.730 → 1.481 (0,30%).

## 3. Frequência & Latência

- **Passo da série:** semanal — mediana de **7 dias** entre semanas de
  referência consecutivas (1 dia entre dias de coleta de campo).
- **Cobertura:** 2019-01-02 a **2026-08-26**.
- **Latência (1 medição):** a coleta mais recente na base em 2026-09-03 é de
  **2026-08-26** → o dado mais novo tem **8 dias**. Medido contra o dia do
  download (não da publicação), então é um **teto**: latência real do registro
  mais recente **≤ 8 dias**. O arquivo semanal traz 4 semanas de uma vez — o
  registro mais antigo do mesmo arquivo tem ~5 semanas.
- **Não verificado:** se a latência é estável. A premissa do CLAUDE.md é
  "~1 a 2 semanas"; não acompanhei várias publicações para confirmar um
  intervalo.
- **Arquivo semestral:** consolidado sai meses após o fim do semestre
  (o de jan–jun/2026 apareceu em setembro; jul–dez/2026 ainda não existe).
- **Buracos:** **13 de 400 semanas** ausentes (387 presentes). Maior lacuna:
  63 dias (8 semanas seguidas em ago–out/2020; 1 em set/2022; 4 seguidas em
  jul/2026).

## 4. Qualidade & Integridade

- **Nulos (base AL):** `valor_compra` **92,81%**, `complemento` **74,45%**,
  todas as outras 16 colunas **0,00%**.
- **`valor_compra` é ausência estrutural, não dado faltante:** último
  preenchimento em **2020-08-17**; 1.408 linhas em 2019, 757 em 2020, **0** de
  2021 em diante. Análise de margem só vale até 2020.
- **Validação (`load.py`):** **0 linhas rejeitadas** em 30.091 — nenhuma data
  inválida, preço ausente/não positivo, preço fora de 0,80–12,00 ou CNPJ ≠ 14
  dígitos. Não gerou `rejeitados.csv`.
- **Faixa de `valor_venda` (R$/L):** por ano fica entre mín 3,50 (2020) e
  máx 8,59 (2022); média sobe de 4,58 (2019) para 6,78 (2026). Sem outlier
  absurdo.
- **`bandeira` precisa de de-para:** 13 valores distintos, com redundância
  temporal — VIBRA (6.569) / VIBRA ENERGIA (3.530) / PETROBRAS DISTRIBUIDORA
  S.A. (2.381) são a mesma linhagem; ALE (114) / ALESAT (403) idem.
  Sem de-para, o teste da H2 sai enviesado.
- **Duplicatas** entre o arquivo "4 últimas semanas" e o semestral
  correspondente: **não verificado**.
- **Amostra irregular no tempo (notebook 01):** Maceió é o único quase contínuo
  (385/387 semanas); o interior some por trimestres — Palmeira dos Índios fica
  fora 64 semanas seguidas (2021 inteiro), Rio Largo 53 (2021), Delmiro Gouveia
  36. A amostra de Maceió caiu de ~24 para ~19 postos/semana em 2023.

## 5. Segurança & Privacidade

- **Dado pessoal:** nenhum identificado — CNPJ e razão social são de pessoa
  jurídica e públicos (CLAUDE.md). Os arquivos trazem endereço do posto
  (rua, número, bairro, CEP), também de PJ.
- **Classificação:** público (dados abertos ANP).
- **Credenciais/segredos:** nenhum — download é HTTP público sem chave.
- **Versionamento:** `data/` está no `.gitignore`; dado bruto nunca é
  commitado nem modificado (toda transformação gera arquivo novo em
  `data/processed/`).
- **Risco reputacional:** ranking nominal de "postos mais caros" não pode ser
  publicado — a amostra é parcial (5 municípios) e o efeito sobre o posto é
  real; agregar por município e bandeira (CLAUDE.md).

## 6. Objetivo do Negócio

- **Pergunta:** prever o preço médio semanal da gasolina em AL na semana
  seguinte; e medir a relação entre Maceió e o interior (assimetria de
  repasse, H1).
- **Entregável:** dashboard com previsão + recomendação "abastecer agora ou
  esperar" e relatório de dispersão de preços entre postos.
- **Público:** motoristas de aplicativo e motoboys que dependem do veículo
  para trabalhar.
- **Baseline a bater:** persistência ("preço da próxima semana = preço desta
  semana"). Só serve modelo que supere isso.
- **Restrição metodológica:** ao prever a semana N, só entram features já
  publicadas naquele momento (latência medida uma vez: ≤ 8 dias para o dado
  mais recente); split temporal, nunca aleatório.
- **Métrica-alvo de sucesso (erro máximo aceitável):** **não verificado** —
  ainda não definida.
