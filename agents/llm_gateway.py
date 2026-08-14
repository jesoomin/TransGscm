"""LLM Gateway(사내 AI Talent Lab, Azure OpenAI 호환) 클라이언트.

자격증명은 .env(커밋 금지)에서만 읽는다 - 키를 코드나 문서에 직접 적지 않는다.
CLAUDE.md "로컬 개발 환경" 참고.
"""
from __future__ import annotations

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


def chat(
    messages: list[dict],
    model: str = DEFAULT_CHAT_MODEL,
    **kwargs,
) -> str:
    """단발 채팅 완성. messages는 OpenAI chat 포맷([{"role": ..., "content": ...}, ...])."""
    _require_model(model)
    client = get_client()
    resp = client.chat.completions.create(model=model, messages=messages, **kwargs)
    return resp.choices[0].message.content


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
