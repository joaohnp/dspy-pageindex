"""PDF utilities for text extraction."""

from io import BytesIO
from pathlib import Path
from typing import BinaryIO, List, Union

from pydantic import BaseModel
from PyPDF2 import PdfReader


class PageInfo(BaseModel):
    """Information about a PDF page."""

    page_num: int
    text: str


class PDFMetadata(BaseModel):
    """Metadata extracted from a PDF."""

    num_pages: int
    metadata: dict = {}


def extract_pages(
    pdf_source: Union[Path, str, bytes, BinaryIO],
) -> List[PageInfo]:
    """
    Extract text from PDF pages.

    Args:
        pdf_source: Path to PDF file, bytes, or file-like object

    Returns:
        List of PageInfo objects
    """
    # Normalize input to bytes
    if isinstance(pdf_source, (str, Path)):
        pdf_path = Path(pdf_source)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    elif isinstance(pdf_source, bytes):
        pdf_bytes = pdf_source
    elif hasattr(pdf_source, "read"):
        pdf_bytes = pdf_source.read()
    else:
        raise TypeError(f"Unsupported pdf_source type: {type(pdf_source)}")

    # Parse PDF
    reader = PdfReader(BytesIO(pdf_bytes))
    pages = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(PageInfo(page_num=i, text=text))

    return pages


def get_pdf_metadata(
    pdf_source: Union[Path, str, bytes, BinaryIO],
) -> PDFMetadata:
    """Extract metadata from a PDF."""
    # Normalize input to bytes
    if isinstance(pdf_source, (str, Path)):
        pdf_path = Path(pdf_source)
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    elif isinstance(pdf_source, bytes):
        pdf_bytes = pdf_source
    elif hasattr(pdf_source, "read"):
        pdf_bytes = pdf_source.read()
    else:
        raise TypeError(f"Unsupported pdf_source type: {type(pdf_source)}")

    reader = PdfReader(BytesIO(pdf_bytes))
    return PDFMetadata(
        num_pages=len(reader.pages),
        metadata=dict(reader.metadata) if reader.metadata else {},
    )
