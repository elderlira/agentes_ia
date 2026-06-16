import json
import re
import unicodedata


# =============================================================
# MAPA DE ENUMS
# Chave  : nome do campo no JSON
# Valor  : lista de valores canônicos aceitos pelo schema
# =============================================================

ENUM_CAMPOS = {
    # jurisprudencia_tcu_schema.json
    "colegiado": [
        "Plenario",
        "Primeira Camara",
        "Segunda Camara",
        "Nao Informado",
    ],
    "relevancia": [
        "Alta",
        "Media",
        "Baixa",
    ],
    "tipo_fonte": [
        "Acordao",
        "Sumula",
        "Informativo",
        "Manual",
        "Referencial",
    ],
    "status_pesquisa": [
        "SUCESSO",
        "SEM_EVIDENCIA",
    ],
    "nivel_evidencia": [
        "DIRETA",
        "ANALOGA",
        "GENERICA",
    ],
    "fonte_consultada": [
        "TCU",
        "BASE_INTERNA",
        "TCU_E_BASE_INTERNA",
        "NAO_LOCALIZADA",
    ],
    "grau_aderencia_objeto": [
        "DIRETO",
        "ANALOGO",
        "GENERICO",
        "NAO_IDENTIFICADO",
    ],
    "dependencia_evidencia": [
        "TOTAL",
        "PARCIAL",
        "INEXISTENTE",
    ],
    # maestro_schema.json
    "tipo_documento": [
        "ETP",
        "TR",
        "ETP_TR",
    ],
}


def _sem_acento(texto: str) -> str:
    """Remove acentos e converte para minúsculas para comparação."""
    normalizado = unicodedata.normalize("NFD", texto)
    sem_acentos = "".join(
        c for c in normalizado
        if unicodedata.category(c) != "Mn"
    )
    return sem_acentos.lower().strip()


def _normalizar_valor_enum(
    campo: str,
    valor: str
) -> str:
    """
    Tenta encontrar o valor canônico correspondente
    comparando sem acentos e sem distinção de maiúsculas.

    Retorna o valor canônico se encontrado,
    ou o valor original (deixa o schema reportar o erro).
    """
    valores_validos = ENUM_CAMPOS.get(campo, [])

    if not valores_validos:
        return valor

    valor_norm = _sem_acento(valor)

    for canonico in valores_validos:
        if _sem_acento(canonico) == valor_norm:
            return canonico

    # Não encontrou correspondência — devolve original
    # para que o schema gere erro com mensagem clara.
    return valor


def normalizar_enums(dados) -> dict | list:
    """
    Percorre recursivamente dicts e listas,
    normalizando valores de campos enum conhecidos.
    """
    if isinstance(dados, dict):
        resultado = {}
        for chave, valor in dados.items():
            if chave in ENUM_CAMPOS and isinstance(valor, str):
                resultado[chave] = _normalizar_valor_enum(
                    chave, valor
                )
            else:
                resultado[chave] = normalizar_enums(valor)
        return resultado

    if isinstance(dados, list):
        return [normalizar_enums(item) for item in dados]

    return dados


# =============================================================
# EXTRAÇÃO DE JSON
# =============================================================

def extrair_json(texto: str) -> dict:
    """
    Extrai e retorna o primeiro objeto JSON encontrado
    no texto bruto do LLM.

    Etapas:
    1. Remove blocos de código markdown (```json ... ```)
    2. Tenta json.loads direto
    3. Tenta localizar {...} via regex
    4. Normaliza enums antes de retornar
    """
    texto = texto.strip()

    # Remove marcadores de bloco de código
    texto = re.sub(r"^```json\s*", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"^```\s*",     "", texto)
    texto = re.sub(r"\s*```$",     "", texto)
    texto = texto.strip()

    dados = None

    try:
        dados = json.loads(texto)

    except json.JSONDecodeError:

        match = re.search(r"\{.*\}", texto, re.DOTALL)

        if not match:
            raise ValueError(
                "Nenhum JSON válido encontrado na resposta do modelo."
            )

        dados = json.loads(match.group())

    # Normaliza enums antes de qualquer validação
    return normalizar_enums(dados)


def normalizar_campos(dados: dict) -> dict:
    """
    Renomeia campos legados para os nomes canônicos do schema.
    Mantido para compatibilidade com versões anteriores.
    """
    mapa = {
        "objeto_contratação": "objeto_contratacao",
        "tipo_documentação":  "tipo_documento",
    }

    for antigo, novo in mapa.items():
        if antigo in dados:
            dados[novo] = dados.pop(antigo)

    return dados