import json

from jsonschema import validate
from jsonschema import ValidationError


class SchemaValidator:

    @staticmethod
    def validar(dados, schema_path):

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

            return True

        except ValidationError as erro:

            raise Exception(
                f"""
Schema inválido.

Arquivo:
{schema_path}

Erro:
{erro.message}
"""
            )