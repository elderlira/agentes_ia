from prompt_loader import load_prompt

from utils.agent_executor import AgentExecutor


class Scout:

    def executar(self, tema):

        prompt_scout = load_prompt(
            "scout"
        )

        prompt_final = f"""
{prompt_scout}

TEMA INFORMADO:

{tema}
"""

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path="schemas/scout_schema.json"
        )

        dados["fonte"] = "Scout"
        dados["versao_agente"] = "1.0"

        return dados