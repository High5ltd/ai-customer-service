from pydantic import BaseModel


class CitationSchema(BaseModel):
    index: int
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    score: float
    text: str


class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"
    document_ids: list[str] | None = None


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationSchema]
    session_id: str
