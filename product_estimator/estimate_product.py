#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from product_estimator.schema import MEASUREMENT_SCHEMA
from product_estimator.prompt import SYSTEM_PROMPT
from product_estimator.post_processing import get_metricas_logisticas, validation
from product_estimator.constants import Objeto
from product_estimator.image_processing import image_to_data_url

from openai import OpenAI



def estimate_product(image_path: Path, product_description: str, model: str) -> dict[str, Any]:
    client = OpenAI()

    response = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Descrição textual do produto:\n"
                            f"{product_description}\n\n"
                            "Analise também a imagem anexada."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": image_to_data_url(image_path),
                    },
                ],
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                **MEASUREMENT_SCHEMA,
            }
        },
    )

    result = {}
    result["resposta"] = json.loads(response.output_text)
    result["validacao"] = validation(result["resposta"])

    if result["validacao"]["status"]:
        produto = Objeto.from_dict(result["resposta"]["produto"])
        result["metricas_logisticas"] = get_metricas_logisticas(produto)
    else:
        result["metricas_logisticas"] = {}

    return result
