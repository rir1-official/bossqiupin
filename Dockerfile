ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    MPLBACKEND=Agg \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app
COPY requirements-docker.txt /app/requirements-docker.txt
RUN pip install --no-cache-dir -r /app/requirements-docker.txt

COPY app /app/app
COPY src /app/src
COPY frontend /app/frontend
COPY data/processed/jobs_cleaned.parquet /app/data/processed/jobs_cleaned.parquet
COPY reports/clustering/cluster_summary.json /app/reports/clustering/cluster_summary.json

# Build the formal FAISS+BGE index inside the image. The index is intentionally
# not committed to GitHub because its metadata is larger than GitHub's file
# limit; the build is reproducible from the cleaned Parquet source.
RUN mkdir -p /app/data/processed/rag \
    && HF_LOCAL_FILES_ONLY=0 python -m job_analysis.rag_faiss build --device cpu --batch-size 32

EXPOSE 8000 8501
CMD ["uvicorn", "app.backend:app", "--host", "0.0.0.0", "--port", "8000"]
