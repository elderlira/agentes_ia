from utils.json_parser import extrair_json


def parse_llm_response(resposta):

    return extrair_json(
        resposta
    )