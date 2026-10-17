from app.pdf_utils import split_text, extract_pages
from io import BytesIO
from pypdf import PdfWriter
import pytest


def test_split_empty():
    assert split_text('   \n  ') == []


def test_split_overlap():
    chunks = split_text(' '.join(['hello'] * 80), chunk_size=65, overlap=12)
    assert len(chunks) > 1
    assert all(len(c) <= 65 for c in chunks)
    assert chunks[0].split()[-1] == chunks[1].split()[0]


def test_invalid_split_settings():
    with pytest.raises(ValueError):
        split_text('anything', chunk_size=10, overlap=10)


def test_blank_pdf():
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    data = BytesIO()
    writer.write(data)
    assert extract_pages(data.getvalue()) == ['']
