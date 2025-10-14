import os
import sys
from typing import List

import fitz
import pytest


os.environ.setdefault("OPENAI_API_KEY", "test-key")

# Ensure the backend application package is importable when running tests from the
# repository root.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.services.pdf_processor import PDFProcessor  # noqa: E402


def _create_sample_pdf(path: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    text = (
        "Abstract\n"
        "This is the abstract.\n\n"
        "Introduction\n"
        "This is the introduction.\n\n"
        "Conclusion\n"
        "This is the conclusion."
    )
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_extract_sections_uses_cached_full_text(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    _create_sample_pdf(str(pdf_path))

    processor = PDFProcessor()

    # Compute the full text and baseline sections before patching the method.
    doc = fitz.open(str(pdf_path))
    full_text = PDFProcessor._extract_full_text(processor, doc)
    baseline_sections = PDFProcessor._extract_sections(processor, doc, full_text)
    doc.close()

    def fail_extract(_self, _doc):
        raise AssertionError(
            "_extract_full_text should not be called during section extraction"
        )

    monkeypatch.setattr(PDFProcessor, "_extract_full_text", fail_extract)

    doc = fitz.open(str(pdf_path))
    sections = processor._extract_sections(doc, full_text)
    doc.close()

    assert sections == baseline_sections


@pytest.mark.asyncio
async def test_process_file_reuses_full_text(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    _create_sample_pdf(str(pdf_path))

    baseline_processor = PDFProcessor()
    baseline_result = await baseline_processor.process_file(str(pdf_path))

    full_text_calls = {"count": 0, "values": []}
    captured_sections_text: List[str] = []

    real_extract_full_text = PDFProcessor._extract_full_text
    real_extract_sections = PDFProcessor._extract_sections

    def counting_extract_full_text(self, doc):
        text = real_extract_full_text(self, doc)
        full_text_calls["count"] += 1
        full_text_calls["values"].append(text)
        return text

    def capturing_extract_sections(self, doc, full_text):
        captured_sections_text.append(full_text)
        return real_extract_sections(self, doc, full_text)

    monkeypatch.setattr(PDFProcessor, "_extract_full_text", counting_extract_full_text)
    monkeypatch.setattr(PDFProcessor, "_extract_sections", capturing_extract_sections)

    processor = PDFProcessor()
    result = await processor.process_file(str(pdf_path))

    assert full_text_calls["count"] == 1
    assert captured_sections_text == full_text_calls["values"]
    assert result["text"] == baseline_result["text"]
    assert result["sections"] == baseline_result["sections"]
