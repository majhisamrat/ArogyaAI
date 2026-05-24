import faiss
import pickle
import numpy as np

from sentence_transformers import SentenceTransformer


VECTOR_DB_PATH = "rag/vector_store/faiss_index.bin"
CHUNKS_PATH = "rag/vector_store/chunks.pkl"

embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

# Load vector DB
index = faiss.read_index(VECTOR_DB_PATH)

# Load chunks
with open(CHUNKS_PATH, "rb") as f:
    chunks = pickle.load(f)


def retrieve_medical_context(query: str, top_k=3):

    query_embedding = embedding_model.encode([query])

    query_embedding = np.array(query_embedding).astype("float32")

    distances, indices = index.search(query_embedding, top_k)

    retrieved = []

    for idx in indices[0]:

        if idx < len(chunks):
            retrieved.append(chunks[idx])

    return retrieved