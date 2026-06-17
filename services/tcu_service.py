"""
TCU Service — Camada 2

Realiza buscas reais na API pública do TCU:
  https://dados-abertos.apps.tcu.gov.br/api/acordao/recupera-acordaos

A API retorna acórdãos paginados por índice (sem busca textual).
Estratégia:
  1. Buscar lotes de acórdãos recentes por página
  2. Filtrar localmente por relevância (palavras-chave no título/sumário)
  3. Retornar os 3 mais relevantes (configurável)

Busca hierárquica em 4 níveis:
  Nível 1 → palavras-chave específicas do objeto
  Nível 2 → subcategorias identificadas pelo Scout
  Nível 3 → categoria + termos do objeto
  Nível 4 → termos genéricos de contratação TI
"""

import re
import time
import logging
import requests

logger = logging.getLogger(__name__)

TCU_API_BASE = (
    "https://dados-abertos.apps.tcu.gov.br"
    "/api/acordao/recupera-acordaos"
)

TCU_PESQUISA_BASE = (
    "https://pesquisa.apps.tcu.gov.br"
    "/resultado/acordao-completo"
)

TIMEOUT_SEGUNDOS = 10
MAX_ACORDAOS_RETORNO = 3
LOTE_BUSCA = 50

MAPA_COLEGIADO = {
    "plenário": "Plenario",
    "plenario": "Plenario",
    "primeira câmara": "Primeira Camara",
    "primeira camara": "Primeira Camara",
    "segunda câmara": "Segunda Camara",
    "segunda camara": "Segunda Camara",
}


def _normalizar_colegiado(valor: str) -> str:
    if not valor:
        return "Nao Informado"
    return MAPA_COLEGIADO.get(valor.strip().lower(), "Nao Informado")


def _pontuar_relevancia(acordao: dict, palavras: list) -> int:
    texto = " ".join([
        acordao.get("titulo", ""),
        acordao.get("sumario", ""),
    ]).lower()
    return sum(1 for p in palavras if p.lower() in texto)


def _formatar_acordao(acordao: dict, score: int) -> dict:
    numero = acordao.get("numeroAcordao", "")
    ano = acordao.get("anoAcordao", "")
    colegiado_raw = acordao.get("colegiado", "")
    colegiado = _normalizar_colegiado(colegiado_raw)

    nome_acordao = (
        f"Acórdão {numero}/{ano}-TCU-"
        f"{colegiado_raw or 'Plenário'}"
    )

    try:
        ano_int = int(ano)
    except (ValueError, TypeError):
        ano_int = 2000

    url_acordao = acordao.get("urlAcordao", "")
    if not url_acordao:
        url_acordao = f"{TCU_PESQUISA_BASE}/{numero}%252F{ano}"

    if score >= 3:
        relevancia = "Alta"
    elif score >= 1:
        relevancia = "Media"
    else:
        relevancia = "Baixa"

    sumario = acordao.get("sumario", "") or acordao.get("titulo", "")

    return {
        "acordao": nome_acordao,
        "colegiado": colegiado,
        "ano": ano_int,
        "tema": acordao.get("titulo", ""),
        "resumo": sumario[:800],
        "link_referencia": url_acordao,
        "link_verificado": bool(url_acordao),
        "aplicabilidade": "Indireta",
        "relevancia": relevancia,
        "tipo_fonte": "Acordao",
        "peso_recomendacao": min(10, max(1, score + 5)),
        "fonte_verificada": True,
    }


def _buscar_por_palavras_chave(
    palavras: list,
    max_resultados: int = MAX_ACORDAOS_RETORNO,
) -> list:
    candidatos = []
    inicio = 1

    for pagina in range(3):
        try:
            resp = requests.get(
                TCU_API_BASE,
                params={"inicio": inicio, "quantidade": LOTE_BUSCA},
                timeout=TIMEOUT_SEGUNDOS,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            acordaos = resp.json()

        except requests.exceptions.Timeout:
            logger.warning(f"TCU API: timeout (página {pagina + 1})")
            break
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"TCU API: conexão falhou: {e}")
            break
        except Exception as e:
            logger.warning(f"TCU API: erro: {e}")
            break

        if not acordaos:
            break

        for a in acordaos:
            score = _pontuar_relevancia(a, palavras)
            if score > 0:
                candidatos.append((score, a))

        inicio += LOTE_BUSCA
        time.sleep(0.3)

    candidatos.sort(key=lambda x: x[0], reverse=True)
    return [
        _formatar_acordao(a, s)
        for s, a in candidatos[:max_resultados]
    ]


def buscar_jurisprudencia(
    objeto: str,
    palavras_chave: list,
    categoria: str,
    subcategorias: list,
    max_resultados: int = MAX_ACORDAOS_RETORNO,
) -> dict:
    """
    Busca hierárquica de jurisprudência do TCU.

    Retorna:
      acordaos        : lista formatada para o schema
      nivel_busca     : nível hierárquico onde encontrou
      total_encontrado: quantidade de resultados
      status          : SUCESSO | SEM_RESULTADO | ERRO_API
      erro            : mensagem de erro (se houver)
    """
    termos_objeto = [
        t for t in re.sub(r"[^\w\s]", " ", objeto).split()
        if len(t) > 3
    ]

    grupos = [
        palavras_chave,
        subcategorias,
        ([categoria] + termos_objeto[:3]) if categoria else termos_objeto[:3],
        ["contratação", "tecnologia", "software", "sistema", "licitação"],
    ]

    for nivel, palavras in enumerate(grupos, start=1):
        validas = [p for p in palavras if p and len(p) > 2]
        if not validas:
            continue

        logger.info(
            f"TCU: buscando nível {nivel} — {validas}"
        )

        try:
            resultados = _buscar_por_palavras_chave(
                validas, max_resultados
            )
        except Exception as e:
            return {
                "acordaos": [],
                "nivel_busca": nivel,
                "total_encontrado": 0,
                "status": "ERRO_API",
                "erro": str(e),
            }

        if resultados:
            logger.info(
                f"TCU: {len(resultados)} resultado(s) no nível {nivel}"
            )
            return {
                "acordaos": resultados,
                "nivel_busca": nivel,
                "total_encontrado": len(resultados),
                "status": "SUCESSO",
                "erro": None,
            }

    return {
        "acordaos": [],
        "nivel_busca": len(grupos),
        "total_encontrado": 0,
        "status": "SEM_RESULTADO",
        "erro": None,
    }