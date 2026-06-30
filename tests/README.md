# Avaliação do estimador

Este diretório concentra a avaliação experimental do estimador de dimensões e peso. A ideia não é fazer um teste unitário tradicional, e sim medir como diferentes modelos e tratamentos de imagem se comportam em um conjunto controlado de produtos.

O fluxo é dividido em duas etapas:

1. `run_tests.py` executa chamadas reais à API para cada produto, modelo, modo de imagem e repetição.
2. `analyze_results.py` lê o CSV gerado, agrega métricas, recalcula custos e produz resumos, gráficos e relatório.

## Estrutura

```txt
tests/
  samples/        Casos de teste em JSON
  images/         Imagens usadas pelos samples, ignoradas pelo Git
  results/        CSVs, relatórios e gráficos gerados, ignorados pelo Git
  run_tests.py    Executor da avaliação
  analyze_results.py
```

## Samples

Cada arquivo em `tests/samples/` representa um produto. O formato mínimo é:

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

As unidades esperadas são:

- dimensões em centímetros;
- peso em quilogramas.

A imagem pode ser indicada por caminho relativo a `tests/images/` ou por caminho absoluto. O campo `descricao` é enviado ao modelo junto com a imagem. O campo `resultado_esperado` é usado apenas na avaliação.

Para avaliar mais de uma foto do mesmo produto, use `imagens` no lugar de `imagem`:

```json
{
  "imagens": [
    "produto_frente.jpg",
    "produto_lateral.jpg",
    "produto_topo.jpg"
  ],
  "descricao": "Descrição textual usada no teste",
  "resultado_esperado": {
    "comprimento": 10,
    "largura": 5,
    "altura": 2,
    "peso": 0.1
  }
}
```

A ordem importa: o runner usa as primeiras imagens da lista conforme a quantidade pedida em `--image-counts`.

Um sample também pode incluir `medidas_conhecidas`, caso a avaliação queira simular o usuário informando uma medida real:

```json
{
  "medidas_conhecidas": {
    "comprimento": 10,
    "peso": 0.12
  }
}
```

## Metodologia

Para cada sample, o runner executa todas as combinações de:

- modelo em `MODELS`;
- modo de imagem em `IMAGE_PROCESSING_MODES`;
- quantidade de imagens configurada em `--image-counts`;
- repetição configurada em `--repetitions`.

A fórmula do total de chamadas é:

```txt
numero_de_produtos x numero_de_modelos x numero_de_modos_de_imagem x quantidades_de_imagens x repeticoes
```

Exemplo:

```txt
5 produtos x 6 modelos x 3 modos x 1 quantidade de imagem x 3 repeticoes = 270 chamadas
```

As repetições existem porque respostas de modelos podem variar mesmo com o mesmo prompt, imagem e descrição. Repetir ajuda a medir estabilidade e reduz o risco de concluir algo a partir de uma resposta isolada.

Para comparar uma foto contra múltiplas fotos, um exemplo de execução é:

```bash
python tests/run_tests.py --image-counts 1 2 3 --repetitions 3
```

Samples que tiverem apenas `imagem` só podem ser executados com `--image-counts 1`.

## Modos de imagem

A avaliação compara os mesmos produtos com diferentes tratamentos de imagem:

- `original`: envia a imagem original;
- `resized`: redimensiona/comprime a imagem antes do envio;
- `quantized`: aplica quantização de cores.

O objetivo é medir se reduzir a imagem preserva qualidade suficiente e se diminui custo, latência ou tokens. Na prática, a análise deve comparar qualidade e custo juntos, porque tamanho de arquivo menor nem sempre significa menos tokens visuais.

## Convenção das dimensões

Comprimento, largura e altura podem ser subjetivos dependendo da orientação do produto na foto. Para reduzir essa ambiguidade, a avaliação normaliza as dimensões antes de calcular erro e acerto:

- `comprimento`: maior lado;
- `largura`: segundo maior lado;
- `altura`: menor lado.

Essa regra vale somente para os testes. O prompt e a resposta do modelo continuam usando as chaves normais. O CSV inclui:

```txt
comprimento_source_dimension
largura_source_dimension
altura_source_dimension
```

Essas colunas mostram de qual eixo retornado pelo modelo veio cada dimensão normalizada.

## Métricas principais

### Erro percentual por medida

Para cada medida, o runner calcula:

```txt
erro_absoluto = abs(estimativa - valor_real)
erro_percentual = erro_absoluto / valor_real * 100
```

Isso gera colunas como:

```txt
comprimento_percent_error
largura_percent_error
altura_percent_error
peso_percent_error
```

### Erro dimensional

A métrica dimensional exclui peso e usa apenas:

```txt
comprimento, largura, altura
```

A coluna principal é:

```txt
mean_abs_percent_error_dimensions
```

Ela é a média dos erros percentuais das três dimensões em cada execução. Depois, na análise, essa métrica é agregada por modelo, modo de imagem ou produto.

Essa é a métrica mais importante para avaliar qualidade dimensional.

### Desvio padrão do erro

A análise também calcula o desvio padrão do erro para medir estabilidade entre execuções. As principais colunas são:

```txt
std_abs_percent_error_dimensions
std_abs_percent_error_all
std_percent_error
```

As duas primeiras aparecem nos resumos agregados, como `summary_by_model_mode.csv`. A coluna `std_percent_error` aparece nos resumos por medida, como `summary_by_model_mode_measure.csv` e `summary_by_measure.csv`.

Quanto menor o desvio padrão, mais consistente foi aquele modelo/modo de imagem. Uma média baixa com desvio alto indica que o resultado pode depender bastante da repetição ou do produto testado.

### Peso por faixa

A análise separa também os erros de peso por faixa, usando o peso real esperado do sample:

```txt
leve: peso < 0.1 kg
medio: 0.1 kg <= peso < 0.5 kg
pesado: peso >= 0.5 kg
```

Isso gera resumos como:

```txt
summary_by_weight_class.csv
summary_by_model_mode_weight_class.csv
summary_by_processing_mode_weight_class.csv
```

Esses arquivos ajudam a separar dois problemas diferentes: erro percentual alto em itens muito leves e erro absoluto alto em itens mais pesados. Para peso, olhe junto para `std_percent_error` e `std_absolute_error_g`.

Use também a coluna `sample_count`: uma faixa com poucos produtos é útil como indício, mas ainda não sustenta uma conclusão robusta.

### Erro geral incluindo peso

A coluna:

```txt
mean_abs_percent_error_all
```

inclui:

```txt
comprimento, largura, altura, peso
```

Ela é útil, mas deve ser lida com cuidado. Produtos muito leves podem ter erro percentual de peso muito alto mesmo quando o erro absoluto em gramas é pequeno.

## Taxa de acerto de intervalo

O modelo retorna faixas `min` e `max`, não apenas uma estimativa pontual. A avaliação considera uma medida como acertada quando o valor real cai dentro do intervalo retornado.

Para dimensões:

```txt
dimension_interval_hits
```

conta quantas das três dimensões ficaram dentro do intervalo.

```txt
dimension_interval_hit_rate = dimension_interval_hits / 3
```

Exemplo: se comprimento e altura acertaram, mas largura errou:

```txt
dimension_interval_hit_rate = 2 / 3 = 0.6667
```

Para todas as medidas, incluindo peso:

```txt
all_interval_hit_rate = acertos / 4
```

A coluna:

```txt
all_interval_hits
```

é mais rígida: ela só fica `True` quando todas as quatro medidas estão dentro do intervalo. Os gráficos principais usam taxa parcial, não esse critério tudo-ou-nada.

## Peso

Peso é analisado separadamente porque costuma ser mais difícil de inferir pela imagem. Além disso, o erro percentual pode distorcer a leitura em produtos leves.

Exemplo: se um produto pesa `34g` e o modelo estima `100g`, o erro absoluto é `66g`, mas o erro percentual passa de `190%`.

Por isso a avaliação também calcula:

```txt
peso_absolute_error_grams
peso_error_within_25g
peso_error_within_50g
peso_error_within_100g
peso_error_within_20_percent
```

Na análise, os resumos incluem:

```txt
weight_mean_absolute_error_g
weight_median_absolute_error_g
weight_within_25g_rate
weight_within_50g_rate
weight_within_100g_rate
weight_within_20_percent_rate
```

Para logística, muitas vezes `erro em gramas` é mais informativo que `erro percentual`.

## Custo

O runner pode receber preço por 1 milhão de tokens via flags:

```bash
python3 tests/run_tests.py \
  --input-price-per-1m 0.00 \
  --output-price-per-1m 0.00
```

Ou por variáveis de ambiente:

```bash
export OPENAI_INPUT_PRICE_PER_1M=0.00
export OPENAI_OUTPUT_PRICE_PER_1M=0.00
python3 tests/run_tests.py
```

Mesmo assim, a análise recalcula custos com uma tabela fixa em `tests/analyze_results.py`. Isso permite analisar CSVs antigos mesmo quando o runner foi executado com custo zerado.

A fórmula usada é:

```txt
input_cost_usd = input_tokens / 1_000_000 * input_price_per_1m
output_cost_usd = output_tokens / 1_000_000 * output_price_per_1m
calculated_cost_usd = input_cost_usd + output_cost_usd
```

Os resumos incluem custo médio por chamada e custo total por grupo.

## Custo-benefício

O score principal de custo-benefício usa apenas dimensões:

```txt
cost_benefit_score_dimensions = mean_dimension_interval_hit_rate / mean_calculated_cost_usd
```

Maior é melhor, mas essa métrica não deve ser lida sozinha. Modelos muito baratos podem ter score alto mesmo com qualidade insuficiente.

Use o score junto com:

```txt
mean_abs_percent_error_dimensions
mean_dimension_interval_hit_rate
weight_mean_absolute_error_g
success_rate
mean_calculated_cost_usd
```

Também existe um score incluindo peso:

```txt
cost_benefit_score_all = mean_all_interval_hit_rate / mean_calculated_cost_usd
```

## Rodar avaliação

Rodada padrão, usando os modelos e modos configurados em `run_tests.py`:

```bash
python3 tests/run_tests.py
```

Rodada menor:

```bash
python3 tests/run_tests.py \
  --samples livro \
  --models gpt-5.4-mini \
  --processing-modes resized \
  --repetitions 1
```

Rodada comparando apenas modelos e modos específicos:

```bash
python3 tests/run_tests.py \
  --models gpt-5.4 gpt-5.4-mini \
  --processing-modes resized quantized \
  --repetitions 3
```

Rodada comparando 1 imagem contra 2 imagens, mantendo apenas o `gpt-5.4-mini`:

```bash
python3 tests/run_tests.py \
  --models gpt-5.4-mini \
  --processing-modes resized quantized \
  --image-counts 1 2 \
  --repetitions 5
```


Ver plano sem chamar a API:

```bash
python3 tests/run_tests.py --dry-run
```

Parar no primeiro erro:

```bash
python3 tests/run_tests.py --stop-on-error
```

## Analisar resultados

Depois de gerar um CSV:

```bash
python3 tests/analyze_results.py tests/results/evaluation_YYYYMMDD_HHMMSS.csv
```

Se o caminho for omitido, o script usa o `evaluation_*.csv` mais recente em `tests/results/`:

```bash
python3 tests/analyze_results.py
```

O script gera uma pasta:

```txt
tests/results/analysis_<nome_do_csv>/
```

## Arquivos gerados

A análise gera resumos como:

```txt
summary_by_model.csv
summary_by_model_mode.csv
summary_by_processing_mode.csv
summary_by_sample_model_mode.csv
summary_by_model_mode_measure.csv
summary_by_measure.csv
summary_by_model_mode_weight.csv
summary_by_weight.csv
summary_by_weight_class.csv
summary_by_model_mode_weight_class.csv
summary_by_processing_mode_weight_class.csv
summary_by_model_mode_image_count.csv
summary_by_image_count.csv
summary_by_processing_mode_image_count.csv
summary_by_sample_model_mode_image_count.csv
summary_by_model_mode_image_count_measure.csv
summary_delta_2_vs_1_images_by_model_mode.csv
summary_delta_2_vs_1_images_by_model_mode_measure.csv
report.md
```

Também gera gráficos em SVG e PNG de alta resolução. O SVG é melhor para edição/vetor; o PNG é mais prático para colar direto em slides. Exemplos:

```txt
mean_abs_percent_error_dimensions_by_model_mode.svg
mean_abs_percent_error_all_by_model_mode.svg
std_abs_percent_error_dimensions_by_model_mode.svg
std_abs_percent_error_all_by_model_mode.svg
dimension_interval_hit_rate_by_model_mode.svg
interval_hit_rate_by_model_mode.svg
mean_percent_error_by_measure.svg
std_percent_error_by_measure.svg
mean_percent_error_by_measure_heatmap.svg
std_percent_error_by_measure_heatmap.svg
interval_hit_rate_by_measure_heatmap.svg
weight_mean_percent_error_by_weight_class.svg
weight_std_percent_error_by_weight_class.svg
weight_std_absolute_error_g_by_weight_class.svg
heatmap_weight_std_percent_error_by_model_mode_weight_class.svg
heatmap_weight_std_absolute_error_g_by_model_mode_weight_class.svg
heatmap_weight_mean_percent_error_by_model_mode_weight_class.svg
heatmap_weight_interval_hit_by_model_mode_weight_class.svg
heatmap_error_dimensions_by_model_mode.svg
heatmap_error_including_weight_by_model_mode.svg
heatmap_std_error_dimensions_by_model_mode.svg
heatmap_std_error_including_weight_by_model_mode.svg
heatmap_interval_hit_dimensions_by_model_mode.svg
heatmap_interval_hit_including_weight_by_model_mode.svg
heatmap_total_cost_by_model_mode.svg
heatmap_error_dimensions_by_model_mode_image_count.svg
heatmap_interval_hit_dimensions_by_model_mode_image_count.svg
heatmap_height_error_by_model_mode_image_count.svg
heatmap_mean_tokens_by_model_mode_image_count.svg
heatmap_mean_cost_by_model_mode_image_count.svg
heatmap_delta_error_dimensions_2_vs_1_images.svg
heatmap_delta_height_error_2_vs_1_images.svg
heatmap_delta_interval_hit_dimensions_2_vs_1_images.svg
heatmap_delta_tokens_2_vs_1_images.svg
heatmap_delta_cost_2_vs_1_images.svg
heatmap_delta_error_by_measure_2_vs_1_images.svg
heatmap_delta_interval_hit_by_measure_2_vs_1_images.svg
weight_absolute_error_grams_by_model_mode.svg
weight_within_25g_rate_by_model_mode.svg
weight_within_50g_rate_by_model_mode.svg
weight_within_100g_rate_by_model_mode.svg
weight_within_20_percent_rate_by_model_mode.svg
cost_benefit_score_by_model_mode.svg
cost_benefit_scatter_by_model_mode.svg
```

## Como interpretar

Use `summary_by_model_mode.csv` para escolher modelo e modo de imagem.

Priorize:

1. menor `mean_abs_percent_error_dimensions`;
2. maior `mean_dimension_interval_hit_rate`;
3. menor `mean_calculated_cost_usd`;
4. peso aceitável em `weight_mean_absolute_error_g` e nas tolerâncias em gramas;
5. estabilidade do peso por faixa em `summary_by_weight_class.csv`;
6. `success_rate` próximo de 1.

Use `summary_by_sample_model_mode.csv` para descobrir produtos problemáticos. Se um produto específico puxa a média para cima, ele pode indicar uma categoria que precisa de tratamento especial.

Use os heatmaps para comparar rápido modelos e modos de imagem. Para erro, desvio padrão e custo, menor é melhor. Para taxa de acerto, maior é melhor.

Para a comparação de quantidade de imagens, use `summary_by_model_mode_image_count.csv` para ver os valores absolutos de 1 e 2 imagens. Use `summary_delta_2_vs_1_images_by_model_mode.csv` para ver a mudança direta. Nessa tabela, deltas são calculados como `2 imagens - 1 imagem`: em erro, custo e tokens, negativo é melhor; em taxa de acerto, positivo é melhor.

## Limitações

A avaliação mede o comportamento nos samples existentes. Mais repetições ajudam a medir estabilidade, mas não substituem variedade de produtos.

Para uma conclusão mais robusta, prefira aumentar a quantidade e diversidade dos samples em vez de repetir muitas vezes os mesmos itens.

Categorias importantes para cobrir:

- itens muito leves, como cabos, adaptadores e cartuchos;
- itens pequenos rígidos, como mouse, carregador e controle;
- itens planos, como livros, jogos e cadernos;
- caixas pequenas, como cosméticos e medicamentos;
- itens densos, como ferramentas e peças metálicas;
- itens volumosos leves, como embalagens grandes e produtos macios.

## Dependências

A execução da avaliação usa o projeto principal e `Pillow`. A análise usa `pandas` e `matplotlib`.

Instale tudo com:

```bash
pip install -r requirements.txt
```
