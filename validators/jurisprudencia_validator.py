def validar_jurisprudencia(
    resposta,
    objeto_original
):

    objeto_recebido = resposta.get(
        "objeto_analisado",
        ""
    ).strip()

    if objeto_recebido != objeto_original.strip():

        raise Exception(
            "OBJETO_ALTERADO"
        )

    status = resposta.get(
        "status_pesquisa"
    )

    if status not in [
        "SUCESSO",
        "SEM_EVIDENCIA"
    ]:

        raise Exception(
            "STATUS_INVALIDO"
        )

    jurisprudencias = resposta.get(
        "jurisprudencias_relevantes",
        []
    )

    evidencias = resposta.get(
        "evidencias_utilizadas",
        []
    )

    nivel_confianca = resposta.get(
        "nivel_confianca",
        0
    )

    nivel_evidencia = resposta.get(
        "nivel_evidencia"
    )

    grau_aderencia = resposta.get(
        "grau_aderencia_objeto"
    )

    dependencia = resposta.get(
        "dependencia_evidencia"
    )

    fonte_consultada = resposta.get(
        "fonte_consultada"
    )

    indicador_alucinacao = resposta.get(
        "indicador_alucinacao",
        False
    )

    # =====================================================
    # BLOCO 1
    # SEM EVIDENCIA
    # =====================================================

    if status == "SEM_EVIDENCIA":

        if len(jurisprudencias) > 0:

            raise Exception(
                "SEM_EVIDENCIA_COM_JURISPRUDENCIA"
            )

        campos_que_devem_estar_vazios = [

            "teses_aplicaveis",
            "riscos_identificados",
            "boas_praticas",
            "recomendacoes_para_etp",
            "recomendacoes_para_tr",
            "alertas_controle_externo",
            "evidencias_utilizadas"

        ]

        for campo in campos_que_devem_estar_vazios:

            if resposta.get(campo):

                raise Exception(
                    f"CAMPO_NAO_VAZIO_EM_SEM_EVIDENCIA: {campo}"
                )

        if nivel_confianca > 40:

            raise Exception(
                "CONFIANCA_ALTA_PARA_SEM_EVIDENCIA"
            )

        if nivel_evidencia != "GENERICA":

            raise Exception(
                "NIVEL_EVIDENCIA_INVALIDO"
            )

        if fonte_consultada != "NAO_LOCALIZADA":

            raise Exception(
                "FONTE_INVALIDA_PARA_SEM_EVIDENCIA"
            )

        if dependencia != "INEXISTENTE":

            raise Exception(
                "DEPENDENCIA_INVALIDA"
            )

        if grau_aderencia not in [
            None,
            "NAO_IDENTIFICADO"
        ]:

            raise Exception(
                "ADERENCIA_INCOMPATIVEL_COM_SEM_EVIDENCIA"
            )

    # =====================================================
    # BLOCO 2
    # SUCESSO
    # =====================================================

    if status == "SUCESSO":

        if len(jurisprudencias) == 0:

            raise Exception(
                "SUCESSO_SEM_JURISPRUDENCIA"
            )

        if nivel_confianca < 50:

            raise Exception(
                "CONFIANCA_INSUFICIENTE"
            )

        if dependencia not in [
            "TOTAL",
            "PARCIAL"
        ]:

            raise Exception(
                "DEPENDENCIA_INVALIDA"
            )

        if grau_aderencia not in [
            "DIRETO",
            "ANALOGO",
            "GENERICO"
        ]:

            raise Exception(
                "ADERENCIA_INVALIDA"
            )

        if not evidencias:

            raise Exception(
                "SEM_EVIDENCIAS_UTILIZADAS"
            )

    # =====================================================
    # BLOCO 3
    # VALIDAR JURISPRUDENCIAS
    # =====================================================

    acordaos = set()

    for item in jurisprudencias:

        acordao = item.get(
            "acordao",
            ""
        ).strip()

        tema = item.get(
            "tema",
            ""
        ).strip()

        resumo = item.get(
            "resumo",
            ""
        ).strip()

        aplicabilidade = item.get(
            "aplicabilidade",
            ""
        ).strip()

        if not acordao:

            raise Exception(
                "ACORDAO_OBRIGATORIO"
            )

        if acordao in acordaos:

            raise Exception(
                "ACORDAO_DUPLICADO"
            )

        acordaos.add(acordao)

        if not tema:

            raise Exception(
                "TEMA_OBRIGATORIO"
            )

        if not resumo:

            raise Exception(
                "RESUMO_OBRIGATORIO"
            )

        if len(resumo) < 50:

            raise Exception(
                "RESUMO_MUITO_CURTO"
            )

        if not aplicabilidade:

            raise Exception(
                "APLICABILIDADE_OBRIGATORIA"
            )

        if len(aplicabilidade) < 30:

            raise Exception(
                "APLICABILIDADE_INSUFICIENTE"
            )

    # =====================================================
    # BLOCO 4
    # COERENCIA ENTRE ADERENCIA E EVIDENCIA
    # =====================================================

    if grau_aderencia == "DIRETO":

        if nivel_evidencia != "DIRETA":

            raise Exception(
                "ADERENCIA_DIRETA_EXIGE_EVIDENCIA_DIRETA"
            )

    if grau_aderencia == "ANALOGO":

        if nivel_evidencia not in [
            "ANALOGA",
            "DIRETA"
        ]:

            raise Exception(
                "ADERENCIA_ANALOGA_INVALIDA"
            )

    if grau_aderencia == "GENERICO":

        if nivel_evidencia == "DIRETA":

            raise Exception(
                "EVIDENCIA_DIRETA_INCOMPATIVEL_COM_GENERICO"
            )

    # =====================================================
    # BLOCO 5
    # CONTROLE DE ALUCINACAO
    # =====================================================

    if indicador_alucinacao:

        if nivel_confianca > 70:

            raise Exception(
                "ALUCINACAO_COM_CONFIANCA_ALTA"
            )

    # =====================================================
    # BLOCO 6
    # CONTROLE DE QUALIDADE
    # =====================================================

    palavras_chave = resposta.get(
        "palavras_chaves",
        []
    )

    if status == "SUCESSO":

        if not palavras_chave:

            raise Exception(
                "PALAVRAS_CHAVE_AUSENTES"
            )

        conclusao = resposta.get(
            "conclusao_executiva",
            ""
        )

        if len(conclusao.strip()) < 50:

            raise Exception(
                "CONCLUSAO_EXECUTIVA_INSUFICIENTE"
            )

        justificativa = resposta.get(
            "justificativa_status",
            ""
        )

        if len(justificativa.strip()) < 50:

            raise Exception(
                "JUSTIFICATIVA_STATUS_INSUFICIENTE"
            )

    return True