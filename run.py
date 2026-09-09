import os
import sys
import webbrowser
import time
from pathlib import Path

# Ensure app directory is on path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app.config import DOCS_DIR, SERVER_HOST, SERVER_PORT
from app.main import run_server, rag_engine

def initialize_sample_data():
    """Pre-load sample study guide if documents folder is empty."""
    sample_file = BASE_DIR / "app" / "data" / "sample_course.md"
    if sample_file.exists() and len(rag_engine.documents) == 0:
        print("[Setup] Ingesting sample course material into RAG index...")
        with open(sample_file, "r", encoding="utf-8") as f:
            content = f.read()
        rag_engine.add_document("CS_AI_Master_Study_Guide.md", content, file_type="markdown")

if __name__ == "__main__":
    print("\n========================================================")
    print(" 🎓 AI Learning & Study Assistant Starting Up...")
    print("========================================================\n")
    
    initialize_sample_data()
    
    url = f"http://{SERVER_HOST}:{SERVER_PORT}"
    print(f"👉 Opening dashboard in browser at: {url}")
    
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        
    run_server(SERVER_HOST, SERVER_PORT)
