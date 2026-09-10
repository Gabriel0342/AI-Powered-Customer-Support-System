# Estrutura dedicada para todas as funções sobre os tickets

from datetime import datetime
from bson.objectid import ObjectId, InvalidId


def criarTicket(db, titulo, descricao, email):
    collection = db["tickets"]

    ticket = {
        "titulo": titulo,
        "descricao": descricao,
        "email": email,
        "status": "Aberto",
        "criado_em": datetime.now()
    }

    result = collection.insert_one(ticket)

    if(result):
        print("Ticket criado com sucesso!")
    else:
        print("Ticket sem sucesso!")



def listarTickets(db, filtro=None):
    collection = db["tickets"]

    if filtro is None:
        filtro = {}

    tickets = collection.find(filtro)
    print(30*"=")
    for ticket in tickets:
        print("ID:", ticket["_id"])
        print("Título:", ticket["titulo"])
        print("Descrição:", ticket["descricao"])
        print("Email:", ticket["email"])
        print("Status:", ticket["status"])
        print("Criado em:", ticket["criado_em"])
    print(30*"=")
    print("\n")

def visualizarTicket(db, ticket_id):
    collection = db["tickets"]

    try:
        id = ObjectId(ticket_id)
    except InvalidId:
        print("ID inválido!")
        return

    ticket = collection.find_one({"_id": id})

    if ticket:
        print("\n===== DETALHES DO TICKET =====")
        print("ID:", ticket["_id"])
        print("Título:", ticket["titulo"])
        print("Descrição:", ticket["descricao"])
        print("Email:", ticket["email"])
        print("Status:", ticket["status"])
        print("Criado em:", ticket["criado_em"])
        print(30*"=")
    else:
        print("Ticket não encontrado.")