from pathlib import Path

PROMPTS_DIR = Path("prompts")

def load_prompt(nome):
    arquivo = PROMPTS_DIR / f"{nome}.md"

    with open(arquivo, "r", encoding="utf-8") as f:
        return f.read()