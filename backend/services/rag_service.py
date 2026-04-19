import faiss
import numpy as np
import re
import warnings
import os

# Suppress harmless transformers warnings
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
warnings.filterwarnings("ignore", message=".*embeddings.position_ids.*")

from backend.core.config import Config

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

import json

class RAGService:
    def __init__(self):
        self.doc_chunks = {}         # doc_id -> [chunks]
        self.doc_embeddings = {}     # doc_id -> embeddings matrix
        self.doc_indexes = {}        # doc_id -> FAISS index
        self.doc_embedding_cache = {} # doc_id -> {text: embedding}
        self.storage_path = os.path.join(os.path.dirname(__file__), '..', 'storage')
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)
        self.storage_path = os.path.join(os.path.dirname(__file__), '..', 'storage')
        if not os.path.exists(self.storage_path):
            os.makedirs(self.storage_path)

    def save_to_disk(self, doc_id: str):
        """
        Save the chunks, embeddings, and FAISS index for a doc_id to disk
        """
        doc_dir = os.path.join(self.storage_path, doc_id)
        if not os.path.exists(doc_dir):
            os.makedirs(doc_dir)

        # Save chunks
        chunks_fp = os.path.join(doc_dir, "chunks.json")
        with open(chunks_fp, 'w', encoding='utf-8') as f:
            json.dump(self.doc_chunks[doc_id], f)

        # Save embeddings
        emb_fp = os.path.join(doc_dir, "embeddings.npy")
        np.save(emb_fp, self.doc_embeddings[doc_id])

        # Save FAISS index
        index_fp = os.path.join(doc_dir, "index.faiss")
        faiss.write_index(self.doc_indexes[doc_id], index_fp)

    def load_from_disk(self, doc_id: str):
        """
        Load the chunks, embeddings, and FAISS index for a doc_id from disk into memory
        """
        if not hasattr(self, 'doc_embedding_cache'):
            self.doc_embedding_cache = {}
        doc_dir = os.path.join(self.storage_path, doc_id)
        chunks_fp = os.path.join(doc_dir, "chunks.json")
        emb_fp = os.path.join(doc_dir, "embeddings.npy")
        index_fp = os.path.join(doc_dir, "index.faiss")

        if not (os.path.exists(chunks_fp) and os.path.exists(emb_fp) and os.path.exists(index_fp)):
            raise ValueError(f"Artifacts for doc_id {doc_id} do not exist on disk.")

        # Load chunks
        with open(chunks_fp, 'r', encoding='utf-8') as f:
            self.doc_chunks[doc_id] = json.load(f)

        # Load embeddings
        self.doc_embeddings[doc_id] = np.load(emb_fp)

        # Load FAISS index
        self.doc_indexes[doc_id] = faiss.read_index(index_fp)

    def chunk_text(self, text: str) -> list:
        chunks = re.split(r'\n{2,}|(?<=[.!?])\s+(?=[A-Z])', text)
        chunks = [chunk.strip() for chunk in chunks if chunk.strip()]
        return chunks

    def process_document(self, doc_id: str, text: str):
        chunks = self.chunk_text(text)
        cache = self.doc_embedding_cache.setdefault(doc_id, {})
        embeddings = np.vstack([self.embed_text(ch, doc_id) for ch in chunks])
        dim = embeddings.shape[1]
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)
        self.doc_chunks[doc_id] = chunks
        self.doc_embeddings[doc_id] = embeddings
        self.doc_indexes[doc_id] = index

    def embed_text(self, text: str, doc_id: str = None):
        if doc_id is not None:
            cache = self.doc_embedding_cache.setdefault(doc_id, {})
            if text in cache:
                return cache[text]
        else:
            cache = self.doc_embedding_cache.setdefault('__global__', {})
            if text in cache:
                return cache[text]
        if _embedding_model:
            vec = _embedding_model.encode(text, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=True)
        else:
            vec = _simple_embed(text)
        cache[text] = vec
        return vec

    def build_index(self, chunks: list):
        self.chunks = chunks
        embeddings = np.vstack([self.embed_text(ch) for ch in chunks])
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)
        self.chunk_cache["chunks"] = chunks
        self.chunk_cache["embeddings"] = embeddings

    def retrieve(self, doc_id: str, query: str) -> list:
        if doc_id not in self.doc_chunks:
            raise ValueError("Document not processed or not found.")
        chunks = self.doc_chunks[doc_id]
        prefiltered = [ch for ch in chunks if any(kw in ch.lower() for kw in RAG_KEYWORDS)]
        if not prefiltered:
            prefiltered = chunks
        query_vec = self.embed_text(query, doc_id)
        k = min(Config.RAG_TOP_K, len(prefiltered))
        pf_embeddings = np.vstack([self.embed_text(ch, doc_id) for ch in prefiltered])
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

    def get_risk_context(self, doc_id: str, top_k=5, max_words=300) -> str:
        if doc_id not in self.doc_chunks:
            raise ValueError("Document not processed or not found.")
        chunks = self.doc_chunks[doc_id]
        risk_keywords = [
            "liability", "indemnity", "termination", "risk", "exposure", "warranty",
            "payment", "breach", "governing law", "arbitration", "confidential"
        ]
        prefiltered = [ch for ch in chunks if any(kw in ch.lower() for kw in risk_keywords)]
        if not prefiltered:
            prefiltered = chunks
        # Remove near-duplicates (by lowering and ignoring >75% overlap)
        unique_chunks = []
        seen = set()
        for ch in prefiltered:
            signature = " ".join(sorted(set(ch.lower().split())))
            if signature not in seen:
                unique_chunks.append(ch)
                seen.add(signature)
            if len(unique_chunks) >= top_k:
                break
        result_chunks = []
        total_words = 0
        for chunk in unique_chunks:
            cleaned = chunk.strip()
            wcount = len(cleaned.split())
            if cleaned and total_words + wcount <= max_words:
                result_chunks.append(cleaned)
                total_words += wcount
            if total_words >= max_words:
                break
        return "\n\n".join(result_chunks)

    def get_compact_context(self, doc_id: str, query: str) -> str:
        chunks = self.retrieve(doc_id, query)
        return "\n\n".join(chunks)
