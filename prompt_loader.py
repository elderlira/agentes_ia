from pathlib import Path


def load_prompt(nome):

    arquivo_simples = Path(
        f"prompts/{nome}.md"
    )

    if arquivo_simples.exists():

        return arquivo_simples.read_text(
            encoding="utf-8"
        )

    pasta_agente = Path(
        f"prompts/{nome}"
    )

    if pasta_agente.exists():

        partes = []

        for arquivo in [
            "system.md",
            "exemplos.md",
            "checklist.md"
        ]:

            caminho = pasta_agente / arquivo

            if caminho.exists():

                partes.append(
                    caminho.read_text(
                        encoding="utf-8"
                    )
                )

        return "\n\n".join(
            partes
        )

    raise FileNotFoundError(
        f"Prompt não encontrado: {nome}"
    )