from prompt_loader import load_prompt

from utils.agent_executor import AgentExecutor


class JurisprudenciaTCU:

    SCHEMA = (
        "schemas/jurisprudencia_tcu_schema.json"
    )

    def executar(self, contexto):

        prompt = load_prompt(
            "jurisprudencia_tcu"
        )

        objeto_original = contexto.get(
            "objeto_original"
        )

        if not objeto_original:

            objeto_original = contexto.get(
                "objeto_contratacao"
            )

        if not objeto_original:

            raise Exception(
                "OBJETO_ORIGINAL_NAO_LOCALIZADO"
            )
        
        palavras_chave = []
        categoria = ""
        subcategorias = []

        if "scout" in contexto:

            palavras_chave = contexto["scout"].get(
                "palavras_chave",
                []
            )

            categoria = contexto["scout"].get(
                "categoria",
                ""
            )

            subcategorias = contexto["scout"].get(
                "subcategorias",
                []
            )

        prompt_final = f"""
{prompt}

OBJETO DA CONTRATAÇÃO:

{objeto_original}

ATENÇÃO CRÍTICA:

O campo objeto_analisado deve conter
EXATAMENTE o texto abaixo:

{objeto_original}

Copie literalmente o texto.

Não altere palavras.
Não resuma.
Não substitua termos.
Não generalize.

CATEGORIA IDENTIFICADA:

{categoria}

SUBCATEGORIAS:

{subcategorias}

PALAVRAS-CHAVE:

{palavras_chave}

REGRAS OBRIGATÓRIAS:

1. Analise exclusivamente o objeto informado.

2. Caso não encontre jurisprudência,
retorne SEM_EVIDENCIA.

3. Mesmo em SEM_EVIDENCIA,
o campo objeto_analisado deve permanecer
idêntico ao texto informado acima.
"""

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA,
            objeto_original=objeto_original
        )

        dados["fonte"] = (
            "Jurisprudencia TCU"
        )

        dados["versao_agente"] = "1.0"

        dados["status"] = "concluido"

        return dados