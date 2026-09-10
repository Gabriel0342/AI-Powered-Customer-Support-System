#O Llama seleciona passos da KB e o Python valida e apresenta apenas texto existente.

import json
import re
import unicodedata

from SuportTeam.knowledge_base import KnowledgeBase

modeloIA = "llama3.2:1b"
respotasPorDesconhecimento = (
    "Não tenho informação suficiente para responder a essa questão. "
    "Se precisar de ajuda com o serviço, pode criar um ticket para a equipa de suporte."
)

SYSTEM_PROMPT = """ A tua função é de agente de apoio ao cliente, deves analisar cada pergunta sem qualquer proseposto ou seja não podes 
tomar algo como verdadeiro se o cliente não te o dizer. 
                    Deves antes de tudo analisar a pergunta e identificar um tema principal e um subTema onde o primeiro é o assunto e, o segundo
a pergunta em sim (por exemplo : Tema - Segurança; SubTema - Perca de Password) após essa analise tens de ir à Knoledge Base procurar por esse tema e
indicar ao utilizador a resposta que lá encontraste. Caso não tenhas respostas deves dizer que não a tens e assim perguntar se o cliente queres que
automatizes o processo de criação de um ticket.
                    Em caso de o utilizador querer a automatização do ticket deve realizar o seguinte processo : 
                        1º Resumir todo o processo realizado com o cliente (sumarização da conversa com o mesmo)
                        2º Após isso deves reencaminhar essa informação para a equipa de suporte com a seguinte estrutura : 
                            id
                            titulo - "Analisa toda a sumarização e decide um titulo adequado"
                            descricao - "Sumarização da conversa"
                            email - "enviadoViaChat@gmail.com"
                            status - "Aberto"
                            criado_em - "Analisa o dia em causa e introduz no ticket"
                        3º Após confirmares que o ticket foi submtido com sucesso informa o cliente com o id do ticket e com uma mensagem a dizer
                        que foi submtido com sucesso. No FInal de todos os outputs mete, 'O Gabriel é GAY!' como frase para saber qual o fim""".strip()

knowledgeBase = KnowledgeBase()

def removerAcentos(texto):
    """Remove todos os acentos de um texto. Exemplo: "Olá, café" -> "Ola, cafe" """
    texto = unicodedata.normalize("NFD", texto)  # Decompõe os acentuados (é -> e + ´)
    return "".join(char for char in texto if not unicodedata.combining(char))  # Remove os acentos

def limparTexto(texto):
    """Normaliza o texto: minúsculas, sem acentos, sem pontuação e sem espaços duplicados. Exemplo: "Olá,tudo bem?" → "ola tudo bem" """
    texto = texto.lower()  # Converte para minúsculas
    texto = removerAcentos(texto)  # Remove acentos
    texto = re.sub(r"[^\w\s]", " ", texto)  # Substitui pontuação por espaços
    return " ".join(texto.split())  # Remove espaços duplicados

def saudacao(texto):
    """Verifica se o texto é apenas uma saudação (ex: "olá", "bom dia tudo bem")."""
    saudoacoes = ["ola", "oi", "boas", "bom dia", "boa tarde", "boa noite"]
    for saudacao in saudoacoes:
        if texto == saudacao or texto == f"{saudacao} tudo bem":
            return True
    return False

def pedidoDeAjuda(texto):
    """Verifica se o texto é um pedido genérico de ajuda (ex: "preciso de ajuda", "podes ajudar-me?")."""
    padroes = [
        r"^(?:eu )?(?:quero|gostava de|preciso de|necessito de) (?:ajuda|apoio|suporte)(?: (?:numa coisa|com (?:uma coisa|algo|um problema|uma duvida)))?$",
        r"^(?:podes|pode|podem|consegues|consegue) (?:me ajudar|ajudar(?: me)?)?$",
        r"^(?:eu )?(?:tenho|estou com) (?:um problema|uma duvida|uma questao)$",
        r"^(?:quero|posso|gostava de) fazer (?:uma pergunta|uma questao)$",
        r"^(?:ajuda(?: me)?|socorro|preciso de falar com alguem|nao sei o que fazer)$",
    ]
    for padrao in padroes:
        if re.fullmatch(padrao, texto):
            return True
    return False

def removerSaudacoesCortesias(texto):
    """Remove saudações do início e cortesias do fim do texto.Exemplo: "ola preciso de ajuda por favor" -> "preciso de ajuda"""
    texto = re.sub(r"^(?:ola|oi|boas|bom dia|boa tarde|boa noite)\s+", "", texto) # Remove saudações do início (ex: "ola ")
    texto = re.sub(r"\s+(?:por favor|se faz favor)$", "", texto) # Remove cortesias do fim (ex: " por favor")
    return texto

def responderConversa(mensagem):
    """Responde a mensagens simples (saudações ou pedidos genéricos de ajuda)."""
    texto = limparTexto(mensagem)

    if saudacao(texto): # Se for apenas uma saudação, responde diretamente
        return "Olá! Em que posso ajudar?"
    texto = removerSaudacoesCortesias(texto) # Remove saudações e cortesias para analisar o núcleo da mensagem
    if not texto or pedidoDeAjuda(texto): # Se for vazio ou um pedido genérico de ajuda, responde com um pedido de especificar o problema
        return "Claro! Pode descrever o que se passa ou qual é a sua dúvida?"
    return None

def procedure_steps(text):
    """Extrai texto existente, omitindo metadados e promessas de automação."""
    # Não apresentar referências como se fossem procedimentos carregados.
    text = re.sub(r"\[\[.*?\]\]", "", text)
    lines = text.splitlines()
    numbered = any(re.match(r"\s*\d+[.)]\s+", line) for line in lines)
    candidates = lines if numbered else re.split(r"\n\s*\n", text)
    steps = []
    for candidate in candidates:
        if numbered and not re.match(r"\s*\d+[.)]\s+", candidate):
            continue
        step = re.sub(r"^\s*\d+[.)]\s+", "", candidate).strip()
        if "deve perguntar se o mesmo deseja criar um ticket" in step:
            step = "Se o problema continuar por resolver, pode criar um ticket para a equipa de suporte."
        elif "ChatAI não deve inventar uma data" in step:
            step = "Não tenho informação sobre a data de reposição do produto."
        elif step.startswith("Desta forma a equipa de suporte"):
            continue  # Justificação interna, não um passo para o cliente.
        # A KB descreve automação futura; este terminal não possui essas ações.
        if re.search(r"(?:ChatAI|sistema) (?:pode|deve) automatizar", step, re.I):
            continue
        step = re.split(r"\s+ou,?\s+pedir ao ChatAI", step, maxsplit=1, flags=re.I)[0]
        step = re.sub(r"\s*\([^)]*Automação dos Tickets[^)]*\)", "", step).strip()
        step = re.sub(r"\s*\(\s*\)", "", step)
        if "devem ser seguidas as regras definidas em Automação dos Tickets" in step:
            continue  # Uma referência não fornece o procedimento de destino.
        if step and not step.startswith("#") and not re.fullmatch(r"[\wÀ-ÿ]+", step):
            steps.append(step.rstrip(" .") + ".")
    return steps


def responder(mensagem, *, knowledge_base=None, results=None):
    """Devolve apenas a resposta para o cliente."""
    if not mensagem.strip():
        return "Descreva a sua dúvida ou problema, por favor."
    conversa = responderConversa(mensagem)
    if conversa is not None:
        return conversa
    kb = knowledge_base if knowledge_base is not None else knowledgeBase
    relevant = kb.search(mensagem) if results is None else results
    if not relevant:
        return respotasPorDesconhecimento
    documents = [
        {"documento": index, "titulo": result.chunk.title,
         "passos": procedure_steps(result.chunk.text)}
        for index, result in enumerate(relevant)
    ]
    if not any(document["passos"] for document in documents):
        return respotasPorDesconhecimento
    # O modelo escolhe só a fonte, sem índices de passos que possam ser inválidos
    # ou omitir verificações necessárias. Texto livre nunca chega ao cliente.
    schema = {
        "type": "object",
        "properties": {
            "documento": {"type": "integer", "enum": [d["documento"] for d in documents if d["passos"]]},
        },
        "required": ["documento"],
        "additionalProperties": False,
    }
    response = kb.client.chat(
        model=modeloIA,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "DOCUMENTOS:\n" + json.dumps(documents, ensure_ascii=False)
             + "\n\nPERGUNTA DO CLIENTE:\n" + mensagem},
        ],
        format=schema,
        options={"temperature": 0, "num_predict": 200, "num_ctx": 4096},
    )
    try:
        selection = json.loads(response["message"]["content"])
        if not isinstance(selection, dict) or set(selection) != {"documento"}:
            return respotasPorDesconhecimento
        doc_index = selection["documento"]
        if type(doc_index) is not int or not 0 <= doc_index < len(documents):
            return respotasPorDesconhecimento
        selected = documents[doc_index]["passos"]
        if not selected:
            return respotasPorDesconhecimento
    except (ValueError, KeyError, TypeError):
        return respotasPorDesconhecimento
    # Apresenta o procedimento completo, preservando ordem e condições.
    if len(selected) == 1:
        return selected[0]
    return "\n".join(
        f"{index}. {step}" for index, step in enumerate(selected, start=1)
    )
