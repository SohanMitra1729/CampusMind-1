"""
ingest.py - Batch ingestion script for all PDFs in ../data/pdfs/

How batch-level resume works:
  - Automatically checks how many chunks are ALREADY in Supabase for each PDF.
  - If 1000 out of 1709 chunks are already stored, it SKIPS the first 1000 chunks
    (0 API calls used) and resumes instantly at batch 101 (chunk 1001)!
  - Retries up to 10 times with max 60s backoff on rate limits.

Run:
  python -m scripts.ingest                     (Resumes automatically)
  python -m scripts.ingest --force             (Clears DB & re-ingests from scratch)
  python -m scripts.ingest --file "Notice.pdf" (Single file resume/ingest)
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


def embed_with_retry(texts: list[str], max_retries: int = 10) -> list:
    """
    Fetch embeddings with robust exponential backoff.
    Waits up to 60s per attempt and retries up to 10 times so rate limit spikes never fail the job.
    """
    for attempt in range(max_retries):
        try:
            return [get_gemini_embedding(text) for text in texts]
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str:
                wait = min(60, 15 * (2 ** attempt))
                print(f"  Rate limit/Quota hit -- waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Embedding failed after {max_retries} retries due to quota limits.")


def delete_existing_chunks(filename: str) -> int:
    """Delete all chunks for this filename from Supabase."""
    try:
        resp = (
            supabase.table("documents")
            .delete()
            .eq("metadata->>filename", filename)
            .execute()
        )
        deleted = len(resp.data) if resp.data else 0
        if deleted:
            print(f"  Cleared {deleted} chunk(s) for '{filename}'")
        return deleted
    except Exception as e:
        print(f"  Warning: Could not clear old chunks for '{filename}': {e}")
        return 0


def get_existing_chunk_count(filename: str) -> int:
    """Check how many chunks are ALREADY saved in Supabase for a file."""
    try:
        resp = (
            supabase.table("documents")
            .select("id", count="exact")
            .eq("metadata->>filename", filename)
            .limit(1)
            .execute()
        )
        return resp.count or 0
    except Exception as e:
        print(f"  Warning checking chunk count: {e}")
        return 0


def ingest_file(pdf_path: str, force_reingest: bool = False) -> int:
    """Process a PDF file and upload remaining chunks to Supabase (resumable)."""
    filename = Path(pdf_path).name
    print(f"\n{'-' * 55}")
    print(f"Processing: {filename}")

    try:
        if force_reingest:
            delete_existing_chunks(filename)

        # Process PDF into chunks locally (fast)
        chunks = process_pdf(pdf_path, source_name=filename)

        if not chunks:
            print(f"  WARNING: No content extracted from '{filename}'")
            print(f"  (File may be a scanned image PDF — use a digital copy instead)")
            return 0

        # Attach filename and chunk_index to metadata
        for idx, c in enumerate(chunks):
            c["metadata"]["filename"] = filename
            c["metadata"]["chunk_index"] = idx

        content_type = chunks[0]["metadata"].get("content_type", "text")
        print(f"  Content type : {content_type}")
        print(f"  Total chunks : {len(chunks)}")

        BATCH_SIZE = 10
        SLEEP_SECS = 7

        # Check how many chunks are already in Supabase
        existing_count = 0 if force_reingest else get_existing_chunk_count(filename)

        if existing_count >= len(chunks):
            print(f"  SKIP: '{filename}' is ALREADY fully indexed ({existing_count}/{len(chunks)} chunks in DB)")
            return existing_count

        # Align start index to batch boundary
        start_index = (existing_count // BATCH_SIZE) * BATCH_SIZE

        if start_index > 0:
            skipped_batches = start_index // BATCH_SIZE
            print(f"  RESUMING: Found {existing_count} chunks already in DB!")
            print(f"  Skipping batches 1..{skipped_batches} ({start_index}/{len(chunks)} chunks skipped, 0 API calls used)")

        uploaded = start_index
        total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(start_index, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
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

        print(f"  DONE: All {uploaded} chunks indexed for '{filename}'")
        return uploaded

    except Exception as e:
        print(f"  ERROR processing '{filename}': {e}")
        return 0


def ingest_all(pdf_dir: str = "../data/pdfs", force_reingest: bool = False) -> None:
    """Ingest all PDFs found in the given directory (resumable by default)."""
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
        total_chunks_all += ingest_file(pdf_path, force_reingest=force_reingest)

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
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force clear DB & re-embed from batch 1 (disables resume mode).",
    )
    args = parser.parse_args()

    if args.file:
        # Single file update mode
        pdf_path = os.path.join("../data/pdfs", args.file)
        if not os.path.isfile(pdf_path):
            print(f"ERROR: File not found at '{pdf_path}'")
            sys.exit(1)
        ingest_file(pdf_path, force_reingest=args.force)
    else:
        # Full batch ingest mode
        ingest_all(force_reingest=args.force)
