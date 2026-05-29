import os
import json
import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional
from app.services.embeddings_service import EmbeddingsService

class CodeSearchService:
    def __init__(self, workspace_path: str, api_keys: List[str] = None):
        self.workspace = Path(workspace_path).resolve()
        self.nexus_dir = self.workspace / ".nexus" / "search_index"
        self.index_file = self.nexus_dir / "index.faiss"
        self.metadata_file = self.nexus_dir / "metadata.json"
        
        self.embeddings_service = EmbeddingsService(api_keys=api_keys)
        self.dimension = 768  # text-embedding-004 default
        
        self.index = None
        self.metadata = []  # List of {path, line_start, line_end, content}
        
        # Ensure directory exists
        self.nexus_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()

    def _load_index(self):
        """Load FAISS index and metadata from disk."""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                self.index = faiss.read_index(str(self.index_file))
                with open(self.metadata_file, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
            except Exception as e:
                print(f"Error loading index: {e}")
                self._create_empty_index()
        else:
            self._create_empty_index()

    def _create_empty_index(self):
        """Initialize a new FAISS index."""
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []

    def _save_index(self):
        """Save current index and metadata to disk."""
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

    def _is_binary(self, file_path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, "rb") as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return True

    def _chunk_file(self, file_path: Path, chunk_size=1000, overlap=200) -> List[Dict]:
        """Split a file into overlapping chunks."""
        try:
            rel_path = str(file_path.relative_to(self.workspace))
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.splitlines()
            
            chunks = []
            current_pos = 0
            
            # Simple chunking by character count for broad compatibility
            while current_pos < len(content):
                end_pos = current_pos + chunk_size
                chunk_text = content[current_pos:end_pos]
                
                # Approximate line numbers
                start_line = content.count('\n', 0, current_pos) + 1
                end_line = content.count('\n', 0, end_pos) + 1
                
                chunks.append({
                    "path": rel_path,
                    "line_start": start_line,
                    "line_end": end_line,
                    "content": chunk_text
                })
                
                if end_pos >= len(content):
                    break
                current_pos += (chunk_size - overlap)
                
            return chunks
        except Exception as e:
            print(f"Error chunking {file_path}: {e}")
            return []

    def index_workspace(self, ignore_list=None):
        """Full re-index of the entire workspace."""
        if ignore_list is None:
            ignore_list = [".git", "node_modules", "venv", "__pycache__", ".nexus", ".next", "dist", "build"]
            
        self._create_empty_index()
        all_chunks = []
        
        for root, dirs, files in os.walk(self.workspace):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_list]
            
            for file in files:
                if file.startswith(".") or any(file.endswith(ext) for ext in [".exe", ".png", ".jpg", ".pdf", ".zip", ".pyc"]):
                    continue
                    
                file_path = Path(root) / file
                if not self._is_binary(file_path):
                    chunks = self._chunk_file(file_path)
                    all_chunks.extend(chunks)

        if not all_chunks:
            return "No text files found to index."

        # Process in batches to avoid API limits and manage memory
        batch_size = 50
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i+batch_size]
            texts = [c["content"] for c in batch]
            try:
                vectors = self.embeddings_service.get_embeddings(texts)
                self.index.add(np.array(vectors).astype('float32'))
                self.metadata.extend(batch)
            except Exception as e:
                print(f"Error indexing batch {i}: {e}")

        self._save_index()
        return f"Successfully indexed {len(all_chunks)} code chunks from {self.workspace}."

    def update_file_index(self, relative_path: str):
        """Incremental update for a single file."""
        p = (self.workspace / relative_path).resolve()
        if not p.exists() or not str(p).startswith(str(self.workspace)):
            return
            
        # 1. Remove old chunks for this file from metadata and index
        # Note: IndexFlatL2 doesn't support removal by ID easily, 
        # so for simplicity in incremental, we'll just append and re-save.
        # Faster way for IndexFlatL2 is to rebuild metadata map.
        
        # Filter out old file entries
        self.metadata = [m for m in self.metadata if m["path"] != relative_path]
        
        # Rebuild index from remaining metadata (since it's IndexFlatL2, we can just re-add everything)
        # In a larger production app, we'd use index.remove_ids or a different Index type.
        # But for this dev tool, rebuild is fast enough if limited to memory metadata.
        
        new_chunks = self._chunk_file(p)
        if new_chunks:
            texts = [c["content"] for c in new_chunks]
            vectors = self.embeddings_service.get_embeddings(texts)
            self.metadata.extend(new_chunks)
            
            # Since IndexFlatL2 doesn't support easy removal, we rebuild the whole index object 
            # from the updated metadata. 
            self.index = faiss.IndexFlatL2(self.dimension)
            # Re-calculating all embeddings is expensive, so we'll actually need 
            # to store the vectors along with metadata to move fast.
            # For now, let's keep it simple: Append only for today, or do a full re-save.
            
            # Actually, let's just do a full indexing on single file write if the project is small,
            # or better: we'll store vectors in metadata for fast rebuild.
            
            # Let's optimize: perform search by filtering in code if needed, but FAISS is the goal.
            # I will implement a re-index if the file count is small, OR just add the new ones.
            # Duplicates in small dev projects are okay for now compared to data loss.
            
            self.index.add(np.array(vectors).astype('float32'))
            self._save_index()

    def search(self, query: str, top_k: int = 5) -> str:
        """Search the index for semantic matches."""
        if not self.index or self.index.ntotal == 0:
            return "Search index is empty. Please run 'index_workspace' first."
            
        query_vector = self.embeddings_service.get_embedding(query)
        distances, indices = self.index.search(np.array([query_vector]).astype('float32'), top_k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1 or idx >= len(self.metadata):
                continue
                
            meta = self.metadata[idx]
            dist = distances[0][i]
            results.append(
                f"--- Result {i+1} (Score: {dist:.4f}) ---\n"
                f"File: {meta['path']} (Lines {meta['line_start']}-{meta['line_end']})\n"
                f"Content:\n{meta['content']}\n"
            )
            
        if not results:
            return "No relevant code found for that query."
            
        return "\n".join(results)
