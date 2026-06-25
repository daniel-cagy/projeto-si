#!/usr/bin/env python3

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any
from product_estimator.schema import MEASUREMENT_SCHEMA
from product_estimator.prompt import SYSTEM_PROMPT
from product_estimator.post_processing import get_metricas_logisticas, validation, get_incertezas
from product_estimator.constants import Objeto

from openai import OpenAI


def image_to_data_url(image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

    mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


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
        result["incertezas"] = get_incertezas(result["resposta"]["produto"])
    else:
        result["metricas_logisticas"] = {}
        result["incertezas"] = {}

    return result
