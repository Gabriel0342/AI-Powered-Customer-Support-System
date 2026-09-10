"""Pesquisa semântica local: Markdown -> embeddings -> similaridade de cosseno."""

from dataclasses import dataclass
from collections import Counter
from hashlib import sha256
from math import isfinite, sqrt
from pathlib import Path
import re
import json
import unicodedata

import ollama

KB_PATH = Path(__file__).resolve().parents[1] / "Knowledge Base"
EMBEDDING_MODEL = "embeddinggemma" ## Usamos este modelo pois é o unico no ollma capaz de converter texto em vetores numericos
MIN_SCORE = 0.47 ##Quanto maior melhor a precisão (realizar teste até acertar no ponto)
TOP_K = 2 ## Ideal para um sistema de Chatbot pois envia um resultado principal e outro alternativo
CHUNK_SIZE = 1200  # Divisão em trechos de 1200 caracters para uma melhor analise (quanto maior o numero mais preciso é mas, mais tokens consome).
CHUNK_OVERLAP = 150 ## Sobreposição de Chunks para não termos frases cortadas a meio e assim perder o seu sentido
SEARCH_TOPICS_PATH = Path(__file__).resolve().parents[1] / "search_topics.json"


EXCLUDED_FILES = {"Welcome.md", "Base de Conhecimento.md", "Automação dos Tickets.md"} # Remove estes ficheiros da primeira leitura para que não haja
# erros na qualidade dos dados.


class KnowledgeBaseError(RuntimeError): # Classe que irá particularizar um erro de forma a facilitar o debugging
    """Erro de ligação à Knowledge base ou, os embadings são inválidos!"""


@dataclass(frozen=True)
class Chunk: ## Prepara o Chunk para receber as informações relativas às KB
    source: str
    title: str
    text: str
    number: int


@dataclass(frozen=True)
class SearchResult: # Guarda os resultados das pesquisas para cada Chunks, neste caso o score
    chunk: Chunk
    score: float


def limparMarkdown(text): # Esta função irá remover caracteres/formatações desnecessárias
    text = re.sub(r"\[\[([^\]]+)\]\]", lambda m: m[1].split("|")[-1].replace("#", " — "), text)
    text = re.sub(r"(?<!\w)#([^\s#]+)", r"\1", text)
    return text.strip()

def separarChunks(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP): #Vai dividir os textos em chunks para uma melhor
# analise por parte do modelo ollama permitindo assim ler longos documentos sem exceder o limite de tokens.
    if not 0 <= overlap < size:
        raise ValueError("A sobreposição deve estar entre zero e o tamanho do chunk.")
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = text.rfind("\n", start + size // 2, end)
            if boundary < 0:
                boundary = text.rfind(" ", start + size // 2, end)
            if boundary >= 0:
                end = boundary
        part = text[start:end].strip()
        if part:
            yield part
        if end == len(text):
            break
        start = max(start + 1, end - overlap)


def normalizar(vector):
    if not vector or not all(isfinite(value) for value in vector):
        raise KnowledgeBaseError("O Ollama devolveu um embedding vazio ou inválido.")
    length = sqrt(sum(value * value for value in vector))
    if length == 0:
        raise KnowledgeBaseError("O Ollama devolveu um embedding de comprimento zero.")
    return [value / length for value in vector]


class KnowledgeBase:
    def __init__(self, path=KB_PATH, client=None, min_score=MIN_SCORE, top_k=TOP_K,
                 topics_path=SEARCH_TOPICS_PATH):
        if not -1 <= min_score <= 1 or top_k < 1:
            raise ValueError("Limiar inválido ou top_k inferior a 1.")
        self.path = Path(path)
        # Host explícito: OLLAMA_HOST não pode encaminhar a KB para uma API cloud.
        self.client = client if client is not None else ollama.Client(
            host="http://localhost:11434", timeout=120
        )
        self.min_score = min_score
        self.top_k = top_k
        self.topics_path = Path(topics_path) if topics_path is not None else None
        self.chunks = []
        self.vectors = []
        self._fingerprint = None

    def readDocuments(self):
        if not self.path.is_dir():
            raise KnowledgeBaseError(f"Pasta da Knowledge Base não encontrada: {self.path}")
        documents = []
        try:
            for path in sorted(self.path.rglob("*")):
                relative = path.relative_to(self.path)
                if (not path.is_file() or path.suffix.lower() != ".md"
                        or any(part.startswith(".") for part in relative.parts)
                        or relative.as_posix() in EXCLUDED_FILES
                        or path.stem == path.parent.name):
                    continue
                documents.append((relative.as_posix(), path.stem, path.read_text(encoding="utf-8-sig")))
        except (OSError, UnicodeError) as error:
            raise KnowledgeBaseError(f"Não foi possível ler a Knowledge Base: {error}") from error
        return documents

    def embed(self, texts):
        vectors = self.client.embed(model=EMBEDDING_MODEL, input=texts, truncate=False)["embeddings"] # Ollama vai gerar os embaddings para cada texto
        if len(vectors) != len(texts): # Garante que o ollama devolveu um embedding para cada texto
            raise KnowledgeBaseError("O número de embeddings devolvido pelo Ollama é incorreto.")
        return [normalizar(vector) for vector in vectors]

    def refresh(self): #Realizar nova leitura quando existem novos documentos
        documents = self.readDocuments()
        topics = {}
        if self.topics_path is not None:
            try:
                topics = json.loads(self.topics_path.read_text(encoding="utf-8-sig"))
                if not isinstance(topics, dict) or not all(
                    isinstance(key, str) and isinstance(value, str) and value.strip()
                    for key, value in topics.items()
                ):
                    raise ValueError("Esperado um objeto com caminhos e descrições de pesquisa.")
            except (OSError, ValueError) as error:
                raise KnowledgeBaseError(f"Não foi possível ler os temas de pesquisa: {error}") from error
        fingerprint = sha256(repr((documents, topics)).encode("utf-8")).hexdigest()
        if fingerprint == self._fingerprint:
            return
        chunks = [Chunk(source, title, part, number)
                  for source, title, text in documents
                  for number, part in enumerate(separarChunks(limparMarkdown(text)), start=1)]
        vectors = []
        counts = Counter(chunk.source for chunk in chunks)
        for start in range(0, len(chunks), 16):
            # As descrições representam o problema, sem diluir o seu significado
            # em passos repetidos (por exemplo, 'criar um ticket' em quase toda a KB).
            # Documentos novos usam o texto original; documentos longos incluem
            # também o trecho para distinguir as suas diferentes secções.
            vectors.extend(self.embed([
                f"title: {chunk.title} | text: " + (
                    topics[chunk.source] + ("\n\n" + chunk.text if counts[chunk.source] > 1 else "")
                    if chunk.source in topics else chunk.text
                )
                for chunk in chunks[start:start + 16]
            ]))
        if vectors and any(len(vector) != len(vectors[0]) for vector in vectors):
            raise KnowledgeBaseError("Os embeddings têm dimensões incompatíveis.")
        # Só publica o índice depois de TODOS os lotes terem sido gerados.
        self.chunks, self.vectors = chunks, vectors
        self._fingerprint = fingerprint

    def search(self, question): #retorna as informações que mais se enquadram com a pergunta
        if not question.strip():
            return []
        self.refresh()
        if not self.chunks:
            return []
        question = unicodedata.normalize("NFC", question.strip())
        question = re.sub(r"\bpalavra\s+passe\b", "palavra-passe", question, flags=re.I)
        query = self.embed([f"task: search result | query: {question}"])[0]
        if len(query) != len(self.vectors[0]): # verifica se o query tem o mesmo tamanho que os vetores da KB
            self._fingerprint = None
            raise KnowledgeBaseError("A dimensão do modelo mudou; volte a tentar para reindexar.")
        ranked = sorted([ # vai classificar o score de compatibilidade da pergunta com as respostas propostas por ordem decrescente
            SearchResult(chunk, sum(a * b for a, b in zip(query, vector)))
            for chunk, vector in zip(self.chunks, self.vectors)
        ], key=lambda result: result.score, reverse=True)
        cutoff = max(self.min_score, ranked[0].score - 0.06)
        return [result for result in ranked if result.score >= cutoff][:self.top_k]
