"""Offline reviewed corpus -> Neo4j concept index, never patient histories."""
from config import get_settings
from db import get_supabase
from rag.evidence_policy import admit_chunk
from rag.knowledge_graph import sync_passages


if __name__ == "__main__":
    settings = get_settings()
    db = get_supabase()
    offset, chunks = 0, []
    while True:
        rows = db.table("evidence_chunks").select("*").order("id").range(offset, offset + 499).execute().data or []
        chunks.extend(c for c in rows if admit_chunk(c, settings))
        if len(rows) < 500:
            break
        offset += 500
    print({"passages_indexed": sync_passages(chunks, settings)})
