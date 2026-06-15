from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
import aiofiles
import os
import uuid
from pathlib import Path
from typing import List
from app.config import settings
from app.auth import require_user

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("")
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    user_id: str = Depends(require_user),
):
    """
    Receives file uploads, validates size/type, and saves locally.
    Returns a list of temporary URIs/Paths for the backend to use during agent runs.
    """
    uploaded_records = []

    for file in files:
        # Check size limit by reading into memory chunks or jumping file cursor
        file.file.seek(0, 2) # Move cursor to end of file
        file_size = file.file.tell() # Get current cursor position (file size)
        file.file.seek(0) # Reset cursor to start
        
        if file_size > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=400, detail=f"File {file.filename} exceeds {MAX_FILE_SIZE_MB}MB limit.")

        ext = file.filename.split('.')[-1] if '.' in file.filename else ''
        new_filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, new_filename)

        async with aiofiles.open(file_path, 'wb') as out_file:
            # Re-read file to save it
            content = await file.read()
            await out_file.write(content)

        uploaded_records.append({
            "original_name": file.filename,
            "path": file_path,
            "mime_type": file.content_type,
            "size_bytes": file_size
        })

    return {"files": uploaded_records}


@router.post("/current-screen")
async def upload_current_screen(
    file: UploadFile = File(...),
    filename: str = "current-screen.png",
    user_id: str = Depends(require_user),
):
    """
    Saves a screenshot captured from the user's current browser tab to the
    configured workspace directory.
    """
    if file.content_type != "image/png":
        raise HTTPException(status_code=400, detail="Current screen capture must be a PNG image.")

    safe_name = Path(filename).name or "current-screen.png"
    if not safe_name.endswith(".png"):
        safe_name = f"{safe_name}.png"

    workspace = Path(settings.workspace_dir).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    output_path = (workspace / safe_name).resolve()

    if not str(output_path).startswith(str(workspace)):
        raise HTTPException(status_code=400, detail="Invalid screenshot filename.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"Screenshot exceeds {MAX_FILE_SIZE_MB}MB limit.")

    async with aiofiles.open(output_path, "wb") as out_file:
        await out_file.write(content)

    return {
        "file": safe_name,
        "path": str(output_path),
        "size_bytes": len(content),
    }
