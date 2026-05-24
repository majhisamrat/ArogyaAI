import os
import faiss
import pickle
import numpy as np

from sentence_transformers import (
    SentenceTransformer
)

MODEL = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

INDEX_PATH = "memory/medical_memory_index.faiss"
CHUNKS_PATH = "memory/medical_chunks.pkl"


class VectorMemory:

    def __init__(self):

        os.makedirs("memory", exist_ok=True)

        self.dimension = 384

        try:

            if os.path.exists(INDEX_PATH) and os.path.exists(CHUNKS_PATH):

                self.index = faiss.read_index(
                    INDEX_PATH
                )

                with open(CHUNKS_PATH, "rb") as f:

                    self.chunks = pickle.load(f)

            else:

                raise Exception("Memory files missing")

        except Exception as e:

            print(f"⚠️ Vector memory reset: {e}")

            self.index = faiss.IndexFlatL2(
                self.dimension
            )

            self.chunks = []

            faiss.write_index(
                self.index,
                INDEX_PATH
            )

            with open(CHUNKS_PATH, "wb") as f:

                pickle.dump(
                    self.chunks,
                    f
                )

    # SAVE MEMORY
    def add_memory(
        self,
        text,
        metadata=None
    ):

        embedding = MODEL.encode([text])

        self.index.add(
            np.array(embedding).astype("float32")
        )

        self.chunks.append({

            "text": text,
            "metadata": metadata or {}
        })

        faiss.write_index(
            self.index,
            INDEX_PATH
        )

        with open(CHUNKS_PATH, "wb") as f:

            pickle.dump(
                self.chunks,
                f
            )

    # SEARCH MEMORY
    def search_memory(
        self,
        query,
        k=3
    ):

        if len(self.chunks) == 0:
            return []

        embedding = MODEL.encode([query])

        distances, indices = self.index.search(

            np.array(embedding).astype("float32"),

            k
        )

        results = []

        for idx in indices[0]:

            if idx < len(self.chunks):

                results.append(
                    self.chunks[idx]
                )

        return results