import logging

from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor
from services.tcu_service import buscar_jurisprudencia

logger = logging.getLogger(__name__)


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
        logger.info(
            f"Jurisprudencia TCU: buscando para '{objeto_original}'"
        )

        resultado_busca = buscar_jurisprudencia(
            objeto=objeto_original,
            palavras_chave=palavras_chave,
            categoria=categoria,
            subcategorias=subcategorias,
        )

        acordaos = resultado_busca["acordaos"]
        status_api = resultado_busca["status"]
        nivel_busca = resultado_busca["nivel_busca"]
        erro_api = resultado_busca.get("erro")

        logger.info(
            f"TCU API: status={status_api}, "
            f"nivel={nivel_busca}, "
            f"total={len(acordaos)}"
        )

        # 4. Monta bloco de contexto com acórdãos reais
        if acordaos:
            linhas = []
            for i, a in enumerate(acordaos, start=1):
                linhas.append(
                    f"ACORDAO {i}:\n"
                    f"  Identificacao : {a['acordao']}\n"
                    f"  Colegiado     : {a['colegiado']}\n"
                    f"  Ano           : {a['ano']}\n"
                    f"  Tema          : {a['tema']}\n"
                    f"  Resumo        : {a['resumo']}\n"
                    f"  Link          : {a['link_referencia']}\n"
                    f"  Relevancia    : {a['relevancia']}\n"
                )

            bloco_acordaos = (
                f"ACORDAOS REAIS ENCONTRADOS NA API DO TCU "
                f"(nivel de busca: {nivel_busca}):\n\n"
                + "\n".join(linhas)
                + "\n\nIMPORTANTE:\n"
                  "- Use SOMENTE estes acordaos como evidencias.\n"
                  "- NAO invente outros acordaos.\n"
                  "- Copie os dados acima exatamente.\n"
                  "- Para o campo colegiado use o valor "
                  "exato da linha 'Colegiado' acima.\n"
            )

            instrucao_status = (
                'Foram encontrados acordaos reais do TCU.\n'
                'Use-os em jurisprudencias_relevantes.\n'
                'Defina status_pesquisa = "SUCESSO".\n'
                'nivel_evidencia deve ser "ANALOGA" ou "DIRETA".\n'
                'nivel_confianca deve ser entre 60 e 100.\n'
            )

        else:
            bloco_acordaos = (
                "RESULTADO DA BUSCA NA API DO TCU:\n\n"
                "Nenhum acordao relevante encontrado "
                f"apos {nivel_busca} nivel(is) de busca.\n"
                + (f"Erro: {erro_api}\n" if erro_api else "")
            )

            instrucao_status = (
                'Nenhuma evidencia real foi encontrada.\n'
                'Defina status_pesquisa = "SEM_EVIDENCIA".\n'
                'Mantenha jurisprudencias_relevantes = [].\n'
                'Mantenha todas as outras listas vazias.\n'
                'NAO invente acordaos.\n'
                'nivel_evidencia deve ser "GENERICA".\n'
                'nivel_confianca deve ser entre 0 e 40.\n'
                'fonte_consultada = "NAO_LOCALIZADA".\n'
                'grau_aderencia_objeto = "NAO_IDENTIFICADO".\n'
                'dependencia_evidencia = "INEXISTENTE".\n'
            )

        # 5. Formata listas para o prompt
        palavras_fmt = (
            "\n".join(f"- {p}" for p in palavras_chave)
            if palavras_chave else "(nao informado)"
        )
        subcategorias_fmt = (
            "\n".join(f"- {s}" for s in subcategorias)
            if subcategorias else "(nao informado)"
        )

        # 6. Prompt final com objeto ancorado 3x
        prompt_final = f"""
╔══════════════════════════════════════════════════════╗
  OBJETO DA CONTRATACAO — REFERENCIA OBRIGATORIA
╚══════════════════════════════════════════════════════╝

{objeto_original}

Copie este texto LITERALMENTE no campo objeto_analisado.
Nao resuma. Nao substitua. Nao generalize.

══════════════════════════════════════════════════════
{prompt_sistema}

══════════════════════════════════════════════════════
DADOS DA PESQUISA
══════════════════════════════════════════════════════

OBJETO DA CONTRATACAO:
{objeto_original}

CATEGORIA:
{categoria or "(nao informado)"}

SUBCATEGORIAS:
{subcategorias_fmt}

PALAVRAS-CHAVE:
{palavras_fmt}

══════════════════════════════════════════════════════
{bloco_acordaos}
══════════════════════════════════════════════════════
INSTRUCOES PARA RESPOSTA
══════════════════════════════════════════════════════

{instrucao_status}

══════════════════════════════════════════════════════
CONFIRMACAO FINAL
══════════════════════════════════════════════════════

Objeto que voce esta analisando:

{objeto_original}

Copie exatamente no campo objeto_analisado.
"""

        # 7. Executa com validação
        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA,
            objeto_original=objeto_original,
        )

        dados["fonte"] = "Jurisprudencia TCU"
        dados["versao_agente"] = "2.0"
        dados["status"] = "concluido"

        return dados