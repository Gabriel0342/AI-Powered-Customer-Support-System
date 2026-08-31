import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

current_dir = Path(__file__).parent
load_dotenv(current_dir / 'atlas-credentials.env')

def get_database(): # Ligação à API do Mongo
    CONNECTION_STRING = os.getenv("MONGODB_URI")
    client = MongoClient(CONNECTION_STRING)
    return client['support_system']
