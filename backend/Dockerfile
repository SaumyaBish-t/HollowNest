FROM mcr.microsoft.com/playwright/python:v1.47.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    HF_HOME=/tmp/hf_cache \
    FASTEMBED_CACHE_PATH=/tmp/hf_cache/fastembed

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the fastembed model so the first /agent/run isn't blocked
# by a ~50MB download. Model weights are cached under FASTEMBED_CACHE_PATH
# inside the image layer.
RUN mkdir -p ${FASTEMBED_CACHE_PATH} && \
    python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python init_db.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
