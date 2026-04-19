from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from backend.services.inference_service import InferenceService
from backend.services.rag_service import RAGService
from backend.db import SessionLocal, ContractDocument, init_db
import os
import threading
import hashlib
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

db_lock = threading.Lock()

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None  # Will throw at runtime if not installed

router = APIRouter()
infer = InferenceService()
rag = RAGService()

class AskRequest(BaseModel):
    question: str
    doc_id: str

class AnalyzeRiskRequest(BaseModel):
    doc_id: str

class OverallRiskRequest(BaseModel):
    doc_id: str

class FairnessRequest(BaseModel):
    doc_id: str

class ConflictRequest(BaseModel):
    doc_id: str

class ExtractClausesRequest(BaseModel):
    doc_id: str

class ExplainTermRequest(BaseModel):
    term: str

class SuggestImprovementsRequest(BaseModel):
    doc_id: str

class GenerateReportRequest(BaseModel):
    doc_id: str

class ClauseAnalyzeRequest(BaseModel):
    clause: str

class SummarizeRequest(BaseModel):
    doc_id: str
    query: str = ""  # Optional summarization focus; empty for global summary

@router.post("/ask")
async def ask_view(req: AskRequest):
    try:
        # Use RAG to get the most relevant context for the question
        try:
            context = rag.get_compact_context(req.doc_id, req.question)
        except Exception as e:
            # Try loading from disk
            try:
                rag.load_from_disk(req.doc_id)
                context = rag.get_compact_context(req.doc_id, req.question)
            except Exception:
                raise HTTPException(status_code=404, detail=f"Document not found. Please upload your PDF and try again.")
        result = infer.ask_question(req.question, context)
        return result
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-risk")
async def analyze_risk_view(req: AnalyzeRiskRequest):
    try:
        if req.doc_id not in rag.doc_chunks:
            try:
                rag.load_from_disk(req.doc_id)
            except Exception:
                session = SessionLocal()
                with db_lock:
                    obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
                session.close()
                if not obj:
                    raise ValueError("Document not processed or not found.")
                rag.process_document(req.doc_id, obj.text)
                try:
                    rag.save_to_disk(req.doc_id)
                except Exception:
                    pass
        context = rag.get_risk_context(req.doc_id, top_k=5, max_words=300)
        result = infer.analyze_risk(context)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/overall-risk")
async def overall_risk_view(req: OverallRiskRequest):
    try:
        # Ensure doc is loaded
        if req.doc_id not in rag.doc_chunks:
            try:
                rag.load_from_disk(req.doc_id)
            except Exception:
                session = SessionLocal()
                with db_lock:
                    obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
                session.close()
                if not obj:
                    raise ValueError("Document not processed or not found.")
                rag.process_document(req.doc_id, obj.text)
                try:
                    rag.save_to_disk(req.doc_id)
                except Exception:
                    pass
        context = rag.get_risk_context(req.doc_id, top_k=8, max_words=600)
        risk_info = infer.analyze_risk(context)
        # Count risk types in points
        points = risk_info.get("points") or []
        breakdown = {"High":0, "Medium":0, "Low":0}
        for pt in points:
            val = pt.lower()
            if "high" in val:
                breakdown["High"] += 1
            elif "medium" in val:
                breakdown["Medium"] += 1
            elif "low" in val:
                breakdown["Low"] += 1
        total = sum(breakdown.values())
        # Fallback: if all zero, boost overall
        if not total:
            if risk_info.get("overall_risk","").lower() == "high":
                breakdown["High"] = 1
                total = 1
            elif risk_info.get("overall_risk","").lower() == "medium":
                breakdown["Medium"] = 1
                total = 1
            elif risk_info.get("overall_risk","").lower() == "low":
                breakdown["Low"] = 1
                total = 1
        # Decide overall
        best = max(breakdown, key=lambda k: breakdown[k])
        # Compute score
        norm_score = 0.0
        if total:
            norm_score = (
                3*breakdown["High"]+2*breakdown["Medium"]+1*breakdown["Low"]
            )/(3*total)
        else:
            norm_score = 0.0
        resp = {
            "overall_risk": best,
            "score": float(f"{norm_score:.2f}"),
            "breakdown": breakdown
        }
        return resp
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fairness")
async def fairness_view(req: FairnessRequest):
    try:
        if req.doc_id not in rag.doc_chunks:
            try:
                rag.load_from_disk(req.doc_id)
            except Exception:
                session = SessionLocal()
                with db_lock:
                    obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
                session.close()
                if not obj:
                    raise ValueError("Document not processed or not found.")
                rag.process_document(req.doc_id, obj.text)
                try:
                    rag.save_to_disk(req.doc_id)
                except Exception:
                    pass
        context = rag.get_compact_context(req.doc_id, "fairness")
        return infer.analyze_fairness(context)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/check-conflicts")
async def check_conflicts_view(req: ConflictRequest):
    try:
        if req.doc_id not in rag.doc_chunks:
            try:
                rag.load_from_disk(req.doc_id)
            except Exception:
                session = SessionLocal()
                with db_lock:
                    obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
                session.close()
                if not obj:
                    raise ValueError("Document not processed or not found.")
                rag.process_document(req.doc_id, obj.text)
                try:
                    rag.save_to_disk(req.doc_id)
                except Exception:
                    pass
        context = rag.get_compact_context(req.doc_id, "conflicts")
        return infer.check_conflicts(context)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-clauses")
async def extract_clauses_view(req: ExtractClausesRequest):
    try:
        if req.doc_id not in rag.doc_chunks:
            try:
                rag.load_from_disk(req.doc_id)
            except Exception:
                session = SessionLocal()
                with db_lock:
                    obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
                session.close()
                if not obj:
                    raise ValueError("Document not processed or not found.")
                rag.process_document(req.doc_id, obj.text)
                try:
                    rag.save_to_disk(req.doc_id)
                except Exception:
                    pass
        # Use full text if available in DB for better clause extraction
        session = SessionLocal()
        with db_lock:
            obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
        session.close()
        text = obj.text if obj else "\n\n".join(rag.doc_chunks.get(req.doc_id, []))
        return infer.extract_clauses(text)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/explain-term")
async def explain_term_view(req: ExplainTermRequest):
    try:
        return infer.explain_term(req.term)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggest-improvements")
async def suggest_improvements_view(req: SuggestImprovementsRequest):
    try:
        if req.doc_id not in rag.doc_chunks:
            try:
                rag.load_from_disk(req.doc_id)
            except Exception:
                session = SessionLocal()
                with db_lock:
                    obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
                session.close()
                if not obj:
                    raise ValueError("Document not processed or not found.")
                rag.process_document(req.doc_id, obj.text)
                try:
                    rag.save_to_disk(req.doc_id)
                except Exception:
                    pass
        context = rag.get_risk_context(req.doc_id, top_k=6, max_words=600)
        return infer.suggest_improvements(context)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-report")
async def generate_report_view(req: GenerateReportRequest):
    try:
        # Ensure doc is loaded
        if req.doc_id not in rag.doc_chunks:
            try:
                rag.load_from_disk(req.doc_id)
            except Exception:
                session = SessionLocal()
                with db_lock:
                    obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
                session.close()
                if not obj:
                    raise ValueError("Document not processed or not found.")
                rag.process_document(req.doc_id, obj.text)
                try:
                    rag.save_to_disk(req.doc_id)
                except Exception:
                    pass

        # Build report parts
        summary = infer.summarize(rag.get_compact_context(req.doc_id, "summary"))
        risk = infer.analyze_risk(rag.get_risk_context(req.doc_id, top_k=6, max_words=600))
        fairness = infer.analyze_fairness(rag.get_compact_context(req.doc_id, "fairness"))
        # Use full text for clause extraction if available
        session = SessionLocal()
        with db_lock:
            obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
        session.close()
        text = obj.text if obj else "\n\n".join(rag.doc_chunks.get(req.doc_id, []))
        clauses = infer.extract_clauses(text)

        # Generate PDF in memory
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        width, height = letter
        y = height - 40
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, "Legal Contract Report")
        y -= 30

        def draw_section(title, lines):
            nonlocal y
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, y, title)
            y -= 18
            c.setFont("Helvetica", 10)
            for line in lines:
                if y < 60:
                    c.showPage()
                    y = height - 40
                    c.setFont("Helvetica", 10)
                c.drawString(50, y, line[:110])
                y -= 14
            y -= 8

        summary_text = summary.get("summary", "") if isinstance(summary, dict) else str(summary)
        summary_lines = [s.strip("- ").strip() for s in summary_text.splitlines() if s.strip()]
        draw_section("Summary", summary_lines[:10])

        risk_lines = [f"Overall Risk: {risk.get('overall_risk','')}" ]
        risk_lines += [f"- {pt}" for pt in (risk.get("points") or [])]
        draw_section("Risk Analysis", risk_lines[:10])

        fairness_lines = [
            f"Favors: {fairness.get('favors','Balanced')}",
            f"Fairness Score: {fairness.get('fairness_score',0.5)}",
            f"Reason: {fairness.get('reason','')}"
        ]
        draw_section("Fairness", fairness_lines)

        clause_lines = []
        for cobj in clauses[:8]:
            clause_lines.append(f"[{cobj.get('section','')}] {cobj.get('type','Clause')} ({cobj.get('risk','')}): {cobj.get('text','')}")
        draw_section("Clauses", clause_lines)

        c.showPage()
        c.save()
        buf.seek(0)
        headers = {
            "Content-Disposition": f"attachment; filename=contract_report_{req.doc_id}.pdf"
        }
        return StreamingResponse(buf, media_type="application/pdf", headers=headers)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Try RAM, fallback to DB
    try:
        if req.doc_id not in rag.doc_chunks:
            # Not in RAM: try disk, then fallback to DB
            try:
                rag.load_from_disk(req.doc_id)
            except Exception:
                # Fallback to DB (legacy)
                session = SessionLocal()
                with db_lock:
                    obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
                session.close()
                if not obj:
                    raise ValueError("Document not processed or not found.")
                rag.process_document(req.doc_id, obj.text)
                try:
                    rag.save_to_disk(req.doc_id)
                except Exception:
                    pass  # silent: best effort
        context = rag.get_risk_context(req.doc_id, top_k=5, max_words=300)
        result = infer.analyze_risk(context)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Existing clause-level analyzer kept for reference
@router.post("/analyze-clause-risk")
async def analyze_clause_risk_view(req: ClauseAnalyzeRequest):
    try:
        result = infer.analyze_clause(req.clause)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summarize")
async def summarize_view(req: SummarizeRequest):
    try:
        # Try RAM, fallback to DB
        if req.doc_id not in rag.doc_chunks:
            # Not in RAM: try disk, then fallback to DB
            try:
                rag.load_from_disk(req.doc_id)
            except Exception:
                session = SessionLocal()
                with db_lock:
                    obj = session.query(ContractDocument).filter_by(doc_id=req.doc_id).first()
                session.close()
                if not obj:
                    raise ValueError("Document not processed or not found.")
                rag.process_document(req.doc_id, obj.text)
                try:
                    rag.save_to_disk(req.doc_id)
                except Exception:
                    pass  # best effort
        context = rag.get_compact_context(req.doc_id, req.query or "summary")
        result = infer.summarize(context)
        return result
    except HTTPException as he:
        raise he
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF documents are supported.")

    pdf_bytes = await file.read()
    max_size = 10 * 1024 * 1024  # 10 MB
    if len(pdf_bytes) > max_size:
        raise HTTPException(status_code=413, detail="PDF file is too large (max 10 MB).")
    doc_hash = hashlib.sha256(pdf_bytes).hexdigest()

    try:
        if fitz is None:
            raise ImportError('PyMuPDF (fitz) is not installed.')
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if doc.page_count == 0:
            raise ValueError("No pages found in PDF.")
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        if not text.strip():
            raise ValueError("No extractable text found in PDF.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF extraction failed: {str(e)}")

    # Store document in DB if new, or update timestamp if existing
    session = SessionLocal()
    with db_lock:
        init_db()
        obj = session.query(ContractDocument).filter_by(doc_id=doc_hash).first()
        if not obj:
            obj = ContractDocument(
                doc_id=doc_hash,
                filename=file.filename or "unknown.pdf",
                text=text,
            )
            session.add(obj)
            session.commit()
    session.close()

    # Process in the RAG pipeline and cache by doc_id
    try:
        rag.process_document(doc_hash, text)
        try:
            rag.save_to_disk(doc_hash)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to persist document artifacts: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG processing failed: {str(e)}")

    return {"doc_id": doc_hash, "length": len(text)}
