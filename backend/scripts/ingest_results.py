"""
ingest_results.py – Parses the provisional result PDF table row by row.
Each student becomes a separate structured document in Supabase.
This is the production-grade way to handle tabular PDF data in a RAG system.
Run: python -m scripts.ingest_results
"""
import os
import sys
import re
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_community.document_loaders import PyPDFLoader
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.db.supabase import supabase

print("Initializing Google Embeddings...")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2")

PDF_PATH = "../data/pdfs/provisional-ug-6th-sem-cse-01062026.pdf"
SOURCE_NAME = "provisional-ug-6th-sem-cse-01062026.pdf"

# Subject codes from the header row
SUBJECTS = [
    "CE381", "CE382", "CS306", "CS307", "CS308",
    "CS315", "CS316", "CS317", "CS321", "CS322",
    "CS331", "CS332", "CS382", "EC382", "EC389",
    "EE385", "EI381", "EI382"
]

def clean_text(text):
    """Remove extra spaces and newlines from PDF-extracted text."""
    text = re.sub(r'\n ', ' ', text)
    text = re.sub(r' \n', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()

def parse_student_rows(raw_text):
    flat = raw_text.replace('\n', ' ')
    pattern = re.compile(
        r'\b(\d+)\s+(23\d{5})\s+((?:\d+\s+[A-Z]+\s*)+?)(\d{2,3})\s+(\d+\.\d+)\s+(\d+\.\d+)'
    )
    students = []
    for m in pattern.finditer(flat):
        slno = m.group(1)
        regn = m.group(2)
        grades_raw = m.group(3).strip()
        gp = m.group(4)
        sgpa = m.group(5)
        cgpa = m.group(6)
        
        grade_tokens = grades_raw.split()
        grade_pairs = []
        i = 0
        while i < len(grade_tokens) - 1:
            val = grade_tokens[i]
            letter = grade_tokens[i+1]
            if re.match(r'^\d+$', val) and re.match(r'^[A-Z]+$', letter):
                grade_pairs.append((val, letter))
                i += 2
            else:
                i += 1

        subject_grades = {}
        for idx, (val, letter) in enumerate(grade_pairs):
            if idx < len(SUBJECTS):
                subject_grades[SUBJECTS[idx]] = f"{val} ({letter})"

        students.append({
            "slno": slno,
            "regn_no": regn,
            "gp": gp,
            "sgpa": sgpa,
            "cgpa": cgpa,
            "subject_grades": subject_grades
        })
    return students

def student_to_text(s):
    grades_str = ", ".join(f"{subj}={grade}" for subj, grade in s["subject_grades"].items())
    text = (
        f"Student Registration Number: {s['regn_no']}\n"
        f"Semester: 6th Semester | Department: CSE | Academic Year: 2025-26\n"
        f"SGPA: {s['sgpa']} | CGPA: {s['cgpa']} | Total Grade Points: {s['gp']}\n"
        f"Subject-wise Grades: {grades_str}\n"
        f"Result Source: Provisional UG 6th Sem CSE Result (01-06-2026)"
    )
    return text

def embed_with_retry(embeddings_model, texts, max_retries=5):
    for attempt in range(max_retries):
        try:
            return embeddings_model.embed_documents(texts)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = 15 * (2 ** attempt)
                print(f"  Rate limit hit, waiting {wait}s before retry {attempt+1}/{max_retries}...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Embedding failed after {max_retries} retries.")

def ingest_results():
    print(f"\nLoading PDF: {PDF_PATH}")
    loader = PyPDFLoader(PDF_PATH)
    pages = loader.load()
    full_text = "\n".join(p.page_content for p in pages)
    full_text = clean_text(full_text)
    
    print("Parsing student rows from table...")
    students = parse_student_rows(full_text)
    print(f"Found {len(students)} student records")
    
    if not students:
        print("ERROR: No students parsed. Raw text sample:")
        print(repr(full_text[:500]))
        return
    
    print("\nSample parsed records:")
    for s in students[:3]:
        print(f"  RegNo={s['regn_no']} SGPA={s['sgpa']} CGPA={s['cgpa']}")
    
    print(f"\nClearing old chunks from '{SOURCE_NAME}' in Supabase...")
    supabase.table("documents").delete().like("metadata->>source", f"%{SOURCE_NAME}%").execute()
    
    docs = []
    for s in students:
        text = student_to_text(s)
        docs.append({
            "text": text,
            "metadata": {
                "source": SOURCE_NAME,
                "regn_no": s["regn_no"],
                "sgpa": s["sgpa"],
                "cgpa": s["cgpa"]
            }
        })
    
    print(f"\nEmbedding and uploading {len(docs)} student documents...")
    BATCH_SIZE = 10
    SLEEP_BETWEEN_BATCHES = 7
    total_uploaded = 0
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i:i+BATCH_SIZE]
        texts = [d["text"] for d in batch]
        batch_embs = embed_with_retry(embeddings, texts)
        rows = [
            {
                "content": doc["text"],
                "metadata": doc["metadata"],
                "embedding": emb
            }
            for doc, emb in zip(batch, batch_embs)
        ]
        supabase.table("documents").insert(rows).execute()
        total_uploaded += len(rows)
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(docs) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  Batch {batch_num}/{total_batches}: uploaded {total_uploaded}/{len(docs)} students")
        if i + BATCH_SIZE < len(docs):
            time.sleep(SLEEP_BETWEEN_BATCHES)
    
    print(f"\nDONE! {total_uploaded} student records indexed in Supabase.")

if __name__ == "__main__":
    ingest_results()
