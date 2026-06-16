from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor


class JurisprudenciaTCU:

    SCHEMA = "schemas/jurisprudencia_tcu_schema.json"

    def executar(self, contexto):

        prompt_sistema = load_prompt("jurisprudencia_tcu")

        # --------------------------------------------------
        # Extração do objeto
        # --------------------------------------------------

        objeto_original = contexto.get("objeto_original")

        if not objeto_original:
            objeto_original = contexto.get(
                "objeto_contratacao"
            )

        if not objeto_original:
            raise Exception(
                "OBJETO_ORIGINAL_NAO_LOCALIZADO"
            )

        # --------------------------------------------------
        # Contexto do Scout (enriquece a pesquisa)
        # --------------------------------------------------

        palavras_chave = []
        categoria = ""
        subcategorias = []

        if "scout" in contexto:
            scout = contexto["scout"]
            palavras_chave = scout.get("palavras_chave", [])
            categoria = scout.get("categoria", "")
            subcategorias = scout.get("subcategorias", [])

        palavras_formatadas = (
            "\n".join(f"- {p}" for p in palavras_chave)
            if palavras_chave
            else "(não informado)"
        )

        subcategorias_formatadas = (
            "\n".join(f"- {s}" for s in subcategorias)
            if subcategorias
            else "(não informado)"
        )

        # --------------------------------------------------
        # Prompt final
        # O objeto é repetido 3 vezes em posições
        # estratégicas: abertura, meio e fechamento.
        # Isso reduz a deriva em modelos locais.
        # --------------------------------------------------

        prompt_final = f"""
╔══════════════════════════════════════════════════════╗
  OBJETO DA CONTRATAÇÃO — REFERÊNCIA PRINCIPAL
╚══════════════════════════════════════════════════════╝

{objeto_original}

O campo objeto_analisado deve conter EXATAMENTE o texto
acima. Copie letra por letra. Não altere nada.

══════════════════════════════════════════════════════

{prompt_sistema}

══════════════════════════════════════════════════════
DADOS PARA PESQUISA
══════════════════════════════════════════════════════

OBJETO DA CONTRATAÇÃO:
{objeto_original}

CATEGORIA IDENTIFICADA:
{categoria if categoria else "(não informado)"}

SUBCATEGORIAS:
{subcategorias_formatadas}

PALAVRAS-CHAVE:
{palavras_formatadas}

══════════════════════════════════════════════════════
CONFIRMAÇÃO FINAL ANTES DE RESPONDER
══════════════════════════════════════════════════════

Objeto que você está analisando:

{objeto_original}

Copie este texto literalmente no campo objeto_analisado.
Não altere nenhuma palavra, acento ou pontuação.
"""

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA,
            objeto_original=objeto_original,
        )

        dados["fonte"] = "Jurisprudencia TCU"
        dados["versao_agente"] = "1.0"
        dados["status"] = "concluido"

        return dados