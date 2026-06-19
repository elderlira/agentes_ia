"""
TCU Service — v3.0

Correção:
  'sequence item 1: expected str instance, NoneType found'
  
  O erro ocorria em _pontuar() ao concatenar campos que podem
  ser None (titulo, sumario). Corrigido com fallback para "".
  
  Também corrigido em _formatar() para garantir que nenhum
  campo None quebre a montagem do dict.
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

TIMEOUT_SEGUNDOS = 10
MAX_ACORDAOS_RETORNO = 3
LOTE_BUSCA = 50
MAX_PAGINAS = 3

MAPA_COLEGIADO = {
    "plenário":      "Plenario",
    "plenario":      "Plenario",
    "primeira câmara": "Primeira Camara",
    "primeira camara": "Primeira Camara",
    "segunda câmara":  "Segunda Camara",
    "segunda camara":  "Segunda Camara",
}


def _str(valor) -> str:
    """Converte qualquer valor para str segura (None → '')."""
    return str(valor) if valor is not None else ""


def _normalizar_colegiado(valor) -> str:
    if not valor:
        return "Nao Informado"
    return MAPA_COLEGIADO.get(_str(valor).strip().lower(), "Nao Informado")


def _pontuar(acordao: dict, palavras: list) -> int:
    # Usa _str() para evitar TypeError com campos None
    texto = " ".join([
        _str(acordao.get("titulo")),
        _str(acordao.get("sumario")),
    ]).lower()
    return sum(1 for p in palavras if _str(p).lower() in texto)


def _formatar(acordao: dict, score: int) -> dict:
    numero      = _str(acordao.get("numeroAcordao"))
    ano         = _str(acordao.get("anoAcordao"))
    colegiado_raw = _str(acordao.get("colegiado"))
    colegiado   = _normalizar_colegiado(colegiado_raw)

    nome = (
        f"Acórdão {numero}/{ano}-TCU-"
        f"{colegiado_raw or 'Plenário'}"
    )

    try:
        ano_int = int(ano)
    except (ValueError, TypeError):
        ano_int = 2000

    url = _str(acordao.get("urlAcordao"))

    if score >= 3:
        relevancia = "Alta"
    elif score >= 1:
        relevancia = "Media"
    else:
        relevancia = "Baixa"

    # Sumário com fallback para título
    sumario = _str(acordao.get("sumario")) or _str(acordao.get("titulo"))

    return {
        "acordao":          nome,
        "colegiado":        colegiado,
        "ano":              ano_int,
        "tema":             _str(acordao.get("titulo")),
        "resumo":           sumario[:800],
        "link_referencia":  url or f"https://pesquisa.apps.tcu.gov.br/resultado/acordao-completo/{numero}%252F{ano}",
        "link_verificado":  bool(url),
        "aplicabilidade":   "Indireta",
        "relevancia":       relevancia,
        "tipo_fonte":       "Acordao",
        "peso_recomendacao": min(10, max(1, score + 5)),
        "fonte_verificada": True,
    }


def _buscar_nivel(palavras: list, max_resultados: int) -> tuple:
    """
    Retorna (resultados, erro_str | None).
    Erro de rede → ([], mensagem).
    Sem resultado → ([], None).
    Com resultado → (lista, None).
    """
    candidatos = []
    inicio = 1

    for pagina in range(1, MAX_PAGINAS + 1):
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
            return [], f"timeout pagina {pagina}"
        except requests.exceptions.ConnectionError as e:
            return [], f"conexao falhou: {e}"
        except requests.exceptions.HTTPError as e:
            return [], f"HTTP error: {e}"
        except Exception as e:
            return [], f"erro inesperado: {e}"

        if not acordaos:
            break

        for a in acordaos:
            score = _pontuar(a, palavras)
            if score > 0:
                candidatos.append((score, a))

        inicio += LOTE_BUSCA
        time.sleep(0.3)

    candidatos.sort(key=lambda x: x[0], reverse=True)
    return [_formatar(a, s) for s, a in candidatos[:max_resultados]], None


def buscar_jurisprudencia(
    objeto: str,
    palavras_chave: list,
    categoria: str,
    subcategorias: list,
    max_resultados: int = MAX_ACORDAOS_RETORNO,
) -> dict:
    """
    Busca hierárquica — erro em um nível não aborta os demais.
    """
    termos_objeto = [
        t for t in re.sub(r"[^\w\s]", " ", objeto).split()
        if len(t) > 3
    ]

    grupos = [
        (1, palavras_chave),
        (2, subcategorias),
        (3, ([categoria] + termos_objeto[:3]) if categoria else termos_objeto[:3]),
        (4, ["contratação", "tecnologia", "software", "sistema"]),
    ]

    erros = []

    for nivel, palavras in grupos:
        validas = [_str(p) for p in palavras if p and len(_str(p)) > 2]
        if not validas:
            continue

        logger.info(f"TCU: nivel {nivel} — {validas}")

        resultados, erro = _buscar_nivel(validas, max_resultados)

        if erro:
            erros.append(f"Nivel {nivel}: {erro}")
            logger.warning(f"TCU: nivel {nivel} com erro — {erro}")
            continue

        if resultados:
            logger.info(f"TCU: {len(resultados)} resultado(s) no nivel {nivel}")
            return {
                "acordaos":        resultados,
                "nivel_busca":     nivel,
                "total_encontrado": len(resultados),
                "status":          "SUCESSO",
                "erro":            None,
            }

        logger.info(f"TCU: nivel {nivel} sem resultados relevantes")

    if erros:
        return {
            "acordaos":        [],
            "nivel_busca":     len(grupos),
            "total_encontrado": 0,
            "status":          "ERRO_API",
            "erro":            " | ".join(erros),
        }

    return {
        "acordaos":        [],
        "nivel_busca":     len(grupos),
        "total_encontrado": 0,
        "status":          "SEM_RESULTADO",
        "erro":            None,
    }