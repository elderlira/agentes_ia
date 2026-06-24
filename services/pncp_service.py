"""
PNCP Service — v8.0

DIAGNÓSTICO DO TESTE v7.0:
  O log mostrou "consultando 7 UFs em paralelo" mesmo após a
  intenção de reduzir para 2 — o ThreadPoolExecutor(max_workers=2)
  efetivamente limitou a CONCORRÊNCIA real (no máximo 2 requisições
  simultâneas), mas a mensagem de log ainda dizia "7 UFs em paralelo"
  porque o texto do log usava len(UFS_BUSCA) ao invés de MAX_WORKERS.
  Isso causou confusão na leitura, mas o comportamento de
  concorrência=2 estava correto.

  O problema real é outro: com concorrência=2, ainda eram
  necessárias ~4 rodadas de 2 requisições para cobrir as 7 UFs,
  e cada rodada podia levar até 8s (backoff de 429) + 6s (timeout)
  = somando ~22-24s por janela. Com 2 janelas × 3 níveis,
  o pior caso ainda chega a 90+ segundos.

OTIMIZAÇÕES v8.0:

  1. CORRIGIDO o texto do log para refletir o paralelismo real.

  2. REDUZIDO O NÚMERO DE UFs: de 7 para 3 (DF, SP, MG) —
     concentram o maior volume de contratações federais de TI.
     Com concorrência=2 e só 3 UFs, cada janela faz no máximo
     2 rodadas em vez de 4.

  3. SEM RETRY EM 429: ao invés de aguardar 8s e tentar de novo
     (o que dobra o tempo da requisição), agora a UF limitada é
     simplesmente descartada nesta rodada — outras UFs/janelas
     têm chance de compensar. Rate limit em uma UF não deve
     bloquear o pipeline.

  4. EARLY-STOP MAIS AGRESSIVO: para a busca no nível assim que
     header_resultados >= 1 (não espera atingir max_resultados=5),
     já que o objetivo é ter ALGUM contexto real para o modelo,
     não uma lista exaustiva.

  5. TIMEOUT REDUZIDO PARA 5s: suficiente para uma API saudável,
     evita acumular espera em UFs lentas.

  Resultado esperado: pior caso cai de ~90s para ~20-25s.
"""

import time
import logging
import random
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)

PNCP_BASE = "https://pncp.gov.br/api/consulta/v1"

TIMEOUT_SEGUNDOS = 5
MAX_CONTRATACOES = 5
TAMANHO_PAGINA = 50

MODALIDADE_PRINCIPAL = 6  # Pregão (maior volume de TI)

# Reduzido de 7 para 3 UFs — maior concentração de
# contratações federais de TI, menos rodadas necessárias.
UFS_BUSCA = ["DF", "SP", "MG"]

# Concorrência real — no máximo 2 requisições simultâneas
MAX_WORKERS = 2

# SEM retry em 429 — descarta a UF nesta rodada e segue.
# Rate limit pontual não deve duplicar o tempo de espera.
SLEEP_APOS_429 = 0  # mantido por compatibilidade, não usado para retry

# Quantos resultados já bastam para parar a busca no nível atual
MIN_RESULTADOS_PARA_PARAR = 1

# Janela mais recente primeiro
JANELAS_BUSCA = [
    ("20250101", "20251231"),  # 2025
    ("20240101", "20241231"),  # 2024
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
    Faz uma única requisição com micro-delay para evitar bloqueios de 429 por concorrência pura.
    """
    # Adiciona um delay dinâmico pequeno entre 0.1 e 0.6 segundos para quebrar o paralelismo exato
    time.sleep(random.uniform(0.1, 0.6))
    
    try:
        # Mantém exatamente os mesmos parâmetros originais da sua função
        params = {
            "dataInicial":                  data_inicial,
            "dataFinal":                    data_final,
            "codigoModalidadeContratacao":  modalidade,
            "tamanhoPagina":                TAMANHO_PAGINA,
            "pagina":                       1,
        }
        if uf: # Permite buscar de forma geral se UF for omitida
            params["uf"] = uf

        resp = requests.get(
            f"{PNCP_BASE}/contratacoes/publicacao",
            params=params,
            timeout=TIMEOUT_SEGUNDOS,
            headers={"Accept": "application/json"},
        )

        if resp.status_code == 422:
            return []

        if resp.status_code == 429:
            logger.warning(f"PNCP: 429 rate limit uf={uf or 'BR'} — descartando.")
            return []

        resp.raise_for_status()
        itens = resp.json().get("data", [])

    except Exception as e:
        logger.warning(f"PNCP: erro uf={uf or 'BR'}: {e}")
        return []

    candidatos = [(s, item) for item in itens if (s := _pontuar(item, palavras)) > 0]
    candidatos.sort(key=lambda x: x[0], reverse=True)
    return [_formatar(i, s) for s, i in candidatos[:MAX_CONTRATACOES]]


def _buscar_janela_paralelo(
    data_inicial: str,
    data_final: str,
    palavras: list,
) -> list:
    todos = []
    vistos = set()

    logger.info(f"PNCP: janela {data_inicial} → {data_final} — {len(UFS_BUSCA)} UFs, concorrencia={MAX_WORKERS}")
    inicio_tempo = time.monotonic()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_requisicao, uf, MODALIDADE_PRINCIPAL, data_inicial, data_final, palavras): uf
            for uf in UFS_BUSCA
        }

        for future in as_completed(futures):
            uf = futures[future]
            try:
                resultados = future.result()
                for c in resultados:
                    nc = c["numero_controle"]
                    if nc not in vistos:
                        vistos.add(nc)
                        todos.append(c)
                if len(todos) >= MIN_RESULTADOS_PARA_PARAR:
                    for f in futures: f.cancel()
                    break
            except Exception as e:
                continue

    # FALLBACK ESTRATÉGICO: Se fomos completamente bloqueados nas UFs (todos vazio),
    # tenta uma única chamada nacional direta (sem UF) para salvar o contexto do ETP.
    if not todos:
        logger.info("PNCP: UFs bloqueadas/vazias. Tentando chamada fallback nacional...")
        resultados_br = _requisicao(None, MODALIDADE_PRINCIPAL, data_inicial, data_final, palavras)
        for c in resultados_br:
            nc = c["numero_controle"]
            if nc not in vistos:
                vistos.add(nc)
                todos.append(c)

    tempo_total = time.monotonic() - inicio_tempo
    logger.info(f"PNCP: janela {data_inicial}-{data_final} concluida em {tempo_total:.1f}s — {len(todos)} resultado(s)")
    return sorted(todos, key=lambda x: x["relevancia_score"], reverse=True)


def _buscar_com_palavras(palavras: list, max_resultados: int) -> list:
    """
    Busca nas janelas configuradas (mais recente primeiro),
    parando assim que encontrar pelo menos 1 resultado relevante.
    """
    todos = []
    vistos = set()

    for data_inicial, data_final in JANELAS_BUSCA:
        resultados_janela = _buscar_janela_paralelo(
            data_inicial, data_final, palavras
        )

        for c in resultados_janela:
            nc = c["numero_controle"]
            if nc not in vistos:
                vistos.add(nc)
                todos.append(c)

        if len(todos) >= MIN_RESULTADOS_PARA_PARAR:
            logger.info(
                f"PNCP: {len(todos)} resultado(s) — "
                f"pulando janelas restantes"
            )
            break

    return sorted(todos, key=lambda x: x["relevancia_score"], reverse=True)


def buscar_contratacoes_similares(
    objeto: str,
    palavras_chave: list,
    categoria: str,
    subcategorias: list,
    max_resultados: int = MAX_CONTRATACOES,
) -> dict:
    """
    Busca hierárquica otimizada no PNCP.

    3 UFs (DF, SP, MG) com concorrência=2, parando no
    primeiro resultado relevante encontrado em qualquer nível.
    """
    logger.info(
        f"PNCP: UFs={UFS_BUSCA}, concorrencia={MAX_WORKERS}, "
        f"janelas={JANELAS_BUSCA}"
    )

    grupos = [
        (1, palavras_chave),
        (2, subcategorias),
        (3, ["software", "sistema", "tecnologia", "monitoramento"]),
    ]

    tempo_inicio_total = time.monotonic()

    for nivel, palavras in grupos:
        validas = [p for p in palavras if p and len(p) > 2]
        if not validas:
            continue

        logger.info(f"PNCP: nivel {nivel} — {validas}")
        resultados = _buscar_com_palavras(validas, max_resultados)

        if resultados:
            tempo_total = time.monotonic() - tempo_inicio_total
            logger.info(
                f"PNCP: {len(resultados)} resultado(s) no nivel "
                f"{nivel} — busca total em {tempo_total:.1f}s"
            )
            return {
                "contratacoes":     resultados[:max_resultados],
                "total_encontrado": len(resultados),
                "nivel_busca":      nivel,
                "status":           "SUCESSO",
                "erro":             None,
            }

    tempo_total = time.monotonic() - tempo_inicio_total
    logger.info(
        f"PNCP: nenhum resultado encontrado "
        f"(busca total em {tempo_total:.1f}s)."
    )
    return {
        "contratacoes":     [],
        "total_encontrado": 0,
        "nivel_busca":      len(grupos),
        "status":           "SEM_RESULTADO",
        "erro":             None,
    }