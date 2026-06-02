from prompt_loader import load_prompt
from ollama_client import generate

from context.contexto import Contexto

from agents.scout import Scout
from agents.analista_mercado import AnalistaMercado

from validators.schema_validator import SchemaValidator
from utils.json_parser import extrair_json

from jsonschema import ValidationError


class Maestro:

    SCHEMA_MAESTRO = "schemas/maestro_schema.json"

    MAPA_AGENTES = {
        "Scout": Scout,
        "Analista Mercado": AnalistaMercado,
        # "Especialista 14.133": Especialista14133,
        # "Redator ETP": RedatorETP,
        # "Redator TR": RedatorTR
    }

    MAPA_SCHEMAS = {
        "Scout": "schemas/scout_schema.json",
        "Analista Mercado": "schemas/analista_mercado_schema.json"
    }

    def __init__(self):

        self.contexto = Contexto()

    def obter_agentes(self, tipo_documento):

        fluxos = {
            "ETP": [
                "Scout",
                "Analista Mercado",
                "Especialista 14.133",
                "Redator ETP"
            ],
            "TR": [
                "Scout",
                "Analista Mercado",
                "Especialista 14.133",
                "Redator TR"
            ]
        }

        return fluxos.get(tipo_documento, [])

    def executar_agentes(self, agentes):

        for agente_nome in agentes:

            if agente_nome not in self.MAPA_AGENTES:
                continue

            agente = self.MAPA_AGENTES[agente_nome]()

            chave_contexto = (
                agente_nome.lower()
                .replace(" ", "_")
                .replace(".", "")
                .replace("ã", "a")
            )

            resultado = agente.executar(
                self.contexto.obter()
            )

            schema_path = self.MAPA_SCHEMAS.get(
                agente_nome
            )

            if schema_path:

                try:

                    SchemaValidator.validar(
                        resultado,
                        schema_path
                    )

                except ValidationError as erro:

                    self.contexto.registrar_execucao(
                        agente_nome,
                        "erro_schema"
                    )

                    self.contexto.atualizar(
                        f"{chave_contexto}_erro",
                        erro.message
                    )

                    continue

                except Exception as erro:

                    self.contexto.registrar_execucao(
                        agente_nome,
                        "erro_schema"
                    )

                    self.contexto.atualizar(
                        f"{chave_contexto}_erro",
                        str(erro)
                    )

                    continue

            self.contexto.atualizar(
                chave_contexto,
                resultado
            )

            self.contexto.registrar_execucao(
                agente_nome,
                "concluido"
            )

    def processar(self, pergunta):

        self.contexto.atualizar(
            "pergunta_original",
            pergunta
        )

        prompt_maestro = load_prompt(
            "maestro"
        )

        prompt_final = f"""
{prompt_maestro}

SOLICITAÇÃO DO USUÁRIO:

{pergunta}
"""

        resposta = generate(
            prompt_final
        )

        try:

            dados_maestro = extrair_json(
                resposta
            )

        except Exception:

            raise Exception(
                f"""
O Maestro não retornou um JSON válido.

Resposta recebida:

{resposta}
"""
            )

        try:

            SchemaValidator.validar(
                dados_maestro,
                self.SCHEMA_MAESTRO
            )

        except ValidationError as erro:

            raise Exception(
                f"""
Erro de validação do Maestro

Schema:
{self.SCHEMA_MAESTRO}

Detalhes:
{erro.message}
"""
            )

        except Exception as erro:

            raise Exception(
                f"""
Erro ao validar o schema do Maestro.

Detalhes:
{str(erro)}
"""
            )

        self.contexto.atualizar(
            "maestro",
            dados_maestro
        )

        self.contexto.atualizar(
            "tipo_solicitacao",
            dados_maestro["tipo_solicitacao"]
        )

        self.contexto.atualizar(
            "tipo_documento",
            dados_maestro["tipo_documento"]
        )

        self.contexto.atualizar(
            "objeto_contratacao",
            dados_maestro["objeto_contratacao"]
        )

        agentes = self.obter_agentes(
            dados_maestro["tipo_documento"]
        )

        self.contexto.atualizar(
            "agentes_planejados",
            agentes
        )

        self.executar_agentes(
            agentes
        )

        return self.contexto.obter()