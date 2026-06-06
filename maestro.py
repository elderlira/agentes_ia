from prompt_loader import load_prompt

from context.contexto import Contexto

from agents.scout import Scout
from agents.analista_mercado import AnalistaMercado
from agents.jurisprudencia_tcu import JurisprudenciaTCU
from agents.especialista_14133 import Especialista14133
# from agents.redator_tr import RedatorTR
# from agents.redator_etp import RedatorETP

from utils.agent_executor import AgentExecutor



class Maestro:

    SCHEMA_MAESTRO = "schemas/maestro_schema.json"

    MAPA_AGENTES = {
        "Scout": Scout,
        "Analista Mercado": AnalistaMercado,
        "Jurisprudencia TCU": JurisprudenciaTCU,
        "Especialista 14.133": Especialista14133,
        # "Redator TR": RedatorTR,
        # "Redator ETP": RedatorETP,
    }

    def __init__(self):

        self.contexto = Contexto()

    def obter_agentes(self, tipo_documento):

        fluxos = {
            "ETP": [
                "Scout",
                "Analista Mercado",
                "Jurisprudencia TCU",
                "Especialista 14.133",
            ],
            "TR": [
                "Scout",
                "Analista Mercado",
                "Jurisprudencia TCU",
                "Especialista 14.133",
            ]
        }

        return fluxos.get(tipo_documento, [])

    def executar_agentes(self, agentes):

        for agente_nome in agentes:


            # if agente_nome not in self.MAPA_AGENTES:

            #     raise Exception(
            #         f"Agente solicitado pelo Maestro não existe: {agente_nome}"
            #     )

            if agente_nome not in self.MAPA_AGENTES:
                raise Exception(
                    f"Agente não mapeado: {agente_nome}"
                )

            agente = self.MAPA_AGENTES[agente_nome]()

            chave_contexto = (
                agente_nome.lower()
                .replace(" ", "_")
                .replace(".", "")
                .replace("ã", "a")
            )

            try:

                resultado = agente.executar(
                    self.contexto.obter()
                )

                if not resultado:
                    raise Exception(
                        f"{agente_nome} retornou vazio."
                    )
                
                self.contexto.atualizar(
                    chave_contexto,
                    resultado
                )

                self.contexto.registrar_execucao(
                    agente_nome,
                    "concluido",
                    # qualidade=resultado.get(
                    #     "nivel_confianca"
                    # )
                )

            except Exception as erro:

                self.contexto.atualizar(
                    f"{chave_contexto}_erro",
                    str(erro)
                )

                self.contexto.registrar_execucao(
                    agente_nome,
                    "erro"
                )

                break

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
        dados_maestro = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA_MAESTRO
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

        agentes = dados_maestro["agentes_necessarios"]

        self.contexto.atualizar(
            "agentes_planejados",
            agentes
        )

        self.executar_agentes(
            agentes
        )

        return self.contexto.obter()