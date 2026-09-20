#!/usr/bin/env bash
# Package only the assets required by FaissJobRetriever.load() at runtime.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${1:-$ROOT_DIR/tmp/render-assets}"
ARCHIVE_NAME="bossqiupin-faiss-bge-week3.tar.gz"
ARCHIVE_PATH="$OUTPUT_DIR/$ARCHIVE_NAME"

required_paths=(
  "data/processed/rag/faiss.index"
  "data/processed/rag/chunks.parquet"
  "data/processed/rag/index_manifest.json"
  "data/processed/models/bge-small-zh-v1.5"
)

for relative_path in "${required_paths[@]}"; do
  if [[ ! -e "$ROOT_DIR/$relative_path" ]]; then
    echo "Required deployment asset is missing: $relative_path" >&2
    exit 1
  fi
done

mkdir -p "$OUTPUT_DIR"
rm -f "$ARCHIVE_PATH" "$ARCHIVE_PATH.sha256"

# SentenceTransformers prefers model.safetensors. The .bin file is a duplicate
# set of weights and chunk_metadata.jsonl is an audit artifact, not a runtime
# dependency of FaissJobRetriever.load().
tar \
  --exclude="data/processed/models/bge-small-zh-v1.5/pytorch_model.bin" \
  --exclude="data/processed/models/bge-small-zh-v1.5/.gitattributes" \
  -C "$ROOT_DIR" \
  -czf "$ARCHIVE_PATH" \
  data/processed/rag/faiss.index \
  data/processed/rag/chunks.parquet \
  data/processed/rag/index_manifest.json \
  data/processed/models/bge-small-zh-v1.5

(cd "$OUTPUT_DIR" && shasum -a 256 "$ARCHIVE_NAME" > "$ARCHIVE_NAME.sha256")
printf 'archive=%s\nchecksum=%s\n' "$ARCHIVE_PATH" "$ARCHIVE_PATH.sha256"
