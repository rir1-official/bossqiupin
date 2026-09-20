"""FastAPI service for the Week 3 job-analysis workflow.

The API is intentionally thin: scoring, matching, clustering, retrieval and
Agent orchestration remain in ``src/job_analysis`` so the same logic is used by
the CLI, tests and the browser demo.
"""

from __future__ import annotations

import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from job_analysis.agent import (
    AgentConfigurationError,
    LocalJobAgent,
    OpenAIJobAgent,
    SemanticRetrievalUnavailable,
    _codex_runtime_settings,
)
from job_analysis.matching import extract_pdf_text, extract_skills, extract_years, infer_category


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data/processed/jobs_cleaned.parquet"
CLUSTER_SUMMARY = PROJECT_ROOT / "reports/clustering/cluster_summary.json"
RAG_INDEX = PROJECT_ROOT / "data/processed/rag"


class ResumeRequest(BaseModel):
    resume_text: str = Field(..., min_length=1, description="粘贴的简历文本")
    top_k: int = Field(default=5, ge=1, le=20)
    preferred_locations: Optional[List[str]] = None


class ScoreRequest(BaseModel):
    job_id: Optional[str] = None
    job_title: Optional[str] = None


class ClusterRequest(BaseModel):
    cluster_id: Optional[int] = None


class ChatRequest(BaseModel):
    task: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    use_real_model: bool = True


class RetrieveRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)


@lru_cache(maxsize=1)
def _load_jobs() -> pd.DataFrame:
    """Load the immutable cleaned dataset once per API process."""
    if not DATA_PATH.exists():
        raise RuntimeError(f"岗位数据不存在: {DATA_PATH}")
    return pd.read_parquet(DATA_PATH)


def _load_cluster_summary() -> Any:
    if not CLUSTER_SUMMARY.exists():
        return []
    return json.loads(CLUSTER_SUMMARY.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _agent() -> LocalJobAgent:
    return LocalJobAgent(
        DATA_PATH,
        None,
        CLUSTER_SUMMARY,
        semantic_retriever_loader=_faiss_retriever,
    )


@lru_cache(maxsize=1)
def _faiss_retriever() -> Any:
    from job_analysis.rag_faiss import FaissJobRetriever

    return FaissJobRetriever.load(RAG_INDEX, device="auto")


app = FastAPI(
    title="Remote Job Intelligence API",
    version="0.1.0",
    description="岗位质量评分、人岗匹配、聚类、RAG 检索与 Agent 对话 API",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "data_records": int(len(_load_jobs())), "data_source": "Himalayas authorized API collection"}


@app.post("/api/match")
def match_resume(request: ResumeRequest) -> Dict[str, Any]:
    text = request.resume_text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="简历文本不能为空或只包含空白字符")
    results = _agent().match_resume(
        text,
        top_k=request.top_k,
        resume_category=infer_category(text),
        resume_years=extract_years(text),
        preferred_locations=request.preferred_locations,
    )
    return {
        "input_type": "text",
        "resume_skills": sorted(extract_skills(text)),
        "resume_years": extract_years(text),
        "resume_category": infer_category(text),
        "results": results,
        "disclaimer": "match_score 是岗位排序参考，不是录用概率。",
    }


@app.post("/api/match/upload")
async def match_resume_upload(
    file: UploadFile = File(...),
    top_k: int = 5,
    preferred_locations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    if top_k < 1 or top_k > 20:
        raise HTTPException(status_code=400, detail="top_k 必须在 1 到 20 之间")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".txt", ""}:
        raise HTTPException(status_code=400, detail="仅支持 PDF 或 TXT 简历")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="上传文件为空")
    try:
        if suffix == ".pdf":
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as handle:
                handle.write(raw)
                handle.flush()
                text = extract_pdf_text(Path(handle.name))
        else:
            text = raw.decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"简历解析失败: {exc}") from exc
    if not text.strip():
        raise HTTPException(status_code=400, detail="未检测到可复制文本，请改用文本型 PDF 或直接粘贴简历")
    result = match_resume(
        ResumeRequest(
            resume_text=text,
            top_k=top_k,
            preferred_locations=preferred_locations,
        )
    )
    result["input_type"] = "pdf" if suffix == ".pdf" else "txt"
    result["filename"] = file.filename
    return result


@app.post("/api/score")
def score_job(request: ScoreRequest) -> Dict[str, Any]:
    if not request.job_id and not request.job_title:
        raise HTTPException(status_code=400, detail="job_id 或 job_title 至少提供一个")
    result = _agent().score_job(job_id=request.job_id, job_title=request.job_title)
    if not result.get("found"):
        raise HTTPException(status_code=404, detail=result.get("message", "未找到岗位"))
    return result


@app.post("/api/cluster")
def cluster_summary(request: ClusterRequest) -> Dict[str, Any]:
    summary = _agent().cluster_summary(cluster_id=request.cluster_id)
    return {"cluster_id": request.cluster_id, "results": summary}


@app.post("/api/retrieve")
def retrieve_jobs(request: RetrieveRequest) -> Dict[str, Any]:
    try:
        results = _faiss_retriever().search(request.question, top_k=request.top_k)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "FAISS+BGE 检索服务不可用，未回退到 TF-IDF。"
                f" 请检查索引、BGE 模型或运行环境：{str(exc)[:500]}"
            ),
        ) from exc
    return {"method": "faiss_bge_embedding", "embedding_model": "BAAI/bge-small-zh-v1.5", "results": results}


@app.post("/api/chat")
def chat(request: ChatRequest) -> Dict[str, Any]:
    if request.use_real_model:
        local = _agent()
        try:
            return OpenAIJobAgent(local_agent=local).run(request.task, top_k=request.top_k)
        except AgentConfigurationError as exc:
            raise HTTPException(status_code=503, detail=f"真实模型不可用: {exc}") from exc
        except Exception as exc:
            # A real-model request must never be represented as a local answer.
            # The UI can explicitly request use_real_model=false when it wants
            # the deterministic rule router.
            raise HTTPException(
                status_code=502,
                detail=f"gpt-5.6-sol 调用未成功: {str(exc)[:500]}",
            ) from exc
    return _agent().run(request.task, top_k=request.top_k)

@app.get("/api/agent_runtime")
def agent_runtime() -> Dict[str, Any]:
    settings = _codex_runtime_settings()
    return {
        "model": settings.get("model") or None,
        "provider": settings.get("provider") or None,
        "base_url": settings.get("base_url") or None,
        "protocol": settings.get("protocol") or "auto",
        "api_key_configured": bool(settings.get("api_key")),
    }


@app.get("/api/clusters")
def clusters() -> Dict[str, Any]:
    return {"results": _load_cluster_summary()}
