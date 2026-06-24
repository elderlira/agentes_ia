from prompt_loader import load_prompt

from context.contexto import Contexto

from agents.scout import Scout
from agents.analista_mercado import AnalistaMercado
from agents.jurisprudencia_tcu import JurisprudenciaTCU
from agents.especialista_14133 import Especialista14133
from agents.especialista_tecnico import EspecialistaTecnico
from agents.redator_tr import RedatorTR
from agents.redator_etp import RedatorETP

from utils.agent_executor import AgentExecutor

class Maestro:

    SCHEMA_MAESTRO = "schemas/maestro_schema.json"

    MAPA_AGENTES = {
        "Scout": Scout,
        "Analista Mercado": AnalistaMercado,
        "Jurisprudencia TCU": JurisprudenciaTCU,
        "Especialista 14.133": Especialista14133,
        "Especialista Tecnico": EspecialistaTecnico,
        "Redator ETP": RedatorETP,
        "Redator TR": RedatorTR,
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
                "Especialista Tecnico",
                "Redator ETP"
            ],
            "TR": [
                "Scout",
                "Analista Mercado",
                "Jurisprudencia TCU",
                "Especialista 14.133",
                "Especialista Tecnico",
                "Redator ETP",
                "Redator TR"
            ]
        }

        return fluxos.get(tipo_documento, [])

    def executar_agentes(self, agentes):

        from services.pncp_service import buscar_contratacoes_similares

        for agente_nome in agentes:
            if agente_nome not in self.MAPA_AGENTES:
                print(f"Agente {agente_nome} não mapeado.")
                continue

            print(f"\n[MAESTRO] Executando: {agente_nome}...")
            agente_classe = self.MAPA_AGENTES[agente_nome]
            agente_instancia = agente_classe()

            try:
                dict_contexto = getattr(self.contexto, "dados", self.contexto.__dict__)

                resultado_agente = agente_instancia.executar(dict_contexto)

                self.contexto.atualizar(agente_nome, resultado_agente)

                chave_snake = agente_nome.lower().replace(" ", "_")
                self.contexto.atualizar(chave_snake, resultado_agente)

                if agente_nome == "Analista Mercado":
                    print("[MAESTRO -> PNCP] Buscando contratações reais no PNCP para fundamentação analítica...")
                    
                    objeto_busca = dict_contexto.get("objeto_contratacao") or dict_contexto.get("pergunta_original", "TI")
                    
                    try:
                        dados_pncp = buscar_contratacoes_similares(objeto_busca, max_resultados=5)
                        contratacoes_reais = dados_pncp.get("contratacoes", [])
                        
                        if isinstance(resultado_agente, dict):
                            resultado_agente["pncp_dados"] = contratacoes_reais
                            
                            self.contexto.atualizar("Analista Mercado", resultado_agente)
                            self.contexto.atualizar("analista_mercado", resultado_agente)
                            print(f"[MAESTRO -> PNCP] Sucesso: {len(contratacoes_reais)} licitações reais integradas ao contexto.")
                    except Exception as p_err:
                        print(f"[MAESTRO -> PNCP] Aviso: Falha ao coletar dados do PNCP: {p_err}")

                self.contexto.registrar_execucao(
                    agente_nome,
                    "sucesso"
                )

            except Exception as e:
                print(f"Erro ao executar agente {agente_nome}: {e}")
                self.contexto.atualizar(
                    f"{agente_nome.lower().replace(' ', '_')}_erro",
                    str(e)
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

        self.contexto.atualizar(
            "objeto_original",
            dados_maestro["objeto_contratacao"]
        )

        agentes = self.obter_agentes(
            dados_maestro["tipo_documento"]
        )

        print("\nAGENTES PLANEJADOS:")
        print(agentes)

        self.contexto.atualizar(
            "agentes_planejados",
            agentes
        )

        self.executar_agentes(
            agentes
        )

        return self.contexto.obter()