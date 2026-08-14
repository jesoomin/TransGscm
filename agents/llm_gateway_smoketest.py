"""LLM Gateway 연결 확인용 스모크 테스트.

.env에 LLM_GATEWAY_API_KEY를 채운 뒤 직접 실행해서 확인할 것:
    python agents/llm_gateway_smoketest.py

이 개발 환경에는 Python이 설치돼 있지 않아 이 스크립트는 작성만 하고
실행/검증은 하지 못했다 - 실제 사용 전에 반드시 로컬에서 한 번 돌려볼 것.
"""
from llm_gateway import chat

if __name__ == "__main__":
    reply = chat(
        messages=[{"role": "user", "content": "안녕, 연결 확인 중이야. 한 문장으로만 답해줘."}],
        model="gpt-4.1",
    )
    print(reply)
