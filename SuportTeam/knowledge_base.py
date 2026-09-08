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
EMBEDDING_MODEL = "embeddinggemma"
# Calibrado com frases completas e variantes curtas.
MIN_SCORE = 0.47
TOP_K = 2
CHUNK_SIZE = 1200  # Caracteres; os procedimentos atuais cabem num único trecho.
CHUNK_OVERLAP = 150
SEARCH_TOPICS_PATH = Path(__file__).with_name("search_topics.json")

# Índices não contêm procedimentos; automação descreve ações internas que este
# chat não executa; Welcome é um exemplo do Obsidian. Não alterar os originais.
EXCLUDED_FILES = {"Welcome.md", "Base de Conhecimento.md", "Automação dos Tickets.md"}


class KnowledgeBaseError(RuntimeError):
    """A base não pôde ser lida ou os embeddings não são válidos."""


@dataclass(frozen=True)
class Chunk:
    source: str
    title: str
    text: str
    number: int


@dataclass(frozen=True)
class SearchResult:
    chunk: Chunk
    score: float


def clean_markdown(text):
    """Normaliza uma cópia; nunca escreve nos documentos originais."""
    text = re.sub(r"\[\[([^\]]+)\]\]", lambda m: m[1].split("|")[-1].replace("#", " — "), text)
    # Mantém o significado das hashtags; preserva títulos Markdown (# Título).
    text = re.sub(r"(?<!\w)#([^\s#]+)", r"\1", text)
    return text.strip()


def split_chunks(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Divide em limites de linhas/palavras, com sobreposição entre trechos."""
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


def normalize(vector):
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

    def _read_documents(self):
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

    def _embed(self, texts):
        vectors = self.client.embed(model=EMBEDDING_MODEL, input=texts, truncate=False)["embeddings"]
        if len(vectors) != len(texts):
            raise KnowledgeBaseError("O número de embeddings devolvido pelo Ollama é incorreto.")
        return [normalize(vector) for vector in vectors]

    def refresh(self):
        """Reconstrói só quando há documentos novos, alterados ou apagados."""
        documents = self._read_documents()
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
                  for number, part in enumerate(split_chunks(clean_markdown(text)), start=1)]
        vectors = []
        counts = Counter(chunk.source for chunk in chunks)
        for start in range(0, len(chunks), 16):
            # As descrições representam o problema, sem diluir o seu significado
            # em passos repetidos (por exemplo, 'criar um ticket' em quase toda a KB).
            # Documentos novos usam o texto original; documentos longos incluem
            # também o trecho para distinguir as suas diferentes secções.
            vectors.extend(self._embed([
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

    def search(self, question):
        if not question.strip():
            return []
        self.refresh()
        if not self.chunks:
            return []
        question = unicodedata.normalize("NFC", question.strip())
        question = re.sub(r"\bpalavra\s+passe\b", "palavra-passe", question, flags=re.I)
        query = self._embed([f"task: search result | query: {question}"])[0]
        if len(query) != len(self.vectors[0]):
            self._fingerprint = None
            raise KnowledgeBaseError("A dimensão do modelo mudou; volte a tentar para reindexar.")
        # Produto escalar de vetores normalizados = similaridade de cosseno.
        ranked = sorted([
            SearchResult(chunk, sum(a * b for a, b in zip(query, vector)))
            for chunk, vector in zip(self.chunks, self.vectors)
        ], key=lambda result: result.score, reverse=True)
        # A margem evita misturar procedimentos muito menos relevantes.
        cutoff = max(self.min_score, ranked[0].score - 0.06)
        return [result for result in ranked if result.score >= cutoff][:self.top_k]
