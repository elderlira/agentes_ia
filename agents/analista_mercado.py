import json

from prompt_loader import load_prompt
from ollama_client import generate


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

        resposta = generate(prompt_final)

        dados = json.loads(resposta)

        dados["fonte"] = "Analista Mercado"

        dados["versao_agente"] = "1.0"

        dados["status"] = "concluido"

        return dados