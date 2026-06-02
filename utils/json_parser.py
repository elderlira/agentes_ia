import json
import re


def extrair_json(texto):

    texto = texto.strip()

    texto = re.sub(
        r"^```json",
        "",
        texto
    )

    texto = re.sub(
        r"^```",
        "",
        texto
    )

    texto = re.sub(
        r"```$",
        "",
        texto
    )

    texto = texto.strip()

    try:

        return json.loads(texto)

    except json.JSONDecodeError:

        match = re.search(
            r"\{.*\}",
            texto,
            re.DOTALL
        )

        if not match:

            raise ValueError(
                "Nenhum JSON válido encontrado."
            )

        return json.loads(
            match.group()
        )