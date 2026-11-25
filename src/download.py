"""
Baixa os arquivos da Serie Historica de Precos de Combustiveis da ANP.

Fonte oficial:
https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis

O servidor da ANP e' instavel para arquivos grandes; o download tem retry com
espera crescente e escreve num .part, so renomeando quando o arquivo vem
inteiro. Rodar de novo retoma de onde parou (arquivos ja baixados sao pulados).

Uso:
    python src/download.py --inicio 2019 --fim 2026
    python src/download.py --ultimas-semanas
"""

import argparse
import time
from pathlib import Path

import requests

BASE = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"

# A ANP mudou o formato ao longo do tempo:
#   2004-2021 -> .csv solto
#   2022-01   -> nome fora do padrao (precos-semestrais-ca.zip)
#   2022-02+  -> .zip
ULTIMO_ANO_CSV = 2021

# O servidor da ANP costuma derrubar a conexao no meio de arquivos grandes
# (ChunkedEncodingError / IncompleteRead). Tenta de novo algumas vezes.
TENTATIVAS = 4
TAMANHO_MINIMO = 1_000_000  # bytes; arquivo menor que isso e' pagina de erro


def url_semestre(ano: int, semestre: int) -> str:
    if ano == 2022 and semestre == 1:
        return f"{BASE}/dsas/ca/precos-semestrais-ca.zip"
    ext = "csv" if ano <= ULTIMO_ANO_CSV else "zip"
    return f"{BASE}/dsas/ca/ca-{ano}-{semestre:02d}.{ext}"


URL_ULTIMAS_SEMANAS = f"{BASE}/qus/ultimas-4-semanas-gasolina-etanol.csv"


def _tentar_baixar(url: str, destino: Path) -> None:
    """Baixa para um .part e so renomeia se veio inteiro. Levanta em erro."""
    parcial = destino.with_suffix(destino.suffix + ".part")
    with requests.get(url, timeout=180, stream=True) as resp:
        resp.raise_for_status()
        esperado = int(resp.headers.get("Content-Length", 0))
        with open(parcial, "wb") as arquivo:
            for bloco in resp.iter_content(chunk_size=1 << 16):
                arquivo.write(bloco)
    recebido = parcial.stat().st_size
    if esperado and recebido < esperado:
        parcial.unlink()
        raise OSError(f"veio incompleto: {recebido} de {esperado} bytes")
    parcial.replace(destino)


def baixar(url: str, destino: Path) -> bool:
    if destino.exists() and destino.stat().st_size >= TAMANHO_MINIMO:
        print(f"  ja existe, pulando: {destino.name}")
        return True

    destino.parent.mkdir(parents=True, exist_ok=True)
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            _tentar_baixar(url, destino)
        except requests.HTTPError as erro:
            if erro.response is not None and erro.response.status_code == 404:
                print(f"  nao publicado ainda (404): {destino.name}")
                return False
            print(f"  tentativa {tentativa}/{TENTATIVAS} falhou: {erro}")
        except (requests.RequestException, OSError) as erro:
            print(f"  tentativa {tentativa}/{TENTATIVAS} falhou: {erro}")
        else:
            print(f"  ok: {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")
            return True
        if tentativa < TENTATIVAS:
            time.sleep(5 * tentativa)  # espera crescente antes de tentar de novo

    print(f"  DESISTI de {destino.name} apos {TENTATIVAS} tentativas")
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inicio", type=int, default=2019)
    parser.add_argument("--fim", type=int, default=2026)
    parser.add_argument("--ultimas-semanas", action="store_true")
    args = parser.parse_args()

    if args.ultimas_semanas:
        baixar(URL_ULTIMAS_SEMANAS, RAW / "ultimas-4-semanas-gasolina-etanol.csv")
        return

    for ano in range(args.inicio, args.fim + 1):
        for semestre in (1, 2):
            url = url_semestre(ano, semestre)
            print(f"{ano}-{semestre}:")
            baixar(url, RAW / url.rsplit("/", 1)[-1])


if __name__ == "__main__":
    main()
