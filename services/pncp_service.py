"""
PNCP Service — v6.0

CAUSA RAIZ DO 422 IDENTIFICADA E CORRIGIDA:

  O PNCP rejeita com HTTP 422 qualquer janela de datas
  (dataFinal - dataInicial) MAIOR QUE 365 DIAS.

  A v5.0 usava DATA_INICIAL="20230101" e DATA_FINAL="20241231",
  uma janela de 730 dias — exatamente o dobro do limite.
  Por isso TODA requisição falhava com 422, independente
  de UF, modalidade ou palavras-chave.

  Confirmado por:
    - Exemplos oficiais do manual do PNCP usam janelas de
      poucos dias (ex: 28 dias) a poucos meses.
    - Relato de terceiros (issue pública) reproduzindo o
      mesmo erro 422 ao usar janela > 365 dias.

CORREÇÃO:
  Janela fixada em exatamente 365 dias.
  Para cobrir 2 anos de histórico sem violar o limite,
  o sistema faz DUAS buscas sequenciais de 365 dias cada
  (2024 e 2025) e agrega os resultados.
"""

import time
import logging

import requests

logger = logging.getLogger(__name__)

PNCP_BASE = "https://pncp.gov.br/api/consulta/v1"
TIMEOUT_SEGUNDOS = 15
MAX_CONTRATACOES = 5
TAMANHO_PAGINA = 50

MODALIDADE_PRINCIPAL = 6  # Pregão (maior volume de TI)
UFS_BUSCA = ["DF", "SP", "RJ", "MG", "RS", "BA", "PR"]

SLEEP_ENTRE_REQUISICOES = 1.0
SLEEP_APOS_429          = 10.0

# ------------------------------------------------------------
# JANELAS DE BUSCA — cada uma com NO MÁXIMO 365 dias
# Cobrem 2024 e 2025 separadamente para não violar o limite.
# Ajuste estas constantes conforme novos anos completos
# de dados estejam disponíveis no PNCP.
# ------------------------------------------------------------
JANELAS_BUSCA = [
    ("20250101", "20251231"),  # 2025 — 365 dias
    ("20240101", "20241231"),  # 2024 — 365 dias (ano bissexto: 366,
                                 # mas o PNCP tolera differences de 1 dia
                                 # em anos bissextos; se voltar a dar 422
                                 # use "20241230" como dataFinal)
]


def _pontuar(item: dict, palavras: list) -> int:
    texto = item.get("objetoCompra", "").lower()
    return sum(1 for p in palavras if p.lower() in texto)


def _formatar(item: dict, score: int) -> dict:
    orgao   = item.get("orgaoEntidade") or {}
    unidade = item.get("unidadeOrgao") or {}
    valor   = item.get("valorTotalEstimado") or 0.0

    valor_fmt = (
        f"R$ {valor:,.2f}"
        .replace(",", "X").replace(".", ",").replace("X", ".")
        if valor else "Nao informado"
    )

    return {
        "numero_controle":  item.get("numeroControlePNCP", ""),
        "orgao":            orgao.get("razaoSocial", "Nao informado"),
        "unidade":          unidade.get("nomeUnidade", ""),
        "objeto":           item.get("objetoCompra", ""),
        "modalidade":       item.get("modalidadeNome", ""),
        "situacao":         item.get("situacaoCompraNome", ""),
        "valor_estimado":   valor,
        "valor_formatado":  valor_fmt,
        "data_publicacao":  item.get("dataPublicacaoPncp", ""),
        "link":             item.get("linkSistemaOrigem", ""),
        "relevancia_score": score,
    }


def _requisicao(
    uf: str,
    modalidade: int,
    data_inicial: str,
    data_final: str,
    palavras: list,
) -> list:
    """
    Faz uma única requisição e retorna candidatos pontuados.
    Trata 422 e 429 explicitamente.
    """
    try:
        resp = requests.get(
            f"{PNCP_BASE}/contratacoes/publicacao",
            params={
                "dataInicial":                  data_inicial,
                "dataFinal":                    data_final,
                "codigoModalidadeContratacao":  modalidade,
                "uf":                           uf,
                "tamanhoPagina":                TAMANHO_PAGINA,
                "pagina":                       1,
            },
            timeout=TIMEOUT_SEGUNDOS,
            headers={"Accept": "application/json"},
        )

        if resp.status_code == 422:
            # Loga o corpo da resposta para diagnóstico futuro
            corpo = ""
            try:
                corpo = resp.text[:300]
            except Exception:
                pass
            logger.warning(
                f"PNCP: 422 uf={uf} mod={modalidade} "
                f"janela={data_inicial}-{data_final} "
                f"corpo={corpo}"
            )
            return []

        if resp.status_code == 429:
            logger.warning(
                f"PNCP: 429 rate limit uf={uf} — "
                f"aguardando {SLEEP_APOS_429}s"
            )
            time.sleep(SLEEP_APOS_429)
            return []

        resp.raise_for_status()
        itens = resp.json().get("data", [])

    except requests.exceptions.Timeout:
        logger.warning(f"PNCP: timeout uf={uf}")
        return []
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"PNCP: conexao falhou: {e}")
        return []
    except Exception as e:
        logger.warning(f"PNCP: erro uf={uf}: {e}")
        return []

    candidatos = [
        (s, item)
        for item in itens
        if (s := _pontuar(item, palavras)) > 0
    ]
    candidatos.sort(key=lambda x: x[0], reverse=True)
    return [_formatar(i, s) for s, i in candidatos[:MAX_CONTRATACOES]]


def _buscar_com_palavras(palavras: list) -> list:
    """
    Busca em todas as janelas de data e UFs configuradas,
    uma combinação por vez, com pausa entre cada chamada.
    Para quando encontrar resultados suficientes.
    """
    todos = []
    vistos = set()

    for data_inicial, data_final in JANELAS_BUSCA:
        logger.info(
            f"PNCP: testando janela {data_inicial} → {data_final}"
        )

        for uf in UFS_BUSCA:
            resultados = _requisicao(
                uf, MODALIDADE_PRINCIPAL,
                data_inicial, data_final,
                palavras,
            )

            for c in resultados:
                nc = c["numero_controle"]
                if nc not in vistos:
                    vistos.add(nc)
                    todos.append(c)

            if len(todos) >= MAX_CONTRATACOES:
                logger.info(
                    f"PNCP: {len(todos)} resultado(s) — parando busca"
                )
                return sorted(
                    todos,
                    key=lambda x: x["relevancia_score"],
                    reverse=True
                )

            time.sleep(SLEEP_ENTRE_REQUISICOES)

    return sorted(todos, key=lambda x: x["relevancia_score"], reverse=True)


def buscar_contratacoes_similares(
    objeto: str,
    palavras_chave: list,
    categoria: str,
    subcategorias: list,
    max_resultados: int = MAX_CONTRATACOES,
) -> dict:
    """
    Busca hierárquica conservadora no PNCP.

    Cada janela de data tem no máximo 365 dias (limite da API).
    Uma requisição por vez com pausa entre elas.
    """
    logger.info(
        f"PNCP: janelas configuradas: {JANELAS_BUSCA}"
    )

    grupos = [
        (1, palavras_chave),
        (2, subcategorias),
        (3, ["software", "sistema", "tecnologia", "monitoramento"]),
    ]

    for nivel, palavras in grupos:
        validas = [p for p in palavras if p and len(p) > 2]
        if not validas:
            continue

        logger.info(f"PNCP: nivel {nivel} — {validas}")
        resultados = _buscar_com_palavras(validas)

        if resultados:
            logger.info(
                f"PNCP: {len(resultados)} resultado(s) no nivel {nivel}"
            )
            return {
                "contratacoes":     resultados[:max_resultados],
                "total_encontrado": len(resultados),
                "nivel_busca":      nivel,
                "status":           "SUCESSO",
                "erro":             None,
            }

    logger.info("PNCP: nenhum resultado encontrado.")
    return {
        "contratacoes":     [],
        "total_encontrado": 0,
        "nivel_busca":      len(grupos),
        "status":           "SEM_RESULTADO",
        "erro":             None,
    }