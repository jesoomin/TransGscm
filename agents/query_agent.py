"""조회 전용 질의 에이전트 — 자연어로 물으면 결정론적 조회로 답한다.

**무엇을 바꾸지 않는가.** 답의 근거는 전부 `agents/mcp_server.call_tool()`이 돌려주는
결정론적 조회 결과다. LLM이 하는 일은 두 가지뿐이다.
  1. 질문을 어느 조회로 옮길지 고르고 인자를 채운다 (`tools` 스펙이 선택지를 가둔다)
  2. 돌아온 결과를 사람 문장으로 옮긴다

노출되는 도구는 MCP 서버와 **같은 4종(읽기 전용)** 이다. 변환 실행·저장 경로는 애초에 목록에
없어서 모델이 고를 수가 없다 - CLAUDE.md의 "완전 자율 탐색형 에이전트를 만들지 않는다"와
MCP 도입 때 세운 "표면을 갈랐다"는 조건을 그대로 따른다.

**지어낸 이름은 막는다.** 도구 결과에 없는 식별자가 답변에 나오면 근거 없는 문장이므로
`QUERY_ANSWER_INVENTED_REF`로 걸러 사람에게 보여준다 - 프롬프트 지시만 믿지 않는다
(`chatui/impact_advisor.py`와 같은 원칙).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

MAX_TOOL_ROUNDS = 4  # 고정 상한. 무한 재질의는 자율 탐색이 된다.
MAX_RESULT_CHARS = 6000  # 한 도구 결과를 프롬프트에 실을 최대 길이

_SYSTEM = """너는 레거시 전환 도구의 **조회 도우미**다.

지킬 것
1. 답은 반드시 도구 조회 결과에만 근거한다. 결과에 없는 함수명·화면ID·트랜잭션ID를 쓰지 마라.
2. 모르면 모른다고 답하고, 어떤 조회를 하면 알 수 있는지 알려줘라.
3. 조회 결과가 비었으면 "해당 없음"을 그대로 전한다 — 그럴듯하게 채우지 마라.
4. 한국어로, 짧고 사실 위주로 답한다. 수치는 조회 결과의 값을 그대로 쓴다.
5. 이 도구들은 **조회만** 한다. 코드를 고치거나 저장할 수 없으니 그런 요청은 할 수 없다고 답해라.

답변 끝에 근거를 한 줄로 붙여라 — 예: `근거: impact_of_method(dPLA04702) → 호출자 2건`
"""

# impact_advisor와 같은 이유로 \b를 쓰지 않는다(한글 조사가 붙으면 경계가 성립하지 않는다).
_IDENT = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"[a-zA-Z]?PLA\d{3,}[A-Za-z0-9_]*"
    r"|R?PLA\d{3,}"
    r"|[dfp][A-Z][A-Za-z0-9_]{2,}"
    r")(?![A-Za-z0-9_])"
)


@dataclass
class QueryAnswer:
    answer: str
    tool_calls: list[dict] = field(default_factory=list)  # {name, args, ok, summary}
    issues: list[dict] = field(default_factory=list)
    rounds: int = 0


def _tool_specs() -> list[dict]:
    """노출할 도구 전부(MCP 4종 + 로컬 3종). **각 도구는 한 곳에만 정의돼 있다.**

    MCP 서버는 외부 클라이언트에 여는 표면이라 메타데이터 조회 4종만 갖고, 소스 본문을
    돌려주는 도구는 `agents/query_tools.py`에 따로 둔다 - 이유는 그 모듈 docstring 참고.
    """
    from agents import mcp_server, query_tools

    return list(mcp_server._tools()) + list(query_tools.tools())


def openai_tools() -> list[dict]:
    """도구 스펙을 OpenAI function 포맷으로 옮긴다(이름만 다른 같은 목록)."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t.get("inputSchema") or {"type": "object", "properties": {}},
            },
        }
        for t in _tool_specs()
    ]


def dispatch(name: str, args: dict) -> dict:
    """도구 이름으로 실행처를 고른다. 조회 외 경로는 어느 쪽에도 없다."""
    from agents import mcp_server, query_tools

    if name in {t["name"] for t in mcp_server._tools()}:
        return mcp_server.call_tool(name, args)
    return query_tools.call(name, args)


def _collect_identifiers(obj) -> set[str]:
    """도구 결과 안에 실제로 등장한 식별자 전부."""
    out: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            out |= _collect_identifiers(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _collect_identifiers(v)
    elif isinstance(obj, str):
        out.update(_IDENT.findall(obj))
    return out


def _summarize(name: str, result: dict) -> str:
    """UI에 한 줄로 보여줄 요약. 결과 자체를 바꾸지 않는다."""
    if name == "impact_of_method":
        r = result.get("result", {})
        return (f"호출자 {len(r.get('callers', []))}건 · "
                f"영향 화면 {len(r.get('affected_screens', []))}건")
    return f"{result.get('count', 0)}건"


def ask(question: str, history: list[dict] | None = None, chat_fn=None,
        tool_fn=None, on_event=None) -> QueryAnswer:
    """질문 하나에 답한다. history는 [{'role','content'}] 형식의 이전 대화.

    chat_fn/tool_fn을 주입할 수 있게 둔 이유는 테스트에서 LLM·DB 없이 루프를 돌리기 위해서다.

    `on_event(ev)`를 주면 진행 상황을 **일어나는 대로** 알려준다 - UI가 "지금 무엇을 하는 중인지"를
    보여줄 수 있게 하려는 것이다. ev["kind"]는 다음 중 하나다.
      think  모델에게 물어보는 중 (round 번호)
      tool   도구 하나를 실행함 (name/args/ok/summary)
      done   답변 확정
    **없는 진행을 지어내지 않는다** - 전부 실제 분기 지점에서 부른다
    (`agents/reasoning_log.py`와 같은 원칙).
    """
    def emit(**ev):
        if on_event:
            try:
                on_event(ev)
            except Exception:  # 표시용 콜백이 대화를 멈추게 두지 않는다
                pass

    if chat_fn is None:
        from agents.llm_gateway import chat_with_tools as chat_fn  # noqa: N806
    if tool_fn is None:
        tool_fn = dispatch

    tools = openai_tools()
    messages: list[dict] = [{"role": "system", "content": _SYSTEM}]
    messages += list(history or [])
    messages.append({"role": "user", "content": question})

    allowed: set[str] = set(_IDENT.findall(question))  # 사용자가 직접 쓴 이름은 허용
    calls: list[dict] = []

    for round_no in range(1, MAX_TOOL_ROUNDS + 1):
        emit(kind="think", round=round_no)
        msg = chat_fn(messages, tools=tools)
        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            answer = (getattr(msg, "content", None) or "").strip()
            issues = _check_grounding(answer, allowed)
            emit(kind="done", issues=issues)
            return QueryAnswer(answer=answer, tool_calls=calls, issues=issues,
                               rounds=round_no - 1)

        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {"id": c.id, "type": "function",
                 "function": {"name": c.function.name, "arguments": c.function.arguments}}
                for c in tool_calls
            ],
        })

        for c in tool_calls:
            name = c.function.name
            try:
                args = json.loads(c.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            try:
                result = tool_fn(name, args)
                ok, summary = True, _summarize(name, result)
                allowed |= _collect_identifiers(result)
            except Exception as exc:  # 조회 실패가 대화를 끊지 않게 한다
                result = {"error": str(exc)}
                ok, summary = False, f"조회 실패: {exc}"
            calls.append({"name": name, "args": args, "ok": ok, "summary": summary})
            emit(kind="tool", name=name, args=args, ok=ok, summary=summary)
            messages.append({
                "role": "tool",
                "tool_call_id": c.id,
                "content": json.dumps(result, ensure_ascii=False)[:MAX_RESULT_CHARS],
            })

    # 상한을 다 쓰면 지어내게 두지 않고 멈춘다
    return QueryAnswer(
        answer="조회를 여러 번 해도 답을 좁히지 못했습니다. 함수명이나 화면 ID를 넣어 다시 물어봐 주세요.",
        tool_calls=calls,
        issues=[{"type": "QUERY_ROUND_BUDGET_EXHAUSTED", "severity": "WARNING",
                 "message": f"도구 호출 {MAX_TOOL_ROUNDS}회를 다 썼습니다."}],
        rounds=MAX_TOOL_ROUNDS,
    )


def _check_grounding(answer: str, allowed: set[str]) -> list[dict]:
    invented = sorted({m for m in _IDENT.findall(answer) if m not in allowed})
    if not invented:
        return []
    return [{
        "type": "QUERY_ANSWER_INVENTED_REF",
        "severity": "BLOCKER",
        "message": "조회 결과에 없는 이름이 답변에 있습니다: " + ", ".join(invented),
        "identifiers": invented,
    }]
