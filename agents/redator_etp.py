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

Lembre-se: os incisos I, IV, VI, VIII e XIII são obrigatórios
e não podem ficar vazios, resumidos ou genéricos.

Preencha todas as seções com conteúdo completo.
Não gere documento_markdown.
Retorne apenas os campos definidos no schema.
"""

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA,
        )

        resultado_json = json.dumps(
            dados,
            ensure_ascii=False
        )

        termos_proibidos = [
            "8.666",
            "10.520",
            "Lei nº 8.666",
            "Lei 8.666",
            "Lei nº 10.520",
            "Lei 10.520"
        ]

        for termo in termos_proibidos:
            if termo.lower() in resultado_json.lower():
                raise Exception(
                    f"REFERENCIA_LEGAL_REVOGADA_DETECTADA: {termo}"
                )

        doc = Document()

        doc.add_heading(
            "ESTUDO TÉCNICO PRELIMINAR",
            level=1
        )

        secoes = [
            ("1. Objeto", dados["objeto_etp"]),
            ("2. Descrição da Necessidade", dados["i_descricao_necessidade"]),
            ("3. Previsão no PCA", dados["ii_previsao_pca"]),
            ("4. Requisitos da Contratação", dados["iii_requisitos_contratacao"]),
            ("5. Levantamento de Mercado", dados["iv_levantamento_mercado"]),
            ("6. Estimativa de Quantidades", dados["v_estimativa_quantidades"]),
            ("7. Estimativa do Valor", dados["vi_estimativa_valor"]),
            ("8. Descrição da Solução", dados["vii_descricao_solucoes_existentes"]),
            ("9. Justificativa da Solução", dados["viii_justificativa_solucao_escolhida"]),
            ("10. Impacto Ambiental", dados["ix_estimativa_impacto_ambiental"]),
            ("11. Providências Prévias", dados["x_providencias_previas"]),
            ("12. Contratações Correlatas", dados["xi_contratacoes_correlatas"]),
            ("13. Resultados Pretendidos", dados["xii_resultados_pretendidos"]),
            ("14. Adequação do Ambiente", dados["xiii_providencias_adequacao_ambiente"]),
            ("15. Análise de Riscos", dados["xiv_analise_riscos"]),
            ("16. Posicionamento Conclusivo", dados["posicionamento_conclusivo"]),
        ]

        for titulo, conteudo in secoes:
            doc.add_heading(titulo, level=2)
            doc.add_paragraph(conteudo)

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
