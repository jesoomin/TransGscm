"""Store 카디널리티(단건/다건) 불일치 — AI 추천 (2026-09-10).

`STORE_CARDINALITY_MISMATCH`(skeleton_gen.py, 2026-09-10)는 원본이 D 메서드 결과를 다건
(recordset)으로 다루는데 Store가 단건(`Map<String,Object>`, `selectOne`)으로 생성돼, 실제로
2행 이상 나오면 런타임에 `TooManyResultsException`이 나는 결함이다. 자동으로 고치지 않기로
한 이유(docs/03-kickoff-plan.md 2026-09-10)는 Store 반환 타입을 바꾸면 그 위 Service/Api
시그니처까지 연쇄적으로 바뀌는 아키텍처 결정이기 때문이다.

같은 이유로 여기서도 규칙 기반 강제 변경이 아니라 `react_variant.py`/`d_orchestration_variant.py`
와 같은 **opt-in AI 추천** 패턴을 쓴다:
- **Store 쪽 변경**(`selectOne`→`selectList`, `Map`→`List<Map<String,Object>>`)은 이 D 메서드가
  실제로 다건이라는 게 이미 확인된 사실이라 **규칙 기반**으로 만든다(LLM 미사용).
- 그 결과를 소비하는 **Service 코드**를 어떻게 고쳐야 하는지만 LLM에 맡긴다 - 원본 F 코드가
  다건 결과를 어떻게 다루는지(색인 없이 통째로 전달하는지 등)는 읽어야 아는 부분이다.
- LLM이 계약 밖의 Store 메서드를 지어내면(react_variant.py의 REACT_VARIANT_INVENTED_FIELD와
  같은 원칙) `CARDINALITY_FIX_INVENTED_CALL` BLOCKER로 막는다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from converters import ConversionIssue


@dataclass
class CardinalityFixRecommendation:
    d_method: str = ""
    store_java: str = ""
    service_java: str = ""
    issues: list[ConversionIssue] = field(default_factory=list)


def find_cardinality_mismatches(
    d_java_text: str | None,
    f_java_text: str | None,
    p_java_text: str | None,
    d_xsql_text: str | None,
) -> dict[str, str]:
    """{D 메서드명: mapper statement id} - `STORE_CARDINALITY_MISMATCH` 대상만.

    skeleton_gen.py의 Store 생성 로직과 같은 판정을 가볍게 재현한다(무거운 `generate_skeletons()`
    전체를 돌리지 않기 위함) - 판정 규칙 자체는 skeleton_gen.py의 `extract_xsql_stmt_kinds()`/
    `infer_d_method_cardinality()`를 그대로 가져다 쓴다(재구현 아님, 단일 진실 공급원 유지).
    """
    from skeleton_gen import extract_d_stmt_ids, extract_xsql_stmt_kinds, infer_d_method_cardinality

    if not d_java_text:
        return {}
    stmt_ids = extract_d_stmt_ids(d_java_text)
    stmt_kinds = extract_xsql_stmt_kinds(d_xsql_text) if d_xsql_text else {}
    caller_text = f"{f_java_text or ''}\n{p_java_text or ''}"
    out: dict[str, str] = {}
    for method, stmt_id in stmt_ids.items():
        if stmt_kinds.get(stmt_id) != "select":
            continue
        if infer_d_method_cardinality(caller_text, method) == "LIST":
            out[method] = stmt_id
    return out


def _find_caller_f_body(f_java_text: str | None, d_method: str) -> str:
    """이 D 메서드를 실제로 호출하는 F 메서드의 본문을 찾는다(첫 번째 매치, 참고용 컨텍스트)."""
    from skeleton_gen import extract_method_bodies

    escaped = re.escape(d_method)
    for body in extract_method_bodies(f_java_text or "").values():
        if re.search(rf"\b{escaped}\s*\(", body):
            return body
    return ""


def find_current_service_method(service_java_text: str | None, d_method: str) -> str:
    """이미 생성된(규칙 기반이든 LLM 포팅이든) Service.java에서 `store.{d_method}(...)`를
    실제로 호출하는 메서드의 현재 본문을 찾는다(첫 번째 매치). `extract_method_bodies`(AS-IS
    전용, `public IDataSet` 시그니처만 인식)를 쓰면 TO-BE 코드에서 조용히 빈 결과를 준다는 게
    실제로 겪은 결함이라(java_ast.extract_tobe_method_bodies docstring 참고),
    TO-BE 전용 파서를 쓴다.
    """
    from java_ast import extract_tobe_method_bodies

    escaped = re.escape(d_method)
    for body in extract_tobe_method_bodies(service_java_text or "").values():
        if re.search(rf"\bstore\s*\.\s*{escaped}\s*\(", body):
            return body
    return ""


def build_fixed_store_method(d_method: str, mapper_stmt_id: str) -> str:
    """`selectOne`(단건) → `selectList`(다건)로 바꾼 Store 메서드를 규칙 기반으로 만든다.

    이 D 메서드가 실제로 다건이라는 사실 자체는 `find_cardinality_mismatches()`가 이미 결정론적
    으로 확인했으므로, 시그니처를 바꾸는 이 부분은 추측이 아니다 - LLM을 부르지 않는다.
    """
    return "\n".join([
        "// [AI 추천 - 사람 검토 전 채택 금지] 원본이 다건(recordset)으로 다루는 statement -",
        "// selectOne(단건)을 selectList(다건)로 교정하는 안(규칙 기반, LLM 미사용).",
        f"public java.util.List<Map<String, Object>> {d_method}(Map<String, Object> params) {{",
        f'    return sqlSession.selectList(NS + "{mapper_stmt_id}", params);',
        "}",
    ])


_FIX_PROMPT = """\
다음은 NEXCORE D BizUnit 메서드 `{d_method}`를 호출하는 Spring Service 메서드다. 지금까지
`store.{d_method}(...)`의 반환 타입이 `Map<String,Object>`(단건)였는데, 원본을 다시 확인한
결과 실제로는 다건(recordset)이라 `List<Map<String,Object>>`로 고쳐야 한다는 게 이미 결정론
적으로 확인됐다(추측이 아니다 - 원본 D BizUnit의 XSQL statement 종류와 원본 F 소스가 그 결과를
소비하는 방식을 대조해 확정함).

원본 F 메서드(참고용 - 이 코드를 그대로 옮기라는 게 아니라, `{d_method}` 결과를 "다건"으로 어떻게
다루는지만 참고해라 - 색인 없이 통째로 응답에 담았다면 리스트를 그대로 담으면 된다):
```java
{f_body}
```

현재 Service 메서드(이 안의 `store.{d_method}(...)` 호출부와 그 결과를 다루는 부분만
`List<Map<String,Object>>` 타입에 맞게 고쳐라 - 그 외 필드·분기·계산 로직은 절대 바꾸지 마라):
```java
{current_service}
```

**절대 하지 말 것**:
- `store.{d_method}` 이외의 새 Store 메서드를 지어내지 마라.
- 이 계약(원본이 다건이라는 사실) 자체를 의심하거나 되돌리지 마라.
- 위 "현재 Service 메서드"에 없던 필드·분기·계산을 추가하거나 빼지 마라.

Java 메서드 코드만 답해라(설명 텍스트나 마크다운 코드펜스 없이, 메서드 시그니처부터 시작).
"""


def recommend_cardinality_fix(
    d_method: str,
    mapper_stmt_id: str,
    f_java_text: str | None,
    current_service_method: str,
) -> CardinalityFixRecommendation:
    """Store 수정(규칙 기반) + Service 적응(LLM 1회) 추천을 만든다.

    `f_java_text`는 F BizUnit 원본 소스 전체다 - 이 D 메서드를 실제로 호출하는 메서드의 본문을
    내부에서 찾는다(호출부가 `_find_caller_f_body()`로 캡슐화돼 있어 호출부(app.py)는 원본
    텍스트만 넘기면 된다).
    """
    from agents.llm_gateway import chat
    from skeleton_gen import strip_code_fence

    f_body = _find_caller_f_body(f_java_text, d_method)

    result = CardinalityFixRecommendation(d_method=d_method)
    result.store_java = build_fixed_store_method(d_method, mapper_stmt_id)

    if not current_service_method:
        result.issues.append(ConversionIssue(
            issue_type="CARDINALITY_FIX_NO_SERVICE_CONTEXT", severity="WARNING",
            message=f"{d_method}: 현재 Service 메서드 코드를 찾지 못해 Service 적응안은 만들지 못했습니다.",
        ))
        return result

    prompt = _FIX_PROMPT.format(
        d_method=d_method, f_body=(f_body or "(원본 F 소스에서 호출부를 찾지 못함)").strip(),
        current_service=current_service_method.strip(),
    )
    try:
        raw = chat(messages=[{"role": "user", "content": prompt}])
    except Exception as e:  # noqa: BLE001 - LLM Gateway 호출 실패는 재시도 가능한 WARNING
        result.issues.append(ConversionIssue(
            issue_type="CARDINALITY_FIX_LLM_ERROR", severity="WARNING",
            message=f"{d_method}: LLM 호출 실패 - {e}",
        ))
        return result

    code = strip_code_fence(raw)
    result.service_java = (
        f"// [AI 추천 - 사람 검토 전 채택 금지] store.{d_method}(...)가 이제 "
        f"List<Map<String,Object>>를 반환하는 것에 맞춘 안.\n{code}"
    )

    invented = {m for m in re.findall(r"\bstore\s*\.\s*(\w+)\s*\(", code) if m != d_method}
    if invented:
        result.issues.append(ConversionIssue(
            issue_type="CARDINALITY_FIX_INVENTED_CALL", severity="BLOCKER",
            message=(
                f"{d_method}: AI가 이 계약과 무관한 Store 메서드를 호출했습니다"
                f"({', '.join(sorted(invented))}) - 이 추천은 채택하지 마세요."
            ),
        ))
    if "List<Map" not in code and "List <Map" not in code:
        result.issues.append(ConversionIssue(
            issue_type="CARDINALITY_FIX_TYPE_NOT_UPDATED", severity="WARNING",
            message=(
                f"{d_method}: 생성된 코드에서 List<Map<String,Object>> 타입 사용을 확인하지 "
                "못했습니다 - 실제로 타입이 반영됐는지 확인하세요."
            ),
        ))

    return result
