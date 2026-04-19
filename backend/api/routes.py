from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from services.inference_service import InferenceService
from services.rag_service import RAGService
import hashlib
import io
from db import SessionLocal, ContractDocument, init_db
import os
import threading

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
        result = infer.analyze_risk(req.doc_id)
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
