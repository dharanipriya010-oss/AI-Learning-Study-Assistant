import os
import json
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from app.config import DOCS_DIR, VECTOR_STORE_FILE, DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP, MAX_SEARCH_RESULTS
from app.core.llm_client import LLMClient

class RAGEngine:
    """
    RAG Engine featuring document parsing, sliding window text chunking,
    TF-IDF cosine vector search index, and cited Q&A generation.
    """
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.documents: List[Dict[str, Any]] = []
        self.chunks: List[Dict[str, Any]] = []
        self.idf_vocab: Dict[str, float] = {}
        self.load_index()

    def add_document(self, filename: str, content: str, file_type: str = "text") -> Dict[str, Any]:
        """
        Incorporate a new document into the RAG index.
        """
        file_path = DOCS_DIR / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        doc_entry = {
            "id": len(self.documents) + 1,
            "filename": filename,
            "file_type": file_type,
            "char_count": len(content),
            "created_at": str(Path(file_path).stat().st_mtime if file_path.exists() else 0)
        }
        self.documents.append(doc_entry)
        
        # Chunk document
        new_chunks = self._chunk_text(filename, content)
        self.chunks.extend(new_chunks)
        
        # Re-build TF-IDF vector index
        self._build_vector_index()
        self.save_index()
        
        return {
            "status": "success",
            "document": doc_entry,
            "chunks_added": len(new_chunks),
            "total_chunks": len(self.chunks)
        }

    def _chunk_text(self, filename: str, text: str) -> List[Dict[str, Any]]:
        """
        Chunk text using sliding window with overlap and paragraph boundaries.
        """
        chunks = []
        paragraphs = text.split("\n\n")
        current_chunk = ""
        chunk_idx = 1
        page_num = 1

        for para in paragraphs:
            para_clean = para.strip()
            if not para_clean:
                continue
                
            if len(current_chunk) + len(para_clean) <= DEFAULT_CHUNK_SIZE:
                current_chunk += ("\n\n" if current_chunk else "") + para_clean
            else:
                if current_chunk:
                    chunks.append({
                        "chunk_id": f"{filename}_c{chunk_idx}",
                        "filename": filename,
                        "chunk_index": chunk_idx,
                        "text": current_chunk,
                        "char_len": len(current_chunk),
                        "page": page_num
                    })
                    chunk_idx += 1
                    # Retain overlap
                    overlap_start = max(0, len(current_chunk) - DEFAULT_CHUNK_OVERLAP)
                    current_chunk = current_chunk[overlap_start:] + "\n\n" + para_clean
                else:
                    current_chunk = para_clean

            # Estimate page count roughly every 2000 chars
            if len(current_chunk) > 2000:
                page_num += 1

        if current_chunk:
            chunks.append({
                "chunk_id": f"{filename}_c{chunk_idx}",
                "filename": filename,
                "chunk_index": chunk_idx,
                "text": current_chunk,
                "char_len": len(current_chunk),
                "page": page_num
            })

        return chunks

    def _tokenize(self, text: str) -> List[str]:
        """Simple lowercase tokenization for TF-IDF vector indexing."""
        return re.findall(r'\b[a-z0-9]{2,}\b', text.lower())

    def _build_vector_index(self):
        """
        Compute TF-IDF vectors for all chunks in standard Python.
        """
        if not self.chunks:
            return

        doc_count = len(self.chunks)
        df_vocab: Dict[str, int] = {}
        
        # Compute Document Frequency (DF)
        for chunk in self.chunks:
            tokens = set(self._tokenize(chunk["text"]))
            chunk["tokens"] = list(tokens)
            for token in tokens:
                df_vocab[token] = df_vocab.get(token, 0) + 1

        # Compute IDF
        self.idf_vocab = {
            token: math.log((doc_count + 1) / (df + 1)) + 1.0 
            for token, df in df_vocab.items()
        }

        # Compute TF-IDF vectors for chunks
        for chunk in self.chunks:
            tokens = self._tokenize(chunk["text"])
            tf_dict: Dict[str, float] = {}
            for t in tokens:
                tf_dict[t] = tf_dict.get(t, 0) + 1.0
            
            # Normalize TF
            total_tokens = max(1, len(tokens))
            vector: Dict[str, float] = {}
            norm_sq = 0.0
            for t, tf in tf_dict.items():
                tfidf = (tf / total_tokens) * self.idf_vocab.get(t, 1.0)
                vector[t] = tfidf
                norm_sq += tfidf * tfidf
            
            chunk["vector"] = vector
            chunk["vector_norm"] = math.sqrt(norm_sq) if norm_sq > 0 else 1.0

    def search(self, query: str, top_k: int = MAX_SEARCH_RESULTS) -> List[Dict[str, Any]]:
        """
        Vector similarity search returning top-K chunks with similarity scores.
        """
        if not self.chunks:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # Compute Query Vector
        tf_dict: Dict[str, float] = {}
        for t in query_tokens:
            tf_dict[t] = tf_dict.get(t, 0) + 1.0

        total_tokens = len(query_tokens)
        q_vector: Dict[str, float] = {}
        q_norm_sq = 0.0
        for t, tf in tf_dict.items():
            idf = self.idf_vocab.get(t, 1.0)
            tfidf = (tf / total_tokens) * idf
            q_vector[t] = tfidf
            q_norm_sq += tfidf * tfidf

        q_norm = math.sqrt(q_norm_sq) if q_norm_sq > 0 else 1.0

        scored_chunks = []
        for chunk in self.chunks:
            c_vec = chunk.get("vector", {})
            c_norm = chunk.get("vector_norm", 1.0)
            
            # Cosine similarity dot product
            dot_product = 0.0
            for t, q_val in q_vector.items():
                if t in c_vec:
                    dot_product += q_val * c_vec[t]

            sim = dot_product / (q_norm * c_norm) if (q_norm * c_norm) > 0 else 0.0
            
            # Substring boost if exact match
            if query.lower() in chunk["text"].lower():
                sim += 0.3

            if sim > 0.01:
                scored_chunks.append({
                    "score": round(sim, 4),
                    "chunk_id": chunk["chunk_id"],
                    "filename": chunk["filename"],
                    "page": chunk.get("page", 1),
                    "text": chunk["text"]
                })

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:top_k]

    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Answer user question using retrieved chunks with precise source citations.
        """
        retrieved_chunks = self.search(question, top_k=MAX_SEARCH_RESULTS)
        
        if not retrieved_chunks:
            context_str = "No specific course materials found for this query."
            citations = []
        else:
            context_blocks = []
            citations = []
            for i, c in enumerate(retrieved_chunks, 1):
                context_blocks.append(f"[Source {i}: {c['filename']} (Page {c['page']})]\n{c['text']}")
                citations.append({
                    "id": i,
                    "filename": c["filename"],
                    "page": c["page"],
                    "snippet": c["text"][:150] + "...",
                    "score": c["score"]
                })
            context_str = "\n\n---\n\n".join(context_blocks)

        system_prompt = (
            "You are an expert AI Learning & Study Assistant. Answer the student's question accurately using ONLY "
            "the provided course material context. Always cite sources in bracket format like [Source 1], [Source 2]. "
            "If the answer is partially outside the materials, explicitly note what comes from course materials and what is supplementary."
        )

        user_prompt = f"Question: {question}\n\nRetrieved Course Material Context:\n{context_str}"
        
        answer = self.llm_client.generate_text(user_prompt, system_instruction=system_prompt)
        
        return {
            "question": question,
            "answer": answer,
            "citations": citations,
            "retrieved_count": len(retrieved_chunks)
        }

    def save_index(self):
        """Save vector store and documents to disk."""
        data = {
            "documents": self.documents,
            "chunks": [
                {
                    "chunk_id": c["chunk_id"],
                    "filename": c["filename"],
                    "chunk_index": c["chunk_index"],
                    "text": c["text"],
                    "page": c.get("page", 1)
                } for c in self.chunks
            ]
        }
        with open(VECTOR_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_index(self):
        """Load vector store from disk if present."""
        if VECTOR_STORE_FILE.exists():
            try:
                with open(VECTOR_STORE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
                    raw_chunks = data.get("chunks", [])
                    self.chunks = raw_chunks
                    self._build_vector_index()
            except Exception as e:
                print(f"[RAGEngine Warning] Failed to load existing vector store: {e}")
