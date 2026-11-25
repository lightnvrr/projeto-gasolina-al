# docs/

Documentação da base de dados e do diagnóstico.

| Arquivo | O que é |
|---|---|
| [`dicionario_dados.md`](dicionario_dados.md) | **Referência da base**: origem, estrutura de arquivos, dicionário de colunas (bruto e processado), o que o `load.py` faz, regras de validação, como regenerar. |
| [`canvas_dados.md`](canvas_dados.md) | Canvas de catalogação (6 blocos), cada afirmação com o número que a sustenta. Feito para apresentação. |
| [`observacoes_base.md`](observacoes_base.md) | Considerações sobre a base: o que está sólido, riscos em ordem de gravidade, decisões que o diagnóstico força, pendências. |
| [`fig_cobertura_postos.png`](fig_cobertura_postos.png) | Gráfico: postos distintos pesquisados por semana, uma linha por município (gerado por `notebooks/01_cobertura_amostral.ipynb`). |

Os números vêm de `notebooks/00_diagnostico.ipynb` e
`notebooks/01_cobertura_amostral.ipynb`, sobre `data/raw/` e
`data/processed/precos_al.parquet`.
