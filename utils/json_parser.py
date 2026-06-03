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
    
def normalizar_campos(dados):

    mapa = {
        "objeto_contratação": "objeto_contratacao",
        "tipo_documentação": "tipo_documento",
    }

    for antigo, novo in mapa.items():

        if antigo in dados:
            dados[novo] = dados.pop(antigo)

    return dados