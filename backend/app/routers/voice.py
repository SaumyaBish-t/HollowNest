from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from app.config import get_user_keys
from openai import AsyncOpenAI
import tempfile
import os

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/transcribe")
async def transcribe_audio(request: Request, audio: UploadFile = File(...)):
    # BYOK only — voice transcription uses the user's Groq key from the
    # X-API-Keys header. The server never falls back to a shared key.
    user_keys = get_user_keys(request)
    groq_key = user_keys.get("groq", "")

    if not groq_key:
        raise HTTPException(
            status_code=400,
            detail=(
                "Voice transcription requires a Groq API key. "
                "Open the model selector, click the key icon on the 'Groq' "
                "row, and paste your key. Free keys: console.groq.com/keys"
            ),
        )

    # Multi-line key pools are supported in the model selector — pick the first.
    primary_key = next(
        (k.strip() for k in groq_key.replace(",", "\n").split("\n") if k.strip()),
        "",
    )

    client = AsyncOpenAI(
        api_key=primary_key,
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
