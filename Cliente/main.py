# Estrutura principal para as funcionalidade dos Clientes onde iram expor os seus problemas e visualizar o progresso dos tickets
# caso o ChatAI não consiga resolver

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