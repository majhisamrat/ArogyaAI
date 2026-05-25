import os
import fitz
import faiss
import pickle
import numpy as np

from sentence_transformers import SentenceTransformer


BASE_DIR = "/app"

PDF_FOLDER = os.path.join(BASE_DIR, "rag/documents")
VECTOR_STORE_DIR = os.path.join(BASE_DIR, "rag/vector_store")

VECTOR_DB_PATH = os.path.join(
    VECTOR_STORE_DIR,
    "faiss_index.bin"
)

CHUNKS_PATH = os.path.join(
    VECTOR_STORE_DIR,
    "chunks.pkl"
)

# Create vector_store folder automatically
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

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

# Check documents folder exists
if not os.path.exists(PDF_FOLDER):
    raise Exception(f"PDF folder not found: {PDF_FOLDER}")

# Read PDFs
for filename in os.listdir(PDF_FOLDER):

    if filename.endswith(".pdf"):

        path = os.path.join(PDF_FOLDER, filename)

        print(f"Processing: {filename}")

        text = extract_text_from_pdf(path)

        chunks = chunk_text(text)

        all_chunks.extend(chunks)

# Ensure chunks exist
if len(all_chunks) == 0:
    raise Exception("No PDF chunks found!")

print(f"Total chunks: {len(all_chunks)}")

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
print(f"Saved FAISS index at: {VECTOR_DB_PATH}")