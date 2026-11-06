
from pathlib import Path

import pymupdf


def extract_text_from_pdf(file_path: Path) -> dict:
    pages = []
    total_characters = 0

    with pymupdf.open(file_path) as document:
        page_count = len(document)

        for page_number, page in enumerate(document, start=1):
            text = page.get_text("text").strip()

            pages.append({
                "page_number": page_number,
                "text": text
            })

            total_characters += len(text)

    return {
        "page_count": page_count,
        "total_characters": total_characters,
        "pages": pages
    }
