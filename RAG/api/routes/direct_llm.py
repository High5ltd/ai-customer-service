from fastapi import APIRouter

from RAG.api.schemas.direct_llm import DirectLLMRequest, DirectLLMResponse
from RAG.services import direct_llm as direct_llm_service

router = APIRouter(prefix="/api/v1/direct-llm", tags=["direct-llm"])


@router.post("", response_model=DirectLLMResponse)
async def direct_llm_chat(request: DirectLLMRequest) -> DirectLLMResponse:
    """
    Send `query` to the configured chat model without RAG retrieval.
    Intended for livechat / Chatwoot integration tests.
    """
    answer = await direct_llm_service.complete_direct_chat(
        query=request.query,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
    )
    return DirectLLMResponse(answer=answer)
