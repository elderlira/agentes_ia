import json

from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor


class EspecialistaTecnico:

    def executar(self, contexto):

        objeto = contexto.get(
            "objeto_contratacao",
            ""
        )

        scout = contexto.get(
            "scout",
            {}
        )

        mercado = contexto.get(
            "analista_mercado",
            {}
        )

        lei14133 = contexto.get(
            "especialista_14133",
            {}
        )

        tcu = contexto.get(
            "jurisprudencia_tcu",
            {}
        )

        prompt_tecnico = load_prompt(
            "especialista_tecnico"
        )

        prompt_final = f"""
{prompt_tecnico}

OBJETO DA CONTRATAÇÃO:

{objeto}

RESULTADO DO SCOUT:

{json.dumps(
    scout,
    ensure_ascii=False,
    indent=2
)}

RESULTADO DO ANALISTA DE MERCADO:

{json.dumps(
    mercado,
    ensure_ascii=False,
    indent=2
)}

RESULTADO DO ANALISTA 14.133:

{json.dumps(
    lei14133,
    ensure_ascii=False,
    indent=2
)}

RESULTADO DA JURISPRUDÊNCIA TCU:

{json.dumps(
    tcu,
    ensure_ascii=False,
    indent=2
)}
"""

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path="schemas/especialista_tecnico_schema.json"
        )

        dados["fonte"] = "Especialista Tecnico"
        dados["versao_agente"] = "1.0"
        dados["status"] = "concluido"

        return dados