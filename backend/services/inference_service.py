import json
from interfaces.llm_client import LLMClient
from services.rag_service import RAGService
from core.config import Config

class InferenceService:
    def __init__(self):
        self.llm = LLMClient()
        self.rag = RAGService()

    def ask_question(self, question, document):
        if not self.rag.chunks or self.rag.chunks != self.rag.chunk_cache.get("chunks"):
            chunks = self.rag.chunk_text(document)
            self.rag.build_index(chunks)
        context = self.rag.get_compact_context(question)
        prompt = f"Answer using context. Be concise. If not found, say so.\nContext:\n{context}\n\nQuestion: {question}\nAnswer:"
        answer = self.llm.generate(prompt)
        return {"answer": answer.strip()}

    def analyze_clause(self, clause):
        prompt = f"Analyze the legal contract clause below.\nReturn Type, Risk, Reason (short).\nClause:\n{clause}\n\nOutput as JSON. Example: {{'type': ..., 'risk': ..., 'reason': ...}}"
        result = self.llm.generate(prompt)
        try:
            fixed = result.replace("'", '"')
            output = json.loads(fixed)
            if 'termination' in clause.lower():
                output['risk'] = 'high'
                output['reason'] += ' [Overridden: Termination clause detected]'
            return output
        except Exception:
            return {"type": "", "risk": "", "reason": result.strip()}

    def summarize(self, text):
        chunks = self.rag.chunk_text(text)
        summaries = []
        for chunk in chunks:
            prompt = f"Summarize in 1-2 bullet points:\n{chunk}"
            s = self.llm.generate(prompt)
            summaries.append(s.strip())
        merge_prompt = "Summarize in 5 bullet points SUMMARY:\n" + "\n".join(summaries)
        concise = self.llm.generate(merge_prompt)
        return {"summary": concise.strip()}