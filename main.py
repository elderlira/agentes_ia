from maestro import Maestro
import logging

logging.basicConfig(level=logging.INFO)

maestro = Maestro()
#    "Crie um ETP para contratação de sistema de contagem de pessoas por inteligência artificial."
resultado = maestro.processar(
    "Sistema de contagem de pessoas por inteligência artificial"
)

print(resultado)