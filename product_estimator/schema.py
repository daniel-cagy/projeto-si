from typing import Any


MEASUREMENT_SCHEMA: dict[str, Any] = {
    "name": "estimativa_dimensional_produto",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "produto_identificado",
            "descricao_resumida",
            "produto",
            "nivel_confianca",
            "principais_pistas_usadas",
            "fatores_de_incerteza",
            "observacoes",
        ],
        "properties": {
            "produto_identificado": {"type": "string"},
            "descricao_resumida": {"type": "string"},
            "produto": {"$ref": "#/$defs/medidas_e_peso"},
            "nivel_confianca": {"type": "string", "enum": ["baixo", "medio", "alto"]},
            "principais_pistas_usadas": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
            },
            "fatores_de_incerteza": {
                "type": "array",
                "items": {"type": "string"},
            },
            "observacoes": {"type": "string"},
        },
        "$defs": {
            "faixa_numerica": {
                "type": "object",
                "additionalProperties": False,
                "required": ["min", "max", "estimativa"],
                "properties": {
                    "min": {"type": "number", "minimum": 0},
                    "max": {"type": "number", "minimum": 0},
                    "estimativa": {"type": "number", "minimum": 0},
                },
            },
            "dimensoes": {
                "type": "object",
                "additionalProperties": False,
                "required": ["comprimento", "largura", "altura"],
                "properties": {
                    "comprimento": {"$ref": "#/$defs/faixa_numerica"},
                    "largura": {"$ref": "#/$defs/faixa_numerica"},
                    "altura": {"$ref": "#/$defs/faixa_numerica"},
                },
            },
            "medidas_e_peso": {
                "type": "object",
                "additionalProperties": False,
                "required": ["dimensoes_estimadas_cm", "peso_estimado_kg"],
                "properties": {
                    "dimensoes_estimadas_cm": {"$ref": "#/$defs/dimensoes"},
                    "peso_estimado_kg": {"$ref": "#/$defs/faixa_numerica"},
                },
            },
        },
    },
}
