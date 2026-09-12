"""조회 질의 에이전트 — 도구 루프와 가드레일.

LLM도 DB도 없이 돌린다(chat_fn/tool_fn 주입). 확인하려는 건 모델의 문장 품질이 아니라
**루프가 정해진 대로만 도는지**다 - 조회만 하는지, 상한을 지키는지, 근거 없는 이름을 막는지.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents import query_agent  # noqa: E402


def _call(name, args, cid="c1"):
    return SimpleNamespace(
        id=cid,
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )


def _msg(content=None, tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


IMPACT = {
    "result": {
        "targets": [{"screen_id": "PLA047", "layer": "D", "method_name": "dPLA04702"}],
        "callers": [{"screen_id": "PLA047", "method_name": "fPLA047QrySelectMainList",
                     "nctrid": "RPLA04701", "depth": 1}],
        "affected_screens": ["PLA047"],
        "affected_nctrids": ["RPLA04701"],
    }
}


def test_calls_a_tool_then_answers_from_its_result() -> None:
    steps = [
        _msg(tool_calls=[_call("impact_of_method", {"method_name": "dPLA04702"})]),
        _msg(content="fPLA047QrySelectMainList가 호출합니다. 영향 화면은 PLA047입니다."),
    ]
    seen = []

    def chat_fn(messages, tools):
        assert tools, "도구 목록이 전달돼야 한다"
        return steps.pop(0)

    def tool_fn(name, args):
        seen.append((name, args))
        return IMPACT

    out = query_agent.ask("dPLA04702 고치면 어디가 영향받아?", chat_fn=chat_fn, tool_fn=tool_fn)
    assert seen == [("impact_of_method", {"method_name": "dPLA04702"})]
    assert out.issues == []
    assert out.tool_calls[0]["ok"] is True


def test_blocks_a_name_the_query_never_returned() -> None:
    steps = [
        _msg(tool_calls=[_call("impact_of_method", {"method_name": "dPLA04702"})]),
        _msg(content="dPLA99999도 함께 고쳐야 합니다."),
    ]
    out = query_agent.ask("영향도 알려줘",
                          chat_fn=lambda m, tools: steps.pop(0),
                          tool_fn=lambda n, a: IMPACT)
    assert out.issues, "조회에 없던 이름이 통과했다"
    assert out.issues[0]["type"] == "QUERY_ANSWER_INVENTED_REF"
    assert "dPLA99999" in out.issues[0]["identifiers"]


def test_korean_particle_does_not_slip_past_the_guardrail() -> None:
    """`dPLA99999를`처럼 조사가 붙어도 잡아야 한다(\\b를 쓰면 여기서 뚫린다)."""
    steps = [
        _msg(tool_calls=[_call("impact_of_method", {"method_name": "dPLA04702"})]),
        _msg(content="dPLA99999를 같이 확인하세요."),
    ]
    out = query_agent.ask("영향도",
                          chat_fn=lambda m, tools: steps.pop(0),
                          tool_fn=lambda n, a: IMPACT)
    assert out.issues and "dPLA99999" in out.issues[0]["identifiers"]


def test_stops_at_the_round_budget_instead_of_looping() -> None:
    def chat_fn(messages, tools):
        return _msg(tool_calls=[_call("unused_methods", {})])

    out = query_agent.ask("계속 조회해", chat_fn=chat_fn, tool_fn=lambda n, a: {"count": 0, "rows": []})
    assert out.rounds == query_agent.MAX_TOOL_ROUNDS
    assert out.issues[0]["type"] == "QUERY_ROUND_BUDGET_EXHAUSTED"


def test_a_failing_query_does_not_break_the_conversation() -> None:
    steps = [
        _msg(tool_calls=[_call("impact_of_method", {"method_name": "없는거"})]),
        _msg(content="해당 함수를 찾지 못했습니다."),
    ]

    def tool_fn(name, args):
        raise RuntimeError("DB 연결 없음")

    out = query_agent.ask("영향도", chat_fn=lambda m, tools: steps.pop(0), tool_fn=tool_fn)
    assert out.tool_calls[0]["ok"] is False
    assert "DB 연결 없음" in out.tool_calls[0]["summary"]
    assert out.answer


def test_only_read_only_tools_are_exposed() -> None:
    """변환 실행·저장 도구가 목록에 끼면 모델이 고를 수 있게 된다."""
    names = {t["function"]["name"] for t in query_agent.openai_tools()}
    assert names == {"impact_of_method", "unused_methods", "duplicate_methods", "nctrid_map"}
