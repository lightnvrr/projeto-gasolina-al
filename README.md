# Previsão de preço da gasolina em Alagoas

Projeto de curso de ciência de dados usando a Série Histórica de Preços de
Combustíveis da ANP.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python src/download.py --inicio 2019 --fim 2026   # baixa os semestres
python src/download.py --ultimas-semanas          # arquivo mais recente
python src/load.py                                # limpa e filtra AL
```

Saída: `data/processed/precos_al.parquet` com as linhas válidas e
`data/processed/rejeitados.csv` com as descartadas e o motivo.

## Estrutura

```
src/download.py   baixa os arquivos da ANP
src/load.py       normaliza colunas, converte tipos, valida, filtra AL + gasolina
data/raw/         arquivos originais, nunca modificados
data/processed/   saída limpa
notebooks/        exploração (00 diagnóstico, 01 cobertura amostral)
docs/             documentação da base — ver docs/README.md
CLAUDE.md         contexto do projeto e armadilhas conhecidas dos dados
```

## Documentação da base

`docs/dicionario_dados.md` é a referência: origem, formatos, dicionário de
colunas, o que o `load.py` faz e regras de validação. `docs/README.md` indexa
os demais documentos.

## Fonte

ANP, Série Histórica de Preços de Combustíveis (dados abertos, coleta semanal
desde 2004). Ao usar, citar a fonte.
