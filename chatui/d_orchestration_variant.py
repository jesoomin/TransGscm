"""D 계층 다중 statement 재구성 — AI 추천 (2026-09-09).

**배경**: `skeleton_gen.extract_secondary_stmt_owners()`가 찾아낸 패턴 — D 메서드 하나가 문
(statement)을 2개 이상 순서대로/조건부로 실행하는 경우(실측: PLA046 `dPLA04625`가 프로시저
P003 실행 후 `dbSelect("S099", ...)`; PLA045 `dPLA04505`는 P001 실행 후 **조건부로만** P002,
마지막에 S099). D 계층은 원래 순수 데이터 접근이어야 하는데(P/F/D 계층 분리 전제), 이 메서드들은
이미 F 계층 성격의 오케스트레이션(순서·분기)을 담고 있다.

`docs/03-kickoff-plan.md`(2026-09-09)는 이걸 규칙 기반 Store 코드 생성기로 **자동 완성하지
않기로** 판단했다 — 조건부 분기가 섞인 사례가 있어 규칙으로 추측하면 "확인 안 된 로직을
만들지 않는다" 원칙에 어긋나기 때문이다. 하지만 이 프로젝트엔 정확히 이런 상황을 위한 장치가
이미 있다 — **AI 추천**(`react_variant.py`): LLM이 제안하고, 원본과 대조해 지어낸 부분은
BLOCKER로 차단하고, 사람이 검토해야만 채택되는 opt-in 산출물. 규칙 기반 파이프라인은 전혀
건드리지 않는다. 같은 패턴을 여기 적용한다(사용자 제안, 2026-09-09).

**분리 원칙 — 결정론과 LLM을 다시 가른다**:
- **Store 분할**은 순수 기계적이다(이 메서드가 실제로 부르는 statement 목록은
  `extract_d_db_calls()`가 이미 정확히 알고 있고, 종류는 `extract_xsql_stmt_kinds()`가 XSQL
  태그로 확정한다) — 그래서 **LLM을 부르지 않고 규칙 기반으로 만든다.**
- **오케스트레이션(F/Service 메서드)**만 LLM에 맡긴다 — "이 실행 순서/조건 구조를 Service
  코드로 어떻게 옮길지"는 원본을 읽고 판단해야 하는 영역이다.
- LLM이 만든 코드가 알려진 Store 메서드 이외의 것을 호출하면(지어내면) BLOCKER로 막는다
  (`react_variant.py`의 REACT_VARIANT_INVENTED_FIELD와 같은 원칙).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from converters import ConversionIssue

_MYBATIS_CALL = {"select": "selectOne", "insert": "insert", "update": "update", "delete": "delete"}

_ORCHESTRATION_PROMPT = """\
다음은 NEXCORE D(Data) BizUnit 메서드 원본이다. 이 메서드는 원래 "순수 데이터 접근"이어야 하는
데이터 접근 계층(D)인데, 실제로는 SQL statement를 2개 이상 순서대로(또는 조건부로) 실행하고 있다 - TO-BE
아키텍처에서는 이런 오케스트레이션(순서·분기)이 F(Service) 계층의 몫이다.

원본 D 메서드 `{d_method}`:
```java
{d_body}
```

이 메서드가 실제로 실행하는 statement 목록(이미 규칙으로 확인됨 - 이 목록 밖의 호출을
만들지 마라):
{call_list}

TO-BE에서는 위 statement들이 각각 별도의 Store 메서드로 이미 분리되어 있다(이름 그대로 써라):
{store_method_list}

**할 일**: 원본 D 메서드의 실행 순서·조건 분기 구조를 그대로 보존하면서, `dbSelect`/`dbInsert`/
`dbUpdate`/`dbDelete`/`dbExecuteProcedure` 호출을 위에 나열된 Store 메서드 호출(`store.이름(...)`
형태)로 바꾼 Service 메서드 자바 코드 하나를 만들어라. `IDataSet`/`IRecordSet`/`getField`/
`putField`/`lookupDataUnit` 같은 NEXCORE 전용 API는 전부 제거하고 `Map<String,Object>` 기반으로
옮겨라. NEXCORE Dataset은 값을 전부 String으로 담는 관례가 있으니, 숫자·불린으로 써야 하는
값은 문자열을 거쳐 방어적으로 변환해라(예: `Double.valueOf(String.valueOf(...))`).

**절대 하지 말 것**:
- 위에 나열되지 않은 Store 메서드를 새로 지어내지 마라.
- 원본에 없는 분기·계산을 추가하거나 원본에 있는 분기·계산을 빼지 마라.
- 대응하는 Store 메서드가 목록에 없는 호출(프로시저 등 종류를 확정 못 한 statement)은 지우지
  말고 `// TODO(수동 처리 필요): ...` 주석으로 남겨라 - 임의로 구현하지 마라.

Java 메서드 코드만 답해라(설명 텍스트나 마크다운 코드펜스 없이, 메서드 시그니처부터 시작).
"""


@dataclass
class SplitStoreMethod:
    name: str
    stmt_id: str
    kind: str
    java: str


@dataclass
class DOrchestrationRecommendation:
    d_method: str = ""
    split_store_methods: list[SplitStoreMethod] = field(default_factory=list)
    service_method_java: str = ""
    rationale: str = ""
    issues: list[ConversionIssue] = field(default_factory=list)


def find_multi_statement_d_methods(
    d_java_text: str | None,
) -> dict[str, list[tuple[str, str]]]:
    """{D 메서드명: [(verb, stmt_id), ...]} - 서로 다른 statement를 2개 이상 쓰는 메서드만.

    UI가 "이 화면엔 AI 추천 후보가 있다"를 판단하는 데 쓴다 - 새 정적분석이 아니라 이미 있는
    `skeleton_gen.extract_d_db_calls()`를 필터링한 것뿐이다(중복 구현 방지).
    """
    from skeleton_gen import extract_d_db_calls

    if not d_java_text:
        return {}
    out: dict[str, list[tuple[str, str]]] = {}
    for method, calls in extract_d_db_calls(d_java_text).items():
        if len({sid for _, sid in calls}) > 1:
            out[method] = calls
    return out


def _split_store_method_name(d_method: str, stmt_id: str) -> str:
    return f"{d_method}_{stmt_id}"


def build_split_store_methods(
    d_method: str,
    calls: list[tuple[str, str]],
    stmt_kinds: dict[str, str],
) -> tuple[list[SplitStoreMethod], list[ConversionIssue]]:
    """statement마다 1개씩 Store 메서드를 규칙 기반으로 만든다(LLM 미사용).

    `stmt_kinds`(=`extract_xsql_stmt_kinds()`)에 없는 statement(프로시저 등 XSQL 태그가 없는
    경우)는 만들지 않고 WARNING만 남긴다 - 추측으로 만들지 않는다(skeleton_gen.py의
    UNSUPPORTED_DB_VERB와 같은 원칙).
    """
    issues: list[ConversionIssue] = []
    seen: dict[str, SplitStoreMethod] = {}
    for verb, sid in calls:
        if sid in seen:
            continue
        kind = stmt_kinds.get(sid, "")
        if not kind:
            issues.append(ConversionIssue(
                issue_type="D_SPLIT_UNSUPPORTED_STATEMENT", severity="WARNING",
                message=(
                    f"{d_method}: {sid}({verb})는 XSQL 태그로 종류를 확정할 수 없어(프로시저 등) "
                    "Store 분할 대상에서 제외했습니다 - 수동으로 처리하세요."
                ),
            ))
            continue
        method_name = _split_store_method_name(d_method, sid)
        namespace_ref = f'NS + "{sid}"'
        if kind == "select":
            java = "\n".join([
                f"    public Map<String, Object> {method_name}(Map<String, Object> params) {{",
                f"        return sqlSession.selectOne({namespace_ref}, params);",
                "    }",
            ])
        else:
            call = _MYBATIS_CALL.get(kind, "selectOne")
            java = "\n".join([
                f"    /** 원본 XSQL의 <{kind}> - MyBatis {call}()는 영향 행 수를 돌려준다. */",
                f"    public int {method_name}(Map<String, Object> params) {{",
                f"        return sqlSession.{call}({namespace_ref}, params);",
                "    }",
            ])
        seen[sid] = SplitStoreMethod(name=method_name, stmt_id=sid, kind=kind, java=java)
    return list(seen.values()), issues


def recommend_d_orchestration_split(
    d_method: str,
    d_java_body: str,
    calls: list[tuple[str, str]],
    stmt_kinds: dict[str, str],
) -> DOrchestrationRecommendation:
    """Store 분할(규칙 기반) + Service 오케스트레이션(LLM 1회) 추천을 만든다.

    `calls`는 `find_multi_statement_d_methods()`가 돌려준, 이 D 메서드의 실제 db*(...) 호출
    목록(순서 보존)이다. LLM 호출은 오케스트레이션 코드 하나에만 쓰고, 결과에 알려지지 않은
    Store 메서드 호출이 있으면 BLOCKER로 막는다(원본 필드 지어내기를 막는 react_variant.py와
    같은 원칙).
    """
    from agents.llm_gateway import chat
    from skeleton_gen import strip_code_fence

    result = DOrchestrationRecommendation(d_method=d_method)
    split_methods, split_issues = build_split_store_methods(d_method, calls, stmt_kinds)
    result.split_store_methods = split_methods
    result.issues.extend(split_issues)
    if not split_methods:
        result.issues.append(ConversionIssue(
            issue_type="D_ORCHESTRATION_NO_SPLITTABLE_STATEMENTS", severity="WARNING",
            message=f"{d_method}: 분할 가능한(XSQL 태그로 종류가 확정된) statement가 없어 추천을 만들 수 없습니다.",
        ))
        return result

    call_list_text = "\n".join(f'- {verb}("{sid}")' for verb, sid in calls)
    store_method_list_text = "\n".join(
        f"- {sm.name}({sm.stmt_id}, {sm.kind})" for sm in split_methods
    )
    prompt = _ORCHESTRATION_PROMPT.format(
        d_method=d_method, d_body=d_java_body.strip(),
        call_list=call_list_text, store_method_list=store_method_list_text,
    )
    try:
        raw = chat(messages=[{"role": "user", "content": prompt}])
    except Exception as e:  # noqa: BLE001 - LLM Gateway 호출 실패는 재시도 가능한 WARNING
        result.issues.append(ConversionIssue(
            issue_type="D_ORCHESTRATION_LLM_ERROR", severity="WARNING",
            message=f"{d_method}: LLM 호출 실패 - {e}",
        ))
        return result

    code = strip_code_fence(raw)
    result.service_method_java = (
        f"// [AI 추천 - 사람 검토 전 채택 금지] {d_method}의 statement 실행 순서/분기를 "
        f"Service 오케스트레이션으로 옮기는 안. Store는 아래 분할된 메서드들을 사용한다.\n"
        f"{code}"
    )

    known_names = {sm.name for sm in split_methods}
    called = set(re.findall(rf"\b({re.escape(d_method)}_\w+)\s*\(", code))
    invented = called - known_names
    if invented:
        result.issues.append(ConversionIssue(
            issue_type="D_ORCHESTRATION_INVENTED_CALL", severity="BLOCKER",
            message=(
                f"{d_method}: AI가 존재하지 않는 Store 메서드를 호출했습니다"
                f"({', '.join(sorted(invented))}) - 이 추천은 채택하지 마세요."
            ),
        ))
    if re.search(r"\bdb(?:Select|Insert|Update|Delete|ExecuteProcedure)\s*\(", code):
        result.issues.append(ConversionIssue(
            issue_type="D_ORCHESTRATION_NEXCORE_CALL_REMAINS", severity="WARNING",
            message=f"{d_method}: 생성된 코드에 NEXCORE 전용 호출(db*)이 남아 있습니다 - 포팅이 불완전할 수 있습니다.",
        ))

    return result
