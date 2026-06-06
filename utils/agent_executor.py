from pathlib import Path

from ollama_client import generate

from utils.json_parser import extrair_json
from validators.schema_validator import SchemaValidator


class AgentExecutor:

    @staticmethod
    def executar(
        prompt,
        schema_path,
        tentativas=3
    ):

        schema_path = Path(schema_path)

        with open(
            schema_path,
            "r",
            encoding="utf-8"
        ) as arquivo:
            schema_json = arquivo.read()

        prompt_base = f"""
{prompt}

=========================
SCHEMA OBRIGATÓRIO
=========================

O JSON retornado DEVE obedecer exatamente ao schema abaixo.

{schema_json}

REGRAS:

- Retorne exclusivamente JSON.
- Não utilize markdown.
- Não utilize comentários.
- Não utilize explicações.
- Não crie campos adicionais.
- Não altere nomes de campos.
- Todos os campos obrigatórios devem ser preenchidos.
- O JSON deve ser compatível com o schema informado.
"""

        prompt_atual = prompt_base

        ultimo_erro = None

        for tentativa in range(tentativas):

            print(
                f"\n======== TENTATIVA {tentativa + 1} ========\n"
            )

            resposta = generate(prompt_atual)

            print("\n===== RESPOSTA BRUTA =====\n")
            print(resposta)

            try:

                dados = extrair_json(resposta)

                print("\n===== JSON EXTRAIDO =====\n")
                print(dados)

                SchemaValidator.validar(
                    dados,
                    str(schema_path)
                )

                print("\n===== JSON VALIDADO =====\n")

                return dados

            except Exception as erro:

                ultimo_erro = erro

                print(
                    f"""
Tentativa: {tentativa + 1}

Tipo do erro:
{type(erro).__name__}

Mensagem:
{erro}
"""
                )

                prompt_atual = f"""
{prompt_base}

=========================
ERRO DE VALIDAÇÃO
=========================

Sua resposta anterior não atende ao schema.

ERRO:

{erro}

RESPOSTA ANTERIOR:

{resposta}

CORRIJA O JSON.

REGRAS:

- Retorne exclusivamente JSON.
- Não utilize markdown.
- Não utilize comentários.
- Não utilize explicações.
- Não altere os nomes dos campos.
- Não remova campos obrigatórios.
- Não crie campos extras.
- Obedeça integralmente o schema.
"""

        raise Exception(
            f"""
Não foi possível validar o JSON após {tentativas} tentativas.

Último erro:

{ultimo_erro}
"""
        )