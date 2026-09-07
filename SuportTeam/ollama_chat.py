import ollama


SYSTEM_PROMPT = """
És um assistente virtual de suporte ao cliente.

A tua função é ajudar clientes com problemas e dúvidas relacionadas com:
- conta e login
- tickets de suporte
- pagamentos
- produtos e serviços
- entregas
- problemas técnicos
- segurança da conta
- utilização do serviço

Conversa naturalmente com o cliente e tenta perceber o problema antes de dar uma resposta.

Se não tiveres informação suficiente para resolver um problema, não inventes informações.
Podes dizer que não tens informação suficiente ou sugerir que o problema seja encaminhado para um agente humano.

Não respondas a perguntas claramente fora do contexto de suporte ao cliente.

Responde de forma curta, clara, educada e natural.
"""


def responder(mensagem):
    response = ollama.chat(
        model="llama3.2:1b",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": mensagem
            }
        ],
        options={
            "temperature": 0.2
        }
    )

    return response["message"]["content"]