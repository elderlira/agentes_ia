import json
import logging

from prompt_loader import load_prompt
from utils.agent_executor import AgentExecutor
from services.pncp_service import buscar_contratacoes_similares

logger = logging.getLogger(__name__)


class AnalistaMercado:

    SCHEMA = "schemas/analista_mercado_schema.json"

    def executar(self, contexto: dict) -> dict:

        prompt_mercado = load_prompt("analista_mercado")

        # --------------------------------------------------
        # 1. Extração do objeto — mantém compatibilidade
        #    com a chave original "objeto_contratacao"
        # --------------------------------------------------

        objeto = (
            contexto.get("objeto_contratacao")
            or contexto.get("objeto_original")
        )
        if not objeto:
            raise Exception("OBJETO_NAO_LOCALIZADO")

        scout = contexto.get("scout", {})
        palavras_chave = scout.get("palavras_chave", [])
        categoria = scout.get("categoria", "")
        subcategorias = scout.get("subcategorias", [])

        # --------------------------------------------------
        # 2. Busca contratações similares no PNCP
        # --------------------------------------------------

        logger.info(
            f"Analista Mercado: buscando no PNCP "
            f"para '{objeto}'"
        )

        resultado_pncp = buscar_contratacoes_similares(
            objeto=objeto,
            palavras_chave=palavras_chave,
            categoria=categoria,
            subcategorias=subcategorias,
        )

        contratacoes = resultado_pncp["contratacoes"]
        status_pncp = resultado_pncp["status"]
        nivel_busca = resultado_pncp["nivel_busca"]
        erro_pncp = resultado_pncp.get("erro")

        logger.info(
            f"PNCP: status={status_pncp}, "
            f"nivel={nivel_busca}, "
            f"total={len(contratacoes)}"
        )

        # --------------------------------------------------
        # 3. Monta bloco de contexto com contratações reais
        # --------------------------------------------------

        if contratacoes:
            linhas = []
            for i, c in enumerate(contratacoes, start=1):
                linhas.append(
                    f"CONTRATACAO {i}:\n"
                    f"  Orgao          : {c['orgao']}\n"
                    f"  Unidade        : {c['unidade']}\n"
                    f"  Objeto         : {c['objeto']}\n"
                    f"  Modalidade     : {c['modalidade']}\n"
                    f"  Situacao       : {c['situacao']}\n"
                    f"  Valor Estimado : {c['valor_formatado']}\n"
                    f"  Data Publicacao: {c['data_publicacao']}\n"
                    f"  Link PNCP      : {c['link']}\n"
                )

            bloco_pncp = (
                f"CONTRATACOES SIMILARES ENCONTRADAS NO PNCP "
                f"(nivel de busca: {nivel_busca}):\n\n"
                + "\n".join(linhas)
                + "\n\nINSTRUCOES SOBRE OS DADOS DO PNCP:\n"
                  "- Use estes dados reais para embasar sua analise.\n"
                  "- Extraia modelos de disponibilizacao praticados.\n"
                  "- Use os valores para referencia de mercado.\n"
                  "- Liste os objetos em objetos_correlatos_encontrados.\n"
                  "- Referencie as modalidades em "
                  "formas_fornecimento_comuns.\n"
            )
            nota_pncp = (
                "O PNCP retornou contratacoes reais similares.\n"
                "Baseie sua analise prioritariamente nesses dados.\n"
                "Complemente com conhecimento tecnico quando necessario.\n"
            )

        else:
            bloco_pncp = (
                "RESULTADO DA BUSCA NO PNCP:\n\n"
                "Nenhuma contratacao similar encontrada "
                f"apos {nivel_busca} nivel(is) de busca.\n"
                + (f"Erro reportado: {erro_pncp}\n" if erro_pncp else "")
                + "Motivo possivel: objeto especifico ou ainda nao "
                  "publicado no PNCP.\n"
            )
            nota_pncp = (
                "O PNCP nao retornou contratacoes similares.\n"
                "Use seu conhecimento tecnico sobre o mercado.\n"
                "Registre a ausencia em observacoes_relevantes.\n"
            )

        # --------------------------------------------------
        # 4. Prompt final — mantém o json.dumps do scout
        #    que já existia na versão original
        # --------------------------------------------------

        prompt_final = f"""
{prompt_mercado}

OBJETO DA CONTRATACAO:

{objeto}

RESULTADO DO SCOUT:

{json.dumps(scout, ensure_ascii=False, indent=2)}

══════════════════════════════════════════════════════
{bloco_pncp}
══════════════════════════════════════════════════════
INSTRUCAO
══════════════════════════════════════════════════════

{nota_pncp}
"""

        # --------------------------------------------------
        # 5. Executa com validação
        # --------------------------------------------------

        dados = AgentExecutor.executar(
            prompt=prompt_final,
            schema_path=self.SCHEMA,
        )

        dados["fonte"] = "Analista Mercado"
        dados["versao_agente"] = "2.0"
        dados["status"] = "concluido"

        return dados