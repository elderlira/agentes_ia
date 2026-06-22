"""
Agente Especialista 14.133 — v2.0

CORREÇÃO DA FALHA IDENTIFICADA:

  O agente original chamava generate() diretamente, sem schema
  formal injetado no prompt e sem retry — uma única falha do
  modelo (que produziu texto livre em inglês, no formato de um
  TR/ETP completo, em vez do JSON esperado) já quebrava todo o
  pipeline, abortando antes do Redator ETP / Redator TR.

  Além disso, o contexto era despejado como repr() do dict
  Python inteiro (aspas simples, todos os campos de todos os
  agentes), o que confundia o modelo sobre o formato esperado
  de saída.

CORREÇÕES APLICADAS:

  1. Migrado para AgentExecutor — agora há retry automático
     com reenvio do erro ao modelo (mesmo padrão dos demais
     agentes: Jurisprudencia TCU, Analista Mercado).

  2. Schema JSON formal criado e injetado no prompt pelo
     AgentExecutor — ancora fortemente o formato esperado.

  3. Contexto filtrado e serializado com json.dumps (não repr).
     Conforme o próprio prompt já instruía, usa exclusivamente:
     objeto_contratacao, scout, analista_mercado.

  4. Reforço explícito no prompt final para responder em
     português e em JSON, com confirmação ao final.
"""

import json
import logging

from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor

logger = logging.getLogger(__name__)


class Especialista14133:

    SCHEMA = "schemas/especialista_14133_schema.json"

    def executar(self, contexto: dict) -> dict:

        prompt_sistema = load_prompt("especialista_14133")

        objeto_original = (
            contexto.get("objeto_original")
            or contexto.get("objeto_contratacao")
        )
        if not objeto_original:
            raise Exception("OBJETO_ORIGINAL_NAO_LOCALIZADO")

        # --------------------------------------------------
        # Filtra exclusivamente as fontes que o prompt já
        # determinava: objeto_contratacao, scout, analista_mercado
        # --------------------------------------------------

        scout = contexto.get("scout", {})
        analista_mercado = contexto.get("analista_mercado", {})

        contexto_filtrado = {
            "objeto_contratacao": objeto_original,
            "scout": scout,
            "analista_mercado": analista_mercado,
        }

        logger.info(
            f"Especialista 14.133: analisando '{objeto_original}'"
        )

        # --------------------------------------------------
        # Prompt final com ancoragem de idioma e formato
        # --------------------------------------------------

        prompt_final = f"""
{prompt_sistema}

══════════════════════════════════════════════════════
OBJETO DA CONTRATACAO
══════════════════════════════════════════════════════

{objeto_original}

══════════════════════════════════════════════════════
CONTEXTO (objeto_contratacao, scout, analista_mercado)
══════════════════════════════════════════════════════

{json.dumps(contexto_filtrado, ensure_ascii=False, indent=2)}

══════════════════════════════════════════════════════
INSTRUCOES FINAIS — OBRIGATORIO
══════════════════════════════════════════════════════

1. Responda SEMPRE em portugues do Brasil.
2. Responda EXCLUSIVAMENTE em JSON, sem texto antes ou depois.
3. NAO redija ETP ou TR — apenas produza as orientacoes
   tecnicas e administrativas conforme os campos obrigatorios
   definidos acima.
4. NAO traduza nem reformule o objeto da contratacao para
   outro idioma.
5. Preencha TODOS os campos obrigatorios do schema.

Confirme antes de responder: sua saida deve ser um unico
objeto JSON, em portugues, comecando com {{ e terminando com }}.
"""

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA,
        )

        dados["fonte"] = "Especialista 14.133"
        dados["versao_agente"] = "2.0"
        dados["status"] = "concluido"

        logger.info("Especialista 14.133: analise concluida")

        return dados