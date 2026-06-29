from __future__ import annotations

import copy
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from product_estimator.constants import FATOR_CUBAGEM
from product_estimator.estimate_product import estimate_product
from product_estimator.image_processing import DEFAULT_IMAGE_PROCESSING_MODE, IMAGE_PROCESSING_MODES
from product_estimator.post_processing import get_metricas_logisticas, get_objeto_ajustado, get_produto_ajustado, validation


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
KNOWN_MEASURE_TYPES = {"comprimento", "largura", "altura", "peso"}
MANUAL_CORRECTION_TYPES = KNOWN_MEASURE_TYPES


def parse_cubage_factor(raw_cubage_factor: str) -> float:
    try:
        cubage_factor = float(raw_cubage_factor)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="O fator de cubagem precisa ser um número válido.",
        ) from exc

    if not math.isfinite(cubage_factor) or cubage_factor <= 0:
        raise HTTPException(
            status_code=400,
            detail="O fator de cubagem precisa ser um número finito maior que zero.",
        )

    return cubage_factor


def parse_manual_corrections(raw_corrections: object) -> dict[str, float]:
    if raw_corrections is None:
        return {}

    if not isinstance(raw_corrections, dict):
        raise HTTPException(
            status_code=400,
            detail="As correções manuais precisam ser enviadas como um objeto.",
        )

    corrections: dict[str, float] = {}
    for correction_type, correction_value in raw_corrections.items():
        if correction_type not in MANUAL_CORRECTION_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Tipo de correção manual inválido.",
            )

        if isinstance(correction_value, bool) or not isinstance(correction_value, (int, float)):
            raise HTTPException(
                status_code=400,
                detail="Valor de correção manual inválido.",
            )

        if not math.isfinite(correction_value) or correction_value <= 0:
            raise HTTPException(
                status_code=400,
                detail="Correções manuais precisam ser números finitos maiores que zero.",
            )

        corrections[correction_type] = float(correction_value)

    return corrections


def get_payload_cubage_factor(payload: dict[str, Any]) -> float:
    raw_factor = payload.get("fator_cubagem_utilizado")
    if raw_factor is None:
        raw_factor = payload.get("metricas_logisticas", {}).get("fator_cubagem", FATOR_CUBAGEM)

    return parse_cubage_factor(str(raw_factor))


def parse_known_measures(raw_known_measures: str) -> dict[str, float]:
    if not raw_known_measures.strip():
        return {}

    try:
        known_measures = json.loads(raw_known_measures)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail="As medidas conhecidas precisam estar em JSON válido.",
        ) from exc

    if not isinstance(known_measures, list):
        raise HTTPException(
            status_code=400,
            detail="As medidas conhecidas precisam ser enviadas como uma lista.",
        )

    parsed_measures: dict[str, float] = {}

    for item in known_measures:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=400,
                detail="Cada medida conhecida precisa ser um objeto.",
            )

        measure_type = item.get("tipo")
        measure_value = item.get("valor")

        if measure_type not in KNOWN_MEASURE_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Tipo de medida conhecida inválido.",
            )

        if isinstance(measure_value, bool) or not isinstance(measure_value, (int, float)):
            raise HTTPException(
                status_code=400,
                detail="Valor de medida conhecida inválido.",
            )

        if measure_value <= 0:
            raise HTTPException(
                status_code=400,
                detail="Medidas conhecidas precisam ser maiores que zero.",
            )

        parsed_measures[measure_type] = float(measure_value)

    return parsed_measures

app = FastAPI(
    title="Cubage AI",
    description="API para estimar dimensões, peso e métricas logísticas de produtos embalados.",
    version="0.1.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse("index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/recalculate")
def recalculate(request: dict[str, Any] = Body(...)) -> dict[str, Any]:
    payload = request.get("payload")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload original inválido.")

    resposta = payload.get("resposta")
    if not isinstance(resposta, dict):
        raise HTTPException(status_code=400, detail="Payload sem resposta válida para recalcular.")

    corrections = parse_manual_corrections(request.get("correcoes_usuario", {}))
    validation_result = validation(resposta, payload.get("medidas_conhecidas_informadas"))
    if not validation_result["status"]:
        raise HTTPException(status_code=400, detail="Payload original não passou na validação.")

    cubage_factor = get_payload_cubage_factor(payload)
    adjusted_object = get_objeto_ajustado(resposta, corrections)
    adjusted_product = get_produto_ajustado(resposta, corrections)

    recalculated_payload = copy.deepcopy(payload)
    if "metricas_logisticas_originais" not in recalculated_payload:
        recalculated_payload["metricas_logisticas_originais"] = payload.get("metricas_logisticas", {})

    recalculated_payload["correcoes_usuario"] = corrections
    recalculated_payload["produto_ajustado"] = adjusted_product
    recalculated_payload["metricas_logisticas"] = get_metricas_logisticas(adjusted_object, cubage_factor)
    recalculated_payload["recalculado_localmente"] = True
    return recalculated_payload


@app.post("/estimate")
async def estimate(
    image: UploadFile = File(...),
    description: str = Form(...),
    known_measures: str = Form("[]"),
    image_processing_mode: str = Form(DEFAULT_IMAGE_PROCESSING_MODE),
    model: str = Form(DEFAULT_MODEL),
    cubage_factor: str = Form(str(FATOR_CUBAGEM)),
) -> dict[str, Any]:
    if not description.strip():
        raise HTTPException(status_code=400, detail="A descrição do produto é obrigatória.")

    model_name = model.strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="O modelo de IA é obrigatório.")

    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="O arquivo enviado precisa ser uma imagem.")

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="A imagem enviada está vazia.")

    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="A imagem deve ter no máximo 10 MB.")

    parsed_known_measures = parse_known_measures(known_measures)
    parsed_cubage_factor = parse_cubage_factor(cubage_factor)
    if image_processing_mode not in IMAGE_PROCESSING_MODES:
        raise HTTPException(status_code=400, detail="Modo de processamento de imagem inválido.")

    suffix = Path(image.filename or "").suffix or ".jpg"
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(image_bytes)

        return estimate_product(
            image_path=temp_path,
            product_description=description.strip(),
            model=model_name,
            known_measures=parsed_known_measures,
            image_processing_mode=image_processing_mode,
            cubage_factor=parsed_cubage_factor,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Não foi possível estimar o produto: {exc}",
        ) from exc
    finally:
        if temp_path:
            temp_path.unlink(missing_ok=True)
