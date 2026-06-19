"""
Agente Jurisprudência TCU — v4.0

MUDANÇA ESTRUTURAL (corrige a alucinação definitivamente):

  Na v3.0, o modelo recebia os acórdãos reais e era INSTRUÍDO a
  copiá-los para jurisprudencias_relevantes. Mas o modelo (mesmo
  orientado) reescrevia os acórdãos com números e textos
  inventados, e ainda chegava a omitir campos obrigatórios do
  schema (status_pesquisa), causando falha total.

  Na v4.0, o código NÃO PEDE ao modelo para reproduzir os
  acórdãos. Os campos fixos (jurisprudencias_relevantes,
  status_pesquisa, fonte_consultada, evidencias_utilizadas,
  nivel_evidencia, grau_aderencia_objeto, dependencia_evidencia,
  nivel_confianca, objeto_analisado) são MONTADOS DIRETAMENTE
  EM PYTHON a partir do retorno real da API.

  O modelo só é chamado para gerar os campos analíticos que
  exigem raciocínio:
    - teses_aplicaveis
    - riscos_identificados
    - boas_praticas
    - recomendacoes_para_etp
    - recomendacoes_para_tr
    - alertas_controle_externo
    - categoria_contratacao
    - palavras_chaves
    - justificativa_status
    - conclusao_executiva

  Isso elimina estruturalmente a possibilidade de o modelo
  inventar acórdãos: ele nunca tem a chance de escrever esse
  campo, porque o campo já chega pronto e é apenas MESCLADO
  ao final.
"""

import json
import logging

from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor
from services.tcu_service import buscar_jurisprudencia

logger = logging.getLogger(__name__)


# ======================================================
# SCHEMA REDUZIDO — apenas os campos analíticos
# que o modelo deve preencher.
# (jurisprudencias_relevantes e os demais campos fixos
# são adicionados depois, em Python)
# ======================================================

SCHEMA_ANALITICO = "schemas/jurisprudencia_tcu_analitico_schema.json"


class JurisprudenciaTCU:

    SCHEMA = "schemas/jurisprudencia_tcu_schema.json"

    def executar(self, contexto: dict) -> dict:

        prompt_sistema = load_prompt("jurisprudencia_tcu")

        # 1. Extração do objeto
        objeto_original = (
            contexto.get("objeto_original")
            or contexto.get("objeto_contratacao")
        )
        if not objeto_original:
            raise Exception("OBJETO_ORIGINAL_NAO_LOCALIZADO")

        # 2. Contexto do Scout
        scout = contexto.get("scout", {})
        palavras_chave = scout.get("palavras_chave", [])
        categoria = scout.get("categoria", "")
        subcategorias = scout.get("subcategorias", [])

        # 3. Busca real na API do TCU
        logger.info(f"Jurisprudencia TCU: buscando '{objeto_original}'")

        resultado = buscar_jurisprudencia(
            objeto=objeto_original,
            palavras_chave=palavras_chave,
            categoria=categoria,
            subcategorias=subcategorias,
        )

        acordaos    = resultado["acordaos"]
        status_api  = resultado["status"]
        nivel_busca = resultado["nivel_busca"]
        erro_api    = resultado.get("erro")

        logger.info(
            f"TCU API: status={status_api}, "
            f"nivel={nivel_busca}, total={len(acordaos)}"
        )

        # ==================================================
        # CAMINHO A — Acórdãos encontrados
        # ==================================================
        if acordaos:
            dados_finais = self._montar_com_evidencia(
                objeto_original=objeto_original,
                acordaos=acordaos,
                nivel_busca=nivel_busca,
                prompt_sistema=prompt_sistema,
            )

        # ==================================================
        # CAMINHO B — Sem acórdãos (SEM_EVIDENCIA)
        # Não precisa chamar o modelo — é determinístico.
        # ==================================================
        else:
            dados_finais = self._montar_sem_evidencia(
                objeto_original=objeto_original,
                nivel_busca=nivel_busca,
                erro_api=erro_api,
            )

        dados_finais["fonte"]         = "Jurisprudencia TCU"
        dados_finais["versao_agente"] = "4.0"
        dados_finais["status"]        = "concluido"

        return dados_finais

    # ======================================================
    # CAMINHO A — monta o JSON com acórdãos reais
    # ======================================================

    def _montar_com_evidencia(
        self,
        objeto_original: str,
        acordaos: list,
        nivel_busca: int,
        prompt_sistema: str,
    ) -> dict:

        # ---- Pede ao modelo APENAS os campos analíticos ----
        acordaos_resumo = "\n".join(
            f"- {a['acordao']} ({a['colegiado']}, {a['ano']}): "
            f"{a['tema']} — {a['resumo'][:300]}"
            for a in acordaos
        )

        prompt_final = f"""
{prompt_sistema}

══════════════════════════════════════════════════════
OBJETO DA CONTRATACAO
══════════════════════════════════════════════════════

{objeto_original}

══════════════════════════════════════════════════════
ACORDAOS REAIS JA CONFIRMADOS (NAO OS REESCREVA)
══════════════════════════════════════════════════════

Os acordaos abaixo JA FORAM VALIDADOS e serao inseridos
automaticamente no resultado final. Voce NAO precisa e
NAO DEVE reproduzi-los. Use-os apenas como base de
RACIOCINIO para preencher os campos analiticos abaixo.

{acordaos_resumo}

══════════════════════════════════════════════════════
TAREFA — RESPONDA SOMENTE COM ESTE JSON
══════════════════════════════════════════════════════

Retorne EXCLUSIVAMENTE um JSON com esta estrutura exata,
sem nenhum outro campo:

{{
  "categoria_contratacao": "string — categoria da contratacao",
  "teses_aplicaveis": ["lista de teses extraidas dos acordaos acima"],
  "riscos_identificados": ["lista de riscos identificados"],
  "boas_praticas": ["lista de boas praticas recomendadas"],
  "recomendacoes_para_etp": ["lista de recomendacoes para o ETP"],
  "recomendacoes_para_tr": ["lista de recomendacoes para o TR"],
  "alertas_controle_externo": ["lista de alertas de controle externo"],
  "palavras_chaves": ["palavras-chave relevantes"],
  "justificativa_status": "string — por que SUCESSO foi atingido",
  "conclusao_executiva": "string — conclusao executiva da analise"
}}

REGRAS:
- NAO inclua o campo jurisprudencias_relevantes.
- NAO inclua o campo status_pesquisa.
- NAO inclua o campo objeto_analisado.
- NAO inclua nenhum campo alem dos listados acima.
- Cada lista deve ter pelo menos 1 item.
- Toda tese/risco/recomendacao deve estar vinculada aos
  acordaos apresentados.
"""

        dados_analiticos = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=SCHEMA_ANALITICO,
        )

        # ---- Monta os campos FIXOS em Python (sem o modelo) ----
        evidencias_utilizadas = [a["acordao"] for a in acordaos]

        dados_finais = {
            "objeto_analisado": objeto_original,
            "status_pesquisa": "SUCESSO",
            "categoria_contratacao": dados_analiticos.get(
                "categoria_contratacao", ""
            ),
            "jurisprudencias_relevantes": acordaos,
            "teses_aplicaveis": dados_analiticos.get(
                "teses_aplicaveis", []
            ),
            "riscos_identificados": dados_analiticos.get(
                "riscos_identificados", []
            ),
            "boas_praticas": dados_analiticos.get(
                "boas_praticas", []
            ),
            "recomendacoes_para_etp": dados_analiticos.get(
                "recomendacoes_para_etp", []
            ),
            "recomendacoes_para_tr": dados_analiticos.get(
                "recomendacoes_para_tr", []
            ),
            "alertas_controle_externo": dados_analiticos.get(
                "alertas_controle_externo", []
            ),
            "nivel_confianca": 75,
            "nivel_evidencia": "ANALOGA",
            "palavras_chaves": dados_analiticos.get(
                "palavras_chaves", []
            ),
            "justificativa_status": dados_analiticos.get(
                "justificativa_status",
                f"Acordaos reais do TCU localizados no nivel "
                f"{nivel_busca} de busca hierarquica.",
            ),
            "conclusao_executiva": dados_analiticos.get(
                "conclusao_executiva", ""
            ),
            "fonte_consultada": "TCU",
            "indicador_alucinacao": False,
            "evidencias_utilizadas": evidencias_utilizadas,
            "grau_aderencia_objeto": "ANALOGO",
            "dependencia_evidencia": "PARCIAL",
        }

        return dados_finais

    # ======================================================
    # CAMINHO B — SEM_EVIDENCIA (determinístico, sem LLM)
    # ======================================================

    def _montar_sem_evidencia(
        self,
        objeto_original: str,
        nivel_busca: int,
        erro_api: str | None,
    ) -> dict:

        motivo = erro_api or (
            f"Nenhum acordao relevante encontrado apos "
            f"{nivel_busca} nivel(is) de busca hierarquica."
        )

        return {
            "objeto_analisado": objeto_original,
            "status_pesquisa": "SEM_EVIDENCIA",
            "jurisprudencias_relevantes": [],
            "teses_aplicaveis": [],
            "riscos_identificados": [],
            "boas_praticas": [],
            "recomendacoes_para_etp": [],
            "recomendacoes_para_tr": [],
            "alertas_controle_externo": [],
            "evidencias_utilizadas": [],
            "nivel_confianca": 20,
            "nivel_evidencia": "GENERICA",
            "justificativa_status": motivo,
            "conclusao_executiva": (
                "Nao foram localizadas evidencias do TCU "
                "aplicaveis ao objeto analisado."
            ),
            "fonte_consultada": "NAO_LOCALIZADA",
            "indicador_alucinacao": False,
            "grau_aderencia_objeto": "NAO_IDENTIFICADO",
            "dependencia_evidencia": "INEXISTENTE",
        }