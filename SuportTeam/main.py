# Terminal para o chatbot de suporte com Knowledge Base local.
import argparse
import sys
from pathlib import Path

import httpx
import ollama

# Permite python -m SuportTeam.main e python SuportTeam/main.py.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from SuportTeam.knowledge_base import KnowledgeBase, KnowledgeBaseError, MIN_SCORE
from ollama_chat import responder, responderConversa


def main():
    parser = argparse.ArgumentParser(description="Chat de suporte com RAG local no Ollama.")
    parser.add_argument("--question", help="Executar uma única pergunta e terminar.")
    parser.add_argument("--min-score", type=float, default=MIN_SCORE, help="Limiar de cosseno entre -1 e 1.")
    args = parser.parse_args()
    if not -1 <= args.min_score <= 1:
        parser.error("--min-score deve estar entre -1 e 1")
    kb = KnowledgeBase(min_score=args.min_score)
    while True:
        try:
            mensagem = args.question if args.question is not None else input("Cliente: ")
        except (EOFError, KeyboardInterrupt):
            print("\nChat terminado.")
            return 0
        if mensagem.strip().lower() == "sair":
            print("Chat terminado.")
            return 0
        try:
            resposta = responderConversa(mensagem)
            if resposta is None:
                results = kb.search(mensagem)
                resposta = responder(mensagem, knowledge_base=kb, results=results)
            print("IA:", resposta)
        except (ollama.ResponseError, ConnectionError, httpx.HTTPError, KnowledgeBaseError) as error:
            print(f"Não foi possível consultar a IA local: {error}", file=sys.stderr)
            print("Verifique o Ollama em localhost:11434 e instale os modelos com "
                  "'ollama pull embeddinggemma' e 'ollama pull llama3.2:1b'.", file=sys.stderr)
            if args.question is not None:
                return 1
        if args.question is not None:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
