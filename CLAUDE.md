# Contexto do projeto

Projeto de curso de ciência de dados. Previsão de preço de gasolina em Alagoas
a partir da Série Histórica de Preços de Combustíveis da ANP.

## Pergunta de pesquisa

1. Como prever o preço médio da gasolina em Alagoas nas próximas semanas?
2. Qual a relação entre a variação de preço em Maceió e nos municípios do interior?

## Hipóteses a testar

- H1: quando o preço sobe em Maceió, o interior acompanha rápido; quando cai, demora mais
  (assimetria de repasse, "rockets and feathers").
- H2: postos de bandeira branca são mais baratos que os bandeirados.

## Variáveis

- **Alvo:** preço médio semanal da gasolina em AL na semana seguinte.
- **Features:** lags do preço (1 a 4 semanas), lags do preço de Maceió, bandeira,
  município, semana do ano.

## Entregável

Dashboard com previsão e recomendação "abastecer agora ou esperar", mais um
relatório sobre a dispersão de preços entre postos.
Público: motoristas de aplicativo e motoboys que dependem do veículo para trabalhar.

---

# Armadilhas dos dados da ANP

Estas já foram descobertas na marra. Não perca tempo redescobrindo.

1. **Separador `;`, decimal `,`.** `pd.read_csv` sem argumentos falha.
2. **Encoding misto.** Arquivos antigos em latin-1, recentes em utf-8.
   `src/load.py` tenta os dois.
3. **Formato muda em 2022.** Até 2021 são `.csv` soltos; de 2022 em diante são
   `.zip`. E o arquivo do 1º semestre de 2022 tem nome fora do padrão
   (`precos-semestrais-ca.zip`).
4. **`Valor de Compra` some a partir de 2020.** A ANP parou de divulgar o preço
   de distribuição. Não trate como dado faltante a ser imputado — é ausência
   estrutural. Qualquer análise que dependa de margem só vale até 2019.
5. **`Bandeira` não é estável no tempo.** BR virou Vibra, Ale foi incorporada
   pela Ipiranga. Sem um de-para, o teste da H2 sai enviesado. Construir o
   de-para é uma etapa obrigatória, não opcional.
6. **A pesquisa é amostral.** Nem todo posto é visitado toda semana. O número de
   observações por município varia muito; Maceió tem muito mais que o interior.
   Média simples por município mistura semanas com 30 postos e semanas com 3.
7. **Composição da amostra muda no tempo.** Municípios entram e saem
   (Palmeira dos Índios e Rio Largo ausentes em 2021 inteiro). Média
   simples confunde preço com composição. Usar painel balanceado ou
   pesos fixos.
8. **Aditivada e comum têm ~54 centavos de diferença.** Não misturar na
   série-alvo — modelar a comum.
9. **Buracos na série vêm de ausências longas, não de rodízio.** Os
   municípios do interior somem da pesquisa por meses seguidos (Palmeira
   dos Índios: 0% das semanas em 2021, 25% em 2025). Em 18 semanas a média
   estadual variou mais de 5 centavos só por entrada ou saída de município
   (máximo: 22,6 centavos em 28/07/2025). Pesquisa suspensa oficialmente
   entre 23/08/2020 e 17/10/2020.

# Cuidado metodológico principal

A ANP publica o arquivo das "4 últimas semanas" com atraso de aproximadamente
uma a duas semanas. O modelo tem que ser treinado e avaliado respeitando essa
defasagem: ao prever a semana N, só podem entrar features que já estariam
publicadas naquele momento.

Consequências práticas:

- **Nunca usar `train_test_split` aleatório.** Split temporal ou
  `TimeSeriesSplit`. Embaralhar série temporal é vazamento.
- Qualquer estatística de normalização (média, desvio) tem que ser calculada
  só sobre o treino.
- O baseline a bater é a persistência: "o preço da próxima semana é igual ao
  desta semana". Se o modelo não bate isso, ele não serve. Reportar sempre.

# Convenções de código

- Português nos nomes de coluna e nas mensagens; inglês nas bibliotecas.
- Dados brutos em `data/raw/` nunca são modificados. Toda transformação gera
  arquivo novo em `data/processed/`.
- `data/` está no `.gitignore`. Não commitar dado.

# Restrições e ética

- Não há dado pessoal: CNPJ e razão social são de pessoa jurídica e públicos.
- Exibir sempre a data de referência do dado e a defasagem. Preço desatualizado
  apresentado como atual engana o consumidor.
- Não publicar ranking nominal de postos mais caros. Agregar por município e
  bandeira: a amostra é parcial e o efeito reputacional é real.
- Conclusões valem para os postos pesquisados, não para o mercado inteiro.

# Estado atual

- Série baixada de 2019-01 a 2026-01 + arquivo das 4 últimas semanas.
  `load.py` rodado nos arquivos reais: 30.091 linhas em AL (19.366 só
  gasolina comum), 5 municípios, 0 rejeições.
- Notebooks 00 (diagnóstico) e 01 (cobertura amostral) prontos. Docs em
  `docs/`.
- Pendente: de-para de bandeira no `load.py`; filtrar só gasolina comum
  na série-alvo.
- **Próximo passo:** baseline de persistência, usando a média estadual
  só com municípios de cobertura contínua.
