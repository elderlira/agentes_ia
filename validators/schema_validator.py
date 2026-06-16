import json

from jsonschema import validate
from jsonschema import ValidationError


class SchemaValidator:

    @staticmethod
    def validar(
        dados,
        schema_path,
        objeto_original=None,
    ):
        """
        Ponto único de validação do sistema.

        Executa em ordem:
        1. Validação estrutural via jsonschema
        2. Validação semântica específica por agente
           (quando disponível)

        Qualquer falha lança Exception com mensagem
        estruturada para ser capturada pelo AgentExecutor.
        """

        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        # --------------------------------------------------
        # ETAPA 1 — Validação estrutural
        # --------------------------------------------------
        try:
            validate(instance=dados, schema=schema)

        except ValidationError as erro:

            caminho = " -> ".join(
                str(x) for x in erro.path
            ) or "(raiz)"

            raise Exception(
                f"\nSchema inválido."
                f"\n\nArquivo:\n{schema_path}"
                f"\n\nCampo:\n{caminho}"
                f"\n\nErro:\n{erro.message}"
                f"\n\nValor recebido:\n{erro.instance}\n"
            )

        # --------------------------------------------------
        # ETAPA 2 — Validação semântica por agente
        # Cada agente que tiver regras semânticas próprias
        # deve ser registrado aqui com seu schema_path.
        # --------------------------------------------------

        validadores_semanticos = {
            "jurisprudencia_tcu_schema.json": (
                SchemaValidator
                ._validar_jurisprudencia_tcu
            ),
        }

        for nome_schema, validador in (
            validadores_semanticos.items()
        ):
            if nome_schema in schema_path:
                validador(
                    dados,
                    objeto_original,
                )
                break

        return True

    # ------------------------------------------------------
    # VALIDADORES SEMÂNTICOS POR AGENTE
    # ------------------------------------------------------

    @staticmethod
    def _validar_jurisprudencia_tcu(
        dados,
        objeto_original,
    ):
        """
        Importa e executa o validador semântico
        do agente Jurisprudência TCU.

        Separado para manter o validador específico
        no seu próprio arquivo, mas chamado a partir
        deste ponto único.
        """
        from validators.jurisprudencia_validator import (
            validar_jurisprudencia,
        )

        # Validação de objeto_analisado centralizada aqui.
        # Removida do AgentExecutor para evitar duplicação
        # e inconsistência de case-sensitivity.
        if objeto_original and "objeto_analisado" in dados:

            recebido = dados["objeto_analisado"].strip()
            esperado = objeto_original.strip()

            if recebido != esperado:
                raise Exception(
                    f"\nOBJETO_ALTERADO"
                    f"\n\nO campo objeto_analisado deve ser exatamente:"
                    f"\n\n{esperado}"
                    f"\n\nValor retornado:"
                    f"\n\n{recebido}"
                    f"\n\nCopie o texto acima literalmente."
                    f"\nNão resuma. Não substitua. Não generalize.\n"
                )

        validar_jurisprudencia(dados, objeto_original)