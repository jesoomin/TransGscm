"""LLM Gateway 연결 확인용 스모크 테스트.

.env에 LLM_GATEWAY_API_KEY를 채운 뒤 직접 실행해서 확인할 것:
    python agents/llm_gateway_smoketest.py

2026-08-27(docs/10-week4-design-devenv.md) 세션에서 requirements.txt 설치 후
스크립트 자체는 정상 실행되며, .env가 없으면 LLMGatewayConfigError로 명확히
실패하는 것까지 확인했다. 다만 이 세션엔 실제 LLM_GATEWAY_API_KEY가 없어
Azure OpenAI 호환 엔드포인트로의 실제 왕복 호출까지는 검증하지 못했다 -
.env를 채운 로컬 환경에서 한 번 더 돌려볼 것.
"""
from llm_gateway import chat

if __name__ == "__main__":
    reply = chat(
        messages=[{"role": "user", "content": "안녕, 연결 확인 중이야. 한 문장으로만 답해줘."}],
        model="gpt-4.1",
    )
    print(reply)
