import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env explicitly for the test script
load_dotenv(Path(__file__).parent / "backend" / ".env")

# Force set Gemini key if it exists in env
if os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

# Add backend to path
sys.path.append(str(Path(__file__).parent / "backend"))

from app.services.code_search import CodeSearchService

async def main():
    print("Starting Semantic Search Test...")
    workspace = Path(os.getcwd()).resolve()
    
    # Initialize service
    # We will use the key from .env which is loaded inside Settings
    search_service = CodeSearchService(workspace)
    
    # 1. Index the project
    print("--- Phase 1: Indexing ---")
    index_result = search_service.index_workspace()
    print(index_result)
    
    # 2. Search test
    print("--- Phase 2: Semantic Search ---")
    query = "How is the key rotation logic implemented in the LLM client?"
    print(f"Query: {query}")
    results = search_service.search(query, top_k=2)
    print("\nSearch Results:")
    print(results)
    
    # 3. Incremental test
    print("--- Phase 3: Incremental Indexing ---")
    test_file = (workspace / "backend" / "scratch" / "test_incremental.txt").resolve()
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("This is a special secret code pattern: DIAMOND-ORANGE-99. It handles the quantum encryption flux.", encoding="utf-8")
    
    # Get relative path properly
    try:
        rel_path = str(test_file.relative_to(workspace))
    except ValueError:
        # Fallback if case mismatch
        rel_path = str(test_file).replace(str(workspace), "").lstrip("\\/")

    print(f"Updating index for {rel_path}...")
    search_service.update_file_index(rel_path)
    
    print("Searching for 'quantum encryption flux'...")
    inc_results = search_service.search("quantum encryption flux", top_k=1)
    print("\nIncremental Results:")
    print(inc_results)
    
    # Cleanup
    if test_file.exists():
        test_file.unlink()

if __name__ == "__main__":
    asyncio.run(main())
