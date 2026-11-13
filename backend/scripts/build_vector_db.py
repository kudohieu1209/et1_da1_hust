"""Build the approved RAG index and embedding cache without application storage."""
import os
import sys
from pathlib import Path

# Build inputs are public documents only; never load local credentials.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["MONGODB_URI"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.rag_engine import rag_engine


if __name__ == "__main__":
    result = rag_engine.sync_knowledge_base()
    if result.get("status") != "success" or not result.get("total_chunks"):
        raise SystemExit("Vector index build failed or contains no approved documents.")
    print(f"Built vector index: {result['total_chunks']} approved chunks.")
