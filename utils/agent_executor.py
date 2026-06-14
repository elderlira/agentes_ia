from pathlib import Path

from ollama_client import generate

from utils.json_parser import extrair_json
from validators.schema_validator import SchemaValidator
from validators.jurisprudencia_validator import validar_jurisprudencia


class AgentExecutor:

    @staticmethod
    def executar(
        prompt,
        schema_path,
        objeto_original=None,
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
                    str(schema_path),
                )

                if objeto_original and "objeto_analisado" in dados:

                    resposta_objeto = (
                        dados["objeto_analisado"]
                        .strip()
                        .lower()
                    )

                    objeto_referencia = (
                        objeto_original
                        .strip()
                        .lower()
                    )

                    if resposta_objeto != objeto_referencia:

                        raise Exception(
                            f"""
                        OBJETO_ALTERADO

                        O campo objeto_analisado deve ser exatamente:

                        {objeto_original}

                        Valor retornado:

                        {dados['objeto_analisado']}

                        Retorne novamente utilizando exatamente o texto informado.
                        """
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

IMPORTANTE:

Se existir o campo objeto_analisado,
ele deve conter exatamente:

{objeto_original}

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