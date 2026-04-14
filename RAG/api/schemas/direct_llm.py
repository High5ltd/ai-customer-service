from pydantic import BaseModel, Field


class DirectLLMRequest(BaseModel):
    """Plain user text → LLM (no retrieval). For integration testing (e.g. Chatwoot)."""

    query: str = Field(..., min_length=1, description="User message sent straight to the chat model")
    system_prompt: str | None = Field(
        default=None,
        description="Optional system message; if omitted, a short default assistant prompt is used",
    )
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class DirectLLMResponse(BaseModel):
    answer: str
