from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.inference_service import InferenceService

router = APIRouter()
infer = InferenceService()

class AskRequest(BaseModel):
    question: str
    context: str

class AnalyzeRiskRequest(BaseModel):
    clause: str

class SummarizeRequest(BaseModel):
    text: str

@router.post("/ask")
async def ask_view(req: AskRequest):
    try:
        result = infer.ask_question(req.question, req.context)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze-risk")
async def analyze_risk_view(req: AnalyzeRiskRequest):
    try:
        result = infer.analyze_clause(req.clause)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/summarize")
async def summarize_view(req: SummarizeRequest):
    try:
        result = infer.summarize(req.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))