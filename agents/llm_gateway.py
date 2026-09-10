"""LLM Gateway(사내 AI Talent Lab, Azure OpenAI 호환) 클라이언트.

자격증명은 .env(커밋 금지)에서만 읽는다 - 키를 코드나 문서에 직접 적지 않는다.
CLAUDE.md "로컬 개발 환경" 참고.
"""
from __future__ import annotations

from pathlib import Path

import json

import hashlib

import os
from functools import lru_cache

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()

# LLM Gateway 발급 화면에서 확인된 허용 모델 목록. 여기 없는 이름은 배포 안 된 모델이라
# 호출 시점이 아니라 코드 작성 시점에 바로 걸러내기 위해 화이트리스트로 둔다.
ALLOWED_MODELS = {
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5.4",
    "text-embedding-3-large",
    "text-embedding-3-small",
    "text-embedding-ada-002",
}

DEFAULT_CHAT_MODEL = os.getenv("LLM_GATEWAY_DEFAULT_MODEL", "gpt-4.1")
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class LLMGatewayConfigError(RuntimeError):
    """LLM_GATEWAY_* 환경변수가 .env에 없거나 비어있을 때."""


def _require_model(model: str) -> None:
    if model not in ALLOWED_MODELS:
        raise ValueError(
            f"허용되지 않은 모델입니다: {model!r}. 허용 목록: {sorted(ALLOWED_MODELS)}"
        )


@lru_cache(maxsize=1)
def get_client() -> AzureOpenAI:
    base_url = os.getenv("LLM_GATEWAY_BASE_URL")
    api_key = os.getenv("LLM_GATEWAY_API_KEY")
    api_version = os.getenv("LLM_GATEWAY_API_VERSION", "2024-12-01-preview")

    if not base_url or not api_key:
        raise LLMGatewayConfigError(
            "LLM_GATEWAY_BASE_URL / LLM_GATEWAY_API_KEY가 .env에 설정되어 있지 않습니다. "
            "프로젝트 루트의 .env.example을 참고해 .env(커밋 금지)를 채워주세요."
        )

    return AzureOpenAI(
        azure_endpoint=base_url,
        api_key=api_key,
        api_version=api_version,
    )


# ── 응답 캐시 ────────────────────────────────────────────────────────────
# 같은 프롬프트에 같은 응답을 돌려준다. 파이프라인을 반복 실행할 때(시연 리허설, 프롬프트
# 조정) 매번 같은 호출을 다시 하느라 몇 분씩 쓰는 걸 없애려는 것이다.
#
# 기본은 꺼짐 - 제출용 실행이 조용히 옛 응답을 재사용하면 안 된다. GSCM_LLM_CACHE=1 로 켠다.
# 키는 모델 + 프롬프트 전문의 해시라, 프롬프트 템플릿을 고치면 자동으로 무효가 된다.
_CACHE_DIR = Path(__file__).resolve().parent.parent / "tracking" / "llm-cache"


def _cache_on() -> bool:
    return os.environ.get("GSCM_LLM_CACHE") == "1"


def _cache_key(model: str, messages: list[dict]) -> str:
    blob = json.dumps({"model": model, "messages": messages},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cache_get(model: str, messages: list[dict]):
    if not _cache_on():
        return None
    p = _CACHE_DIR / f"{_cache_key(model, messages)}.txt"
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def _cache_put(model: str, messages: list[dict], out: str) -> None:
    if not _cache_on() or out is None:
        return
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / f"{_cache_key(model, messages)}.txt").write_text(out, encoding="utf-8")
    except OSError:
        pass  # 캐시는 편의 기능이다 - 못 써도 실행을 막지 않는다


def chat(
    messages: list[dict],
    model: str = DEFAULT_CHAT_MODEL,
    **kwargs,
) -> str:
    """단발 채팅 완성. messages는 OpenAI chat 포맷([{"role": ..., "content": ...}, ...])."""
    _require_model(model)
    cached = _cache_get(model, messages)
    if cached is not None:
        return cached
    client = get_client()
    resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
    out = resp.choices[0].message.content
    _cache_put(model, messages, out)
    return out


def chat_stream(
    messages: list[dict],
    model: str = DEFAULT_CHAT_MODEL,
    **kwargs,
):
    """스트리밍 채팅 완성. 델타 텍스트 조각을 순서대로 yield한다."""
    _require_model(model)
    client = get_client()
    stream = client.chat.completions.create(
        model=model, messages=messages, stream=True, **kwargs
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def embed(texts: list[str], model: str = DEFAULT_EMBEDDING_MODEL) -> list[list[float]]:
    """텍스트 목록을 임베딩 벡터 목록으로 변환."""
    _require_model(model)
    client = get_client()
    resp = client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]
