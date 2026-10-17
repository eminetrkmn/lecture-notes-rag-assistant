from io import BytesIO
from pypdf import PdfReader


def split_text(text: str, chunk_size: int = 900, overlap: int = 160) -> list[str]:
    """Create overlapping, word-boundary-friendly chunks; never produce an infinite loop."""
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError('chunk_size must exceed overlap and be positive')
    normalized = ' '.join(text.split())
    if not normalized:
        return []
    chunks = []
    start = 0
    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(' ', start + max(1, chunk_size // 2), end)
            if boundary > start:
                end = boundary
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = max(start + 1, end - overlap)
    return [chunk for chunk in chunks if chunk]


def extract_pages(contents: bytes) -> list[str]:
    reader = PdfReader(BytesIO(contents), strict=False)
    if reader.is_encrypted:
        raise ValueError('Password-protected PDFs are not supported')
    return [(page.extract_text(extraction_mode='plain') or '').strip() for page in reader.pages]
