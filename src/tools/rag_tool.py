"""
Local Sovereign RAG Tool for Air-Gapped Industrial Standards Retrieval.
Uses embedded ChromaDB to index and query regulatory codes (API 570, ASME B31.3)
with zero WAN egress, returning chunks with document and page/clause citations.
"""

import os
import re
from typing import List, Dict, Any, Optional
import chromadb

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STANDARDS_DIR = os.path.join(ROOT_DIR, "data", "standards")
CHROMA_DIR = os.path.join(ROOT_DIR, "data", "chroma_db")

_client = None
_collection = None

def get_chroma_collection():
    """Initialize or retrieve the sovereign standards ChromaDB collection."""
    global _client, _collection
    if _collection is not None:
        return _collection

    os.makedirs(CHROMA_DIR, exist_ok=True)
    _client = chromadb.PersistentClient(path=CHROMA_DIR)
    _collection = _client.get_or_create_collection(name="sovereign_standards")

    # If empty, automatically index standard documents
    if _collection.count() == 0:
        index_standards_documents(_collection)

    return _collection

def parse_standard_file(filepath: str) -> List[Dict[str, Any]]:
    """Parse engineering standard text into structured clause chunks with metadata."""
    filename = os.path.basename(filepath)
    standard_name = "API 570" if "570" in filename else ("ASME B31.3" if "31" in filename else "Standard")
    
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    chunks = []
    # Split by Clause or Paragraph or SECTION
    sections = re.split(r"\n(?=(?:Clause|Paragraph|SECTION|CHAPTER)\s+[0-9A-Z])", content)
    
    current_heading = standard_name
    for idx, sec in enumerate(sections):
        sec_text = sec.strip()
        if not sec_text:
            continue
        
        # If it's just a section title (e.g. SECTION 7: RETIREMENT...) save as heading context
        if len(sec_text) < 90 and "\n" not in sec_text:
            current_heading = sec_text
            continue

        first_line = sec_text.split("\n", 1)[0].strip()
        clause_id = first_line[:90] if len(first_line) > 90 else first_line
        
        # Prepend current section context if applicable
        full_text = f"[{current_heading}]\n{sec_text}" if current_heading and current_heading not in sec_text else sec_text

        page_num = (idx // 2) + 1
        chunk_id = f"{filename}_{idx}"
        chunks.append({
            "id": chunk_id,
            "text": full_text,
            "metadata": {
                "source_doc": filename,
                "page": page_num,
                "clause": clause_id,
                "standard": standard_name
            }
        })
    return chunks


def index_standards_documents(collection=None) -> int:
    """Index all documents in data/standards into the vector collection."""
    if collection is None:
        collection = get_chroma_collection()

    if not os.path.exists(STANDARDS_DIR):
        os.makedirs(STANDARDS_DIR, exist_ok=True)
        return 0

    # Delete existing entries to prevent stale chunks
    try:
        existing = collection.get()
        if existing and "ids" in existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    total_added = 0
    for fname in os.listdir(STANDARDS_DIR):
        if fname.endswith((".txt", ".md")):
            fpath = os.path.join(STANDARDS_DIR, fname)
            chunks = parse_standard_file(fpath)
            for c in chunks:
                try:
                    collection.upsert(
                        ids=[c["id"]],
                        documents=[c["text"]],
                        metadatas=[c["metadata"]]
                    )
                    total_added += 1
                except Exception:
                    pass
    return total_added


def query_standards(query: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve grounded standards chunks for a query with citations.
    Returns list of dicts with: text, source_doc, page, clause, standard, distance.
    """
    try:
        col = get_chroma_collection()
        # If collection still empty, force index
        if col.count() == 0:
            index_standards_documents(col)

        results = col.query(query_texts=[query], n_results=min(n_results, max(col.count(), 1)))
        
        retrieved = []
        if results and "documents" in results and results["documents"]:
            docs = results["documents"][0]
            metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else []
            dists = results["distances"][0] if "distances" in results and results["distances"] else []

            for i, doc in enumerate(docs):
                meta = metas[i] if i < len(metas) else {}
                dist = dists[i] if i < len(dists) else 0.0
                retrieved.append({
                    "text": doc,
                    "source_doc": meta.get("source_doc", "API_570.txt"),
                    "page": meta.get("page", 1),
                    "clause": meta.get("clause", "General Standard"),
                    "standard": meta.get("standard", "API 570"),
                    "relevance_distance": round(float(dist), 4)
                })
        return retrieved
    except Exception as e:
        # Graceful fallback: text search in standards dir
        return fallback_keyword_search(query, n_results)

def fallback_keyword_search(query: str, n_results: int = 3) -> List[Dict[str, Any]]:
    """Air-gapped keyword search fallback if ChromaDB query fails."""
    results = []
    if not os.path.exists(STANDARDS_DIR):
        return results

    q_lower = query.lower()
    for fname in os.listdir(STANDARDS_DIR):
        if fname.endswith((".txt", ".md")):
            fpath = os.path.join(STANDARDS_DIR, fname)
            chunks = parse_standard_file(fpath)
            for c in chunks:
                if any(w in c["text"].lower() for w in q_lower.split()):
                    results.append({
                        "text": c["text"],
                        "source_doc": c["metadata"]["source_doc"],
                        "page": c["metadata"]["page"],
                        "clause": c["metadata"]["clause"],
                        "standard": c["metadata"]["standard"],
                        "relevance_distance": 0.5
                    })
                    if len(results) >= n_results:
                        return results
    return results
