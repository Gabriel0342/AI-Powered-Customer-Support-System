import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def get_database(): # Ligação à API do Mongo
    CONNECTION_STRING = os.getenv("MONGODB_URI")
    client = MongoClient(CONNECTION_STRING)
    print("Conectado")
    return client

