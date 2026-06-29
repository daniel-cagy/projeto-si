#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from product_estimator.schema import MEASUREMENT_SCHEMA
from product_estimator.prompt import SYSTEM_PROMPT
from product_estimator.post_processing import get_metricas_logisticas, validation
from product_estimator.image_processing import DEFAULT_IMAGE_PROCESSING_MODE, image_to_data_url
from product_estimator.constants import Objeto, KNOWN_MEASURE_LABELS, KNOWN_MEASURE_UNITS

from openai import OpenAI



def parse_response_json(response: Any) -> dict[str, Any]:
    raw_output = getattr(response, "output_text", "") or ""
    response_id = getattr(response, "id", None)
    response_status = getattr(response, "status", None)
    incomplete_details = getattr(response, "incomplete_details", None)

    if not raw_output.strip():
        raise ValueError(
            "Resposta vazia da OpenAI. "
            f"response_id={response_id}; "
            f"status={response_status}; "
            f"incomplete_details={incomplete_details}"
        )

    try:
        return json.loads(raw_output)
    except json.JSONDecodeError as exc:
        output_preview = raw_output[:500].replace("\n", " ")
        raise ValueError(
            "Resposta da OpenAI não veio como JSON válido. "
            f"response_id={response_id}; "
            f"status={response_status}; "
            f"incomplete_details={incomplete_details}; "
            f"output_preview={output_preview!r}"
        ) from exc


def format_known_measures(known_measures: dict[str, float] | None) -> str:
    if not known_measures:
        return ""

    lines = []
    for measure_type in ("comprimento", "largura", "altura", "peso"):
        if measure_type in known_measures:
            label = KNOWN_MEASURE_LABELS[measure_type]
            unit = KNOWN_MEASURE_UNITS[measure_type]
            lines.append(f"- {label}: {known_measures[measure_type]:g} {unit}")

    if not lines:
        return ""

    return (
        "Medidas conhecidas informadas pelo usuário:\n"
        + "\n".join(lines)
        + "\nUse essas medidas como referência prioritária se forem compatíveis com a imagem."
    )



def estimate_product(
    image_path: Path,
    product_description: str,
    model: str,
    known_measures: dict[str, float] | None = None,
    image_processing_mode: str = DEFAULT_IMAGE_PROCESSING_MODE,
) -> dict[str, Any]:
    client = OpenAI()
    known_measures_text = format_known_measures(known_measures)

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
                            f"{known_measures_text}\n\n"
                            "Analise também a imagem anexada."
                        ),
                    },
                    {
                        "type": "input_image",
                        "image_url": image_to_data_url(image_path, image_processing_mode),
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
    result["resposta"] = parse_response_json(response)
    result["openai_response_id"] = getattr(response, "id", None)
    result["openai_response_status"] = getattr(response, "status", None)
    result["medidas_conhecidas_informadas"] = known_measures or {}
    result["modo_processamento_imagem"] = image_processing_mode
    result["validacao"] = validation(result["resposta"], known_measures)

    if result["validacao"]["status"]:
        produto = Objeto.from_dict(result["resposta"]["produto"])
        result["metricas_logisticas"] = get_metricas_logisticas(produto)
    else:
        result["metricas_logisticas"] = {}

    usage = getattr(response, "usage", None)
    if usage:
        result["uso_de_tokens"] = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "total_tokens": usage.total_tokens,
        }
    else:
        result["uso_de_tokens"] = {}

    return result
