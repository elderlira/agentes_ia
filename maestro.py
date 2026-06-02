import json

from prompt_loader import load_prompt
from ollama_client import generate

from context.contexto import Contexto

from agents.scout import Scout


class Maestro:

    MAPA_AGENTES = {
        "Scout": Scout,
        # "Analista Mercado": AnalistaMercado,
        # "Especialista 14.133": Especialista14133,
        # "Redator ETP": RedatorETP,
        # "Redator TR": RedatorTR
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

            resultado = agente.executar(
                self.contexto.obter()
            )

            chave_contexto = agente_nome.lower() \
                .replace(" ", "_") \
                .replace(".", "") \
                .replace("ã", "a")

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

        prompt_maestro = load_prompt("maestro")

        prompt_final = f"""
{prompt_maestro}

SOLICITAÇÃO DO USUÁRIO:

{pergunta}
"""

        resposta = generate(prompt_final)

        dados_maestro = json.loads(resposta)

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