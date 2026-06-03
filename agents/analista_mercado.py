import json

from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor


class AnalistaMercado:

    def executar(self, contexto):

        objeto = contexto["objeto_contratacao"]

        scout = contexto["scout"]

        prompt_mercado = load_prompt(
            "analista_mercado"
        )

        prompt_final = f"""
{prompt_mercado}

OBJETO DA CONTRATAÇÃO:

{objeto}

RESULTADO DO SCOUT:

{json.dumps(
    scout,
    ensure_ascii=False,
    indent=2
)}
"""

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path="schemas/analista_mercado_schema.json"
        )

        dados["fonte"] = "Analista Mercado"
        dados["versao_agente"] = "1.0"
        dados["status"] = "concluido"

        return dados