from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: str
    filename: str
    pages: int
    chunks: int


class Source(BaseModel):
    document_id: str
    filename: str
    page: int
    excerpt: str
    distance: float | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    document_ids: list[str] | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]


class QuizRequest(BaseModel):
    document_ids: list[str] | None = None
    count: int = Field(default=5, ge=1, le=10)


class QuizQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=4, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str
    source_page: int | None = None


class QuizResponse(BaseModel):
    questions: list[QuizQuestion]
