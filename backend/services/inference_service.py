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

    def analyze_risk(self, doc_id: str):
        context = self.rag.get_risk_context(doc_id, top_k=5, max_words=300)
        prompt = (
            "Analyze the contract and identify risks.\n\n"
            "Return:\n"
            "Overall Risk: <Low | Medium | High>\n"
            "\nKey Risks:\n"
            "- Point 1 (short explanation)\n"
            "- Point 2\n"
            "- Point 3\n"
            "\nKeep response concise.\n"
            "\nCONTEXT:\n" + context
        )
        result = self.llm.generate(prompt)
        # Parse LLM output
        overall = ""
        points = []
        try:
            lines = result.strip().splitlines()
            for line in lines:
                if line.lower().startswith("overall risk:"):
                    overall = line.split(":",1)[-1].strip().capitalize()
                elif line.lstrip().startswith("-"):
                    points.append(line.lstrip("- ").strip())
            if not overall:
                # fallback: try match in plain text
                for word in ("High", "Medium", "Low"):
                    if word.lower() in result.lower():
                        overall = word
                        break
            if not points:
                # fallback: just use all content after 'Key Risks:' split
                if "Key Risks:" in result:
                    after = result.split("Key Risks:",1)[-1]
                    points = [pt.strip().lstrip("- ") for pt in after.split("\n") if pt.strip()]
            if not points:
                points = [result.strip()]
        except Exception:
            overall = ""
            points = [result.strip()]
        return {"overall_risk": overall, "points": points}

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