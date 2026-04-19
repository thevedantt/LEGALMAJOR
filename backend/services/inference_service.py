import json
import re
from backend.interfaces.llm_client import LLMClient
from backend.services.rag_service import RAGService
from backend.core.config import Config

class InferenceService:
    def __init__(self):
        self.llm = LLMClient()
        self.rag = RAGService()

    def ask_question(self, question, context):
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

    def analyze_risk(self, context: str):
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

    def analyze_fairness(self, context: str):
        prompt = (
            "Assess fairness in the contract. Return JSON only with keys: "
            "favors (Company|Customer|Balanced), fairness_score (0-1), reason (short).\n"
            "CONTEXT:\n" + context
        )
        result = self.llm.generate(prompt)
        try:
            fixed = result.replace("'", '"')
            output = json.loads(fixed)
            return {
                "favors": output.get("favors", "Balanced"),
                "fairness_score": float(output.get("fairness_score", 0.5)),
                "reason": output.get("reason", "")
            }
        except Exception:
            # Fallback parsing
            favors = "Balanced"
            if "company" in result.lower():
                favors = "Company"
            elif "customer" in result.lower() or "client" in result.lower():
                favors = "Customer"
            score_match = re.search(r"(0\.\d+|1\.0|1)", result)
            score = float(score_match.group(1)) if score_match else 0.5
            return {"favors": favors, "fairness_score": score, "reason": result.strip()}

    def check_conflicts(self, context: str):
        prompt = (
            "Identify conflicting or contradictory clauses. Return JSON only: "
            "{\"conflicts\":[{\"clauses\":[\"Clause A\",\"Clause B\"],\"reason\":\"...\"}]}\n"
            "CONTEXT:\n" + context
        )
        result = self.llm.generate(prompt)
        try:
            fixed = result.replace("'", '"')
            output = json.loads(fixed)
            conflicts = output.get("conflicts", []) if isinstance(output, dict) else output
            return {"conflicts": conflicts}
        except Exception:
            return {"conflicts": []}

    def extract_clauses(self, text: str):
        prompt = (
            "Extract key clauses from the contract. Return a JSON array only, each with: "
            "type, risk (High|Medium|Low), text, section.\n"
            "CONTEXT:\n" + text
        )
        result = self.llm.generate(prompt)
        try:
            fixed = result.replace("'", '"')
            output = json.loads(fixed)
            if isinstance(output, dict) and "clauses" in output:
                output = output["clauses"]
            return output if isinstance(output, list) else []
        except Exception:
            # Fallback: simple heuristic from chunks
            clauses = []
            for chunk in text.split("\n\n"):
                if len(clauses) >= 6:
                    break
                lowered = chunk.lower()
                if not lowered.strip():
                    continue
                ctype = "General"
                risk = "Low"
                if any(k in lowered for k in ["liability", "indemnity"]):
                    ctype = "Liability"
                    risk = "High"
                elif any(k in lowered for k in ["termination", "breach"]):
                    ctype = "Termination"
                    risk = "Medium"
                elif any(k in lowered for k in ["payment", "fees"]):
                    ctype = "Payment"
                    risk = "Medium"
                section_match = re.search(r"\b\d+(?:\.\d+)+\b", chunk)
                section = section_match.group(0) if section_match else ""
                clauses.append({
                    "type": ctype,
                    "risk": risk,
                    "text": chunk.strip(),
                    "section": section
                })
            return clauses

    def explain_term(self, term: str):
        prompt = (
            "Explain the legal term in simple language. Return JSON only with keys: "
            "definition, example. Term: " + term
        )
        result = self.llm.generate(prompt)
        try:
            fixed = result.replace("'", '"')
            output = json.loads(fixed)
            return {
                "definition": output.get("definition", ""),
                "example": output.get("example", "")
            }
        except Exception:
            return {"definition": result.strip(), "example": ""}

    def suggest_improvements(self, context: str):
        prompt = (
            "Suggest safer clause improvements. Return JSON only with keys: "
            "suggestions (array of short bullet strings).\nCONTEXT:\n" + context
        )
        result = self.llm.generate(prompt)
        try:
            fixed = result.replace("'", '"')
            output = json.loads(fixed)
            if isinstance(output, dict) and "suggestions" in output:
                return {"suggestions": output["suggestions"]}
            if isinstance(output, list):
                return {"suggestions": output}
        except Exception:
            pass
        # Fallback: split lines
        suggestions = [s.strip("- ").strip() for s in result.splitlines() if s.strip()]
        return {"suggestions": suggestions}

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
