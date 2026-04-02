from fastapi import APIRouter
from ..schemas import CodeAssistRequest
from ..services.ai_agent import analyze_code

router = APIRouter(prefix="/assistant", tags=["AI Code Assistant"])

@router.post("/analyze")
def request_code_analysis(request: CodeAssistRequest):
    result = analyze_code(
        code=request.code, 
        language=request.language, 
        action=request.action, 
        question=request.question,
        context_text=request.context_text
    )
    return result
