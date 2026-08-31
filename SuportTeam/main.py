# Estrutura principal para as funcionalidade da equipa de gestão que irão permitir responder aos clientes que não virem o seu
# problema resolvido pelo chatAI
import textwrap

import ConectarBaseDados
from ollama import generate

#ConectarBaseDados.get_database()
response = generate('llama3.2:1b','Quais as tuas principais funcionalidade?')
print(textwrap.fill(response['response']))