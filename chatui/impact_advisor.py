"""영향도 조회 결과 위에 얹는 "수정 가이드" — 선택 실행, 사람 검토 필수.

**왜 별도 모듈인가.** 영향도 조회 자체(`agents/impact_analysis.py`)는 호출 관계도를 역방향으로
타는 규칙 기반 조회다. 답이 결정적이고 근거를 그대로 붙일 수 있는 게 그 기능의 전부이자 가치라,
거기에 LLM을 섞으면 안 된다. 이 모듈은 **이미 확정된 조회 결과를 입력으로 받아** 사람이 다음에
무엇을 해야 하는지만 제안한다 — 조회 결과를 다시 계산하지도, 바꾸지도 않는다.

`react_variant.py` / `cardinality_fix_variant.py`와 같은 "AI 추천" 계열이다.
  · 규칙으로 아는 것(누가 호출하는가)은 규칙이 답한다
  · LLM은 원본을 읽어야 아는 것(무엇을 같이 고쳐야 하는가)만 맡는다
  · 조회 결과에 없는 메서드·화면을 지어내면 BLOCKER로 막는다 — 프롬프트 지시만 믿지 않는다
  · 채택은 전적으로 사람 몫이다
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ImpactAdvice:
    guidance: str
    issues: list[dict] = field(default_factory=list)
    prompt_chars: int = 0


# 화면·메서드 식별자 모양. LLM이 없는 이름을 지어내면 이 패턴으로 잡는다.
#
# `\b`를 쓰면 안 된다 - 한글은 파이썬 정규식에서 단어 문자라 "dPLA99999를"처럼 조사가 붙으면
# 뒤쪽 경계가 성립하지 않아 그대로 통과한다. 가드레일이 한국어 문장에서만 조용히 뚫리는
# 셈이라, ASCII 단어 문자만 보는 전후방 탐색으로 바꿨다.
_IDENT = re.compile(
    r"(?<![A-Za-z0-9_])(?:"
    r"[a-zA-Z]?PLA\d{3,}[A-Za-z0-9_]*"   # PLA046 / dPLA04606 / fPLA046QrySelectMainList
    r"|[dfp][A-Z][A-Za-z0-9_]{2,}"       # fAuthCheck / dCommonCodeQry 같은 공통 메서드
    r")(?![A-Za-z0-9_])"
)


def _allowed_identifiers(result: dict) -> set[str]:
    """조회 결과가 실제로 담고 있는 이름 전부. 이 밖의 이름은 근거가 없다."""
    out: set[str] = set()
    for t in result.get("targets", []):
        out.add(t.get("method_name", ""))
        out.add(t.get("screen_id", ""))
    for c in result.get("callers", []):
        out.add(c.get("method_name", ""))
        out.add(c.get("screen_id", ""))
        if c.get("nctrid"):
            out.add(c["nctrid"])
    out.update(result.get("affected_screens", []))
    out.update(result.get("affected_nctrids", []))
    return {x for x in out if x}


def _facts(result: dict) -> str:
    lines = ["[조회로 확정된 사실 — 이 목록 밖의 이름을 쓰지 마라]", "", "대상 메서드"]
    for t in result.get("targets", []):
        lines.append(f"  - {t['screen_id']} / {t['layer']} / {t['method_name']}"
                     + (f" (SQL: {t['mapper_stmt_id']})" if t.get("mapper_stmt_id") else ""))
    lines.append("")
    lines.append("이 메서드를 (간접적으로라도) 호출하는 쪽")
    if result.get("callers"):
        for c in result["callers"]:
            nct = f" / 트랜잭션 {c['nctrid']}" if c.get("nctrid") else ""
            lines.append(f"  - 깊이 {c['depth']} : {c['screen_id']} / {c['layer']} / "
                         f"{c['method_name']}{nct}")
    else:
        lines.append("  - 없음 (호출자를 찾지 못했다)")
    lines.append("")
    lines.append(f"영향받는 화면 : {', '.join(result.get('affected_screens', [])) or '없음'}")
    lines.append(f"영향받는 트랜잭션 : {', '.join(result.get('affected_nctrids', [])) or '없음'}")
    for n in result.get("notes", []):
        lines.append(f"조회 한계 : {n}")
    return "\n".join(lines)


_PROMPT = """너는 NEXCORE 레거시(P/F/D BizUnit + XSQL)를 Spring/MyBatis로 옮기는 전환 작업을
돕는다. 아래는 **호출 관계도를 역방향으로 조회해 이미 확정된 사실**이다.

{facts}
{source}

이 사실만 근거로, 대상 메서드를 수정하려는 개발자에게 줄 가이드를 써라.

규칙
- 위 목록에 없는 메서드명·화면ID·트랜잭션ID를 절대 쓰지 마라. 모르면 모른다고 써라.
- 조회 한계가 적혀 있으면 그 한계를 가이드에 반영해라(예: 수집되지 않은 경로가 있을 수 있음).
- 추측한 내용은 "추정:"으로 시작해 사실과 구분해라.
- 코드를 새로 작성하지 마라. 무엇을 확인하고 무엇을 함께 고쳐야 하는지만 적어라.

다음 네 항목으로, 각 항목 3줄 이내로 써라. 서술형 문단을 쓰지 마라.

1. 이 메서드의 역할
2. 수정 시 함께 확인할 대상 (위 호출자 목록 기준, 왜 봐야 하는지 한 줄씩)
3. 시그니처·반환 형태를 바꿀 때의 파급
4. 확인 방법 (어떤 화면·트랜잭션을 어떤 순서로 확인할지)
"""


def build_prompt(result: dict, source_body: str | None = None) -> str:
    src = ""
    if source_body:
        body = source_body if len(source_body) <= 4000 else source_body[:4000] + "\n// ...(생략)"
        src = f"\n[대상 메서드의 AS-IS 원본]\n```java\n{body}\n```\n"
    return _PROMPT.format(facts=_facts(result), source=src)


def _check_invented(text: str, allowed: set[str]) -> list[dict]:
    """조회 결과에 없는 식별자를 쓰면 막는다. 프롬프트에 '쓰지 마라'라고 적는 것만으로는
    부족하다 - 결과를 기계적으로 대조해야 한다(react_variant.py와 같은 원칙)."""
    seen = {m.group(0) for m in _IDENT.finditer(text)}
    invented = sorted(seen - allowed)
    if not invented:
        return []
    return [{
        "issue_type": "IMPACT_ADVICE_INVENTED_REF",
        "severity": "BLOCKER",
        "message": ("조회 결과에 없는 식별자를 언급했습니다: "
                    + ", ".join(invented[:8])
                    + " — 근거가 없는 내용이므로 채택하지 마세요."),
    }]


def advise_on_impact(result: dict, source_body: str | None = None,
                     chat_fn=None) -> ImpactAdvice:
    """조회 결과를 읽고 수정 가이드를 만든다. 조회 결과 자체는 건드리지 않는다."""
    if not result.get("targets"):
        return ImpactAdvice(guidance="", issues=[{
            "issue_type": "IMPACT_ADVICE_NO_TARGET",
            "severity": "WARNING",
            "message": "대상 메서드를 찾지 못해 가이드를 만들 수 없습니다.",
        }])

    if chat_fn is None:
        from agents.llm_gateway import chat as chat_fn  # 지연 import - UI 부팅을 막지 않는다

    prompt = build_prompt(result, source_body)
    text = chat_fn(messages=[{"role": "user", "content": prompt}])
    return ImpactAdvice(
        guidance=(text or "").strip(),
        issues=_check_invented(text or "", _allowed_identifiers(result)),
        prompt_chars=len(prompt),
    )
