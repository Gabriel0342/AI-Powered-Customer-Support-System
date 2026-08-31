# Estrutura principal para as funcionalidade dos Clientes onde iram expor os seus problemas e visualizar o progresso dos tickets
# caso o ChatAI não consiga resolver

import ConectarBaseDados
import bcrypt

db = ConectarBaseDados.get_database()
collection = db['clients']

salt = bcrypt.gensalt()

def criarPerfil():
    nome = input(str("Qual o seu nome: "))
    password = input(str("Qual a sua password: ")).encode("utf-8")
    password_hash = bcrypt.hashpw(password, salt)

    dados = {'nome': nome, 'password': password_hash}
    res = collection.insert_one(dados) #Adiconar dados
    print("Perfil criado com sucesso!")

def login():
    nome = input(str("Qual o seu nome: "))
    password = input(str("Qual a sua password: ")).encode("utf-8")

    user = collection.find_one({'nome': nome})
    if user and bcrypt.checkpw(password, bytes(user['password'])):
        print("Login realizado com sucesso!")
    else:
        print("Password ou nome incorreto!")

