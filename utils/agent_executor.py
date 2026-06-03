from ollama_client import generate

from utils.json_parser import extrair_json

from validators.schema_validator import SchemaValidator


class AgentExecutor:

    @staticmethod
    def executar(prompt, schema_path, tentativas=3):

        prompt_atual = prompt

        for tentativa in range(tentativas):

            resposta = generate(
                prompt_atual
            )

            try:

                dados = extrair_json(
                    resposta
                )

                SchemaValidator.validar(
                    dados,
                    schema_path
                )

                return dados

            except Exception as erro:

                prompt_atual = f"""
Corrija o JSON abaixo.

ERRO:
{erro}

JSON RECEBIDO:

{resposta}

Retorne exclusivamente JSON válido.

Não utilize markdown.

Não utilize explicações.
"""

        raise Exception(
            f"Não foi possível validar o JSON após {tentativas} tentativas."
        )