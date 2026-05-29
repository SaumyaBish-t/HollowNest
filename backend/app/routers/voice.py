from fastapi import APIRouter, UploadFile, File, HTTPException
from app.config import settings
from openai import AsyncOpenAI
import tempfile
import os

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    if not settings.groq_api_key:
        raise HTTPException(
            status_code=400,
            detail="Voice transcription requires GROQ_API_KEY. Get a free key at console.groq.com",
        )

    client = AsyncOpenAI(
        api_key=settings.groq_api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    suffix = os.path.splitext(audio.filename or "audio.webm")[1] or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            transcription = await client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
                response_format="text",
                language="en",
            )
        return {"text": transcription.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    finally:
        os.unlink(tmp_path)
