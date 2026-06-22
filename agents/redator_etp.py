"""
Agente Redator ETP — Camada 3

Consolida os dados de Scout, Analista Mercado, Jurisprudencia TCU,
Especialista 14.133 e Especialista Tecnico em um Estudo Tecnico
Preliminar completo, seguindo a estrutura do art. 18, §1º da
Lei 14.133/2021.

Roda ANTES do Redator TR — o TR depende do ETP gerado aqui.
"""

import json
import logging

from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor
from docx import Document
from datetime import datetime

logger = logging.getLogger(__name__)


class RedatorETP:

    SCHEMA = "schemas/redator_etp_schema.json"

    def executar(self, contexto: dict) -> dict:

        prompt_sistema = load_prompt("redator_etp")

        objeto_original = (
            contexto.get("objeto_original")
            or contexto.get("objeto_contratacao")
        )
        if not objeto_original:
            raise Exception("OBJETO_ORIGINAL_NAO_LOCALIZADO")

        # --------------------------------------------------
        # Coleta o contexto de todos os agentes anteriores
        # --------------------------------------------------

        scout = contexto.get("scout", {})
        analista_mercado = contexto.get("analista_mercado", {})
        jurisprudencia_tcu = contexto.get("jurisprudencia_tcu", {})
        especialista_14133 = contexto.get("especialista_14133", {})
        especialista_tecnico = contexto.get("especialista_tecnico", {})

        logger.info(
            f"Redator ETP: consolidando dados para '{objeto_original}'"
        )

        # --------------------------------------------------
        # Monta o prompt com todo o contexto consolidado
        # --------------------------------------------------

        contexto_consolidado = {
            "scout": scout,
            "analista_mercado": analista_mercado,
            "jurisprudencia_tcu": jurisprudencia_tcu,
            "especialista_14133": especialista_14133,
            "especialista_tecnico": especialista_tecnico,
        }

        prompt_final = f"""
{prompt_sistema}

══════════════════════════════════════════════════════
OBJETO DA CONTRATACAO
══════════════════════════════════════════════════════

{objeto_original}

══════════════════════════════════════════════════════
CONTEXTO CONSOLIDADO DOS AGENTES ANTERIORES
══════════════════════════════════════════════════════

{json.dumps(contexto_consolidado, ensure_ascii=False, indent=2)}

══════════════════════════════════════════════════════
INSTRUCAO FINAL
══════════════════════════════════════════════════════

Com base no contexto acima, elabore o ETP completo seguindo
rigorosamente a estrutura do art. 18, §1º da Lei 14.133/2021.

Preencha objeto_etp com:
{objeto_original}

Lembre-se: os incisos I, IV, VI, VIII e XIII sao OBRIGATORIOS
e nao podem ficar vazios ou genericos.

O campo documento_markdown deve conter o ETP completo e
autossuficiente, formatado com cabecalhos ## para cada secao.
"""

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA,
        )

        doc = Document()

        doc.add_heading(
            "ESTUDO TÉCNICO PRELIMINAR",
            level=1
        )

        for linha in dados["documento_markdown"].splitlines():

            if linha.startswith("## "):
                doc.add_heading(
                    linha.replace("## ", ""),
                    level=2
                )

            elif linha.strip():
                doc.add_paragraph(linha)

        arquivo = (
            f"ETP_"
            f"{datetime.now():%Y%m%d_%H%M%S}.docx"
        )

        doc.save(arquivo)

        dados["arquivo_docx"] = arquivo
        dados["fonte"] = "Redator ETP"
        dados["versao_agente"] = "1.0"
        dados["status"] = "concluido"

        logger.info("Redator ETP: documento gerado com sucesso")
        
        return dados
