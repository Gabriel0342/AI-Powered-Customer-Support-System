# Estrutura principal para as funcionalidades da equipa de gestão que irão permitir
# responder aos clientes que não virem o seu problema resolvido pelo chatAI

import ConectarBaseDados
from SuportTeam.ollama_chat import responder


# db = ConectarBaseDados.get_database()


if __name__ == "__main__":
    while True:
        mensagem = input("Cliente: ")

        if mensagem.lower() == "sair":
            print("Chat terminado.")
            break

        resposta = responder(mensagem)

        print("IA:", resposta)