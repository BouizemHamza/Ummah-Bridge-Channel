# library_ingest.py
# Build islamic_library.db from PDF files in the pdfs/ folder.
#
# Run locally:
#   python library_ingest.py
#
# Requirements:
#   pip install pypdf

import unicodedata
import argparse
import hashlib
import re
import sqlite3
from pathlib import Path

from pypdf import PdfReader


DEFAULT_PDF_DIR = "pdfs"
DEFAULT_DB_PATH = "islamic_library.db"


BOOK_CATEGORIES = {
    "الرحيق": "السيرة النبوية",
    "المختوم": "السيرة النبوية",
    "زاد المعاد": "السيرة النبوية",
    "البداية": "قصص الأنبياء والتاريخ",
    "النهاية": "قصص الأنبياء والتاريخ",
    "قصص الأنبياء": "قصص الأنبياء",
    "الصحابة": "الصحابة",
    "سير أعلام": "التراجم",
}


def clean_text(text: str) -> str:
    text = text or ""

    # Convert Arabic Presentation Forms like ﻟ ﻜ ﺘ to normal Arabic letters
    text = unicodedata.normalize("NFKC", text)

    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def infer_category(filename: str) -> str:
    for key, category in BOOK_CATEGORIES.items():
        if key in filename:
            return category
    return "عام"


def chunk_text(text: str, max_chars: int = 1300, overlap: int = 180) -> list[str]:
    text = clean_text(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                chunks.append(current)

            if len(paragraph) <= max_chars:
                current = paragraph
            else:
                start = 0
                while start < len(paragraph):
                    end = start + max_chars
                    part = paragraph[start:end].strip()
                    if part:
                        chunks.append(part)
                    start = max(0, end - overlap)
                current = ""

    if current:
        chunks.append(current)

    if overlap > 0 and len(chunks) > 1:
        overlapped = []
        prev_tail = ""
        for chunk in chunks:
            combined = f"{prev_tail}\n\n{chunk}".strip() if prev_tail else chunk
            overlapped.append(combined)
            prev_tail = chunk[-overlap:]
        return overlapped

    return chunks


def init_db(db_path: str):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS books")
    c.execute("DROP TABLE IF EXISTS chunks")
    c.execute("DROP TABLE IF EXISTS chunks_fts")

    c.execute("""
        CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            category TEXT DEFAULT '',
            sha256 TEXT DEFAULT '',
            pages_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            book_title TEXT NOT NULL,
            category TEXT DEFAULT '',
            page_number INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            FOREIGN KEY(book_id) REFERENCES books(id)
        )
    """)

    c.execute("""
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            text,
            book_title UNINDEXED,
            category UNINDEXED,
            page_number UNINDEXED,
            chunk_id UNINDEXED,
            tokenize='unicode61'
        )
    """)

    conn.commit()
    conn.close()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ingest_pdf(conn: sqlite3.Connection, pdf_path: Path):
    title = pdf_path.stem
    category = infer_category(pdf_path.name)
    sha = file_sha256(pdf_path)

    print(f"\n📘 Reading: {pdf_path.name}")
    print(f"   Category: {category}")

    reader = PdfReader(str(pdf_path))
    pages_count = len(reader.pages)

    c = conn.cursor()
    c.execute(
        "INSERT INTO books(title, filename, category, sha256, pages_count) VALUES (?, ?, ?, ?, ?)",
        (title, pdf_path.name, category, sha, pages_count)
    )
    book_id = c.lastrowid

    total_chunks = 0

    for page_idx, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception as e:
            print(f"   ⚠️ Page {page_idx}: extraction error: {e}")
            continue

        page_text = clean_text(page_text)
        if not page_text:
            continue

        chunks = chunk_text(page_text)

        for chunk_index, chunk in enumerate(chunks):
            c.execute(
                """
                INSERT INTO chunks(book_id, book_title, category, page_number, chunk_index, text)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (book_id, title, category, page_idx, chunk_index, chunk)
            )
            chunk_id = c.lastrowid

            c.execute(
                """
                INSERT INTO chunks_fts(text, book_title, category, page_number, chunk_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (chunk, title, category, page_idx, chunk_id)
            )

            total_chunks += 1

        if page_idx % 25 == 0:
            conn.commit()
            print(f"   processed {page_idx}/{pages_count} pages...")

    conn.commit()
    print(f"   ✅ Done: {pages_count} pages, {total_chunks} chunks")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", default=DEFAULT_PDF_DIR)
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    db_path = args.db

    if not pdf_dir.exists():
        print(f"❌ PDF folder not found: {pdf_dir}")
        print("Create a folder named pdfs and put your PDF books inside it.")
        return

    pdf_files = sorted(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print(f"❌ No PDF files found in: {pdf_dir}")
        return

    print("🚀 Building Islamic library database...")
    print(f"PDF folder: {pdf_dir}")
    print(f"Database: {db_path}")
    print(f"PDF files: {len(pdf_files)}")

    init_db(db_path)
    conn = sqlite3.connect(db_path)

    for pdf_path in pdf_files:
        try:
            ingest_pdf(conn, pdf_path)
        except Exception as e:
            print(f"❌ Failed to ingest {pdf_path.name}: {e}")

    conn.close()

    print("\n✅ Finished building database.")
    print(f"Output: {db_path}")
    print('Next test: python library_search.py "غزوة بدر"')


if __name__ == "__main__":
    main()
