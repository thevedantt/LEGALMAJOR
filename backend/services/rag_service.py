import faiss
import numpy as np
import re
import warnings
import os

# Suppress harmless transformers warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", message=".*embeddings.position_ids.*")

from core.config import Config

try:
    from sentence_transformers import SentenceTransformer
    _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
except ImportError:
    _embedding_model = None

RAG_KEYWORDS = [
    "liability", "termination", "confidential", "governing law",
    "indemnity", "warranty", "arbitration", "force majeure",
    "payment", "assignment"
]

def _simple_embed(text):
    vec = np.zeros(128, dtype=np.float32)
    for i, c in enumerate(text.encode("utf-8")):
        vec[i % 128] += c
    return vec / (np.linalg.norm(vec) + 1e-6)

class RAGService:
    def __init__(self):
        self.chunk_cache = {}
        self.embedding_cache = {}
        self.index = None
        self.chunks = []

    def chunk_text(self, text: str) -> list:
        chunks = re.split(r'\n{2,}|(?<=[.!?])\s+(?=[A-Z])', text)
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        return chunks

    def embed_text(self, text: str):
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        if _embedding_model:
            vec = _embedding_model.encode(text, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
        else:
            vec = _simple_embed(text)
        self.embedding_cache[text] = vec
        return vec

    def build_index(self, chunks: list):
        self.chunks = chunks
        embeddings = np.vstack([self.embed_text(ch) for ch in chunks])
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)
        self.chunk_cache["chunks"] = chunks
        self.chunk_cache["embeddings"] = embeddings

    def retrieve(self, query: str) -> list:
        prefiltered = [ch for ch in self.chunks if any(kw in ch.lower() for kw in RAG_KEYWORDS)]
        if not prefiltered: prefiltered = self.chunks
        query_vec = self.embed_text(query)
        k = min(Config.RAG_TOP_K, len(prefiltered))
        pf_embeddings = np.vstack([self.embed_text(ch) for ch in prefiltered])
        dim = pf_embeddings.shape[1]
        pf_index = faiss.IndexFlatL2(dim)
        pf_index.add(pf_embeddings)
        D, I = pf_index.search(np.array([query_vec]), k)
        retrieved = [prefiltered[idx] for idx in I[0]]
        seen = set()
        result_chunks = []
        total_words = 0
        for chunk in retrieved:
            cleaned = chunk.strip()
            wcount = len(cleaned.split())
            if cleaned and cleaned not in seen and total_words + wcount <= Config.MAX_CONTEXT_WORDS:
                result_chunks.append(cleaned)
                seen.add(cleaned)
                total_words += wcount
            if total_words >= Config.MAX_CONTEXT_WORDS:
                break
        return result_chunks

    def get_compact_context(self, query: str) -> str:
        chunks = self.retrieve(query)
        return "\n\n".join(chunks)
