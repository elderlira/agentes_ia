from pathlib import Path

from ollama_client import generate

from utils.json_parser import extrair_json
from validators.schema_validator import SchemaValidator


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

        # --------------------------------------------------
        # BLOCO DE ANCORAGEM DO OBJETO
        # Montado uma única vez e repetido em TODA tentativa.
        # Modelos locais tendem a "esquecer" o objeto quando
        # recebem mensagens longas de erro. Ancorá-lo no topo
        # e no rodapé do prompt reduz drasticamente a deriva.
        # --------------------------------------------------

        if objeto_original:
            ancora_objeto = f"""
╔══════════════════════════════════════════════════╗
  OBJETO DA CONTRATAÇÃO — LEIA ANTES DE RESPONDER
╚══════════════════════════════════════════════════╝

{objeto_original}

REGRA ABSOLUTA:
O campo objeto_analisado deve conter EXATAMENTE
o texto acima. Copie letra por letra.
Não resuma. Não substitua. Não generalize.

══════════════════════════════════════════════════
"""
        else:
            ancora_objeto = ""

        # --------------------------------------------------
        # PROMPT BASE
        # Objeto ancorado no topo + instruções + schema.
        # --------------------------------------------------

        prompt_base = f"""{ancora_objeto}
{prompt}

=========================
SCHEMA OBRIGATÓRIO
=========================

O JSON retornado DEVE obedecer exatamente ao schema abaixo.

{schema_json}

REGRAS DE FORMATAÇÃO:

- Retorne exclusivamente JSON.
- Não utilize markdown.
- Não utilize comentários.
- Não utilize explicações.
- Não crie campos adicionais.
- Não altere nomes de campos.
- Todos os campos obrigatórios devem ser preenchidos.
- O JSON deve ser compatível com o schema informado.
{ancora_objeto}"""

        prompt_atual = prompt_base
        ultimo_erro = None
        ultima_resposta = None

        for tentativa in range(tentativas):

            print(
                f"\n======== TENTATIVA {tentativa + 1} ========\n"
            )

            resposta = generate(prompt_atual)
            ultima_resposta = resposta

            print("\n===== RESPOSTA BRUTA =====\n")
            print(resposta)

            try:
                dados = extrair_json(resposta)

                print("\n===== JSON EXTRAIDO =====\n")
                print(dados)

                # Validação de schema + semântica (inclui
                # jurisprudencia_validator quando aplicável).
                # Ponto único de validação — sem duplicação.
                SchemaValidator.validar(
                    dados,
                    str(schema_path),
                    objeto_original=objeto_original,
                )

                print("\n===== JSON VALIDADO =====\n")
                return dados

            except Exception as erro:

                ultimo_erro = erro

                print(
                    f"\nTentativa: {tentativa + 1}"
                    f"\n\nTipo do erro:\n{type(erro).__name__}"
                    f"\n\nMensagem:\n{erro}\n"
                )

                # ----------------------------------------------
                # PROMPT DE RETRY
                # O objeto é ancorado novamente no topo e no
                # rodapé. O erro é descrito com precisão.
                # A resposta anterior é incluída para que o
                # modelo saiba exatamente o que corrigir.
                # ----------------------------------------------

                prompt_atual = f"""{ancora_objeto}
{prompt_base}

╔══════════════════════════════════════════════════╗
  ERRO DE VALIDAÇÃO — CORRIJA E RESPONDA NOVAMENTE
╚══════════════════════════════════════════════════╝

ERRO IDENTIFICADO:

{erro}

SUA RESPOSTA ANTERIOR (com o erro):

{ultima_resposta}

O QUE VOCÊ DEVE FAZER:

1. Leia o erro acima com atenção.
2. Identifique o campo ou valor incorreto.
3. Corrija APENAS o que está errado.
4. Mantenha todos os outros campos inalterados.
5. Retorne o JSON completo e corrigido.

LEMBRETE CRÍTICO:
{f'O campo objeto_analisado deve ser: {objeto_original}' if objeto_original else ''}

REGRAS:
- Retorne exclusivamente JSON.
- Não utilize markdown.
- Não utilize comentários.
- Não utilize explicações.
- Não altere os nomes dos campos.
- Não remova campos obrigatórios.
- Não crie campos extras.
- Obedeça integralmente o schema.
{ancora_objeto}"""

        raise Exception(
            f"\nNão foi possível validar o JSON "
            f"após {tentativas} tentativas."
            f"\n\nÚltimo erro:\n\n{ultimo_erro}\n"
        )