# Documentação da base — Preços de combustíveis da ANP (recorte AL / gasolina)

Referência de estrutura, colunas e transformações. Para os números do
diagnóstico ver [`canvas_dados.md`](canvas_dados.md); para riscos e limitações
ver [`observacoes_base.md`](observacoes_base.md).

---

## 1. Visão geral

| | |
|---|---|
| **Origem** | ANP — Série Histórica de Preços de Combustíveis (dados abertos) |
| **URL** | https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis |
| **Coleta** | pesquisa de campo semanal em postos revendedores, amostral |
| **Grão** | 1 linha = 1 preço de 1 produto em 1 posto numa data de coleta |
| **Escopo bruto** | nacional, todos os combustíveis automotivos |
| **Recorte do projeto** | UF = `AL`, produto começando com `GASOLINA` (comum + aditivada) |
| **Período disponível** | 2019-01-02 a 2026-08-26 (16 arquivos semestrais + arquivo de "últimas 4 semanas") |
| **Recorte processado** | 30.091 linhas, 5 municípios (`data/processed/precos_al.parquet`) |
| **Licença** | dados abertos; obrigatório citar a fonte |
| **Dado pessoal** | nenhum — CNPJ, razão social e endereço são de pessoa jurídica |

## 2. Estrutura de arquivos

```
data/raw/          arquivos originais da ANP — NUNCA modificados
data/processed/    saída do pipeline
  precos_al.parquet   linhas válidas do recorte AL + gasolina
  rejeitados.csv      linhas descartadas + motivo (só existe se houver alguma)
src/download.py    baixa os arquivos da ANP (com retry / retomada)
src/load.py        normaliza, converte tipos, valida, filtra AL + gasolina
```

`data/` está no `.gitignore` (exceto `.gitkeep`). Dado não é versionado.
Toda transformação gera arquivo novo em `data/processed/`; `data/raw/` é imutável.

## 3. Arquivos brutos (`data/raw/`)

- **CSV separado por `;`**, decimal com **vírgula**, aspas padrão.
- **Encoding misto**: arquivos antigos em `latin-1`, recentes em `utf-8`.
  O `load.py` tenta `utf-8-sig` e cai para `latin-1`.
- **Formato muda em 2022**:
  - até 2021-02 → `.csv` solto (`ca-AAAA-SS.csv`), ~40–90 MB
  - 2022-01 → `.zip` com nome fora do padrão: `precos-semestrais-ca.zip`
  - 2022-02 em diante → `.zip` (`ca-AAAA-SS.zip`), ~7–17 MB
  - dentro do zip às vezes o CSV tem nome com acento (`Preços semestrais - AUTOMOTIVOS_AAAA.SS.csv`)
- **`ultimas-4-semanas-gasolina-etanol.csv`**: arquivo à parte com as 4 semanas
  mais recentes (só gasolina e etanol, nacional). Preenche o intervalo entre o
  fim do último semestre publicado e hoje. Latência medida uma vez: o registro
  mais novo tinha 8 dias (ver seção 10).
- **Cabeçalho idêntico** nos 16 arquivos: as 16 colunas da seção 4, na mesma ordem.

## 4. Colunas do arquivo bruto (16)

| # | Coluna (ANP) | Exemplo | Descrição |
|---|---|---|---|
| 1 | `Regiao - Sigla` | `NE` | Região geográfica (N, NE, CO, SE, S). No recorte AL: sempre `NE`. |
| 2 | `Estado - Sigla` | `AL` | Sigla da UF. No recorte: sempre `AL`. |
| 3 | `Municipio` | `MACEIO` | Nome do município (sem acento no arquivo). |
| 4 | `Revenda` | `POSTO X LTDA` | Razão social do posto (PJ). |
| 5 | `CNPJ da Revenda` | ` 12.451.076/0001-12` | CNPJ do posto, com máscara e às vezes espaço à esquerda. |
| 6 | `Nome da Rua` | `AVENIDA FERNANDES LIMA` | Logradouro do posto. |
| 7 | `Numero Rua` | `252` / `S/N` | Número; é texto. |
| 8 | `Complemento` | `KM 68` | Complemento do endereço. Frequentemente vazio. |
| 9 | `Bairro` | `CENTRO` | Bairro do posto. |
| 10 | `Cep` | `57300-590` | CEP com máscara. |
| 11 | `Produto` | `GASOLINA` | Combustível. No recorte: `GASOLINA`, `GASOLINA ADITIVADA`. |
| 12 | `Data da Coleta` | `02/01/2026` | Data da visita de campo (`dd/mm/aaaa`). |
| 13 | `Valor de Venda` | `7,97` | Preço ao consumidor (R$), decimal com vírgula. |
| 14 | `Valor de Compra` | `3,8906` | Preço pago pelo posto à distribuidora (R$). **Só até 2020-08-17**; depois sempre vazio. |
| 15 | `Unidade de Medida` | `R$ / litro` | Unidade do preço. Gasolina: sempre `R$ / litro` (`R$ / m³` é GNV, fora do recorte). |
| 16 | `Bandeira` | `IPIRANGA` | Distribuidora do posto, ou `BRANCA` se sem bandeira. **Não é estável no tempo** (fusões — ver seção 7). |

## 5. Colunas do parquet processado (`precos_al.parquet`, 18)

16 colunas renomeadas + 2 derivadas. Ordem: a mesma da seção 4, com
`arquivo_origem` e `semana` no fim.

| Coluna | Tipo | Nulos | Origem / regra |
|---|---|---|---|
| `regiao` | str | 0% | ← `Regiao - Sigla`. Sempre `NE`. |
| `uf` | str | 0% | ← `Estado - Sigla`. `strip().upper()`. Sempre `AL`. |
| `municipio` | str | 0% | ← `Municipio`. `strip().upper()`. 5 valores. |
| `revenda` | str | 0% | ← `Revenda`. |
| `cnpj` | str | 0% | ← `CNPJ da Revenda`, **só os dígitos** (`\D` removido) → 14 caracteres. |
| `nome_da_rua` | str | 0% | ← `Nome da Rua`. Sem renomeação no `RENOMEAR`. |
| `numero_rua` | str | 0% | ← `Numero Rua`. |
| `complemento` | str | **74,5%** | ← `Complemento`. Nulo alto é esperado, não é erro. |
| `bairro` | str | 0% | ← `Bairro`. `strip().upper()`. |
| `cep` | str | 0% | ← `Cep`. Mantém a máscara. |
| `produto` | str | 0% | ← `Produto`. `strip().upper()`. `GASOLINA` ou `GASOLINA ADITIVADA`. |
| `data_coleta` | datetime64 | 0% | ← `Data da Coleta`, `to_datetime(format="%d/%m/%Y")`. Nula → linha rejeitada. |
| `valor_venda` | float64 | 0% | ← `Valor de Venda`, vírgula→ponto, `to_numeric`. R$/litro. |
| `valor_compra` | float64 | **92,8%** | ← `Valor de Compra`. **Ausência estrutural** desde 2020-08-17 — não imputar. |
| `unidade` | str | 0% | ← `Unidade de Medida`. Sempre `R$ / litro` no recorte. |
| `bandeira` | str | 0% | ← `Bandeira`. `strip().upper()`. Precisa de de-para (seção 7). |
| `arquivo_origem` | str | 0% | **derivada** — nome do arquivo bruto da linha. Rastreabilidade. |
| `semana` | datetime64 | 0% | **derivada** — segunda-feira da semana da coleta (`to_period("W-SUN").start_time`). Chave para séries semanais. |

## 6. O que o `load.py` faz (pipeline)

1. **Lê** cada arquivo de `data/raw/` (`.csv` ou `.zip`) como texto, `sep=";"`,
   tentando `utf-8-sig` e depois `latin-1`.
2. **Normaliza os nomes de coluna**: `"Regiao - Sigla"` → `regiao_sigla`
   (minúsculo, sem acento, não-alfanumérico vira `_`). Depois aplica o de-para
   `RENOMEAR` (7 renomeações efetivas: `estado_sigla`→`uf`,
   `cnpj_da_revenda`→`cnpj`, `data_da_coleta`→`data_coleta`,
   `valor_de_venda`→`valor_venda`, `valor_de_compra`→`valor_compra`,
   `unidade_de_medida`→`unidade`, `regiao_sigla`→`regiao`).
3. **Filtra cedo**, arquivo por arquivo, antes de concatenar: `uf == "AL"` e
   `produto` começa com `"GASOLINA"`. (O arquivo é nacional; só interessa o recorte.)
4. **Limpa** (`limpar`): datas → `datetime`; preços → `float` (vírgula→ponto);
   `municipio/bandeira/produto/bairro/uf` → `strip().upper()`; `cnpj` → só dígitos;
   deriva `semana`.
5. **Valida** (`validar`): separa linhas boas das rejeitadas (seção 8).
6. **Escreve** `data/processed/precos_al.parquet` (válidas) e, se houver rejeição,
   `data/processed/rejeitados.csv` (com a coluna `motivo_rejeicao`).

## 7. `bandeira` — de-para pendente

A mesma empresa aparece com nomes diferentes em épocas diferentes. Antes de
qualquer análise por bandeira, unificar:

| Aparece como | É |
|---|---|
| `PETROBRAS DISTRIBUIDORA S.A.`, `VIBRA`, `VIBRA ENERGIA` | mesma empresa (BR → Vibra) |
| `ALE`, `ALESAT` | mesma empresa (Ale → incorporada pela Ipiranga) |
| `BRANCA` | posto sem bandeira (não é distribuidora) |

13 valores distintos no recorte atual: `BRANCA`, `VIBRA`, `IPIRANGA`, `RAIZEN`,
`VIBRA ENERGIA`, `PETROBRAS DISTRIBUIDORA S.A.`, `DISLUB`, `ALESAT`, `ALE`,
`PETROX DISTRIBUIDORA`, `TEMAPE`, `LARCO`, `SETTA DISTRIBUIDORA`.

## 8. Regras de validação (`validar`)

Uma linha vai para `rejeitados.csv` com o **primeiro** motivo que se aplica:

| `motivo_rejeicao` | Condição |
|---|---|
| `data invalida` | `data_coleta` não parseou (`dd/mm/aaaa`) |
| `preco ausente` | `valor_venda` nulo |
| `preco nao positivo` | `valor_venda <= 0` |
| `preco fora da faixa plausivel` | `valor_venda < 0,80` ou `> 12,00` (R$/litro) |
| `cnpj malformado` | `cnpj` com número de dígitos ≠ 14 |

A faixa 0,80–12,00 serve para pegar erro de digitação, não outlier real.
**No recorte atual: 0 linhas rejeitadas** em 30.091 (o `rejeitados.csv` não é
gerado). A faixa é larga para o preço atual (~R$ 5,4–8,0) — ver
[`observacoes_base.md`](observacoes_base.md), risco 5.

## 9. Como regenerar

```bash
python src/download.py --inicio 2019 --fim 2026   # semestres (retry automático)
python src/download.py --ultimas-semanas           # arquivo das últimas 4 semanas
python src/load.py                                 # gera data/processed/precos_al.parquet
```

Diagnóstico e conferência dos números:

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/00_diagnostico.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/01_cobertura_amostral.ipynb
```

## 10. Limitações conhecidas

Resumo (detalhe em [`observacoes_base.md`](observacoes_base.md)):

- **Amostra amostral e irregular.** Nº de postos por município/semana varia muito
  (Maceió ~19, interior ~7). Palmeira dos Índios e Rio Largo ficam fora da amostra
  o ano de 2021 inteiro. Média simples por município engana — usar mediana ou
  exigir n mínimo de postos.
- **Quebra de amostragem em 2023** (Maceió ~24→19 postos/semana).
- **`valor_compra` só até 2020-08-17** — análise de margem só vale até lá.
- **`bandeira` precisa de de-para** (seção 7).
- **Latência: 1 medição — o registro mais novo tinha 8 dias** (2026-09-03 vs.
  última coleta 2026-08-26), medido contra o dia do download → teto ≤ 8 dias.
  Não verificado se é estável (premissa do CLAUDE.md: ~1 a 2 semanas). O modelo
  tem que respeitar (features só com dados já publicados; split temporal).
- **13 de 400 semanas ausentes** na série.
