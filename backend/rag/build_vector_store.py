import os
import fitz
import faiss
import pickle
import numpy as np

from sentence_transformers import SentenceTransformer


PDF_FOLDER = "rag/documents"
VECTOR_DB_PATH = "rag/vector_store/faiss_index.bin"
CHUNKS_PATH = "rag/vector_store/chunks.pkl"

# Embedding model
embedding_model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)


def extract_text_from_pdf(pdf_path):

    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:
        text += page.get_text()

    return text


def chunk_text(text, chunk_size=500):

    chunks = []

    words = text.split()

    for i in range(0, len(words), chunk_size):

        chunk = " ".join(words[i:i + chunk_size])

        chunks.append(chunk)

    return chunks


all_chunks = []

# Read PDFs
for filename in os.listdir(PDF_FOLDER):

    if filename.endswith(".pdf"):

        path = os.path.join(PDF_FOLDER, filename)

        print(f"Processing: {filename}")

        text = extract_text_from_pdf(path)

        chunks = chunk_text(text)

        all_chunks.extend(chunks)


# Create embeddings
embeddings = embedding_model.encode(all_chunks)

embedding_array = np.array(embeddings).astype("float32")

# Build FAISS index
dimension = embedding_array.shape[1]

index = faiss.IndexFlatL2(dimension)

index.add(embedding_array)

# Save index
faiss.write_index(index, VECTOR_DB_PATH)

# Save chunks
with open(CHUNKS_PATH, "wb") as f:
    pickle.dump(all_chunks, f)

print("✅ Vector store created successfully!")