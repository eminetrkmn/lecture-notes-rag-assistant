from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(BASE_DIR / '.env'), extra='ignore')
    groq_api_key: str = ''
    groq_model: str = 'llama-3.3-70b-versatile'
    embedding_model: str = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    data_dir: Path = BASE_DIR / 'data'
    max_upload_mb: int = 20
    chunk_size: int = 900
    chunk_overlap: int = 160
    top_k: int = 5
    frontend_origin: str = 'http://localhost:5173'


@lru_cache
def get_settings() -> Settings:
    return Settings()
