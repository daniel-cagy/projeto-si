#!/usr/bin/env python3
import argparse
import os
import json

from pathlib import Path
from product_estimator.estimate_product import estimate_product



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estima dimensões e peso de um produto usando imagem + descrição."
    )
    parser.add_argument("image", type=Path, help="Caminho da imagem do produto.")
    parser.add_argument(
        "description",
        help="Descrição textual do produto. Use aspas se tiver espaços.",
    )
    parser.add_argument(
        "--extra-image",
        action="append",
        type=Path,
        default=[],
        help="Imagem adicional do mesmo produto. Pode ser usado mais de uma vez.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-5.5"),
        help="Modelo da OpenAI. Padrão: OPENAI_MODEL ou gpt-5.5.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Arquivo .json para salvar o resultado. Se omitido, imprime no terminal.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    image_paths = [args.image, *args.extra_image]
    result = estimate_product(
        image_path=args.image,
        image_paths=image_paths,
        product_description=args.description,
        model=args.model,
    )
    pretty_json = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        args.output.write_text(pretty_json + "\n", encoding="utf-8")
    else:
        print(pretty_json)
