from prompt_loader import load_prompt
from ollama_client import generate

maestro = load_prompt("maestro")

pergunta = """
Crie um ETP para contratação de sistema de contagem de pessoas por inteligência artificial.
"""

prompt_final = f"""
{maestro}

SOLICITAÇÃO DO USUÁRIO:

{pergunta}
"""

resposta = generate(prompt_final)

print(resposta)