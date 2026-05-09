# library_search.py
# Hybrid Arabic search for islamic_library.db.
#
# Run:
#   python library_search.py --stats
#   python library_search.py "بدر"
#   python library_search.py "غزوة بدر"
#
# In bot.py later:
#   from library_search import search_library, format_search_results

import argparse
import re
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = "islamic_library.db"

ARABIC_DIACRITICS_RE = re.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]"
)


def normalize_arabic(text: str) -> str:
    text = text or ""

    text = ARABIC_DIACRITICS_RE.sub("", text)

    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ى": "ي",
        "ئ": "ي",
        "ؤ": "و",
        "ة": "ه",
        "ـ": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^\w\u0600-\u06FF\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def query_terms(query: str) -> list[str]:
    normalized = normalize_arabic(query)

    terms = [w for w in normalized.split() if len(w) >= 2]

    stopwords = {
        "في", "من", "عن", "على", "الى", "ما", "هو", "هي",
        "هل", "كان", "كانت", "هذا", "هذه", "ذلك", "تلك",
        "مع", "كما", "ثم", "او", "و"
    }

    return [t for t in terms if t not in stopwords][:8]


def make_fts_query(query: str) -> str:
    terms = query_terms(query)

    if not terms:
        return ""

    return " OR ".join(terms)


def fts_search(query: str, db_path: str, limit: int) -> list[dict]:
    fts_query = make_fts_query(query)

    if not fts_query:
        return []

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        c.execute(
            """
            SELECT
                c.id AS chunk_id,
                c.book_title,
                c.category,
                c.page_number,
                c.text,
                bm25(chunks_fts) AS score
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.chunk_id
            WHERE chunks_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (fts_query, limit)
        )
        rows = c.fetchall()
    except Exception:
        rows = []

    conn.close()

    return [
        {
            "chunk_id": row["chunk_id"],
            "book_title": row["book_title"],
            "category": row["category"],
            "page_number": row["page_number"],
            "text": row["text"],
            "score": float(row["score"]),
            "method": "fts",
        }
        for row in rows
    ]


def fallback_python_search(query: str, db_path: str, limit: int) -> list[dict]:
    terms = query_terms(query)

    if not terms:
        return []

    normalized_query = normalize_arabic(query)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        """
        SELECT id AS chunk_id, book_title, category, page_number, text
        FROM chunks
        """
    )

    rows = c.fetchall()
    conn.close()

    scored = []

    for row in rows:
        original_text = row["text"] or ""
        normalized_text = normalize_arabic(original_text)

        score = 0

        for term in terms:
            count = normalized_text.count(term)
            if count:
                score += count * 10

        if normalized_query and normalized_query in normalized_text:
            score += 50

        if score > 0:
            scored.append({
                "chunk_id": row["chunk_id"],
                "book_title": row["book_title"],
                "category": row["category"],
                "page_number": row["page_number"],
                "text": original_text,
                "score": score,
                "method": "fallback",
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


def search_library(query: str, db_path: str = DEFAULT_DB_PATH, limit: int = 5) -> list[dict]:
    if not Path(db_path).exists():
        return []

    results = fts_search(query, db_path, limit)

    if not results:
        results = fallback_python_search(query, db_path, limit)

    return results


def format_search_results(query: str, results: list[dict]) -> str:
    if not results:
        return (
            "🔎 <b>نتيجة البحث</b>\n\n"
            "لم أجد نتيجة واضحة في المكتبة.\n\n"
            "جرّب كلمات أبسط مثل:\n"
            "• بدر\n"
            "• محمد\n"
            "• مكة\n"
            "• أحد\n\n"
            "⚠️ هذه الأداة تعليمية وليست للإفتاء."
        )

    text = f"""🔎 <b>نتائج البحث في المكتبة الإسلامية</b>

<b>سؤالك:</b>
{query}

⚠️ <b>تنبيه:</b>
هذه النتائج تعليمية من مصادر مختارة، وليست فتوى.

━━━━━━━━━━━━━━
"""

    for i, item in enumerate(results, start=1):
        snippet = item["text"].strip()

        if len(snippet) > 900:
            snippet = snippet[:900].rsplit(" ", 1)[0] + "..."

        text += f"""
<b>{i}. {item['book_title']}</b>
📚 القسم: {item['category']}
📄 الصفحة: {item['page_number']}

{snippet}

━━━━━━━━━━━━━━
"""

    return text.strip()


def print_db_stats(db_path: str):
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM books")
    books = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM chunks")
    chunks = c.fetchone()[0]

    print(f"Books: {books}")
    print(f"Chunks: {chunks}")

    c.execute("SELECT title, pages_count FROM books")
    for title, pages in c.fetchall():
        print(f"- {title}: {pages} pages")

    conn.close()


def print_sample_chunks(db_path: str, limit: int = 3):
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute(
        """
        SELECT book_title, page_number, text
        FROM chunks
        LIMIT ?
        """,
        (limit,)
    )

    rows = c.fetchall()
    conn.close()

    for i, row in enumerate(rows, start=1):
        print("=" * 80)
        print(f"{i}. {row['book_title']} | page {row['page_number']}")
        print("-" * 80)
        print((row["text"] or "")[:1000])
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?")
    parser.add_argument("--db", default=DEFAULT_DB_PATH)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()

    if args.stats:
        print_db_stats(args.db)
        return

    if args.sample:
        print_sample_chunks(args.db)
        return

    if not args.query:
        print('Usage: python library_search.py "غزوة بدر"')
        print("Or:    python library_search.py --stats")
        print("Or:    python library_search.py --sample")
        return

    results = search_library(args.query, args.db, args.limit)

    print(f"\nFound {len(results)} results.\n")

    for i, item in enumerate(results, start=1):
        print("=" * 80)
        print(
            f"{i}. {item['book_title']} | {item['category']} | "
            f"page {item['page_number']} | method={item.get('method')}"
        )
        print("-" * 80)
        print(item["text"][:1200])
        print()


if __name__ == "__main__":
    main()
