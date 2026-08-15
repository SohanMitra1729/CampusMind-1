"""
ingest.py - Batch ingestion script for all PDFs in ../data/pdfs/

How updates are handled:
  - Before re-inserting a PDF, all existing chunks for that filename are
    deleted from Supabase first (matched by metadata->filename).
  - This means you can replace a PDF in data/pdfs/ and re-run this script
    to get a fresh, up-to-date index with zero duplicates.

Run: python -m scripts.ingest
     python -m scripts.ingest --file "Fees_Notice_2026.pdf"   (single file)
"""
import os
import sys
import glob
import time
import argparse
from pathlib import Path

# Add project root to sys.path so app imports work when run as script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.supabase import supabase
from app.services.pdf_processor import process_pdf
from app.services.rag_service import get_gemini_embedding


def embed_with_retry(texts: list[str], max_retries: int = 5) -> list:
    for attempt in range(max_retries):
        try:
            return [get_gemini_embedding(text) for text in texts]
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 15 * (2 ** attempt)
                print(f"  Rate limit hit -- waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Embedding failed after max retries.")


def delete_existing_chunks(filename: str) -> int:
    """Delete all chunks for this filename from Supabase before re-ingesting."""
    try:
        resp = (
            supabase.table("documents")
            .delete()
            .eq("metadata->>filename", filename)
            .execute()
        )
        deleted = len(resp.data) if resp.data else 0
        if deleted:
            print(f"  Cleared {deleted} old chunk(s) for '{filename}'")
        return deleted
    except Exception as e:
        print(f"  Warning: Could not clear old chunks for '{filename}': {e}")
        return 0


def ingest_file(pdf_path: str) -> int:
    """Process a single PDF file and upload chunks to Supabase. Returns chunk count."""
    filename = Path(pdf_path).name
    print(f"\n{'-' * 55}")
    print(f"Processing: {filename}")

    try:
        # Delete existing chunks for this file (handles updates/re-ingestion)
        delete_existing_chunks(filename)

        # Process PDF into chunks
        chunks = process_pdf(pdf_path, source_name=filename)

        if not chunks:
            print(f"  WARNING: No content extracted from '{filename}'")
            print(f"  (File may be a scanned image PDF — use a digital copy instead)")
            return 0

        content_type = chunks[0]["metadata"].get("content_type", "text")
        print(f"  Content type : {content_type}")
        print(f"  Total chunks : {len(chunks)}")

        # Embed & upload in batches with rate-limit protection
        BATCH_SIZE = 10
        SLEEP_SECS = 7
        uploaded = 0
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i:i + BATCH_SIZE]
            texts = [c["content"] for c in batch]
            batch_embs = embed_with_retry(texts)
            rows = [
                {"content": c["content"], "metadata": c["metadata"], "embedding": emb}
                for c, emb in zip(batch, batch_embs)
            ]
            supabase.table("documents").insert(rows).execute()
            uploaded += len(rows)
            batch_num = i // BATCH_SIZE + 1
            print(f"  Batch {batch_num}/{total_batches}: {uploaded}/{len(chunks)} uploaded")
            if i + BATCH_SIZE < len(chunks):
                time.sleep(SLEEP_SECS)

        print(f"  DONE: {uploaded} chunks indexed for '{filename}'")
        return uploaded

    except Exception as e:
        print(f"  ERROR processing '{filename}': {e}")
        return 0


def ingest_all(pdf_dir: str = "../data/pdfs") -> None:
    """Ingest all PDFs found in the given directory (recursive)."""
    pdf_files = sorted(set(glob.glob(os.path.join(pdf_dir, "**/*.pdf"), recursive=True)))

    if not pdf_files:
        print(f"ERROR: No PDF files found in '{pdf_dir}'")
        return

    print("\n" + "=" * 55)
    print("CAMPUSMIND BATCH INGESTION PIPELINE")
    print("=" * 55)
    print(f"\nFound {len(pdf_files)} PDF file(s):")
    for i, f in enumerate(pdf_files, 1):
        print(f"  {i}. {Path(f).name}")

    total_chunks_all = 0
    for pdf_path in pdf_files:
        total_chunks_all += ingest_file(pdf_path)

    print("\n" + "=" * 55)
    print("INGESTION COMPLETE")
    print(f"  Total chunks indexed: {total_chunks_all}")
    print("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CampusMind PDF Ingestion Script")
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Ingest a single PDF by filename (e.g. --file 'Faculty_List_2026.pdf'). "
             "Must be inside ../data/pdfs/",
    )
    args = parser.parse_args()

    if args.file:
        # Single file update mode
        pdf_path = os.path.join("../data/pdfs", args.file)
        if not os.path.isfile(pdf_path):
            print(f"ERROR: File not found at '{pdf_path}'")
            sys.exit(1)
        ingest_file(pdf_path)
    else:
        # Full batch ingest mode
        ingest_all()
