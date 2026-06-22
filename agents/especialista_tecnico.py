"""
Agente Especialista Tecnico

CORRECAO APLICADA:
  Havia uma chamada DUPLICADA a AgentExecutor.executar()
  no codigo original. A primeira chamada gerava uma resposta
  completa do modelo (custando tempo real de inferencia,
  possivelmente com retries), mas o resultado era IMEDIATAMENTE
  DESCARTADO porque a segunda chamada sobrescrevia a variavel
  `dados`. Isso dobrava o tempo de execucao deste agente sem
  nenhum beneficio.

  Mantida apenas UMA chamada ao AgentExecutor.
"""

import json

from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor


class EspecialistaTecnico:

    SCHEMA = "schemas/especialista_tecnico_schema.json"

    # Termos de leis revogadas pela Lei 14.133/2021 (art. 193)
    # que NAO podem aparecer no resultado deste agente.
    TERMOS_PROIBIDOS = [
        "8.666",
        "10.520",
        "Lei nº 8.666",
        "Lei 8.666",
        "Lei nº 10.520",
        "Lei 10.520",
    ]

    def executar(self, contexto):

        objeto = contexto.get("objeto_contratacao", "")
        scout = contexto.get("scout", {})
        mercado = contexto.get("analista_mercado", {})
        lei14133 = contexto.get("especialista_14133", {})
        tcu = contexto.get("jurisprudencia_tcu", {})

        prompt_tecnico = load_prompt("especialista_tecnico")

        prompt_final = f"""
{prompt_tecnico}

OBJETO DA CONTRATAÇÃO:

{objeto}

RESULTADO DO SCOUT:

{json.dumps(scout, ensure_ascii=False, indent=2)}

RESULTADO DO ANALISTA DE MERCADO:

{json.dumps(mercado, ensure_ascii=False, indent=2)}

RESULTADO DO ANALISTA 14.133:

{json.dumps(lei14133, ensure_ascii=False, indent=2)}

RESULTADO DA JURISPRUDÊNCIA TCU:

{json.dumps(tcu, ensure_ascii=False, indent=2)}
"""

        # --------------------------------------------------
        # ÚNICA chamada ao AgentExecutor (duplicata removida)
        # --------------------------------------------------
        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA,
        )

        # --------------------------------------------------
        # Guarda contra referências a leis revogadas
        # --------------------------------------------------
        resultado_json = json.dumps(dados, ensure_ascii=False)

        for termo in self.TERMOS_PROIBIDOS:
            if termo.lower() in resultado_json.lower():
                raise Exception(
                    f"ESPECIALISTA_TECNICO_REFERENCIA_REVOGADA: {termo}"
                )

        dados["fonte"] = "Especialista Tecnico"
        dados["versao_agente"] = "1.0"
        dados["status"] = "concluido"

        return dados