# Estrutura principal para as funcionalidade da equipa de gestão que irão permitir responder aos clientes que não virem o seu
# problema resolvido pelo chatAI

import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def get_database(): # Ligação à API do Mongo
    CONNECTION_STRING = os.getenv("MONGODB_URI")
    client = MongoClient(CONNECTION_STRING)
    return client['user_shopping_list']


if __name__ == "__main__":
    dbname = get_database()