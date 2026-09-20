"""Local tools plus a real OpenAI-compatible Responses API Agent.

``LocalJobAgent`` remains deterministic and offline. ``OpenAIJobAgent`` uses a
real model call for intent understanding, tool selection, and final response;
the tools themselves continue to execute against the local cleaned dataset.
The production Agent follows the configured Codex provider's Responses API
contract and does not silently switch protocols after a request failure.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import pandas as pd

from .cleaning import PROJECT_ROOT, clean_text, ensure_derived_output
from .matching import build_matching_index, extract_skills, extract_years, infer_category, match_jobs
DEFAULT_DATA = PROJECT_ROOT / "data/processed/jobs_cleaned.parquet"
DEFAULT_RAG_INDEX = PROJECT_ROOT / "data/processed/rag"
DEFAULT_CLUSTER_SUMMARY = PROJECT_ROOT / "reports/clustering/cluster_summary.json"
DEFAULT_DEMO_OUTPUT = PROJECT_ROOT / "reports/agent/demo_output.json"
DEFAULT_REAL_DEMO_OUTPUT = PROJECT_ROOT / "reports/agent/real_demo_output.json"
DEFAULT_CODEX_CONFIG = Path.home() / ".codex" / "config.toml"
DEFAULT_CODEX_AUTH = Path.home() / ".codex" / "auth.json"


FUNCTION_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "search_jobs",
        "description": "按关键词、技能、类别和地区筛选本地岗位数据",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "skills": {"type": "array", "items": {"type": "string"}},
                "category": {"type": "string"},
                "district": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "score_job",
        "description": "查询岗位信息质量分和质量等级",
        "parameters": {
            "type": "object",
            "properties": {"job_id": {"type": "string"}, "job_title": {"type": "string"}},
            "oneOf": [{"required": ["job_id"]}, {"required": ["job_title"]}],
        },
    },
    {
        "name": "match_resume",
        "description": "使用既有 TF-IDF + 余弦相似度公式计算人岗匹配",
        "parameters": {
            "type": "object",
            "properties": {
                "resume_text": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
                "resume_category": {"type": "string"},
                "resume_years": {"type": "number"},
                "preferred_locations": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["resume_text"],
        },
    },
    {
        "name": "cluster_summary",
        "description": "解释指定岗位聚类的业务名称、技能、标题和类别",
        "parameters": {
            "type": "object",
            "properties": {"cluster_id": {"type": "integer"}},
        },
    },
    {
        "name": "retrieve_jobs",
        "description": "使用本地 FAISS + BGE 岗位知识库召回 Top-k 岗位并保留来源；不可用时返回错误，不降级到 TF-IDF",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 20},
                "skills": {"type": "array", "items": {"type": "string"}},
                "category": {"type": "string"},
                "district": {"type": "string"},
            },
            "required": ["question"],
        },
    },
]


class SemanticRetrievalUnavailable(RuntimeError):
    """Raised when the required FAISS+BGE RAG runtime is unavailable."""


def _default_faiss_retriever_loader() -> Any:
    """Load the formal semantic retriever and never substitute a lexical index."""
    try:
        from .rag_faiss import FaissJobRetriever

        return FaissJobRetriever.load(DEFAULT_RAG_INDEX, device="auto")
    except Exception as exc:
        raise SemanticRetrievalUnavailable(
            "FAISS+BGE 检索器加载失败；RAG 不允许回退到 TF-IDF。"
            f" {str(exc)[:500]}"
        ) from exc


def _safe_value(value: Any) -> Any:
    if pd.isna(value):
        return ""
    return value.item() if hasattr(value, "item") else value


class LocalJobAgent:
    """Deterministic local workflow that mirrors an Agent tool loop."""

    def __init__(
        self,
        data_path: Path = DEFAULT_DATA,
        index_dir: Optional[Path] = None,
        cluster_summary_path: Path = DEFAULT_CLUSTER_SUMMARY,
        semantic_retriever_loader: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.jobs = pd.read_parquet(data_path)
        self.matching_index = build_matching_index(self.jobs)
        # RAG is intentionally separate from the deterministic matching scorer.
        # This agent never loads the historical TF-IDF retrieval baseline.
        self._semantic_retriever_loader = semantic_retriever_loader or _default_faiss_retriever_loader
        self._semantic_retriever: Any = None
        self.cluster_summary_path = cluster_summary_path

    def search_jobs(
        self,
        query: str,
        skills: Optional[Iterable[str]] = None,
        category: Optional[str] = None,
        district: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        terms = [clean_text(term) for term in (skills or extract_skills(query)) if clean_text(term)]
        lowered = clean_text(query)
        mask = pd.Series(True, index=self.jobs.index)
        if lowered:
            fields = self.jobs[["job_title", "job_category", "skills_normalized", "description_clean"]].fillna("").agg(" ".join, axis=1).map(clean_text)
            query_terms = [term for term in lowered.split() if len(term) > 2]
            if query_terms:
                mask &= fields.map(lambda value: any(term in value for term in query_terms))
        if terms:
            skill_text = self.jobs["skills_normalized"].fillna("").map(clean_text)
            mask &= skill_text.map(lambda value: all(term in value for term in terms))
        if category:
            mask &= self.jobs["broad_category"].fillna("").map(clean_text).str.contains(clean_text(category), regex=False)
        if district:
            mask &= self.jobs["district"].fillna("").map(clean_text).str.contains(clean_text(district), regex=False)
        subset = self.jobs.loc[mask].head(max(1, int(top_k)))
        return [self._job_record(row) for _, row in subset.iterrows()]

    def score_job(self, job_id: Optional[str] = None, job_title: Optional[str] = None) -> Dict[str, Any]:
        subset = self.jobs
        if job_id:
            subset = subset[subset["job_id"].astype(str) == str(job_id)]
        elif job_title:
            subset = subset[subset["job_title"].fillna("").str.contains(str(job_title), case=False, regex=False)]
        if subset.empty:
            return {"found": False, "message": "未找到岗位"}
        row = subset.iloc[0]
        return {
            "found": True,
            "job_id": _safe_value(row.get("job_id")),
            "job_title": _safe_value(row.get("job_title")),
            "quality_score": float(_safe_value(row.get("quality_score", 0))),
            "quality_level": _safe_value(row.get("quality_level")),
            "quality_definition": "岗位信息透明度与完整度，不是企业信誉或录用概率",
            "source_url": _safe_value(row.get("source_url")),
        }

    def match_resume(
        self,
        resume_text: str,
        top_k: int = 5,
        resume_category: Optional[str] = None,
        resume_years: Optional[float] = None,
        preferred_locations: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        results = match_jobs(
            resume_text,
            self.jobs,
            top_k=top_k,
            resume_category=resume_category or infer_category(resume_text),
            resume_years=resume_years if resume_years is not None else extract_years(resume_text),
            preferred_locations=preferred_locations,
            matching_index=self.matching_index,
        )
        enriched: List[Dict[str, Any]] = []
        for result in results:
            scored = self.score_job(job_id=str(result.get("job_id", "")))
            result["quality_score"] = scored.get("quality_score", "")
            result["quality_level"] = scored.get("quality_level", result.get("quality_level", ""))
            enriched.append(result)
        return enriched

    def cluster_summary(self, cluster_id: Optional[int] = None) -> Any:
        if not self.cluster_summary_path.exists():
            return {"found": False, "message": "聚类摘要尚未生成"}
        summaries = json.loads(self.cluster_summary_path.read_text(encoding="utf-8"))
        if cluster_id is None:
            return summaries
        for item in summaries:
            if int(item.get("cluster_id")) == int(cluster_id):
                return item
        return {"found": False, "message": f"未找到 cluster_id={cluster_id}"}

    def retrieve_jobs(
        self,
        question: str,
        top_k: int = 5,
        skills: Optional[Iterable[str]] = None,
        category: Optional[str] = None,
        district: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if self._semantic_retriever_loader is None:
            raise SemanticRetrievalUnavailable(
                "FAISS+BGE 检索器未配置；RAG 不允许回退到 TF-IDF。"
            )
        if self._semantic_retriever is None:
            self._semantic_retriever = self._semantic_retriever_loader()
        candidate_k = max(int(top_k) * 20, 100) if any((skills, category, district)) else int(top_k)
        candidates = self._semantic_retriever.search(question, top_k=candidate_k)
        filtered: List[Dict[str, Any]] = []
        required_skills = [clean_text(value) for value in (skills or []) if clean_text(value)]
        for item in candidates:
            skill_text = clean_text(item.get("skills_normalized", ""))
            if required_skills and not all(skill in skill_text for skill in required_skills):
                continue
            if category and clean_text(category) not in clean_text(item.get("broad_category", "")):
                continue
            if district and clean_text(district) not in clean_text(item.get("district", "")):
                continue
            filtered.append(item)
            if len(filtered) >= int(top_k):
                break
        return filtered

    def _job_record(self, row: pd.Series) -> Dict[str, Any]:
        fields = [
            "job_id",
            "job_title",
            "company_name",
            "broad_category",
            "skills_normalized",
            "district",
            "salary_raw",
            "quality_score",
            "quality_level",
            "source_url",
            "crawl_time",
            "data_origin",
        ]
        return {field: _safe_value(row.get(field, "")) for field in fields}

    def _route(self, task: str) -> str:
        lowered = clean_text(task)
        if "聚类" in task or "cluster" in lowered:
            return "cluster_summary"
        if "质量" in task and ("job_id" in lowered or re.search(r"[a-f0-9]{20,}", lowered)):
            return "score_job"
        if any(token in task for token in ("简历", "匹配", "适合", "经验")) or extract_skills(task):
            return "match_resume"
        if any(token in task for token in ("检索", "召回", "哪些", "有哪些", "找")):
            return "retrieve_jobs"
        return "search_jobs"

    def run(self, task: str, top_k: int = 5) -> Dict[str, Any]:
        tool = self._route(task)
        calls: List[Dict[str, Any]] = []
        if tool == "match_resume":
            locations = ["United States"] if any(term in clean_text(task) for term in ("美国", "us", "united states")) else None
            category = "Data Science" if any(term in clean_text(task) for term in ("data", "数据", "sql", "python")) else infer_category(task)
            args = {
                "resume_text": task,
                "top_k": top_k,
                "resume_category": category,
                "resume_years": extract_years(task),
                "preferred_locations": locations,
            }
            calls.append({"tool": tool, "arguments": args})
            results = self.match_resume(**args)
            # A composite request asks for both matching and information-quality
            # evidence. Keep the first call as match_resume for traceability,
            # then record deterministic score lookups for the top results.
            if any(token in task for token in ("质量", "quality", "信息完整", "透明")):
                for item in results[:3]:
                    score_args = {"job_id": str(item.get("job_id", ""))}
                    calls.append({"tool": "score_job", "arguments": score_args})
                    self.score_job(**score_args)
        elif tool == "retrieve_jobs":
            locations = "United States" if any(term in clean_text(task) for term in ("美国", "us", "united states")) else None
            category = "Data Science" if any(term in clean_text(task) for term in ("data", "数据")) else infer_category(task)
            args = {"question": task, "top_k": top_k, "skills": sorted(extract_skills(task)) or None, "category": category, "district": locations}
            calls.append({"tool": tool, "arguments": args})
            results = self.retrieve_jobs(**args)
        elif tool == "cluster_summary":
            match = re.search(r"(?:cluster|聚类)\s*(\d+)", task, re.IGNORECASE)
            args = {"cluster_id": int(match.group(1)) if match else None}
            calls.append({"tool": tool, "arguments": args})
            results = self.cluster_summary(**args)
        elif tool == "score_job":
            match = re.search(r"[a-f0-9]{20,}", task, re.IGNORECASE)
            args = {"job_id": match.group(0) if match else None, "job_title": None if match else task}
            calls.append({"tool": tool, "arguments": args})
            results = self.score_job(**args)
        else:
            args = {"query": task, "top_k": top_k}
            calls.append({"tool": tool, "arguments": args})
            results = self.search_jobs(**args)
        return {
            "agent_mode": "local_rule_router",
            "model_call": False,
            "task": task,
            "tool_calls": calls,
            "results": results,
            "explanation": "本地规则路由已完成工具调用；未调用外部大模型，Function Calling schema 仅作为接口契约。",
        }


class AgentConfigurationError(RuntimeError):
    """Raised when the real model mode has no usable credentials or SDK."""


def _codex_runtime_settings() -> Dict[str, str]:
    """Read API settings without copying credentials into project files.

    Environment variables take precedence. When running inside the Codex desktop
    app, the existing local Codex login and provider configuration are used as a
    convenience fallback. The secret is only held in memory for the API call.
    """
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key and DEFAULT_CODEX_AUTH.exists():
        try:
            auth = json.loads(DEFAULT_CODEX_AUTH.read_text(encoding="utf-8"))
            api_key = str(auth.get("OPENAI_API_KEY", "")).strip()
        except (OSError, json.JSONDecodeError):
            api_key = ""

    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    model = (os.getenv("AGENT_MODEL") or os.getenv("CODEX_MODEL") or "").strip()
    wire_api = os.getenv("AGENT_PROTOCOL", "").strip().lower()
    provider_name = ""
    if DEFAULT_CODEX_CONFIG.exists() and (not base_url or not model or not wire_api):
        try:
            config_text = DEFAULT_CODEX_CONFIG.read_text(encoding="utf-8")
            try:
                import tomllib
                config = tomllib.loads(config_text)
            except ImportError:
                # Python 3.10 and older do not ship tomllib.  Keep this small
                # fallback limited to the three scalar settings used here so
                # the local Codex provider can still configure the Agent.
                def _toml_scalar(pattern: str) -> str:
                    match = re.search(pattern, config_text, flags=re.MULTILINE)
                    return match.group(1).strip() if match else ""

                model = model or _toml_scalar(r'^model\s*=\s*["\']([^"\']+)["\']')
                provider_name = provider_name or _toml_scalar(r'^model_provider\s*=\s*["\']([^"\']+)["\']')
                base_url = base_url or _toml_scalar(r'^base_url\s*=\s*["\']([^"\']+)["\']')
                wire_api = wire_api or _toml_scalar(r'^wire_api\s*=\s*["\']([^"\']+)["\']')
                config = {}
            model = model or str(config.get("model", "")).strip()
            provider_name = provider_name or str(config.get("model_provider", "")).strip()
            providers = config.get("model_providers", {})
            provider = providers.get(provider_name, {}) if isinstance(providers, dict) else {}
            if not isinstance(provider, dict):
                provider = {}
            base_url = base_url or str(provider.get("base_url", "")).strip()
            # Codex custom providers declare wire_api as chat|responses.
            if not wire_api:
                wire_api = str(provider.get("wire_api", "")).strip().lower()
        except (OSError, ValueError, ImportError):
            provider_name = provider_name or ""

    if wire_api in {"responses", "response"}:
        protocol = "responses"
    elif wire_api in {"chat", "chat_completions", "completions"}:
        protocol = "chat"
    else:
        protocol = ""

    return {
        "api_key": api_key,
        "base_url": base_url,
        "model": model,
        "protocol": protocol,
        "provider": provider_name,
    }


def _responses_tools() -> List[Dict[str, Any]]:
    """Convert the shared schemas to the Responses API function-tool shape."""
    return [
        {
            "type": "function",
            "name": schema["name"],
            "description": schema.get("description", ""),
            "parameters": schema["parameters"],
        }
        for schema in FUNCTION_SCHEMAS
    ]


def _chat_tools() -> List[Dict[str, Any]]:
    """Convert the shared schemas to Chat Completions tool definitions."""
    return [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema.get("description", ""),
                "parameters": schema["parameters"],
            },
        }
        for schema in FUNCTION_SCHEMAS
    ]


def _json_default(value: Any) -> str:
    return str(_safe_value(value))


REAL_AGENT_SYSTEM_PROMPT = """你是本项目的岗位分析 Agent。你可以调用本地工具完成岗位检索、岗位信息质量评分、人岗匹配、聚类摘要和 RAG 检索。

工作约束：
1. 只使用工具返回的本地岗位数据，不联网，不更换数据源。
2. 保留并展示 source_url、crawl_time、data_origin 等溯源字段。
3. quality_score 只表示岗位信息透明度与完整度，不表示企业信誉或录用概率。
4. match_score 只表示候选岗位排序参考，不表示录用概率。
5. RAG 工具必须使用本地 FAISS+BGE 索引；不要把 TF-IDF 匹配或历史检索基线描述成 Embedding RAG，也不要在 RAG 失败时声称已经召回岗位。
6. 需要岗位事实时先调用工具，再根据工具结果回答；不要编造工具没有返回的指标。
7. 先完成最少的必要工具调用，再用简洁中文总结结果。
"""


class OpenAIJobAgent:
    """A real Responses API Agent backed by the local job-analysis tools."""

    def __init__(
        self,
        local_agent: Optional[LocalJobAgent] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        max_turns: int = 6,
        protocol: Optional[str] = None,
    ) -> None:
        settings = _codex_runtime_settings()
        self.api_key = (api_key or settings["api_key"]).strip()
        self.base_url = (base_url or settings["base_url"]).strip()
        self.model = (model or settings["model"] or "gpt-5.6-sol").strip()
        self.provider = str(settings.get("provider") or "").strip()
        self.max_turns = max(1, int(max_turns or os.getenv("AGENT_MAX_TURNS", "4")))
        requested_protocol = (protocol or os.getenv("AGENT_PROTOCOL") or settings.get("protocol") or "responses").strip().lower()
        if requested_protocol in {"", "auto"}:
            requested_protocol = settings.get("protocol") or "responses"
        if requested_protocol not in {"responses", "response"}:
            raise AgentConfigurationError(
                "当前 Agent 固定使用 Codex custom provider 的 Responses API；"
                "请将 AGENT_PROTOCOL 设为 responses。"
            )
        self.protocol = "responses"
        if not self.api_key:
            raise AgentConfigurationError(
                "未找到 OPENAI_API_KEY；请设置环境变量，或在 Codex 登录后使用 ~/.codex/auth.json。"
            )
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise AgentConfigurationError("缺少 openai Python SDK，请运行 scripts/python.sh -m pip install -r requirements.txt") from exc
        client_kwargs: Dict[str, Any] = {"api_key": self.api_key, "timeout": 90.0, "max_retries": 1}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        self.client = OpenAI(**client_kwargs)
        self.local_agent = local_agent or LocalJobAgent()

    def _dispatch(self, name: str, arguments: Dict[str, Any]) -> Any:
        if name not in {schema["name"] for schema in FUNCTION_SCHEMAS}:
            return {"found": False, "message": f"未知工具: {name}"}
        method = getattr(self.local_agent, name)
        return method(**arguments)

    @staticmethod
    def _function_calls(response: Any) -> List[Any]:
        output = getattr(response, "output", None) or []
        return [item for item in output if getattr(item, "type", None) == "function_call"]

    def _run_responses(self, task: str, top_k: int = 5) -> Dict[str, Any]:
        started = time.perf_counter()
        input_items: List[Any] = [{"role": "user", "content": task}]
        tool_calls: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []
        final_answer = ""
        turns = 0

        for turns in range(1, self.max_turns + 1):
            response = self.client.responses.create(
                model=self.model,
                instructions=REAL_AGENT_SYSTEM_PROMPT,
                input=input_items,
                tools=_responses_tools(),
                tool_choice="auto",
            )
            output = getattr(response, "output", None) or []
            input_items.extend(output)
            calls = self._function_calls(response)
            if not calls:
                final_answer = str(getattr(response, "output_text", "") or "").strip()
                break
            for call in calls:
                raw_arguments = getattr(call, "arguments", "{}") or "{}"
                try:
                    arguments = json.loads(raw_arguments)
                except (TypeError, json.JSONDecodeError):
                    arguments = {}
                if "top_k" in arguments:
                    arguments["top_k"] = min(max(1, int(arguments["top_k"])), max(1, int(top_k)))
                result = self._dispatch(str(getattr(call, "name", "")), arguments)
                serialised = json.dumps(result, ensure_ascii=False, default=_json_default)
                tool_calls.append(
                    {
                        "tool": str(getattr(call, "name", "")),
                        "arguments": arguments,
                        "call_id": str(getattr(call, "call_id", "")),
                    }
                )
                tool_results.append(
                    {
                        "tool": str(getattr(call, "name", "")),
                        "call_id": str(getattr(call, "call_id", "")),
                        "result": result,
                    }
                )
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": str(getattr(call, "call_id", "")),
                        "output": serialised,
                    }
                )
        if not final_answer:
            final_answer = "模型在达到最大工具调用轮次前未返回最终文本。"

        return {
            "agent_mode": "openai_responses",
            "model_call": True,
            "protocol": "responses",
            "model": self.model,
            "provider": self.provider or "custom",
            "base_url": self.base_url or "https://api.openai.com/v1",
            "task": task,
            "turns": turns,
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "answer": final_answer,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "explanation": "真实 Responses API 调用已完成；工具函数仍在本地执行并保留岗位溯源字段。",
        }

    def run(self, task: str, top_k: int = 5) -> Dict[str, Any]:
        return self._run_responses(task, top_k=top_k)


def write_prompt_version(path: Path) -> None:
    text = """# Agent Prompt Versions

## v1 2026-09-09

### Purpose
Route a user request to one or more local job-analysis tools and return traceable results.

### System prompt
You are a local job-analysis assistant. Select the smallest set of tools needed for the request. Always preserve job_id and source_url. Describe quality_score as job-information quality, never employer reputation or hiring probability. Describe match_score as a ranking score, never an employment probability. If a true language-model call is unavailable, use the local rule router and disclose that no external model was called.

### Routing notes
- Resume, skills, years, or “suitable for me” requests use `match_resume`.
- Retrieval questions use `retrieve_jobs` with the formal FAISS+BGE index; if that index is unavailable, report the error instead of downgrading to TF-IDF.
- Quality questions use `score_job`.
- Cluster questions use `cluster_summary`.

### Change log
v1 is the first runnable Week 2 prototype. Future versions may add API-backed structured output after an API key and model endpoint are configured.
"""
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_schemas(path: Path = PROJECT_ROOT / "reports/agent/function_schemas.json") -> None:
    ensure_derived_output(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(FUNCTION_SCHEMAS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the job-analysis Agent")
    parser.add_argument("--task", default="帮我找适合 Python、SQL、4 年经验、允许美国远程的数据岗位，并说明哪些技能匹配、哪些岗位信息质量较高。")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--mode", choices=["local", "real", "auto"], default="local")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.mode == "real":
        result = OpenAIJobAgent().run(args.task, top_k=args.top_k)
        output_path = args.output or DEFAULT_REAL_DEMO_OUTPUT
    elif args.mode == "auto":
        try:
            result = OpenAIJobAgent().run(args.task, top_k=args.top_k)
            output_path = args.output or DEFAULT_REAL_DEMO_OUTPUT
        except AgentConfigurationError:
            result = LocalJobAgent().run(args.task, top_k=args.top_k)
            output_path = args.output or DEFAULT_DEMO_OUTPUT
    else:
        result = LocalJobAgent().run(args.task, top_k=args.top_k)
        output_path = args.output or DEFAULT_DEMO_OUTPUT
    write_schemas()
    prompt_text_path = PROJECT_ROOT / "docs/prompts/week2_agent_v1.md"
    write_prompt_version(prompt_text_path)
    write_prompt_version(PROJECT_ROOT / "reports/agent/prompt_versions.md")
    ensure_derived_output(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
