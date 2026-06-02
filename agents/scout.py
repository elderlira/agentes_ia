import json
from prompt_loader import load_prompt
from ollama_client import generate


class Scout:

    def executar(self, tema):

        prompt_scout = load_prompt("scout")

        prompt_final = f"""
{prompt_scout}

TEMA INFORMADO:

{tema}
"""

        resposta = generate(prompt_final)
        
        dados = json.loads(resposta)

        dados["fonte"] = "Scout"
        dados["versao_agente"] = "1.0"

        return dados