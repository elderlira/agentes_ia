from prompt_loader import load_prompt
from ollama_client import generate

from utils.json_parser import extrair_json

class JurisprudenciaTCU:

    def executar(self, contexto):

        prompt = load_prompt(
            "jurisprudencia_tcu"
        )

        prompt_final = f""" 
{prompt}

CONTEXTO COMPLETO:

{contexto}
"""

        resposta = generate(
                prompt_final
            )

        try:

            return extrair_json(
                resposta
            )
        
        except Exception:

            raise Exception(
                f"""O agente Jurisprudência TCU
                não retornou um JSON válido.
                Resposta recebida:

                {resposta}
                """
            )