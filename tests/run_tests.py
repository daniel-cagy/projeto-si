#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from product_estimator.estimate_product import estimate_product
from product_estimator.image_processing import (
    IMAGE_PROCESSING_MODE_ORIGINAL,
    IMAGE_PROCESSING_MODE_QUANTIZED,
    IMAGE_PROCESSING_MODE_RESIZED,
    process_image,
)


MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-5.5",
]

IMAGE_PROCESSING_MODES = [
    IMAGE_PROCESSING_MODE_ORIGINAL,
    IMAGE_PROCESSING_MODE_RESIZED,
    IMAGE_PROCESSING_MODE_QUANTIZED,
]

MEASURES = ("comprimento", "largura", "altura", "peso")
DIMENSION_MEASURES = ("comprimento", "largura", "altura")
WEIGHT_THRESHOLDS_GRAMS = (25, 50, 100)
DEFAULT_REPETITIONS = 3

FIELDNAMES = [
    "executed_at",
    "sample_id",
    "sample_file",
    "image_file",
    "model",
    "image_processing_mode",
    "repetition",
    "success",
    "error_type",
    "error_message",
    "duration_seconds",
    "image_preprocessing_seconds",
    "produto_identificado",
    "descricao_resumida",
    "nivel_confianca",
    "validation_status",
    "validation_errors",
    "validation_alerts",
    "dimension_interval_hits",
    "dimension_interval_hit_rate",
    "all_interval_hits",
    "all_interval_hit_rate",
    "mean_abs_percent_error_dimensions",
    "mean_abs_percent_error_all",
    "max_abs_percent_error_all",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "estimated_cost",
    "original_mime_type",
    "final_mime_type",
    "original_width",
    "original_height",
    "final_width",
    "final_height",
    "original_bytes",
    "final_bytes",
    "original_megapixels",
    "final_megapixels",
    "byte_reduction_percent",
    "final_to_original_size_ratio",
    "final_image_mode",
    "final_color_count",
    "volume_produto_cm3",
    "densidade_produto_kg_cm3",
    "peso_cubado_kg",
    "peso_cobravel_estimado_kg",
    "fator_cubagem",
    "known_measures_json",
    "comprimento_source_dimension",
    "largura_source_dimension",
    "altura_source_dimension",
    "peso_absolute_error_grams",
    "peso_error_within_25g",
    "peso_error_within_50g",
    "peso_error_within_100g",
    "peso_error_within_20_percent",
]

for measure in MEASURES:
    FIELDNAMES.extend([
        f"{measure}_expected",
        f"{measure}_min",
        f"{measure}_estimate",
        f"{measure}_max",
        f"{measure}_signed_error",
        f"{measure}_absolute_error",
        f"{measure}_percent_error",
        f"{measure}_interval_hit",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa avaliação dos modelos e modos de processamento de imagem."
    )
    parser.add_argument(
        "--samples-dir",
        type=Path,
        default=ROOT_DIR / "tests" / "samples",
        help="Diretório com arquivos .json dos casos de teste.",
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=ROOT_DIR / "tests" / "images",
        help="Diretório com as imagens referenciadas pelos samples.",
    )
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=ROOT_DIR / "tests" / "results",
        help="Diretório onde o CSV será gravado.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Caminho do CSV de saída. Se omitido, cria arquivo em tests/results.",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=DEFAULT_REPETITIONS,
        help=f"Número de repetições por produto/modelo/modo. Padrão: {DEFAULT_REPETITIONS}.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="Lista de modelos para testar. Se omitido, usa MODELS.",
    )
    parser.add_argument(
        "--processing-modes",
        nargs="+",
        choices=IMAGE_PROCESSING_MODES,
        default=IMAGE_PROCESSING_MODES,
        help="Modos de processamento de imagem a testar.",
    )
    parser.add_argument(
        "--samples",
        nargs="+",
        default=None,
        help="IDs dos samples a testar, sem .json. Se omitido, usa todos.",
    )
    parser.add_argument(
        "--input-price-per-1m",
        type=float,
        default=float(os.getenv("OPENAI_INPUT_PRICE_PER_1M", "0")),
        help="Preço de input por 1M tokens. Também pode usar OPENAI_INPUT_PRICE_PER_1M.",
    )
    parser.add_argument(
        "--output-price-per-1m",
        type=float,
        default=float(os.getenv("OPENAI_OUTPUT_PRICE_PER_1M", "0")),
        help="Preço de output por 1M tokens. Também pode usar OPENAI_OUTPUT_PRICE_PER_1M.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o plano de execução sem chamar a API.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Interrompe a avaliação no primeiro erro.",
    )
    return parser.parse_args()


def resolve_output_path(args: argparse.Namespace) -> Path:
    if args.output:
        return args.output

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return args.results_dir / f"evaluation_{timestamp}.csv"


def load_samples(samples_dir: Path, selected_samples: list[str] | None) -> list[dict[str, Any]]:
    sample_paths = sorted(samples_dir.glob("*.json"))
    if selected_samples:
        selected = set(selected_samples)
        sample_paths = [path for path in sample_paths if path.stem in selected]

    samples = []
    for sample_path in sample_paths:
        with sample_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        validate_sample(sample_path, data)
        data["id"] = sample_path.stem
        data["sample_file"] = str(sample_path)
        samples.append(data)

    return samples


def validate_sample(sample_path: Path, data: dict[str, Any]) -> None:
    required_keys = {"imagem", "descricao", "resultado_esperado"}
    missing_keys = required_keys - data.keys()
    if missing_keys:
        raise ValueError(f"{sample_path} faltando chaves: {', '.join(sorted(missing_keys))}")

    expected = data["resultado_esperado"]
    if not isinstance(expected, dict):
        raise ValueError(f"{sample_path}: 'resultado_esperado' deve ser objeto.")

    for measure in MEASURES:
        if measure not in expected:
            raise ValueError(f"{sample_path}: resultado_esperado sem '{measure}'.")
        if isinstance(expected[measure], bool) or not isinstance(expected[measure], (int, float)):
            raise ValueError(f"{sample_path}: resultado_esperado.{measure} deve ser número.")


def resolve_image_path(images_dir: Path, image_name: str) -> Path:
    image_path = Path(image_name)
    if image_path.is_absolute():
        return image_path
    return images_dir / image_path


def get_image_metadata(image_path: Path, processing_mode: str) -> dict[str, Any]:
    started_at = time.perf_counter()
    original_bytes = image_path.read_bytes()

    with Image.open(image_path) as original_image:
        original_width, original_height = original_image.size
        original_mime_type = Image.MIME.get(original_image.format, "image/jpeg")

    final_bytes, final_mime_type = process_image(image_path, processing_mode)
    preprocessing_seconds = time.perf_counter() - started_at

    with Image.open(BytesIO(final_bytes)) as final_image:
        final_width, final_height = final_image.size
        final_image_mode = final_image.mode
        colors = final_image.getcolors(maxcolors=300) if final_image.mode == "P" else None

    original_size = len(original_bytes)
    final_size = len(final_bytes)

    return {
        "image_preprocessing_seconds": preprocessing_seconds,
        "original_mime_type": original_mime_type,
        "final_mime_type": final_mime_type,
        "original_width": original_width,
        "original_height": original_height,
        "final_width": final_width,
        "final_height": final_height,
        "original_bytes": original_size,
        "final_bytes": final_size,
        "original_megapixels": (original_width * original_height) / 1_000_000,
        "final_megapixels": (final_width * final_height) / 1_000_000,
        "byte_reduction_percent": calculate_reduction_percent(original_size, final_size),
        "final_to_original_size_ratio": final_size / original_size if original_size else "",
        "final_image_mode": final_image_mode,
        "final_color_count": len(colors) if colors else "",
    }


def calculate_reduction_percent(original_size: int, final_size: int) -> float | str:
    if not original_size:
        return ""
    return (1 - final_size / original_size) * 100


def canonicalize_expected_dimensions(expected: dict[str, Any]) -> dict[str, Any]:
    dimensions = [(measure, expected[measure]) for measure in DIMENSION_MEASURES]
    dimensions.sort(key=lambda item: item[1], reverse=True)

    canonical_expected = {
        canonical_measure: value
        for canonical_measure, (_, value) in zip(DIMENSION_MEASURES, dimensions)
    }
    canonical_expected["peso"] = expected["peso"]
    return canonical_expected


def canonicalize_dimension_ranges(result: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    dimensions = result.get("resposta", {}).get("produto", {}).get("dimensoes_estimadas_cm", {})
    ranges = []

    for measure in DIMENSION_MEASURES:
        range_data = dimensions.get(measure, {})
        estimate = range_data.get("estimativa")
        sort_value = estimate if is_number(estimate) else float("-inf")
        ranges.append((measure, range_data, sort_value))

    ranges.sort(key=lambda item: item[2], reverse=True)

    canonical_ranges = {}
    source_dimensions = {}
    for canonical_measure, (source_measure, range_data, _) in zip(DIMENSION_MEASURES, ranges):
        canonical_ranges[canonical_measure] = range_data
        source_dimensions[canonical_measure] = source_measure

    return canonical_ranges, source_dimensions


def get_range(
    result: dict[str, Any],
    measure: str,
    canonical_dimension_ranges: dict[str, Any] | None = None,
) -> dict[str, Any]:
    produto = result.get("resposta", {}).get("produto", {})
    if measure == "peso":
        return produto.get("peso_estimado_kg", {})
    if canonical_dimension_ranges is not None:
        return canonical_dimension_ranges.get(measure, {})
    return produto.get("dimensoes_estimadas_cm", {}).get(measure, {})


def calculate_measure_metrics(expected_value: float, range_data: dict[str, Any]) -> dict[str, Any]:
    min_value = range_data.get("min", "")
    max_value = range_data.get("max", "")
    estimate = range_data.get("estimativa", "")

    if not all(is_number(value) for value in (min_value, max_value, estimate)):
        return {
            "min": min_value,
            "max": max_value,
            "estimate": estimate,
            "signed_error": "",
            "absolute_error": "",
            "percent_error": "",
            "interval_hit": False,
        }

    signed_error = estimate - expected_value
    absolute_error = abs(signed_error)
    percent_error = (absolute_error / expected_value) * 100 if expected_value else ""
    interval_hit = min_value <= expected_value <= max_value

    return {
        "min": min_value,
        "max": max_value,
        "estimate": estimate,
        "signed_error": signed_error,
        "absolute_error": absolute_error,
        "percent_error": percent_error,
        "interval_hit": interval_hit,
    }


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def average(values: list[float]) -> float | str:
    if not values:
        return ""
    return sum(values) / len(values)


def get_usage(result: dict[str, Any]) -> dict[str, int]:
    usage = result.get("uso_de_tokens", {}) or {}
    return {
        "input_tokens": int(usage.get("input_tokens", usage.get("input", 0)) or 0),
        "output_tokens": int(usage.get("output_tokens", usage.get("output", 0)) or 0),
        "total_tokens": int(usage.get("total_tokens", usage.get("total", 0)) or 0),
    }


def calculate_cost(input_tokens: int, output_tokens: int, input_price: float, output_price: float) -> float:
    return (input_tokens / 1_000_000 * input_price) + (output_tokens / 1_000_000 * output_price)


def serialize_list(items: list[Any]) -> str:
    return " | ".join(str(item) for item in items)


def build_success_row(
    *,
    sample: dict[str, Any],
    image_path: Path,
    model: str,
    processing_mode: str,
    repetition: int,
    duration_seconds: float,
    image_metadata: dict[str, Any],
    result: dict[str, Any],
    input_price: float,
    output_price: float,
) -> dict[str, Any]:
    resposta = result.get("resposta", {})
    validacao = result.get("validacao", {})
    metricas = result.get("metricas_logisticas", {})
    expected = canonicalize_expected_dimensions(sample["resultado_esperado"])
    canonical_dimension_ranges, source_dimensions = canonicalize_dimension_ranges(result)
    usage = get_usage(result)

    row = build_base_row(
        sample=sample,
        image_path=image_path,
        model=model,
        processing_mode=processing_mode,
        repetition=repetition,
        image_metadata=image_metadata,
    )
    row.update({
        "success": True,
        "duration_seconds": duration_seconds,
        "produto_identificado": resposta.get("produto_identificado", ""),
        "descricao_resumida": resposta.get("descricao_resumida", ""),
        "nivel_confianca": resposta.get("nivel_confianca", ""),
        "validation_status": validacao.get("status", ""),
        "validation_errors": serialize_list(validacao.get("erros", [])),
        "validation_alerts": serialize_list(validacao.get("alertas", [])),
        "input_tokens": usage["input_tokens"],
        "output_tokens": usage["output_tokens"],
        "total_tokens": usage["total_tokens"],
        "estimated_cost": calculate_cost(
            usage["input_tokens"],
            usage["output_tokens"],
            input_price,
            output_price,
        ),
        "volume_produto_cm3": metricas.get("volume_produto_cm3", ""),
        "densidade_produto_kg_cm3": metricas.get("densidade_produto_kg_cm3", ""),
        "peso_cubado_kg": metricas.get("peso_cubado_kg", ""),
        "peso_cobravel_estimado_kg": metricas.get("peso_cobravel_estimado_kg", ""),
        "fator_cubagem": metricas.get("fator_cubagem", ""),
        "known_measures_json": json.dumps(result.get("medidas_conhecidas_informadas", {}), ensure_ascii=False),
        "comprimento_source_dimension": source_dimensions.get("comprimento", ""),
        "largura_source_dimension": source_dimensions.get("largura", ""),
        "altura_source_dimension": source_dimensions.get("altura", ""),
    })

    percent_errors_all = []
    percent_errors_dimensions = []
    interval_hits_all = []
    interval_hits_dimensions = []

    for measure in MEASURES:
        metrics = calculate_measure_metrics(
            expected[measure],
            get_range(result, measure, canonical_dimension_ranges),
        )
        row[f"{measure}_expected"] = expected[measure]
        row[f"{measure}_min"] = metrics["min"]
        row[f"{measure}_estimate"] = metrics["estimate"]
        row[f"{measure}_max"] = metrics["max"]
        row[f"{measure}_signed_error"] = metrics["signed_error"]
        row[f"{measure}_absolute_error"] = metrics["absolute_error"]
        row[f"{measure}_percent_error"] = metrics["percent_error"]
        row[f"{measure}_interval_hit"] = metrics["interval_hit"]

        if measure == "peso":
            absolute_error_grams = (
                metrics["absolute_error"] * 1000
                if is_number(metrics["absolute_error"])
                else ""
            )
            row["peso_absolute_error_grams"] = absolute_error_grams
            for threshold in WEIGHT_THRESHOLDS_GRAMS:
                row[f"peso_error_within_{threshold}g"] = (
                    is_number(absolute_error_grams) and absolute_error_grams <= threshold
                )
            row["peso_error_within_20_percent"] = (
                is_number(metrics["percent_error"]) and metrics["percent_error"] <= 20
            )

        if is_number(metrics["percent_error"]):
            percent_errors_all.append(metrics["percent_error"])
            if measure in DIMENSION_MEASURES:
                percent_errors_dimensions.append(metrics["percent_error"])

        interval_hits_all.append(bool(metrics["interval_hit"]))
        if measure in DIMENSION_MEASURES:
            interval_hits_dimensions.append(bool(metrics["interval_hit"]))

    dimension_hits = sum(interval_hits_dimensions)
    all_hits = sum(interval_hits_all)

    row.update({
        "dimension_interval_hits": dimension_hits,
        "dimension_interval_hit_rate": dimension_hits / len(DIMENSION_MEASURES),
        "all_interval_hits": all(interval_hits_all),
        "all_interval_hit_rate": all_hits / len(MEASURES),
        "mean_abs_percent_error_dimensions": average(percent_errors_dimensions),
        "mean_abs_percent_error_all": average(percent_errors_all),
        "max_abs_percent_error_all": max(percent_errors_all) if percent_errors_all else "",
    })
    return row


def build_error_row(
    *,
    sample: dict[str, Any],
    image_path: Path,
    model: str,
    processing_mode: str,
    repetition: int,
    image_metadata: dict[str, Any] | None,
    error: Exception,
    duration_seconds: float = 0,
) -> dict[str, Any]:
    row = build_base_row(
        sample=sample,
        image_path=image_path,
        model=model,
        processing_mode=processing_mode,
        repetition=repetition,
        image_metadata=image_metadata or {},
    )
    row.update({
        "success": False,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "duration_seconds": duration_seconds,
    })
    return row


def build_base_row(
    *,
    sample: dict[str, Any],
    image_path: Path,
    model: str,
    processing_mode: str,
    repetition: int,
    image_metadata: dict[str, Any],
) -> dict[str, Any]:
    row = {fieldname: "" for fieldname in FIELDNAMES}
    row.update({
        "executed_at": datetime.now().isoformat(timespec="seconds"),
        "sample_id": sample["id"],
        "sample_file": sample["sample_file"],
        "image_file": str(image_path),
        "model": model,
        "image_processing_mode": processing_mode,
        "repetition": repetition,
    })
    row.update(image_metadata)
    return row


def run_evaluation(args: argparse.Namespace) -> Path:
    samples = load_samples(args.samples_dir, args.samples)
    models = args.models or MODELS
    processing_modes = args.processing_modes
    output_path = resolve_output_path(args)

    total_runs = len(samples) * len(models) * len(processing_modes) * args.repetitions
    print(f"Samples: {len(samples)}")
    print(f"Modelos: {len(models)}")
    print(f"Modos de imagem: {len(processing_modes)}")
    print(f"Repetições: {args.repetitions}")
    print(f"Total de chamadas planejadas: {total_runs}")

    if args.dry_run:
        print("Dry run: nenhuma chamada será executada.")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()

        run_number = 0
        for sample in samples:
            image_path = resolve_image_path(args.images_dir, sample["imagem"])

            for model in models:
                for processing_mode in processing_modes:
                    for repetition in range(1, args.repetitions + 1):
                        run_number += 1
                        print(
                            f"[{run_number}/{total_runs}] "
                            f"{sample['id']} | {model} | {processing_mode} | repetição {repetition}"
                        )

                        image_metadata = None
                        started_at = time.perf_counter()
                        try:
                            if not image_path.exists():
                                raise FileNotFoundError(f"Imagem não encontrada: {image_path}")

                            image_metadata = get_image_metadata(image_path, processing_mode)
                            result = estimate_product(
                                image_path=image_path,
                                product_description=sample["descricao"],
                                model=model,
                                known_measures=sample.get("medidas_conhecidas"),
                                image_processing_mode=processing_mode,
                            )
                            duration_seconds = time.perf_counter() - started_at
                            row = build_success_row(
                                sample=sample,
                                image_path=image_path,
                                model=model,
                                processing_mode=processing_mode,
                                repetition=repetition,
                                duration_seconds=duration_seconds,
                                image_metadata=image_metadata,
                                result=result,
                                input_price=args.input_price_per_1m,
                                output_price=args.output_price_per_1m,
                            )
                        except Exception as error:
                            duration_seconds = time.perf_counter() - started_at
                            row = build_error_row(
                                sample=sample,
                                image_path=image_path,
                                model=model,
                                processing_mode=processing_mode,
                                repetition=repetition,
                                image_metadata=image_metadata,
                                error=error,
                                duration_seconds=duration_seconds,
                            )
                            print(f"Erro: {type(error).__name__}: {error}")
                            if args.stop_on_error:
                                writer.writerow(row)
                                csv_file.flush()
                                raise

                        writer.writerow(row)
                        csv_file.flush()

    print(f"CSV gerado em: {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    if args.repetitions < 1:
        raise ValueError("--repetitions deve ser maior ou igual a 1.")
    run_evaluation(args)


if __name__ == "__main__":
    main()
