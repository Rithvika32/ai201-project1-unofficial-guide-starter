"""
embed.py — Chunk, embed, and store documents in ChromaDB.

Loads all .txt files from documents/, splits them using chunk_text(),
embeds with all-MiniLM-L6-v2, and stores in a local ChromaDB collection.
Also provides query() for semantic retrieval used by app.py.

Run once to build the vector store:
    python embed.py
"""

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from ingest import chunk_text

DOCUMENTS_DIR = Path("documents")
CHROMA_DIR = ".chroma"
COLLECTION_NAME = "unl_cs_guide"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K = 4


# ── Setup ─────────────────────────────────────────────────────────────────────

def get_collection(reset: bool = False):
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    if reset:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
    return client.get_or_create_collection(COLLECTION_NAME)


# ── Embed and store ───────────────────────────────────────────────────────────

def build_index():
    txt_files = sorted(DOCUMENTS_DIR.glob("*.txt"))
    if not txt_files:
        raise FileNotFoundError("No .txt files found in documents/. Run ingest.py first.")

    print(f"Loading embedding model: {EMBEDDING_MODEL}")
    model = _get_model()
    collection = get_collection(reset=True)

    all_chunks = []
    all_ids = []
    all_metadatas = []

    for doc_path in txt_files:
        text = doc_path.read_text(encoding="utf-8")
        chunks = chunk_text(text)
        print(f"  {doc_path.name}: {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_ids.append(f"{doc_path.stem}__{i}")
            all_metadatas.append({"source": doc_path.name, "chunk_index": i})

    print(f"\nEmbedding {len(all_chunks)} total chunks...")
    embeddings = model.encode(all_chunks, show_progress_bar=True, convert_to_list=True)

    # ChromaDB has a max batch size — insert in batches of 500
    batch_size = 500
    for start in range(0, len(all_chunks), batch_size):
        end = start + batch_size
        collection.add(
            ids=all_ids[start:end],
            documents=all_chunks[start:end],
            embeddings=embeddings[start:end],
            metadatas=all_metadatas[start:end],
        )

    print(f"Stored {collection.count()} chunks in ChromaDB ({CHROMA_DIR}/)")
    return collection


# ── Query ─────────────────────────────────────────────────────────────────────

_model_cache = None

def _get_model():
    global _model_cache
    if _model_cache is None:
        _model_cache = SentenceTransformer(EMBEDDING_MODEL)
    return _model_cache


def query(question: str, k: int = TOP_K) -> list[dict]:
    """
    Return the top-k most relevant chunks for a question.
    Each result is a dict with keys: text, source, distance.
    """
    model = _get_model()
    collection = get_collection()

    embedding = model.encode(question, convert_to_list=True)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text": doc,
            "source": meta["source"],
            "distance": round(dist, 4),
        })
    return chunks


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    collection = build_index()

    # Smoke-test with 3 evaluation queries
    test_queries = [
        "What do students say about the difficulty of CSCE 235?",
        "What are the core degree requirements for CS at UNL?",
        "How do students describe CSCE 322?",
    ]

    print("\n--- Retrieval smoke test ---\n")
    for q in test_queries:
        print(f"Q: {q}")
        results = query(q)
        for r in results:
            print(f"  [{r['distance']:.3f}] ({r['source']}) {r['text'][:120].strip()}...")
        print()
