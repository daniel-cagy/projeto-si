# Estimador de Produtos com IA

Projeto Python para estimar dimensões e peso de produtos a partir de uma imagem
e uma descrição textual, usando a OpenAI Responses API.

A imagem deve representar o item que será medido. Quando o produto estiver na
embalagem, as estimativas consideram o conjunto embalado exatamente como aparece
na foto.

O sistema retorna um JSON estruturado com:

- identificação provável do produto;
- descrição resumida do que foi observado;
- `produto`, contendo dimensões estimadas em centímetros e peso estimado em quilogramas do item fotografado;
- nível de confiança binário: `alto` ou `baixo`;
- `validacao`, adicionada no pós-processamento, com `status`, `erros` e `alertas`;
- `metricas_logisticas`, calculadas localmente a partir da estimativa.

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY="sua_chave_aqui"
```

Opcionalmente, defina o modelo padrão:

```bash
export OPENAI_MODEL="gpt-5.5"
```

## Uso

### Interface web

Inicie o backend FastAPI:

```bash
python3 -m uvicorn api:app --reload
```

Abra a interface em:

```text
http://localhost:8000
```

A documentação interativa da API fica em:

```text
http://localhost:8000/docs
```

### CLI

```bash
python cli.py ./imagem.jpg "Caixa de papelão com notebook Dell, modelo Inspiron 15, embalagem original lacrada"
```

Para salvar o JSON em arquivo:

```bash
python cli.py ./imagem.jpg "Caixa de papelão com notebook Dell, modelo Inspiron 15, embalagem original lacrada" --output resultado.json
```

Para informar outro modelo na execução:

```bash
python cli.py ./imagem.jpg "Produto de exemplo" --model gpt-5.2
```

## Estrutura

```text
.
├── api.py
├── cli.py
├── index.html
├── static/
│   ├── app.js
│   └── styles.css
├── product_estimator/
│   ├── constants.py
│   ├── estimate_product.py
│   ├── image_processing.py
│   ├── post_processing.py
│   ├── prompt.py
│   └── schema.py
├── requirements.txt
└── README.md
```

`api.py` expõe o backend FastAPI e serve a interface web.

`index.html` contém a estrutura da interface web.

`static/styles.css` contém os estilos da interface.

`static/app.js` envia imagem e descrição para o endpoint `/estimate` e renderiza o resultado.

`cli.py` é o ponto de entrada por terminal.

`product_estimator/estimate_product.py` contém a integração com a OpenAI e pode
ser reaproveitado por uma API web.

`product_estimator/image_processing.py` redimensiona e comprime a imagem antes da chamada ao modelo.

`product_estimator/constants.py` guarda constantes operacionais, como o fator de cubagem.

`product_estimator/post_processing.py` adiciona validação e métricas logísticas à resposta.

`product_estimator/prompt.py` guarda o prompt de sistema.

`product_estimator/schema.py` guarda o schema JSON esperado da resposta do modelo, antes do pós-processamento.

## Observação

As medidas retornadas são estimativas. Sem escala explícita na imagem ou medidas
na descrição, o resultado deve ser tratado como aproximação para triagem ou MVP,
não como medição exata.
