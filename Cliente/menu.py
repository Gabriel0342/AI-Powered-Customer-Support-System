from datetime import datetime, timedelta

def menu_listar_tickets(listar_tickets, db):
    while True:
        print("\n===== LISTAR TICKETS =====")
        print("1 - Todos os tickets")
        print("2 - Filtrar por status")
        print("3 - Filtrar por data")
        print("4 - Filtrar por cliente")
        print("0 - Voltar")

        opcao = input(int("Escolha uma opção: "))

        if opcao == "1":
            listar_tickets(db)

        elif opcao == "2":
            status = input(str("Status: "))
            listar_tickets(db, {"status": status})

        elif opcao == "3":
            data = input(str("Data (DD/MM/AAAA): "))
            data_inicio = datetime.strptime(data, "%d/%m/%Y")
            data_fim = data_inicio + timedelta(days=1)

            listar_tickets(db, {
                "criado_em": {
                    "$gte": data_inicio,
                    "$lt": data_fim
                }
            })

        elif opcao == "4":
            email = input(str("Email do cliente: "))
            listar_tickets(db, {"email": email})

        elif opcao == "0":
            break

        else:
            print("Opção inválida!")

def menu(criarPerfil, login, novo_ticket, listar_tickets, visualizar_ticket, db):
    while True:
        print("\n========== MENU CLIENTE ==========")
        print("1 - Criar perfil")
        print("2 - Login")
        print("3 - Criar ticket")
        print("4 - Listar tickets")
        print("5 - Visualizar ticket")
        print("0 - Sair")
        print("==================================")

        opcao = input(int("Escolha uma opção: "))

        if opcao == "1":
            criarPerfil()

        elif opcao == "2":
            login()

        elif opcao == "3":
            novo_ticket()

        elif opcao == "4":
            menu_listar_tickets(listar_tickets, db)

        elif opcao == "5":
            ticket_id = input(str("ID do ticket: "))
            visualizar_ticket(db, ticket_id)

        elif opcao == "0":
            print("Programa terminado.")
            break

        else:
            print("Opção inválida! Tente novamente.")