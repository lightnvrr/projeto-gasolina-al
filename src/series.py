"""
Monta as series semanais usadas na modelagem a partir de
data/processed/precos_al_comum.parquet (saida do load.py).

Decisoes (ver docs/observacoes_base.md):
  - Um preco por posto por semana (mediana, se o posto foi coletado mais de
    uma vez na semana).
  - Preco do municipio na semana = MEDIANA dos postos, nunca media simples:
    a amostra varia de 1 a 30 postos por semana.
  - Calendario semanal completo (segunda-feira): semanas sem coleta ficam NaN
    em vez de sumir, para que os lags sejam lags de calendario de verdade.
  - Indice estadual = Maceio e Arapiraca com PESOS FIXOS. Sao os dois unicos
    municipios com cobertura quase continua; os outros tres somem da pesquisa
    por meses seguidos e trocariam preco por composicao da amostra.
"""

from pathlib import Path

import pandas as pd

PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

# Pesos fixos proporcionais a mediana de postos/semana (19 em Maceio, 14 em
# Arapiraca; notebook 01). Fixos no tempo de proposito.
PESOS_INDICE = {"MACEIO": 19 / 33, "ARAPIRACA": 14 / 33}


def carregar_comum() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED / "precos_al_comum.parquet")


def preco_posto_semana(df: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por (semana, municipio, posto)."""
    return (
        df.groupby(
            ["semana", "municipio", "cnpj", "bandeira_grupo", "bandeira_branca"]
        )["valor_venda"]
        .median()
        .reset_index()
    )


def painel_municipios(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Retorna (preco mediano, numero de postos), semana x municipio,
    reindexados no calendario semanal completo."""
    ps = preco_posto_semana(df)
    agg = ps.groupby(["semana", "municipio"])["valor_venda"].agg(["median", "size"])
    preco = agg["median"].unstack()
    n_postos = agg["size"].unstack()
    calendario = pd.date_range(preco.index.min(), preco.index.max(), freq="W-MON")
    return preco.reindex(calendario), n_postos.reindex(calendario).fillna(0)


def indice_estadual(preco: pd.DataFrame) -> pd.Series:
    """Indice de pesos fixos. Semana em que falta um dos municipios -> NaN
    (nao renormaliza os pesos, que e justamente o que mistura composicao)."""
    total = sum(preco[m] * w for m, w in PESOS_INDICE.items())
    return total.rename("indice_al")
