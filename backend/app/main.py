import logging
from functools import lru_cache
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .store import NotesStore
from .llm import LLMService
from .pdf_utils import extract_pages
from .schemas import DocumentOut, AskRequest, AskResponse, QuizRequest, QuizResponse, Source

settings = get_settings()
app = FastAPI(title='Lecture Notes RAG Assistant API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.frontend_origin.split(',')],
                   allow_credentials=False, allow_methods=['GET', 'POST', 'DELETE'], allow_headers=['*'])
logger = logging.getLogger(__name__)


@lru_cache
def get_store() -> NotesStore:
    return NotesStore(get_settings())


def get_llm() -> LLMService:
    return LLMService(get_settings())


@app.get('/health')
def health():
    return {'status': 'ok'}


@app.get('/documents', response_model=list[DocumentOut])
def documents(store: NotesStore = Depends(get_store)):
    return store.list_documents()


@app.post('/documents', response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile = File(...), store: NotesStore = Depends(get_store)):
    filename = (file.filename or '').replace('\\', '/').split('/')[-1]
    if not filename.lower().endswith('.pdf'):
        raise HTTPException(415, 'Only PDF files are accepted')
    limit = settings.max_upload_mb * 1024 * 1024
    contents = await file.read(limit + 1)
    await file.close()
    if len(contents) > limit:
        raise HTTPException(413, f'File exceeds {settings.max_upload_mb} MB')
    if not contents.startswith(b'%PDF-'):
        raise HTTPException(415, 'Invalid PDF file')
    try:
        pages = extract_pages(contents)
        return store.add_document(filename, pages)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.exception('Document ingestion failed')
        raise HTTPException(422, 'PDF could not be processed') from exc


@app.delete('/documents/{document_id}', status_code=204)
def delete_document(document_id: str, store: NotesStore = Depends(get_store)):
    if not store.delete_document(document_id):
        raise HTTPException(404, 'Document not found')


@app.post('/ask', response_model=AskResponse)
def ask(body: AskRequest, store: NotesStore = Depends(get_store), llm: LLMService = Depends(get_llm)):
    sources = store.search(body.question, body.document_ids, settings.top_k)
    if not sources:
        return AskResponse(answer='Seçili belgelerde yanıt oluşturmak için kullanılabilecek içerik bulunamadı.', sources=[])
    try:
        answer = llm.answer(body.question, sources)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        logger.exception('Question answering failed')
        raise HTTPException(502, 'LLM provider request failed') from exc
    return AskResponse(answer=answer, sources=[Source(**s) for s in sources])


@app.post('/quiz', response_model=QuizResponse)
def quiz(body: QuizRequest, store: NotesStore = Depends(get_store), llm: LLMService = Depends(get_llm)):
    sources = store.quiz_context(body.document_ids)
    if not sources:
        raise HTTPException(422, 'Upload or select a PDF with extractable text first')
    try:
        return QuizResponse(questions=llm.quiz(sources, body.count))
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    except Exception as exc:
        logger.exception('Quiz generation failed')
        raise HTTPException(502, 'Could not generate quiz') from exc
