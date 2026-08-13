"""
app/services/pdf_processor.py
──────────────────────────────
Smart PDF ingestion pipeline with automatic content-type detection.

Flow:
  PDF Upload
    ↓
  detect_content_type()
    ├── "image"   → PyMuPDF renders pages at 300 DPI
    │               → pytesseract OCR per page
    │               → reconstructed text re-classified:
    │                   ├── tabular patterns? → row-sentence chunks  (ocr_tabular)
    │                   └── plain text        → text-splitter chunks (ocr_text)
    ├── "tabular" → pdfplumber table extraction
    │               → header reconstruction (multi-row aware)
    │               → row → natural-language sentence
    │               → each row sentence = one chunk
    └── "text"    → PyPDFLoader + RecursiveCharacterTextSplitter

Returns a list of dicts: [{"content": str, "metadata": dict}, ...]
"""

import re
import os
import io
import json
import warnings
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings

# ── Constants ─────────────────────────────────────────────────────────────────
TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""],
)

TABULAR_PAGE_THRESHOLD = 0.30
MIN_ROW_CELLS = 2
IMAGE_CHAR_THRESHOLD = 80
IMAGE_PAGE_THRESHOLD = 0.60
OCR_DPI = 300
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ── 0. Tesseract bootstrap ─────────────────────────────────────────────────────

def _configure_tesseract() -> bool:
    try:
        import pytesseract
        if os.path.isfile(TESSERACT_CMD):
            pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


# ── 1. Image-PDF detection ─────────────────────────────────────────────────────

def _page_char_count(page) -> int:
    text = page.get_text("text")
    return len(text.strip())


def is_image_based_pdf(pdf_path: str) -> bool:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        total = len(doc)
        if total == 0:
            doc.close()
            return False

        sample_indices = sorted(set(
            [0] +
            [total // 4, total // 2, 3 * total // 4] +
            [total - 1]
        ))
        sample_indices = [i for i in sample_indices if 0 <= i < total]

        image_pages = 0
        for idx in sample_indices:
            page = doc[idx]
            chars = _page_char_count(page)
            if chars < IMAGE_CHAR_THRESHOLD:
                image_pages += 1
            print(f"[PDF Processor]   [detect] page {idx+1}: {chars} chars extracted")

        doc.close()
        ratio = image_pages / len(sample_indices)
        print(f"[PDF Processor]   [detect] {image_pages}/{len(sample_indices)} image-like pages (ratio={ratio:.2f}, threshold={IMAGE_PAGE_THRESHOLD})")
        return ratio >= IMAGE_PAGE_THRESHOLD

    except ImportError:
        print("[PDF Processor] PyMuPDF not installed — cannot detect image PDFs.")
        return False
    except Exception as e:
        print(f"[PDF Processor] Image detection error: {e}")
        return False


# ── 2. Content-type detection (3-way) ─────────────────────────────────────────

def detect_content_type(pdf_path: str) -> str:
    if is_image_based_pdf(pdf_path):
        print(f"[PDF Processor] {Path(pdf_path).name}: image-based PDF detected → 'image'")
        return "image"

    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            if total == 0:
                return "text"
            tabular_pages = 0
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    for table in tables:
                        if any(
                            len([c for c in row if c and str(c).strip()]) >= MIN_ROW_CELLS
                            for row in table
                        ):
                            tabular_pages += 1
                            break
            ratio = tabular_pages / total
            content_type = "tabular" if ratio >= TABULAR_PAGE_THRESHOLD else "text"
            print(
                f"[PDF Processor] {Path(pdf_path).name}: "
                f"{tabular_pages}/{total} tabular pages → '{content_type}'"
            )
            return content_type

    except ImportError:
        print("[PDF Processor] pdfplumber not installed, falling back to text mode.")
        return "text"
    except Exception as e:
        print(f"[PDF Processor] Content detection error: {e} — falling back to text.")
        return "text"


# ── 3. Text-mode processing ────────────────────────────────────────────────────

def process_text_pdf(
    pdf_path: str,
    source_name: str,
    content_type_label: str = "text",
) -> List[Dict[str, Any]]:
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    valid = [p for p in pages if len(p.page_content.strip()) > 50]
    if not valid:
        return []

    splits = TEXT_SPLITTER.split_documents(valid)
    chunks = []
    for split in splits:
        meta = dict(split.metadata)
        meta["source"] = source_name
        meta["content_type"] = content_type_label
        chunks.append({"content": split.page_content.strip(), "metadata": meta})
    print(f"[PDF Processor] Text mode: {len(valid)} pages → {len(chunks)} chunks")
    return chunks


# ── 4. Tabular-mode processing ─────────────────────────────────────────────────

def _clean_cell(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _reconstruct_headers(table: List[List]) -> Optional[Tuple[List[str], int]]:
    if not table:
        return None

    def _is_data_row(row: List) -> bool:
        for cell in row:
            c = _clean_cell(cell)
            if re.match(r"^\d+(\.\d+)?$", c):
                return True
        return False

    header_rows = []
    data_start = 0
    for i, row in enumerate(table):
        if all(_clean_cell(c) == "" for c in row):
            continue
        if not _is_data_row(row):
            header_rows.append(row)
            data_start = i + 1
        else:
            data_start = i
            break

    if not header_rows:
        n_cols = max(len(r) for r in table)
        return [f"Col{i+1}" for i in range(n_cols)], 0

    n_cols = max(len(r) for r in header_rows)
    headers = []
    for col in range(n_cols):
        parts = []
        for row in header_rows:
            cell = _clean_cell(row[col]) if col < len(row) else ""
            if cell and cell not in parts:
                parts.append(cell)
        headers.append(" ".join(parts) if parts else f"Col{col+1}")

    return headers, data_start


def _table_to_nl_sentences(
    table: List[List],
    source_name: str,
    page_num: int,
    table_idx: int,
    content_type_label: str = "tabular",
) -> List[Dict[str, Any]]:
    result = _reconstruct_headers(table)
    if result is None:
        return []

    headers, data_start = result
    chunks = []

    for row in table[data_start:]:
        cells = [_clean_cell(c) for c in row]
        if not any(cells):
            continue

        pairs = []
        for header, value in zip(headers, cells):
            if value and header:
                pairs.append(f"{header}: {value}")

        if not pairs:
            continue

        sentence = " | ".join(pairs)

        regn_match = None
        for header, value in zip(headers, cells):
            if re.match(r"^\d{7}$", value):
                regn_match = value
                break

        meta: Dict[str, Any] = {
            "source": source_name,
            "content_type": content_type_label,
            "page": page_num,
            "table_index": table_idx,
        }
        if regn_match:
            meta["regn_no"] = regn_match

        chunks.append({"content": sentence, "metadata": meta})

    return chunks


def process_tabular_pdf(
    pdf_path: str,
    source_name: str,
    content_type_label: str = "tabular",
) -> List[Dict[str, Any]]:
    import pdfplumber

    all_chunks: List[Dict[str, Any]] = []
    pages_with_no_tables: List[int] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            if not tables:
                pages_with_no_tables.append(page_num)
                continue

            for t_idx, table in enumerate(tables):
                sentences = _table_to_nl_sentences(
                    table, source_name, page_num, t_idx,
                    content_type_label=content_type_label,
                )
                all_chunks.extend(sentences)

    print(f"[PDF Processor] Tabular mode: {len(all_chunks)} row-sentences from tables")

    if pages_with_no_tables:
        try:
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            text_pages = [p for i, p in enumerate(pages, start=1) if i in pages_with_no_tables]
            valid = [p for p in text_pages if len(p.page_content.strip()) > 50]
            if valid:
                splits = TEXT_SPLITTER.split_documents(valid)
                fallback_label = (
                    "ocr_text_in_tabular_doc"
                    if "ocr" in content_type_label
                    else "text_in_tabular_doc"
                )
                for split in splits:
                    meta = dict(split.metadata)
                    meta["source"] = source_name
                    meta["content_type"] = fallback_label
                    all_chunks.append({"content": split.page_content.strip(), "metadata": meta})
                print(f"[PDF Processor] + {len(splits)} text chunks from non-table pages")
        except Exception as e:
            print(f"[PDF Processor] Text fallback error: {e}")

    return all_chunks


# ── 5. OCR-mode processing ─────────────────────────────────────────────────────

def ocr_page_to_text(page, dpi: int = OCR_DPI) -> str:
    try:
        import fitz
        import pytesseract
        from PIL import Image

        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        text = pytesseract.image_to_string(img, lang="eng")
        return text

    except Exception as e:
        print(f"[PDF Processor] OCR error on page: {e}")
        return ""


def _ocr_text_looks_tabular(ocr_text: str) -> bool:
    lines = [l.strip() for l in ocr_text.splitlines() if l.strip()]
    if len(lines) < 3:
        return False

    multi_col = sum(
        1 for l in lines
        if re.search(r"\s{2,}", l) and len(l.split()) >= 2
    )

    digit_rows = sum(
        1 for l in lines
        if len(re.findall(r"\b\d+\b", l)) >= 2
    )

    ratio = multi_col / len(lines)
    print(f"[PDF Processor]   [tabular?] multi_col={multi_col}/{len(lines)} ({ratio:.2f}), digit_rows={digit_rows}")
    return ratio >= 0.35 or digit_rows >= max(3, len(lines) // 5)


def _split_ocr_tabular_rows(
    page_texts: List[Tuple[int, str]],
    source_name: str,
) -> List[Dict[str, Any]]:
    all_chunks: List[Dict[str, Any]] = []

    for page_num, text in page_texts:
        lines = [l.strip() for l in text.splitlines()]
        lines = [l for l in lines if re.search(r"[A-Za-z0-9]", l)]

        rows: List[str] = []
        current: List[str] = []

        for line in lines:
            if re.match(r"^\d", line):
                if current:
                    rows.append(" | ".join(current))
                current = [line]
            else:
                current.append(line)

        if current:
            rows.append(" | ".join(current))

        for row_text in rows:
            row_text = row_text.strip()
            if len(row_text) < 10:
                continue

            meta: Dict[str, Any] = {
                "source": source_name,
                "content_type": "ocr_tabular",
                "page": page_num,
                "ocr": True,
            }

            regn = re.search(r"\b(\d{7})\b", row_text)
            if regn:
                meta["regn_no"] = regn.group(1)

            all_chunks.append({"content": row_text, "metadata": meta})

    return all_chunks


def process_image_pdf(pdf_path: str, source_name: str) -> List[Dict[str, Any]]:
    import fitz

    if not _configure_tesseract():
        print(
            "[PDF Processor] ⚠ Tesseract not found — OCR skipped. "
            "Install from https://github.com/UB-Mannheim/tesseract/wiki"
        )
        return []

    print(f"[PDF Processor] Image-PDF mode: running OCR on '{Path(pdf_path).name}' …")

    doc = fitz.open(pdf_path)
    page_texts: List[Tuple[int, str]] = []

    for page_num, page in enumerate(doc, start=1):
        text = ocr_page_to_text(page, dpi=OCR_DPI)
        if text.strip():
            page_texts.append((page_num, text))
        print(f"[PDF Processor]   Page {page_num}/{len(doc)}: {len(text.strip())} chars from OCR")

    doc.close()

    if not page_texts:
        print("[PDF Processor] OCR produced no text — check Tesseract language data.")
        return []

    full_text = "\n\n".join(t for _, t in page_texts)
    is_tabular = _ocr_text_looks_tabular(full_text)
    label = "ocr_tabular" if is_tabular else "ocr_text"
    print(f"[PDF Processor] OCR content classified as: '{label}'")

    if is_tabular:
        all_chunks = _split_ocr_tabular_rows(page_texts, source_name)
        print(
            f"[PDF Processor] Image-PDF mode: {len(page_texts)} pages OCR'd "
            f"→ {len(all_chunks)} row-chunks (ocr_tabular)"
        )
    else:
        all_chunks: List[Dict[str, Any]] = []
        for page_num, text in page_texts:
            if not text.strip():
                continue
            splits = TEXT_SPLITTER.split_text(text)
            for chunk_text in splits:
                chunk_text = chunk_text.strip()
                if len(chunk_text) < 30:
                    continue
                all_chunks.append({
                    "content": chunk_text,
                    "metadata": {
                        "source": source_name,
                        "content_type": "ocr_text",
                        "page": page_num,
                        "ocr": True,
                    },
                })
        print(
            f"[PDF Processor] Image-PDF mode: {len(page_texts)} pages OCR'd "
            f"→ {len(all_chunks)} chunks (ocr_text)"
        )

    return all_chunks


# ── 6. LLM metadata generation ────────────────────────────────────────────────

def generate_pdf_metadata(
    filename: str,
    first_text: str,
    content_type: str,
) -> Dict[str, str]:
    excerpt = first_text[:500].strip()
    prompt = f"""You are a metadata generator for a university document management system.

Filename  : {filename}
Content   : {content_type}
Excerpt   :
\"\"\"
{excerpt}
\"\"\"

Generate concise, accurate metadata for this document.
Respond with a single JSON object only — no markdown, no explanation:
{{
  "title":       "<short human-readable document title, max 60 chars>",
  "category":    "<one of: notice | results | allotment | syllabus | timetable | handbook | fee | scholarship | event | general>",
  "department":  "<department or branch if identifiable, else 'All Departments'>",
  "description": "<one sentence describing the document, max 100 chars>",
  "audience":    "<who this document is for, max 40 chars, e.g. '3rd year CSE students'>"
}}

Rules:
- title must be human-readable, NOT the raw filename
- category must be exactly one of the listed values
- If department/audience is unclear from the excerpt, use 'All Students'
- Keep every field concise — this is stored as searchable metadata"""

    try:
        from groq import Groq
        groq_client = Groq(api_key=settings.GROQ_API_KEY or "placeholder_key")
        resp = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.0,
            max_tokens=150,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
        result = json.loads(raw)
        print(
            f"[PDF Processor] LLM metadata: title='{result.get('title')}' "
            f"category='{result.get('category')}' dept='{result.get('department')}'"
        )
        return result
    except Exception as e:
        print(f"[PDF Processor] Metadata generation failed ({e}) — using filename fallback.")
        clean = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
        return {
            "title":       clean,
            "category":    "general",
            "department":  "All Departments",
            "description": f"Document: {clean}",
            "audience":    "All Students",
        }


# ── 7. Main entry point ────────────────────────────────────────────────────────

def process_pdf(pdf_path: str, source_name: Optional[str] = None) -> List[Dict[str, Any]]:
    if source_name is None:
        source_name = Path(pdf_path).name

    content_type = detect_content_type(pdf_path)

    if content_type == "image":
        chunks = process_image_pdf(pdf_path, source_name)
    elif content_type == "tabular":
        chunks = process_tabular_pdf(pdf_path, source_name)
    else:
        chunks = process_text_pdf(pdf_path, source_name)

    if not chunks:
        return chunks

    first_text = chunks[0]["content"]
    actual_content_type = chunks[0]["metadata"].get("content_type", content_type)
    llm_meta = generate_pdf_metadata(source_name, first_text, actual_content_type)

    for chunk in chunks:
        chunk["metadata"].update({
            "source":      llm_meta.get("title", source_name),
            "filename":    source_name,
            "title":       llm_meta.get("title", source_name),
            "category":    llm_meta.get("category", "general"),
            "department":  llm_meta.get("department", "All Departments"),
            "description": llm_meta.get("description", ""),
            "audience":    llm_meta.get("audience", "All Students"),
        })

    print(
        f"[PDF Processor] Metadata enrichment complete: "
        f"{len(chunks)} chunks tagged with title='{llm_meta.get('title')}'"
    )
    return chunks
