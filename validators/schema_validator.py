import json

from jsonschema import validate
from jsonschema import ValidationError

from validators.jurisprudencia_validator import (
    validar_jurisprudencia
)


class SchemaValidator:

    @staticmethod
    def validar(
        dados,
        schema_path,
        objeto_original=None
    ):

        with open(
            schema_path,
            "r",
            encoding="utf-8"
        ) as f:

            schema = json.load(f)

        try:

            validate(
                instance=dados,
                schema=schema
            )

            if (
                "jurisprudencia_tcu_schema"
                in schema_path
                and objeto_original
            ):

                validar_jurisprudencia(
                    dados,
                    objeto_original
                )

            return True

        except ValidationError as erro:

            raise Exception(
                f"""
Schema inválido.

Arquivo:
{schema_path}

Campo:
{' -> '.join(str(x) for x in erro.path)}

Erro:
{erro.message}

Valor recebido:
{erro.instance}
"""
            )