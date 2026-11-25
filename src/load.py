"""
Le, normaliza e valida os CSVs da ANP.

Os arquivos da ANP tem tres armadilhas:
  1. separador ';' e decimal ','
  2. encoding latin-1 nos arquivos antigos, utf-8 nos recentes
  3. nomes de coluna que mudam de ano para ano (acento, hifen, espaco)

Uso:
    python src/load.py            # gera data/processed/precos_al.parquet
"""

import re
import unicodedata
import zipfile
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
PROCESSED = Path(__file__).resolve().parents[1] / "data" / "processed"

UF_ALVO = "AL"
PRODUTO_ALVO = "GASOLINA"  # pega "GASOLINA" e "GASOLINA ADITIVADA"

# Faixa plausivel para preco de gasolina no varejo (R$/litro).
# Serve para pegar erro de digitacao, nao para filtrar outlier real.
PRECO_MIN, PRECO_MAX = 0.80, 12.00

RENOMEAR = {
    "regiao_sigla": "regiao",
    "estado_sigla": "uf",
    "municipio": "municipio",
    "revenda": "revenda",
    "cnpj_da_revenda": "cnpj",
    "bairro": "bairro",
    "produto": "produto",
    "data_da_coleta": "data_coleta",
    "valor_de_venda": "valor_venda",
    "valor_de_compra": "valor_compra",
    "unidade_de_medida": "unidade",
    "bandeira": "bandeira",
}


def normalizar_nome(coluna: str) -> str:
    """'Regiao - Sigla' -> 'regiao_sigla'"""
    sem_acento = unicodedata.normalize("NFKD", coluna)
    sem_acento = sem_acento.encode("ascii", "ignore").decode("ascii")
    limpo = re.sub(r"[^a-z0-9]+", "_", sem_acento.lower()).strip("_")
    return limpo


def ler_csv(caminho: Path) -> pd.DataFrame:
    """Le um CSV da ANP tentando os dois encodings usados ao longo dos anos."""
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(
                caminho,
                sep=";",
                encoding=encoding,
                dtype=str,
                low_memory=False,
            )
        except UnicodeDecodeError:
            continue
    raise ValueError(f"nao consegui decodificar {caminho.name}")


def ler_zip(caminho: Path) -> pd.DataFrame:
    """Alguns semestres vem zipados, as vezes com mais de um CSV dentro."""
    quadros = []
    with zipfile.ZipFile(caminho) as zf:
        for nome in zf.namelist():
            if not nome.lower().endswith(".csv"):
                continue
            for encoding in ("utf-8-sig", "latin-1"):
                try:
                    with zf.open(nome) as f:
                        quadros.append(
                            pd.read_csv(
                                f, sep=";", encoding=encoding,
                                dtype=str, low_memory=False,
                            )
                        )
                    break
                except UnicodeDecodeError:
                    continue
    if not quadros:
        raise ValueError(f"nenhum csv dentro de {caminho.name}")
    return pd.concat(quadros, ignore_index=True)


def carregar_arquivo(caminho: Path) -> pd.DataFrame:
    bruto = ler_zip(caminho) if caminho.suffix == ".zip" else ler_csv(caminho)
    bruto.columns = [normalizar_nome(c) for c in bruto.columns]
    bruto = bruto.rename(columns=RENOMEAR)
    bruto["arquivo_origem"] = caminho.name
    return bruto


def limpar(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Datas: os arquivos usam dd/mm/aaaa, mas ha excecoes.
    df["data_coleta"] = pd.to_datetime(
        df["data_coleta"], format="%d/%m/%Y", errors="coerce"
    )

    # Precos: virgula decimal -> ponto.
    for coluna in ("valor_venda", "valor_compra"):
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(
                df[coluna].str.replace(",", ".", regex=False), errors="coerce"
            )

    # Texto: tira espaco sobrando e padroniza caixa.
    for coluna in ("municipio", "bandeira", "produto", "bairro", "uf"):
        if coluna in df.columns:
            df[coluna] = df[coluna].str.strip().str.upper()

    df["cnpj"] = df["cnpj"].str.replace(r"\D", "", regex=True)

    # Semana de referencia (segunda-feira da semana da coleta).
    df["semana"] = df["data_coleta"].dt.to_period("W-SUN").dt.start_time

    return df


def validar(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa as linhas boas das rejeitadas, com o motivo da rejeicao."""
    motivos = pd.Series("", index=df.index)

    def marcar(mascara, motivo):
        motivos[mascara & (motivos == "")] = motivo

    marcar(df["data_coleta"].isna(), "data invalida")
    marcar(df["valor_venda"].isna(), "preco ausente")
    marcar(df["valor_venda"] <= 0, "preco nao positivo")
    marcar(
        (df["valor_venda"] < PRECO_MIN) | (df["valor_venda"] > PRECO_MAX),
        "preco fora da faixa plausivel",
    )
    marcar(df["cnpj"].str.len() != 14, "cnpj malformado")

    rejeitados = df[motivos != ""].assign(motivo_rejeicao=motivos[motivos != ""])
    validos = df[motivos == ""]
    return validos, rejeitados


def main() -> None:
    arquivos = sorted(
        p for p in RAW.iterdir() if p.suffix in (".csv", ".zip")
    )
    if not arquivos:
        raise SystemExit("data/raw esta vazio. Rode src/download.py primeiro.")

    partes = []
    for caminho in arquivos:
        print(f"lendo {caminho.name}...")
        bruto = carregar_arquivo(caminho)
        # Filtra cedo: o arquivo e nacional, so interessa AL + gasolina.
        recorte = bruto[
            (bruto["uf"].str.strip().str.upper() == UF_ALVO)
            & (bruto["produto"].str.upper().str.startswith(PRODUTO_ALVO))
        ]
        print(f"  {len(bruto):>8} linhas -> {len(recorte):>7} em {UF_ALVO}")
        partes.append(recorte)

    df = limpar(pd.concat(partes, ignore_index=True))
    validos, rejeitados = validar(df)

    PROCESSED.mkdir(parents=True, exist_ok=True)
    validos.to_parquet(PROCESSED / "precos_al.parquet", index=False)
    if not rejeitados.empty:
        rejeitados.to_csv(PROCESSED / "rejeitados.csv", index=False)

    print(f"\n{len(validos)} linhas validas -> data/processed/precos_al.parquet")
    if not rejeitados.empty:
        print(f"{len(rejeitados)} rejeitadas -> data/processed/rejeitados.csv")
        print(rejeitados["motivo_rejeicao"].value_counts().to_string())
    print(
        f"periodo: {validos['data_coleta'].min():%d/%m/%Y} "
        f"a {validos['data_coleta'].max():%d/%m/%Y}"
    )
    print(f"municipios: {validos['municipio'].nunique()}")


if __name__ == "__main__":
    main()
