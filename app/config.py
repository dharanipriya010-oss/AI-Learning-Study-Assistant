import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Storage Directories
DATA_DIR = BASE_DIR / "app" / "data"
DOCS_DIR = DATA_DIR / "documents"
MEMORY_FILE = DATA_DIR / "memory.json"
VECTOR_STORE_FILE = DATA_DIR / "vector_store.json"

# Ensure directories exist
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Default LLM Configuration
DEFAULT_MODEL = "gemini-1.5-flash"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# RAG Configuration
DEFAULT_CHUNK_SIZE = 500  # characters
DEFAULT_CHUNK_OVERLAP = 100
MAX_SEARCH_RESULTS = 5

# SRS Configuration (SuperMemo SM-2 defaults)
DEFAULT_EASE_FACTOR = 2.5
DEFAULT_INTERVAL = 1

# System Settings
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
