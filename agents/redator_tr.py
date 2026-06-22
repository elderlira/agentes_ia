"""
Agente Redator TR — Camada 3

Roda APOS o Redator ETP. Le o ETP ja gerado e o contexto
consolidado para produzir o Termo de Referencia, seguindo
a estrutura do art. 6º, XXIII da Lei 14.133/2021.

DEPENDENCIA CRITICA: este agente exige que
contexto["redator_etp"] ja esteja preenchido. Caso contrario,
lanca exception — o pipeline deve garantir a ordem sequencial
(Redator ETP antes do Redator TR).
"""

import json
import logging

from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor

logger = logging.getLogger(__name__)


class RedatorTR:

    SCHEMA = "schemas/redator_tr_schema.json"

    def executar(self, contexto: dict) -> dict:

        prompt_sistema = load_prompt("redator_tr")

        objeto_original = (
            contexto.get("objeto_original")
            or contexto.get("objeto_contratacao")
        )
        if not objeto_original:
            raise Exception("OBJETO_ORIGINAL_NAO_LOCALIZADO")

        # --------------------------------------------------
        # Validação de dependência: ETP deve existir
        # --------------------------------------------------

        etp = contexto.get("redator_etp", {})

        if not etp or not etp.get("documento_markdown"):
            raise Exception(
                "ETP_NAO_DISPONIVEL: O Redator TR depende do "
                "Redator ETP ja executado. Verifique a ordem "
                "de execucao no Maestro — o Redator ETP deve "
                "rodar antes do Redator TR."
            )

        logger.info(
            f"Redator TR: ETP localizado, consolidando TR "
            f"para '{objeto_original}'"
        )

        # --------------------------------------------------
        # Contexto complementar (alem do ETP)
        # --------------------------------------------------

        analista_mercado = contexto.get("analista_mercado", {})
        jurisprudencia_tcu = contexto.get("jurisprudencia_tcu", {})
        especialista_14133 = contexto.get("especialista_14133", {})
        especialista_tecnico = contexto.get("especialista_tecnico", {})

        contexto_consolidado = {
            "etp_gerado": etp,
            "analista_mercado": analista_mercado,
            "jurisprudencia_tcu": jurisprudencia_tcu,
            "especialista_14133": especialista_14133,
            "especialista_tecnico": especialista_tecnico,
        }

        # --------------------------------------------------
        # Prompt final
        # --------------------------------------------------

        prompt_final = f"""
{prompt_sistema}

══════════════════════════════════════════════════════
OBJETO DA CONTRATACAO
══════════════════════════════════════════════════════

{objeto_original}

══════════════════════════════════════════════════════
ETP JA ELABORADO (FONTE PRIMARIA — NAO CONTRADIGA)
══════════════════════════════════════════════════════

{etp.get("documento_markdown", "")}

══════════════════════════════════════════════════════
CONTEXTO COMPLEMENTAR DOS DEMAIS AGENTES
══════════════════════════════════════════════════════

{json.dumps(contexto_consolidado, ensure_ascii=False, indent=2)}

══════════════════════════════════════════════════════
INSTRUCAO FINAL
══════════════════════════════════════════════════════

Com base no ETP acima e no contexto complementar, elabore
o Termo de Referencia completo seguindo rigorosamente a
estrutura do art. 6º, XXIII da Lei 14.133/2021.

Preencha objeto_tr com:
{objeto_original}

O TR deve ser CONSISTENTE com o ETP — nao contradiga valores,
requisitos ou justificativas ja apresentados no ETP.

O campo documento_markdown deve conter o TR completo e
autossuficiente, formatado com cabecalhos ## para cada secao
(alineas a) a i) do art. 6º, XXIII).
"""

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA,
        )

        dados["fonte"] = "Redator TR"
        dados["versao_agente"] = "1.0"
        dados["status"] = "concluido"

        logger.info("Redator TR: documento gerado com sucesso")

        return dados