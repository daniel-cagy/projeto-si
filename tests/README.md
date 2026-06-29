# Avaliação

Este diretório concentra os casos e resultados de avaliação do estimador.

## Estrutura dos samples

Cada arquivo em `tests/samples/` deve seguir o formato:

```json
{
  "imagem": "produto.jpg",
  "descricao": "Descrição textual usada no teste",
  "resultado_esperado": {
    "comprimento": 10,
    "largura": 5,
    "altura": 2,
    "peso": 0.1
  }
}
```

As imagens referenciadas ficam em `tests/images/`, que é ignorado pelo Git.
Os CSVs gerados ficam em `tests/results/`, também ignorado pelo Git.

## Convenção das dimensões nos testes

Para reduzir ambiguidade entre comprimento, largura e altura, a avaliação normaliza as três dimensões antes de calcular erro e acerto de intervalo:

- `comprimento`: maior lado;
- `largura`: segundo maior lado;
- `altura`: menor lado.

Essa regra vale só para os testes. O prompt e a resposta do modelo continuam usando as chaves normais. O CSV inclui `comprimento_source_dimension`, `largura_source_dimension` e `altura_source_dimension` para mostrar de qual eixo retornado pelo modelo veio cada dimensão normalizada.

## Rodar avaliação completa

```bash
python3 tests/run_tests.py
```

A execução padrão roda todos os samples, todos os modelos da lista `MODELS`, os três modos de imagem e 3 repetições por combinação.

Com 5 samples, 6 modelos, 3 modos e 3 repetições, isso gera 270 chamadas à API.

## Smoke test barato

```bash
python3 tests/run_tests.py   --samples livro   --models gpt-4o-mini   --processing-modes resized   --repetitions 1
```

## Estimar custo

Informe os preços por 1M tokens via flag:

```bash
python3 tests/run_tests.py   --input-price-per-1m 0.00   --output-price-per-1m 0.00
```

Ou via ambiente:

```bash
export OPENAI_INPUT_PRICE_PER_1M=0.00
export OPENAI_OUTPUT_PRICE_PER_1M=0.00
python3 tests/run_tests.py
```

O CSV inclui tokens de entrada, saída, total e custo estimado quando a API retorna `usage`.

## Analisar resultados

Depois de gerar um CSV de avaliação, rode:

```bash
python3 tests/analyze_results.py tests/results/evaluation_YYYYMMDD_HHMMSS.csv
```

Se o caminho do CSV for omitido, o script usa o `evaluation_*.csv` mais recente em `tests/results/`.

O script gera uma pasta `analysis_<nome_do_csv>` com:

- resumos CSV por modelo, modo de imagem, produto e medida avaliada;
- gráficos SVG gerados com matplotlib para erro médio dimensional, erro geral com peso, erro por medida, peso em gramas/faixas de tolerância, taxa de acerto, tokens, custo, custo-benefício, duração, sucesso e tamanho final da imagem;
- `report.md` com os principais achados.

O script usa pandas para agregação dos resultados e matplotlib para geração dos gráficos. A análise recalcula custo com uma tabela fixa de preços por modelo definida em `tests/analyze_results.py`, então não depende das flags de custo usadas no `run_tests.py`. O score principal de custo-benefício usa apenas dimensões, enquanto peso é analisado separadamente por erro absoluto em gramas e tolerâncias de 25g, 50g, 100g e 20%.
