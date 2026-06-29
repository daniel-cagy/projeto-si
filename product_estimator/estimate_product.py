#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from product_estimator.schema import MEASUREMENT_SCHEMA
from product_estimator.prompt import SYSTEM_PROMPT
from product_estimator.post_processing import get_metricas_logisticas, validation
from product_estimator.image_processing import DEFAULT_IMAGE_PROCESSING_MODE, image_to_data_url
from product_estimator.constants import FATOR_CUBAGEM, Objeto, KNOWN_MEASURE_LABELS, KNOWN_MEASURE_UNITS

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


def normalize_image_paths(image_path: Path | None, image_paths: list[Path] | None) -> list[Path]:
    paths = image_paths if image_paths is not None else [image_path]
    valid_paths = [path for path in paths if path is not None]

    if not valid_paths:
        raise ValueError("Ao menos uma imagem precisa ser informada.")

    return valid_paths


def get_image_instruction(image_count: int) -> str:
    if image_count == 1:
        return "Analise também a imagem anexada."

    return (
        "Analise também as imagens anexadas. "
        "Todas mostram o mesmo produto por ângulos diferentes. "
        "Use as imagens adicionais para melhorar a estimativa de proporções, "
        "especialmente altura, profundidade e partes parcialmente ocultas."
    )


def build_user_content(
    product_description: str,
    known_measures_text: str,
    image_paths: list[Path],
    image_processing_mode: str,
) -> list[dict[str, Any]]:
    content = [
        {
            "type": "input_text",
            "text": (
                "Descrição textual do produto:\n"
                f"{product_description}\n\n"
                f"{known_measures_text}\n\n"
                f"{get_image_instruction(len(image_paths))}"
            ),
        }
    ]

    for image_path in image_paths:
        content.append({
            "type": "input_image",
            "image_url": image_to_data_url(image_path, image_processing_mode),
        })

    return content



def estimate_product(
    image_path: Path | None,
    product_description: str,
    model: str,
    known_measures: dict[str, float] | None = None,
    image_processing_mode: str = DEFAULT_IMAGE_PROCESSING_MODE,
    cubage_factor: float = FATOR_CUBAGEM,
    image_paths: list[Path] | None = None,
) -> dict[str, Any]:
    client = OpenAI()
    known_measures_text = format_known_measures(known_measures)
    normalized_image_paths = normalize_image_paths(image_path, image_paths)

    response = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=[
            {
                "role": "user",
                "content": build_user_content(
                    product_description=product_description,
                    known_measures_text=known_measures_text,
                    image_paths=normalized_image_paths,
                    image_processing_mode=image_processing_mode,
                ),
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
    result["modelo_utilizado"] = model
    result["fator_cubagem_utilizado"] = cubage_factor
    result["medidas_conhecidas_informadas"] = known_measures or {}
    result["modo_processamento_imagem"] = image_processing_mode
    result["quantidade_imagens"] = len(normalized_image_paths)
    result["multiplas_imagens_utilizadas"] = len(normalized_image_paths) > 1
    result["validacao"] = validation(result["resposta"], known_measures)

    if result["validacao"]["status"]:
        produto = Objeto.from_dict(result["resposta"]["produto"])
        result["metricas_logisticas"] = get_metricas_logisticas(produto, cubage_factor)
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
