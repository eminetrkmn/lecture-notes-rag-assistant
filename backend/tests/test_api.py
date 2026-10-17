from fastapi.testclient import TestClient
from app.main import app, get_store, get_llm


class StubStore:
    def list_documents(self):
        return [{'id': 'doc', 'filename': 'lesson.pdf', 'pages': 2, 'chunks': 3}]

    def search(self, question, ids, limit):
        return [{'document_id': 'doc', 'filename': 'lesson.pdf', 'page': 2,
                 'excerpt': 'Gradient descent minimizes loss.', 'distance': 0.1}]

    def quiz_context(self, ids):
        return [{'page': 2, 'excerpt': 'Gradient descent minimizes loss.'}]


class StubLLM:
    def answer(self, question, sources):
        return 'Gradient descent minimizes loss. [Kaynak 1]'

    def quiz(self, sources, count):
        return [{'question': 'What minimizes loss?', 'options': ['Gradient descent', 'RGB', 'HTTP', 'CSS'],
                 'correct_index': 0, 'explanation': 'From the notes', 'source_page': 2}]


def test_api():
    app.dependency_overrides[get_store] = lambda: StubStore()
    app.dependency_overrides[get_llm] = lambda: StubLLM()
    try:
        client = TestClient(app)
        assert client.get('/health').json()['status'] == 'ok'
        assert client.get('/documents').json()[0]['filename'] == 'lesson.pdf'
        answer = client.post('/ask', json={'question': 'What is gradient descent?'}).json()
        assert answer['sources'][0]['page'] == 2
        assert '[Kaynak 1]' in answer['answer']
        quiz = client.post('/quiz', json={'count': 1}).json()
        assert quiz['questions'][0]['correct_index'] == 0
    finally:
        app.dependency_overrides.clear()
