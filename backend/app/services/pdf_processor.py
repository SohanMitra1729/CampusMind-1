"""
app/services/pdf_processor.py
──────────────────────────────
Smart PDF ingestion pipeline optimized for campus documents (result sheets,
notices, hostel allotments, timetables, and fee structures).

Flow:
  PDF Upload
    ↓
  detect_content_type()
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
from pathlib import Path
from typing import List, Dict, Any, Optional

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


# ── 1. Content-type detection ─────────────────────────────────────────────────

import gc

def detect_content_type(pdf_path: str) -> str:
    """Check if PDF contains tabular pages (e.g. result sheets, fee tables, allotments)."""
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            if total == 0:
                return "text"
            # Sample up to first 10 pages only to save RAM and time
            sample_count = min(10, total)
            tabular_pages = 0
            for i in range(sample_count):
                page = pdf.pages[i]
                try:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            if any(
                                len([c for c in row if c and str(c).strip()]) >= MIN_ROW_CELLS
                                for row in table
                            ):
                                tabular_pages += 1
                                break
                finally:
                    page.flush_cache()
            ratio = tabular_pages / sample_count
            content_type = "tabular" if ratio >= TABULAR_PAGE_THRESHOLD else "text"
            print(
                f"[PDF Processor] {Path(pdf_path).name}: "
                f"{tabular_pages}/{sample_count} sample tabular pages -> '{content_type}'"
            )
            return content_type

    except ImportError:
        print("[PDF Processor] pdfplumber not installed, falling back to text mode.")
        return "text"
    except Exception as e:
        print(f"[PDF Processor] Content detection error: {e} -- falling back to text.")
        return "text"


# ── 2. Text-mode processing ────────────────────────────────────────────────────

def process_text_pdf(
    pdf_path: str,
    source_name: str,
    content_type_label: str = "text",
) -> List[Dict[str, Any]]:
    """Standard text extraction using PyPDFLoader and character splitting."""
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
    print(f"[PDF Processor] Text mode: {len(valid)} pages -> {len(chunks)} chunks")
    return chunks


# ── 3. Tabular-mode processing ─────────────────────────────────────────────────

def _flatten_headers(raw_headers: List[List[Optional[str]]]) -> List[str]:
    """Merge multi-row header cells into single column labels."""
    if not raw_headers:
        return []

    cols = len(raw_headers[0])
    flat = []
    for c in range(cols):
        parts = []
        for r in range(len(raw_headers)):
            if c < len(raw_headers[r]):
                val = raw_headers[r][c]
                if val and str(val).strip():
                    parts.append(str(val).strip().replace("\n", " "))
        flat.append(" ".join(parts) if parts else f"Col_{c+1}")
    return flat


def _row_to_sentence(
    row: List[Optional[str]],
    headers: List[str],
    doc_title: str,
) -> Optional[str]:
    """Convert a single table row into a self-contained natural-language sentence."""
    pairs = []
    for idx, cell in enumerate(row):
        val = str(cell).strip().replace("\n", " ") if cell is not None else ""
        if not val:
            continue
        col_name = headers[idx] if idx < len(headers) else f"Col_{idx+1}"
        pairs.append(f"{col_name}: {val}")

    if not pairs:
        return None

    row_str = " | ".join(pairs)
    return f"[{doc_title}] Record -> {row_str}"


def process_tabular_pdf(pdf_path: str, source_name: str) -> List[Dict[str, Any]]:
    """Extract structured tables page-by-page using pdfplumber with memory flushing."""
    import pdfplumber

    doc_title = Path(pdf_path).stem.replace("_", " ").replace("-", " ")
    all_chunks: List[Dict[str, Any]] = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for page_num in range(1, total_pages + 1):
                page = pdf.pages[page_num - 1]
                try:
                    tables = page.extract_tables()
                    if not tables:
                        continue

                    for table in tables:
                        if not table or len(table) < 2:
                            continue

                        header_rows: List[List[Optional[str]]] = []
                        data_start = 0

                        for i, row in enumerate(table):
                            non_empty = [c for c in row if c and str(c).strip()]
                            if len(non_empty) >= MIN_ROW_CELLS:
                                header_rows.append(row)
                                data_start = i + 1
                                if i > 0 and not any(
                                    str(c).isdigit() for c in non_empty if c
                                ):
                                    pass
                                else:
                                    break

                        headers = _flatten_headers(header_rows)

                        for row_idx, row in enumerate(
                            table[data_start:], start=data_start + 1
                        ):
                            if not any(c and str(c).strip() for c in row):
                                continue

                            sentence = _row_to_sentence(row, headers, doc_title)
                            if not sentence:
                                continue

                            meta: Dict[str, Any] = {
                                "source": source_name,
                                "content_type": "tabular",
                                "page": page_num,
                                "row": row_idx,
                            }

                            regn = re.search(r"\b(\d{7})\b", sentence)
                            if regn:
                                meta["regn_no"] = regn.group(1)

                            all_chunks.append(
                                {"content": sentence, "metadata": meta}
                            )
                finally:
                    # Explicitly release page layout memory
                    page.flush_cache()
                    if page_num % 10 == 0:
                        gc.collect()

    except Exception as e:
        print(f"[PDF Processor] pdfplumber error: {e} -- falling back to text mode.")
        return process_text_pdf(pdf_path, source_name, "text")

    print(f"[PDF Processor] Tabular mode: {len(all_chunks)} row-sentences from tables")

    if len(all_chunks) < 3:
        try:
            text_chunks = process_text_pdf(pdf_path, source_name, "tabular")
            if text_chunks:
                all_chunks.extend(text_chunks)
                print(f"[PDF Processor] + {len(text_chunks)} text chunks from non-table pages")
        except Exception as e:
            print(f"[PDF Processor] Text fallback error: {e}")

    gc.collect()
    return all_chunks


# ── 4. LLM metadata generation ────────────────────────────────────────────────

def generate_pdf_metadata(
    filename: str,
    first_text: str,
    content_type: str,
) -> Dict[str, str]:
    """Uses Groq LLaMA model to classify document metadata automatically."""
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
        from app.core.key_pool import groq_pool
        resp = groq_pool.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=settings.GROQ_MODEL,
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
        print(f"[PDF Processor] Metadata generation failed ({e}) -- using filename fallback.")
        clean = Path(filename).stem.replace("_", " ").replace("-", " ").strip()
        return {
            "title":       clean,
            "category":    "general",
            "department":  "All Departments",
            "description": f"Document: {clean}",
            "audience":    "All Students",
        }


# ── 5. Main entry point ────────────────────────────────────────────────────────

def process_pdf(pdf_path: str, source_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Entry point for parsing any campus PDF (tabular or text)."""
    if source_name is None:
        source_name = Path(pdf_path).name

    content_type = detect_content_type(pdf_path)

    if content_type == "tabular":
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
