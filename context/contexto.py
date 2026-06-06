from datetime import datetime

class Contexto:

    def __init__(self):

        self.dados = {
            "pergunta_original": "",
            "tipo_solicitacao": "",
            "tipo_documento": "",
            "objeto_contratacao": "",

            "agentes_planejados": [],
            "historico_execucao": [],

            "versao_fluxo": "1.0",
            "data_execucao": datetime.now().isoformat(),

            "maestro": {},
            "scout": {},
            "analista_mercado": {},
            "jurisprudencia_tcu": {},
            "especialista_14133": {},
            "redator_etp": {},
            "redator_tr": {},
        }

    def atualizar(self, chave, valor):
        self.dados[chave] = valor


    def registrar_execucao(self, agente, status, qualidade=None):
        if qualidade is not None:
            self.dados["historico_execucao"].append({
                "agente": agente,
                "status": status,
                "qualidade": qualidade,
                "data_hora": datetime.now().isoformat()
            })
        else:
            self.dados["historico_execucao"].append({
                "agente": agente,
                "status": status,
                "data_hora": datetime.now().isoformat()
            })

    def obter(self):
        return self.dados