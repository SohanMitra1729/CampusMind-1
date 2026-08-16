import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

sys.stdout.reconfigure(encoding="utf-8")

from app.db.supabase import supabase

# Print chunks from provisional results PDF in full
res = supabase.table("documents").select("id, content, metadata").execute()

prov_chunks = [
    r
    for r in (res.data or [])
    if "result" in (r.get("metadata") or {}).get("source", "").lower()
    or "result" in (r.get("metadata") or {}).get("category", "").lower()
]
print(f"Total results PDF chunks: {len(prov_chunks)}\n")

for i, row in enumerate(prov_chunks[:5]):
    content = (row.get("content") or "").encode("ascii", errors="replace").decode("ascii")
    print(f"=== Chunk {i+1} (id={row.get('id')}) ===")
    print(content[:600])
    print()
