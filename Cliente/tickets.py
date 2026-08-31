from datetime import datetime
from bson.objectid import ObjectId, InvalidId


def criar_ticket(db, titulo, descricao, email):
    collection = db["tickets"]

    ticket = {
        "titulo": titulo,
        "descricao": descricao,
        "email": email,
        "status": "Aberto",
        "criado_em": datetime.now()
    }

    result = collection.insert_one(ticket)

    print("Ticket criado com sucesso!")


def listar_tickets(db, filtro=None):
    collection = db["tickets"]

    if filtro is None:
        filtro = {}

    tickets = collection.find(filtro)

    for ticket in tickets:
        print("ID:", ticket["_id"])
        print("Título:", ticket["titulo"])
        print("Descrição:", ticket["descricao"])
        print("Email:", ticket["email"])
        print("Status:", ticket["status"])
        print("Criado em:", ticket["criado_em"])
        print("=" * 30)


def visualizar_ticket(db, ticket_id):
    collection = db["tickets"]

    try:
        id = ObjectId(ticket_id)
    except InvalidId:
        print("ID inválido!")
        return

    ticket = collection.find_one({
        "_id": id
    })

    if ticket:
        print("\n===== DETALHES DO TICKET =====")
        print("ID:", ticket["_id"])
        print("Título:", ticket["titulo"])
        print("Descrição:", ticket["descricao"])
        print("Email:", ticket["email"])
        print("Status:", ticket["status"])
        print("Criado em:", ticket["criado_em"])
        print("==============================")
    else:
        print("Ticket não encontrado.")