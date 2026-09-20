ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    MPLBACKEND=Agg \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    RAG_EMBEDDING_MODEL_PATH=/app/data/processed/models/bge-small-zh-v1.5

WORKDIR /app
COPY requirements-docker.txt /app/requirements-docker.txt
RUN pip install --no-cache-dir -r /app/requirements-docker.txt

COPY app /app/app
COPY src /app/src
COPY frontend /app/frontend
COPY data/processed/jobs_cleaned.parquet /app/data/processed/jobs_cleaned.parquet
COPY reports/clustering/cluster_summary.json /app/reports/clustering/cluster_summary.json

# The formal semantic index is published as a verified GitHub Release asset.
# It contains only the runtime FAISS files and the safetensors BGE snapshot.
ARG RAG_ASSET_URL=https://github.com/rir1-official/bossqiupin/releases/download/week3-faiss-bge-20260920/bossqiupin-faiss-bge-week3.tar.gz
ARG RAG_ASSET_SHA256=4fb92d5c2f3102c6b608446e99ab5e84fc76bde2e2f2ef0dcefbfab8eee47d44
RUN set -eux; \
    test -n "$RAG_ASSET_URL"; \
    test -n "$RAG_ASSET_SHA256"; \
    python -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], '/tmp/rag-assets.tar.gz')" "$RAG_ASSET_URL"; \
    echo "$RAG_ASSET_SHA256  /tmp/rag-assets.tar.gz" | sha256sum -c -; \
    tar -xzf /tmp/rag-assets.tar.gz -C /app; \
    rm /tmp/rag-assets.tar.gz; \
    test -s /app/data/processed/rag/faiss.index; \
    test -s /app/data/processed/rag/chunks.parquet; \
    test -s /app/data/processed/models/bge-small-zh-v1.5/model.safetensors

EXPOSE 8000 8501
CMD ["uvicorn", "app.backend:app", "--host", "0.0.0.0", "--port", "8000"]
