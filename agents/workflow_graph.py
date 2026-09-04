"""화면 1개 변환 파이프라인의 LangGraph 오케스트레이션.

지금까지 chatui/app.py는 "1단계 규칙기반 변환 -> 2단계 LLM 포팅(메서드별 순차 호출) -> 정적
검증/스캔"을 Streamlit 스크립트가 직접 순서대로 함수 호출하는 방식으로 제어했다(수제 파이프라인).
이 모듈은 같은 단계를 LangGraph의 StateGraph로 다시 표현한다 - 단, **로직 자체는 재구현하지
않는다.** 각 노드는 chatui/converters.py, chatui/skeleton_gen.py, chatui/validators.py,
chatui/quality_scanner.py의 기존 함수를 그대로 호출하는 얇은 래퍼일 뿐이다(CLAUDE.md: "결정론적
변환기와 검증기는 분리하고, 그 자체를 다시 짜지 않는다"의 연장 - 오케스트레이션 레이어를
바꾸는 것과 변환 로직을 바꾸는 것은 다른 일이다).

그래프 구조 (상태 기반 병렬 제어 + 피드백 루프):

    convert --(F 메서드 없음)--------------------------> validate -> scan -> END
       L--(F 메서드 있음: Send로 메서드별 병렬 디스패치)--/
                    v
            port_one_method (병렬, LLM Gateway 호출)
                    v
                 splice  --(아직 안 된 메서드 있고 재시도 한도 안 남음: 다시 Send)--> port_one_method
                    L--(끝났거나 한도 소진)--> validate -> scan -> END

- **병렬 제어**: F BizUnit 메서드는 서로 독립적인 로직이라(원본도 별개 IDataSet 메서드) 동시에
  LLM Gateway에 보낼 수 있다. LangGraph의 `Send`로 메서드 개수만큼 `port_one_method`를 동시
  실행하고, `splice` 노드에서 한 곳으로 모아 순서 상관없이 Service.java에 이어붙인다.
- **피드백 루프(이 화면 1개짜리 ScreenState 그래프 한정)**: 지금 구현한 재시도는 "LLM 호출
  자체가 실패한 메서드"(타임아웃/네트워크 오류 등)만 `max_retries`(기본 2)까지 다시 시도하는
  좁은 범위다. "정적 검증에서 BLOCKER가 나온 코드를 LLM에게 다시 보여주고 고치게 하는" 수리
  루프(Reflection)는 아래 폴더 전체용 `PipelineState` 그래프에 2026-09-04에 추가했다(사용자가
  AlphaTrans/ReCodeAgent/MatchFixAgent 검토 후 명시적으로 요청 - docs/06-mentor-feedback.md §D).
  이 단일 화면 그래프에는 아직 없다(파일 업로드 모드 전용이라 우선순위가 낮음) - 자세한 설계는
  `repair_gate_node`/`_repair_prompt` 참고.
- **사람 승인 게이트**: CLAUDE.md 핵심 원칙("사람 리뷰 없는 자동 커밋/배포는 금지")에 따라 이
  그래프는 저장(pilot/ 폴더 기록, DB 적재)을 하지 않는다. `scan` 다음이 곧 END다 - 검증/스캔
  결과를 사람이 chatui/app.py에서 보고 승인해야 그 다음(저장)으로 넘어간다.

사용 예:
    from agents.workflow_graph import run_screen_conversion
    result = run_screen_conversion(
        screen_id="PLA047", package_p1="pm", package_p2="pla",
        p_java=..., f_java=..., d_java=..., p_bizunit=..., d_xsql=...,
    )
    result["files"], result["validation_results"], result["review_findings"]
"""
from __future__ import annotations

import operator
import sys
from pathlib import Path
from typing import Annotated, TypedDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CHATUI_DIR = _PROJECT_ROOT / "chatui"
for _p in (str(_PROJECT_ROOT), str(_CHATUI_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from converters import convert_xsql_fragment, finalize_mapper_document  # noqa: E402
from java_ast import extract_tobe_method_bodies  # noqa: E402
from skeleton_gen import (  # noqa: E402
    extract_method_bodies,
    generate_dto,
    generate_skeletons,
    splice_ported_method,
    strip_code_fence,
    to_prefix,
)
from validators import validate_screen  # noqa: E402
from quality_scanner import run_review  # noqa: E402

from langgraph.graph import END, START, StateGraph  # noqa: E402
from langgraph.types import Send  # noqa: E402

from .llm_gateway import chat  # noqa: E402
from .reasoning_log import log  # noqa: E402


class ScreenState(TypedDict, total=False):
    # 입력 (읽기 전용)
    screen_id: str
    package_p1: str
    package_p2: str
    p_java: str | None
    f_java: str | None
    d_java: str | None
    p_bizunit: str | None
    d_xsql: str | None
    max_retries: int

    # convert 노드가 채움
    files: dict[str, str]
    generation_issues: list
    pending_methods: list[str]

    # port_one_method(병렬) -> splice(수렴) 사이를 오가는 값 - 여러 병렬 브랜치가 동시에 쓰므로
    # 반드시 리듀서(operator.add)가 있어야 한다(없으면 LangGraph가 동시 쓰기 충돌로 에러를 낸다).
    port_results: Annotated[list[tuple[str, str]], operator.add]
    port_errors: Annotated[list[tuple[str, str]], operator.add]
    ported_methods: Annotated[list[str], operator.add]
    attempt_count: int

    # validate/scan 노드가 채움
    validation_results: list
    review_findings: dict


# 2026-09-04 정정: 처음엔 "Map 값은 전부 String이다"라고 단정해서 넣었는데, 그건 AS-IS(NEXCORE
# Dataset)의 관례지 TO-BE 코드의 사실이 아니다. TO-BE에서 이 Map은 출처마다 런타임 타입이 다르다 -
# 요청은 Jackson JSON 역직렬화(숫자 -> Integer/Double), Store 반환값은 MyBatis/Oracle 매핑
# (숫자 -> BigDecimal, 날짜 -> Timestamp), AS-IS에서 그대로 옮겨온 값은 String. 틀린 모델을
# LLM에게 가르치지 않도록 "타입이 고정돼 있지 않다"는 사실과 방어적 변환 규칙만 남긴다.
_VALUE_TYPE_NOTE = (
    "**Map<String,Object> 값 타입 주의**: 이 Map의 값은 런타임 타입이 한 가지로 고정돼 있지 않다 - "
    "요청(request)은 JSON 역직렬화 결과라 숫자가 Integer/Double로, store 반환값은 MyBatis/Oracle "
    "매핑 결과라 숫자가 BigDecimal·날짜가 Timestamp로, AS-IS에서 그대로 넘어온 값은 String으로 들어올 "
    "수 있다. 그래서 `(Double) map.get(...)`처럼 특정 타입으로 직접 캐스팅하면 ClassCastException이 "
    "난다(이 프로젝트에서 실제로 겪었다). 숫자로 써야 하면 "
    "`Double.valueOf(String.valueOf(map.get(...)))`처럼 문자열을 거쳐 방어적으로 변환하고, 값이 "
    "null일 수 있는 경우도 같이 처리해라."
)


def _callee_note(callees: list[str] | None) -> str:
    """이 F 메서드가 원본에서 실제로 호출하는 D 메서드 목록을 포팅 프롬프트에 명시한다.

    AlphaTrans(FSE 2025)가 프래그먼트를 번역할 때 콜러/콜리 의존관계를 명시적 메타데이터로
    넘기는 것과 같은 발상이다 - LLM이 D 메서드 이름을 추측하게 두지 않고, 이미 결정론적으로
    생성된 Store 메서드 이름을 그대로 쓰도록 강제해서 "존재하지 않는 메서드를 호출하는" 실수
    (validators.py의 UNRESOLVED_STORE_CALL)를 애초에 줄인다.
    """
    if not callees:
        return ""
    call_forms = ", ".join(f"store.{c}(...)" for c in callees)
    return (
        f"\n\n**호출 대상 참고**: 이 메서드는 원본에서 D 계층 메서드 {', '.join(callees)}를 "
        f"호출한다. Store 계층에는 이미 이 이름 그대로 메서드가 만들어져 있으니, 포팅한 코드에서도 "
        f"정확히 이 이름으로 {call_forms} 형태로 호출해라(새로 이름을 짓거나 존재하지 않는 메서드를 "
        "부르지 마라)."
    )


_RATIONALE_NOTE = (
    "메서드 본문 맨 첫 줄에 `// AI 변경 요약: <한 줄>` 주석을 추가해라 - 원본 대비 무엇을 어떻게 "
    "옮겼는지(NEXCORE 의존 제거 방식, 타입 변환 처리 등) 한 줄로 요약한 것이다. 이건 사람이 리뷰할 "
    "때 보는 변경 가이드이므로 반드시 채워라(빈 문자열이나 원본 그대로 옮겼다는 말만 반복하지 말 것)."
)


def _port_prompt(method: str, body: str, callees: list[str] | None = None) -> str:
    return (
        f"다음은 NEXCORE(BizUnit) F(Function) 계층 Java 메서드 {method}의 본문이다. "
        "이 로직(계산/분기/문자열 처리 등)을 하나도 빠짐없이 그대로 유지하면서, "
        "IDataSet/IOnlineContext/lookupDataUnit/lookupFunctionUnit 같은 NEXCORE 프레임워크 "
        "의존만 제거하고 Spring 서비스 메서드로 옮겨라. "
        "D BizUnit 호출(du.dXXXX(...))은 store.dXXXX(...) 형태로 바꿔라 (Service에 이미 "
        "`store` 필드가 있다). SQL이나 업무 규칙을 새로 설계하지 말고 원본 그대로 포팅만 해라. "
        "원본에 컴파일 에러나 미선언 변수가 있어도 그 부분을 고치지 말고 원본 그대로 옮긴 뒤 "
        "`// FIXME(원본 버그): ...` 로 표시해라. "
        f"`public Map<String, Object> {method}(Map<String, Object> request) {{ ... }}` 형태의 "
        "완성된 메서드 코드 하나만 출력하고, 코드 펜스나 다른 설명은 붙이지 마라."
        + _callee_note(callees)
        + f"\n\n{_VALUE_TYPE_NOTE}\n\n{_RATIONALE_NOTE}"
        + f"\n\n원본 메서드 본문:\n```\n{body}\n```"
    )


# 수리 후보를 여러 갈래로 만들 때 쓰는 전략. Tree-of-Thoughts의 "가지를 여러 개 펼친 뒤
# 평가해서 고른다"를 이 문제에 맞게 적용한 것인데, **평가자가 LLM이 아니라 결정론적 검증기**라는
# 점이 일반적인 ToT와 다르다(보통은 모델이 자기 가지를 자기가 채점해서 신뢰도가 낮다). 우리는
# 후보마다 실제로 splice해서 validate_screen을 돌리고, 그 메서드에 귀속된 BLOCKER 수로 채점한다.
# 가지가 서로 달라야 의미가 있으므로 지시 자체를 다르게 준다.
_REPAIR_STRATEGIES: list[tuple[str, str]] = [
    ("최소수정",
     "오류의 직접 원인이 되는 **한 줄 수준의 최소 변경**만 해라. 구조를 재배치하지 마라."),
    ("계약우선",
     "오류가 호출 대상 불일치라면, 아래 실재 목록에서 의미가 맞는 이름으로 **호출부를 교체**하는 "
     "것을 우선 검토해라. 목록에 맞는 것이 없다고 판단되면 지어내지 말고 FIXME 주석을 남겨라."),
]


def _repair_prompt(method: str, current_code: str, error_message: str,
                   available_callees: list[str] | None = None,
                   strategy: str = "") -> str:
    """정적 검증에서 BLOCKER가 난 방금 포팅한 메서드를 다시 LLM에게 보여주고 그 오류만 고치게
    한다(MatchFixAgent/ACToR 패턴, docs/06-mentor-feedback.md §D) - `repair_gate_node`가 호출
    대상을 정하고, 이 함수는 그 대상 1건에 대한 프롬프트만 만든다. 업무 로직 재설계를 막기 위해
    "이 오류만 고쳐라"를 반복해서 강조한다 - 안 그러면 LLM이 김에 코드를 통째로 다시 짜서 원본
    로직이 바뀔 위험이 있다.
    """
    return (
        f"다음은 방금 포팅한 Spring 서비스 메서드 {method}의 현재 코드다. 정적 검증에서 아래 오류가 "
        f"났다:\n{error_message}\n\n"
        "**이 오류만 고쳐라** - 계산/분기 등 업무 로직은 절대 바꾸지 말고, 오류의 직접 원인이 되는 "
        "구문/구조 문제만 최소한으로 고쳐라. 원본 자체에 있던 결함을 `// FIXME(원본 버그)`로 표시만 "
        "해두고 옮긴 거라면, 그 부분은 정적 검증을 통과할 수 있는 최소한의 형태로만 고치고(예: 짝이 "
        "안 맞는 중괄호 보정) 로직 자체를 새로 설계하지 마라. "
        f"`public Map<String, Object> {method}(Map<String, Object> request) {{ ... }}` 형태의 완성된 "
        "메서드 코드 하나만 출력하고, 코드 펜스나 다른 설명은 붙이지 마라. "
        "메서드 본문 첫 줄에 `// AI 수정: <무엇을 왜 고쳤는지 한 줄>` 주석을 추가해라.\n\n"
        # 최초 포팅에는 콜리 계약(_callee_note)을 주는데 수리에는 안 줬다 - 그래서 "없는 Store
        # 메서드를 부른다"는 오류를 받아도 LLM이 **실재하는 이름을 알 방법이 없어** 고칠 수가
        # 없었다(실측: PLA087의 주입 결함 dPLA08710을 2라운드 다 쓰고도 못 고침). 실재하는
        # 메서드 목록은 이미 생성된 Store에서 그대로 읽은 사실이라 추측을 주는 게 아니다.
        + (
            f"참고 - `store`에 실제로 정의된 메서드는 이것뿐이다: {', '.join(available_callees)}. "
            "이 목록에 없는 이름을 호출하고 있었다면 목록 안에서 의미가 맞는 것으로 바꿔라. "
            "맞는 것이 없다고 판단되면 지어내지 말고 호출부에 "
            "`// FIXME(사람 확인 필요): 대응되는 Store 메서드를 찾지 못함` 주석을 남겨라.\n\n"
            if available_callees else ""
        )
        + (f"**이번 시도의 접근 방침**: {strategy}\n\n" if strategy else "")
        + f"현재 코드:\n```\n{current_code}\n```"
    )


def _dispatch_ports(methods: list[str], state: ScreenState) -> list[Send]:
    """대상 메서드 목록을 각각 독립된 port_one_method 실행으로 병렬 디스패치한다."""
    f_java = state.get("f_java") or ""
    bodies = extract_method_bodies(f_java)
    return [
        Send("port_one_method", {"_method": m, "_method_body": bodies.get(m, "")})
        for m in methods
    ]


def _convert_screen(
    screen_id: str, package_p1: str, package_p2: str,
    p_java: str | None, f_java: str | None, d_java: str | None,
    p_bizunit: str | None, d_xsql: str | None,
) -> dict:
    """화면 1개 분량 규칙 기반 골격 + Mapper + Dto 생성(LLM 미사용) - chatui의 결정론적 변환기
    그대로 호출. `convert_node`(화면 1개 그래프)와 `convert_all_node`(폴더 전체 그래프) 둘 다
    이 함수를 그대로 쓴다 - 로직은 한 곳에만 있다. `chatui/app.py`의 `_run_batch_generate()`와
    똑같은 순서(generate_skeletons -> convert_xsql_fragment + finalize_mapper_document ->
    generate_dto)로 호출한다 - 이전엔 이 그래프가 finalize_mapper_document()를 빼먹어서
    Mapper.xml에 DOCTYPE/namespace/select id 정리가 안 들어가는 차이가 있었다(2026-09-02
    발견, 여기서 맞춤 - 새 로직을 만든 게 아니라 이미 다른 경로에서 쓰던 단계를 빠짐없이 적용).

    이슈는 skel/mapper/dto로 따로 반환한다(하나로 합치지 않음) - DB에 저장할 때
    AS_IS_LAYER(P(JAVA)/XSQL/DERIVED)별로 정확히 귀속시켜야 하기 때문(`_run_batch_save` 참고).
    """
    skel = generate_skeletons(
        screen_id=screen_id, package_p1=package_p1, package_p2=package_p2,
        p_java_text=p_java, f_java_text=f_java, d_java_text=d_java, p_bizunit_text=p_bizunit,
    )
    files = dict(skel.files)

    mapper_issues: list = []
    if d_xsql:
        mapper_result = convert_xsql_fragment(d_xsql)
        doc_result = finalize_mapper_document(
            mapper_result.mybatis_xml, screen_id=screen_id, package_p1=package_p1, package_p2=package_p2,
            stmt_id_to_method=skel.stmt_id_to_method,
        )
        files[f"{to_prefix(screen_id)}Mapper.xml"] = doc_result.mybatis_xml
        mapper_issues = list(mapper_result.issues) + list(doc_result.issues)

    dto_issues: list = []
    if p_java:
        dto = generate_dto(
            screen_id=screen_id, package_p1=package_p1, package_p2=package_p2,
            p_java_text=p_java, f_java_text=f_java, p_bizunit_text=p_bizunit,
        )
        files.update(dto.files)
        dto_issues = list(dto.issues)

    prefix = to_prefix(screen_id)
    service_fname = f"{prefix}Service.java"
    # LLM 포팅이 **실제로 필요한** 메서드만 담는다(2026-09-04 수정). 예전엔 F 메서드를 전부
    # 넣었는데, generate_skeletons가 "단순 위임"으로 판정한 메서드는 이미 규칙 기반 코드
    # (`return store.dXXX(dto);`)로 생성돼 PORT_START/PORT_END 스텁이 없다 - 그런 메서드에 LLM을
    # 돌려봐야 splice_ported_method가 마커를 못 찾아 결과를 버린다. 게다가 버려지니 영원히
    # ported_methods에 안 들어가서 route_after_splice_all이 "아직 안 된 메서드"로 보고 재시도
    # 라운드마다 다시 호출했다(PLA047 실측: 유효 1건에 호출 5건, 80% 낭비). 생성기가 스스로 남긴
    # conversion_method 기록을 그대로 신뢰한다 - 여기서 detect_simple_delegation을 다시 부르면
    # 두 판정이 어긋날 수 있다.
    pending = (
        [
            m["method_name"] for m in skel.methods
            if m.get("layer") == "F" and m.get("conversion_method") == "LLM_PENDING"
        ]
        if service_fname in files else []
    )

    return {
        "files": files,
        "skel_issues": list(skel.issues),
        "mapper_issues": mapper_issues,
        "dto_issues": dto_issues,
        "pending_methods": pending,
        "skel_methods": skel.methods,
        "skel_method_calls": skel.method_calls,
    }


def convert_node(state: ScreenState) -> dict:
    """1단계: 규칙 기반 골격 + Mapper + Dto 생성 (LLM 미사용) - _convert_screen() 그대로 호출.

    ScreenState(화면 1개 그래프)는 이슈를 하나로 합친 generation_issues 필드만 쓰던 기존
    계약을 유지한다 - 여기서만 세 리스트를 합쳐서 돌려준다(호환 유지, 외부에 새 필드 안 늘림).
    """
    result = _convert_screen(
        screen_id=state["screen_id"], package_p1=state["package_p1"], package_p2=state["package_p2"],
        p_java=state.get("p_java"), f_java=state.get("f_java"), d_java=state.get("d_java"),
        p_bizunit=state.get("p_bizunit"), d_xsql=state.get("d_xsql"),
    )
    return {
        "files": result["files"],
        "generation_issues": result["skel_issues"] + result["mapper_issues"] + result["dto_issues"],
        "pending_methods": result["pending_methods"],
        "attempt_count": 0,
    }


def route_after_convert(state: ScreenState):
    pending = state.get("pending_methods") or []
    if not pending:
        return "validate"
    return _dispatch_ports(pending, state)


def port_one_method_node(state: ScreenState) -> dict:
    """병렬 실행 노드 - 메서드 1개를 LLM Gateway에 보내 포팅한다. 다른 브랜치와 상태를 공유하지
    않고 오직 이 메서드 결과(port_results 또는 port_errors)만 반환한다(병렬 안전)."""
    method = state["_method"]
    body = state["_method_body"]
    try:
        raw = chat(messages=[{"role": "user", "content": _port_prompt(method, body)}])
        return {"port_results": [(method, strip_code_fence(raw))]}
    except Exception as e:  # LLM Gateway 타임아웃/네트워크 오류 등 - 코드 자체의 버그가 아니다
        return {"port_errors": [(method, str(e))]}


def splice_node(state: ScreenState) -> dict:
    """병렬 포팅 결과를 한 곳(Service.java)에 순서 상관없이 모아 이어붙이는 수렴 지점.

    splice_ported_method는 PORT_START/PORT_END 마커를 못 찾으면 원본을 그대로 돌려주는
    멱등(idempotent) 함수라(chatui/skeleton_gen.py), 이전 라운드에서 이미 스플라이스된 결과가
    port_results에 누적돼 다시 섞여 들어와도(reducer 특성상 라운드 간 초기화가 안 됨) 안전하게
    아무 일도 하지 않는다 - 새로 성공한 것만 실제로 반영된다.
    """
    prefix = to_prefix(state["screen_id"])
    service_fname = f"{prefix}Service.java"
    files = dict(state.get("files", {}))
    newly_ported: list[str] = []
    if service_fname in files:
        for method, code in state.get("port_results", []):
            spliced = splice_ported_method(files[service_fname], method, code)
            if spliced != files[service_fname]:
                newly_ported.append(method)
            files[service_fname] = spliced
    return {
        "files": files,
        "ported_methods": newly_ported,
        "attempt_count": state.get("attempt_count", 0) + 1,
    }


def route_after_splice(state: ScreenState):
    """피드백 루프: LLM 호출 자체가 실패했던 메서드만, 재시도 한도 안에서 다시 디스패치한다.

    검증(validate) 결과를 보고 코드를 고쳐 재시도하는 수리 루프는 여기 없다(모듈 docstring 참고,
    Phase 5로 미룸) - 이건 어디까지나 "호출이 실패해서 아직 시도조차 못 해본" 메서드의 재시도다.
    """
    pending = set(state.get("pending_methods") or [])
    ported = set(state.get("ported_methods") or [])
    still_pending = sorted(pending - ported)
    max_retries = state.get("max_retries", 2)
    if still_pending and state.get("attempt_count", 0) < max_retries:
        return _dispatch_ports(still_pending, state)
    return "validate"


def validate_node(state: ScreenState) -> dict:
    prefix = to_prefix(state["screen_id"])
    return {"validation_results": validate_screen(state.get("files", {}), prefix)}


def scan_node(state: ScreenState) -> dict:
    prefix = to_prefix(state["screen_id"])
    return {"review_findings": run_review(state.get("files", {}), prefix)}


def build_graph():
    builder = StateGraph(ScreenState)
    builder.add_node("convert", convert_node)
    builder.add_node("port_one_method", port_one_method_node)
    builder.add_node("splice", splice_node)
    builder.add_node("validate", validate_node)
    builder.add_node("scan", scan_node)

    builder.add_edge(START, "convert")
    builder.add_conditional_edges("convert", route_after_convert, ["port_one_method", "validate"])
    builder.add_edge("port_one_method", "splice")
    builder.add_conditional_edges("splice", route_after_splice, ["port_one_method", "validate"])
    builder.add_edge("validate", "scan")
    builder.add_edge("scan", END)
    return builder.compile()


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def run_screen_conversion(
    screen_id: str,
    package_p1: str,
    package_p2: str,
    p_java: str | None = None,
    f_java: str | None = None,
    d_java: str | None = None,
    p_bizunit: str | None = None,
    d_xsql: str | None = None,
    max_retries: int = 2,
) -> ScreenState:
    """화면 1개를 골격 생성 -> (필요시 병렬 LLM 포팅, 실패 시 재시도) -> 검증 -> 스캔까지 실행한다.

    저장(pilot/ 기록, DB 적재)은 하지 않는다 - 사람이 결과를 보고 승인해야 하는 단계라 이 그래프
    범위 밖이다(모듈 docstring "사람 승인 게이트" 참고).
    """
    initial: ScreenState = {
        "screen_id": screen_id,
        "package_p1": package_p1,
        "package_p2": package_p2,
        "p_java": p_java,
        "f_java": f_java,
        "d_java": d_java,
        "p_bizunit": p_bizunit,
        "d_xsql": d_xsql,
        "max_retries": max_retries,
        "port_results": [],
        "port_errors": [],
        "ported_methods": [],
    }
    return get_graph().invoke(initial)


# =====================================================================================
# 폴더 전체(여러 화면) 파이프라인 - Part A: 1~5단계, 저장 전까지 (2026-09-02)
#
# 위 ScreenState/build_graph()는 화면 1개 단위라 그대로 두고(호환 유지), 여기서는 화면 여러 개를
# 한 그래프 실행 안에서 "단계별로" 진행한다: 폴더에 화면이 50개면 1단계(convert_all)가 50개를
# 전부 처리한 다음에 2단계(port_all)로 넘어간다(화면 A를 끝까지 다 하고 화면 B로 넘어가는 방식이
# 아님) - 사용자가 명시적으로 요청한 "단계가 순서대로 진행되는 걸 눈으로 보고 싶다"는 요구에
# 맞춘 구조. 노드 함수 자체는 위 화면 1개용 헬퍼(_convert_screen 등)와 chatui의 기존 함수를
# 그대로 재사용한다 - 로직 재구현 없음.
#
# 6단계(교차분석)·7단계(Maven)는 여기 없다 - 둘 다 디스크에 저장된 pilot/ 트리를 직접 읽는
# 함수라(chatui/cross_analysis.py, chatui/validators.py) 사람이 승인해서 저장한 뒤에만 실행
# 가능하다(CLAUDE.md "사람 리뷰 없는 자동 저장/배포 금지"). 그 두 단계는 app.py가 저장 이후
# 별도로(Part B) 직접 호출한다 - LangGraph 그래프로 감쌀 필요가 없는 단발 호출이라서.
# =====================================================================================


def _replace_list(a: list, b: list) -> list:
    """수리 후보용 리듀서. 빈 리스트가 오면 초기화로 해석해 라운드 간 누적을 끊고, 그 외에는
    누적한다(병렬 브랜치가 각자 1건씩 더하는 경우)."""
    if not b:
        return []
    return (a or []) + b


def _merge_dicts(a: dict, b: dict) -> dict:
    """화면ID를 키로 쓰는 dict 필드용 리듀서. convert_all/validate_all/scan_all은 각각 단일
    노드라 실제로 동시 쓰기 충돌은 없지만, 재실행/체크포인트 재생 시에도 안전하게 합쳐지도록
    Annotated 리듀서로 선언해둔다.
    """
    return {**(a or {}), **(b or {})}


class PipelineState(TypedDict, total=False):
    # 입력 (읽기 전용)
    screens: dict[str, dict]  # {screen_id: {"P": {...}, "F": {...}, "D": {...}}} - agents/source_scan.scan_folder() 결과
    all_paths: dict[str, dict]  # {screen_id: {"P.java": 원본경로, ...}} - 계획서에 AS-IS 경로를 남기는 용도
    package_map: dict[str, tuple[str, str]]  # {screen_id: (package_p1, package_p2)}
    include_ai_recommend: bool
    max_retries: int

    # Stage 0 (plan_all - 코드 생성 전에 화면별 변환 계획을 파일로 고정, 2026-09-04)
    plans: dict[str, dict]  # {screen_id: agents/conversion_plan.build_screen_plan() 결과}
    plan_paths: dict[str, str]  # {screen_id: 기록된 conversion-plan.json 경로}

    # Stage 1 (convert_all - 단일 노드, 화면마다 순차 루프)
    files: Annotated[dict[str, dict[str, str]], _merge_dicts]  # {screen_id: {fname: content}}
    skel_issues: Annotated[dict[str, list], _merge_dicts]  # P(JAVA) 계층 이슈 - _run_batch_save 저장용
    mapper_issues: Annotated[dict[str, list], _merge_dicts]  # XSQL 계층 이슈
    dto_issues: Annotated[dict[str, list], _merge_dicts]  # DERIVED 계층 이슈
    pending_methods: dict[str, list[str]]  # {screen_id: [F 메서드명, ...]}
    skel_methods: dict[str, list]  # {screen_id: SkeletonResult.methods} - CONV_METHOD 적재용
    skel_method_calls: dict[str, list]  # {screen_id: SkeletonResult.method_calls} - CONV_METHOD_CALL 적재용

    # Stage 2 (port_one_screen_method: Send 병렬 (화면,메서드) 단위 -> splice_all: 수렴)
    port_results: Annotated[list[tuple[str, str, str]], operator.add]  # (screen_id, method, ported_code)
    port_errors: Annotated[list[tuple[str, str, str]], operator.add]  # (screen_id, method, error)
    ported_methods: Annotated[list[tuple[str, str]], operator.add]  # (screen_id, method)
    attempt_count: int

    # Stage 3 / 4 (단일 노드, 화면마다 순차 루프)
    validation_results: Annotated[dict[str, list], _merge_dicts]  # {screen_id: [ValidationResult,...]}
    review_findings: Annotated[dict[str, dict], _merge_dicts]  # {screen_id: {fname: [ConversionIssue,...]}}

    # 수리 루프 (validate_all -> repair_gate -> port_one_screen_method(재사용) -> splice_all ->
    # validate_all ... 최대 max_repair_retries 라운드, 2026-09-04 추가). repair_round/repair_targets는
    # repair_gate_node 하나만 쓰는 값이라 리듀서 없이 매번 덮어쓴다(병렬 브랜치가 동시에 안 씀).
    max_repair_retries: int
    repair_round: int
    repair_targets: list[tuple[str, str, str]]  # [(screen_id, method, error_message), ...]
    # ToT 수리 후보: (screen_id, method, 전략라벨, 코드). 병렬 브랜치가 동시에 쓰므로 리듀서 필요.
    # select_repair_node가 채점 후 빈 리스트로 덮어써서 라운드 간 누적을 끊는다.
    repair_candidates: Annotated[list[tuple[str, str, str, str]], _replace_list]
    repair_candidates_n: int

    # Stage 5 (ai_recommend_one: Send 병렬 (화면, nctRid) 단위)
    ai_recommend_results: Annotated[list[tuple[str, str, object]], operator.add]  # (screen_id, p_method, ReactVariantResult)


def plan_all_node(state: PipelineState) -> dict:
    """Stage 1: 코드를 만들기 **전에** 화면별 변환 계획을 세우고 파일로 고정한다.

    CLAUDE.md 핵심 원칙("계획 없이 바로 코드를 생성하지 않는다")을 구조적으로 보장하려고 그래프
    맨 앞(convert_all 이전)에 둔다 - app.py가 나중에 따로 쓰는 방식이면 계획 파일이 변환 *후에*
    생겨서 원칙의 취지가 깨진다. LLM은 쓰지 않는다(전부 정적 분석).

    쓰는 위치는 `tracking/conversion-plans/`이지 `pilot/`이 아니다 - "승인 전까지 pilot/엔 아무
    파일도 안 생긴다"는 보장은 그대로 지킨다(agents/conversion_plan.py docstring 참고).
    """
    from agents.conversion_plan import build_plans, write_plans

    screens = state.get("screens", {})
    log.stage(1, 7, "PLAN", f"변환 계획 수립 — 대상 화면 {len(screens)}건 (LLM 미사용, 정적 분석)")

    plans = build_plans(screens, state.get("package_map", {}), state.get("all_paths", {}))

    # 계획서가 이미 계산해 둔 값을 그대로 읽어서 "무엇을 왜 그렇게 정했는지"를 드러낸다.
    # 여기서 새로 판단하지 않는다 - build_plans()가 내린 결정을 옮겨 적을 뿐이다.
    total_llm = total_rule = 0
    for screen_id, plan in plans.items():
        frags = plan.get("fragments", {})
        present = sorted(k for k, v in frags.items() if v.get("present"))
        log.observe(
            f"{screen_id}: fragment {len(present)}/{len(frags)} 존재 ({', '.join(present) or '없음'})",
            f"nctRid {len(plan.get('nctrids', []))}건 · 예상 산출물 {len(plan.get('expected_outputs', []))}종",
        )
        est = plan.get("estimated_llm_calls", {})
        llm_n, rule_n = est.get("porting", 0), est.get("porting_skipped_rule_based", 0)
        total_llm += llm_n
        total_rule += rule_n
        for m in plan.get("llm_porting_targets", []):
            log.decide(f"{screen_id}.{m}", "LLM 포팅",
                       "계산·분기가 있어 기계적 1:1 치환 불가 — 결정론적 규칙으로 못 만듦")
        for m in plan.get("rule_based_delegations", []):
            log.decide(f"{screen_id}.{m}", "규칙 기반 생성 (LLM 호출 안 함)",
                       "단순 위임 패턴 — store 호출 1건으로 결정론적 생성 가능")
        sig = plan.get("track_signals", {})
        if sig.get("as_is_source_broken"):
            log.block(f"{screen_id}: AS-IS 원본이 그대로는 컴파일 안 됨",
                      f"중괄호 불일치 {sig.get('as_is_unbalanced_braces')} — 원본을 고치지 않고 보존, "
                      f"Reimagine 트랙 후보로 신호만 남김(트랙 결정은 사람 몫)")
        if sig.get("has_unsupported_db_verbs"):
            log.block(f"{screen_id}: 미지원 DB 동사 {plan.get('unsupported_db_verbs')}",
                      "조회(SELECT) 외 패턴은 샘플이 없어 규칙을 만들지 않았다 — 추측 생성 대신 조기 차단")
        log.observe(f"{screen_id}: 트랙 = {plan.get('track')}", "자동 배정하지 않음 — 판단 근거만 기록하고 사람이 결정")

    denom = total_llm + total_rule
    saved = f"{total_rule}/{denom}건({total_rule * 100 // denom}%)을 규칙으로 처리 → LLM 호출 회피" if denom else "포팅 대상 없음"
    log.plan(f"LLM 호출 예산 확정: {total_llm}건", saved)

    try:
        plan_paths = write_plans(plans)
    except OSError as e:  # 계획 파일을 못 써도 변환 자체는 계속한다 - 다만 조용히 넘기진 않는다
        plan_paths = {"_error": f"계획 파일 기록 실패: {e}"}
        log.block("계획 파일 기록 실패", str(e))
    log.end_stage(f"계획 고정 완료 — tracking/conversion-plans/ 에 {len(plans)}건 기록")
    return {"plans": plans, "plan_paths": plan_paths}


def convert_all_node(state: PipelineState) -> dict:
    """Stage 1: 화면마다 _convert_screen()을 순차로 돌린다. 규칙 기반이라 빠르고 부작용이
    없어서(LLM 호출 없음) Send 병렬화가 필요 없다 - 화면 수가 많아지면 필요시 병렬화 가능."""
    screens = state.get("screens", {})
    package_map = state.get("package_map", {})
    files: dict[str, dict[str, str]] = {}
    skel_issues: dict[str, list] = {}
    mapper_issues: dict[str, list] = {}
    dto_issues: dict[str, list] = {}
    pending: dict[str, list[str]] = {}
    skel_methods: dict[str, list] = {}
    skel_method_calls: dict[str, list] = {}

    log.stage(2, 7, "TOOL", f"규칙 기반 변환 — 화면 {len(screens)}건 (LLM 미사용)")
    for screen_id, buckets in screens.items():
        package_p1, package_p2 = package_map.get(screen_id, ("TODO", "TODO"))
        result = _convert_screen(
            screen_id, package_p1, package_p2,
            buckets.get("P", {}).get("java"), buckets.get("F", {}).get("java"),
            buckets.get("D", {}).get("java"), buckets.get("P", {}).get("bizunit"),
            buckets.get("D", {}).get("xsql"),
        )
        files[screen_id] = result["files"]
        skel_issues[screen_id] = result["skel_issues"]
        mapper_issues[screen_id] = result["mapper_issues"]
        dto_issues[screen_id] = result["dto_issues"]
        pending[screen_id] = result["pending_methods"]
        skel_methods[screen_id] = result["skel_methods"]
        skel_method_calls[screen_id] = result["skel_method_calls"]
        n_issue = len(result["skel_issues"]) + len(result["mapper_issues"]) + len(result["dto_issues"])
        log.tool(
            "iBatis→MyBatis + 골격/DTO 생성", screen_id,
            f"산출 {len(result['files'])}종 · 콜그래프 간선 {len(result['skel_method_calls'])}개 · "
            f"이슈 {n_issue}건 · LLM 대기 {len(result['pending_methods'])}건",
        )

    total_pending = sum(len(v) for v in pending.values())
    log.end_stage(f"규칙 기반 변환 완료 — 화면 {len(screens)}건, LLM 포팅 대상 {total_pending}건만 남음")
    return {
        "files": files, "skel_issues": skel_issues, "mapper_issues": mapper_issues, "dto_issues": dto_issues,
        "pending_methods": pending, "skel_methods": skel_methods, "skel_method_calls": skel_method_calls,
        "attempt_count": 0,
    }


def _dispatch_ports_all(screen_method_pairs: list[tuple[str, str]], state: PipelineState) -> list[Send]:
    """대상 (화면, F메서드) 조합을 전부 독립된 port_one_screen_method 실행으로 병렬 디스패치한다.

    각 메서드가 실제로 호출하는 D 메서드 목록(skel_method_calls에 이미 있음)을 같이 실어 보내서
    포팅 프롬프트에 의존관계 힌트로 쓴다(`_callee_note` 참고, AlphaTrans식 콜리 메타데이터 주입).
    """
    screens = state.get("screens", {})
    skel_calls = state.get("skel_method_calls", {})
    body_cache: dict[str, dict[str, str]] = {}
    sends = []
    for screen_id, method in screen_method_pairs:
        if screen_id not in body_cache:
            f_java = screens.get(screen_id, {}).get("F", {}).get("java") or ""
            body_cache[screen_id] = extract_method_bodies(f_java)
        callees = [
            c["callee_method"] for c in skel_calls.get(screen_id, [])
            if c.get("caller_layer") == "F" and c.get("caller_method") == method and c.get("callee_layer") == "D"
        ]
        if callees:
            log.context(
                f"{screen_id}.{method} ← 피호출자 계약 {len(callees)}건 주입: {', '.join(callees)}",
                "콜그래프에서 뽑은 실제 Store 메서드명 — LLM이 이름을 추측하지 않게 고정 "
                "(AlphaTrans 방식: 조각마다 콜러/콜리 메타데이터를 함께 전달)",
            )
        else:
            log.context(f"{screen_id}.{method} ← 피호출자 없음", "이 메서드는 하위 계층을 호출하지 않는다")
        sends.append(Send("port_one_screen_method", {
            "_screen_id": screen_id, "_method": method, "_method_body": body_cache[screen_id].get(method, ""),
            "_callees": callees,
        }))
    return sends


def route_after_convert_all(state: PipelineState):
    pairs = [(sid, m) for sid, methods in state.get("pending_methods", {}).items() for m in methods]
    if not pairs:
        log.stage(3, 7, "DECIDE", "LLM 포팅 건너뜀 — 규칙 기반으로 전부 처리됨")
        log.end_stage("LLM 호출 0건")
        return "validate_all"
    log.stage(3, 7, "TOOL", f"LLM 포팅 — {len(pairs)}건 병렬 디스패치 (fan-out)")
    return _dispatch_ports_all(pairs, state)


def port_one_screen_method_node(state: dict) -> dict:
    """병렬 실행 노드 - (화면, 메서드) 조합 1개를 LLM Gateway에 보내 포팅한다. port_one_method_node와
    로직은 동일하고, 결과에 screen_id만 같이 실어 나른다(여러 화면이 섞여서 디스패치되므로).

    `_repair_error`가 실려 있으면(repair_gate_node가 재디스패치한 경우) 원본 재포팅이 아니라
    "방금 포팅한 코드의 이 오류만 고쳐라" 프롬프트(_repair_prompt)를 쓴다 - 같은 노드를 재사용해서
    splice_all로 합쳐지는 경로(port_results 리듀서)를 그대로 타게 한다(새 수렴 지점을 안 만듦).
    """
    screen_id = state["_screen_id"]
    method = state["_method"]
    body = state["_method_body"]
    repair_error = state.get("_repair_error")
    prompt = (
        _repair_prompt(method, body, repair_error, state.get("_callees"))
        if repair_error else _port_prompt(method, body, state.get("_callees"))
    )
    kind = "수리 재생성" if repair_error else "최초 포팅"
    log.tool("LLM Gateway", f"{screen_id}.{method}",
             f"{kind} · 프롬프트 {len(prompt):,}자" + (f" · 오류 피드백 주입: {repair_error[:80]}" if repair_error else ""))
    try:
        raw = chat(messages=[{"role": "user", "content": prompt}])
        log.ok(f"{screen_id}.{method} 응답 수신 ({len(raw):,}자)")
        return {"port_results": [(screen_id, method, strip_code_fence(raw))]}
    except Exception as e:  # LLM Gateway 타임아웃/네트워크 오류 등 - 코드 자체의 버그가 아니다
        log.block(f"{screen_id}.{method} LLM 호출 실패", str(e))
        return {"port_errors": [(screen_id, method, str(e))]}


def splice_all_node(state: PipelineState) -> dict:
    """병렬 포팅 결과를 화면별 Service.java에 이어붙이는 수렴 지점 - splice_node와 동일한
    멱등 splice_ported_method()를 재사용, 화면별로 나눠서 적용한다."""
    files = {sid: dict(f) for sid, f in state.get("files", {}).items()}
    newly_ported: list[tuple[str, str]] = []
    for screen_id, method, code in state.get("port_results", []):
        prefix = to_prefix(screen_id)
        service_fname = f"{prefix}Service.java"
        screen_files = files.get(screen_id)
        if not screen_files or service_fname not in screen_files:
            continue
        current = screen_files[service_fname]
        spliced = splice_ported_method(current, method, code)
        if spliced != current:
            newly_ported.append((screen_id, method))
        elif f'UnsupportedOperationException("TODO: {method} 포팅 필요")' in current:
            # 스텁이 그대로 남아 있는데 결합이 아무것도 안 바꿨다 = 진짜 실패(마커를 못 찾음).
            # 스텁이 이미 없는 경우는 앞선 라운드에서 같은 코드로 이미 반영된 것이다 -
            # port_results가 누적 리스트(operator.add)라 수리 라운드마다 이전 결과까지 다시
            # 결합되는데, splice가 멱등이라 "변화 없음"이 된다. 그걸 실패로 찍으면 안 된다.
            log.block(f"{screen_id}.{method} 결합 실패 — 결과를 반영하지 못했다",
                      "스텁이 남아 있는데 포팅 마커를 찾지 못했다")
        screen_files[service_fname] = spliced
    if newly_ported:
        log.ok(f"결합(fan-in) 완료 — {len(newly_ported)}건을 Service에 반영",
               ", ".join(f"{s}.{m}" for s, m in newly_ported))
    return {"files": files, "ported_methods": newly_ported, "attempt_count": state.get("attempt_count", 0) + 1}


def route_after_splice_all(state: PipelineState):
    """route_after_splice와 동일한 재시도 규칙을 화면×메서드 조합 단위로 적용한다."""
    pending_pairs = {(sid, m) for sid, methods in state.get("pending_methods", {}).items() for m in methods}
    ported_pairs = set(state.get("ported_methods", []))
    still_pending = sorted(pending_pairs - ported_pairs)
    max_retries = state.get("max_retries", 2)
    if still_pending and state.get("attempt_count", 0) < max_retries:
        return _dispatch_ports_all(still_pending, state)
    return "validate_all"


def validate_all_node(state: PipelineState) -> dict:
    """Stage 3: 화면마다 validate_screen()을 그대로 호출한다(로직 변경 없음)."""
    round_no = state.get("repair_round", 0)
    suffix = f" (수리 {round_no}라운드 후 재검증)" if round_no else ""
    log.stage(4, 7, "VALIDATE", f"정적 검증{suffix} — 변환기와 분리된 검증기")
    results = {}
    n_block = n_warn = 0
    for screen_id, screen_files in state.get("files", {}).items():
        results[screen_id] = validate_screen(screen_files, to_prefix(screen_id))
        for r in results[screen_id]:
            blocks = [i for i in r.issues if i.severity == "BLOCKER"]
            warns = [i for i in r.issues if i.severity == "WARNING"]
            n_block += len(blocks)
            n_warn += len(warns)
            for i in blocks:
                log.block(f"{screen_id} [{r.check}] {i.issue_type} @ {i.method_name or r.file_name}:{i.line_no or '-'}",
                          i.message[:160])
    (log.ok if n_block == 0 else log.block)(f"검증 결과 — BLOCKER {n_block}건 · WARNING {n_warn}건")
    log.end_stage(f"정적 검증 완료 — 화면 {len(results)}건")
    return {"validation_results": results}


def _find_repairable_targets(state: PipelineState) -> list[tuple[str, str, str]]:
    """방금 validate_all이 낸 BLOCKER 이슈 중, "LLM이 실제로 포팅한 F 메서드"에 귀속된 것만 골라
    (screen_id, method, 합친 오류 메시지) 목록으로 돌려준다.

    규칙 기반으로 생성된 골격(Api/Store/단순위임 Service)의 BLOCKER는 대상에서 뺀다 - 그건
    생성기 자체의 버그지 LLM이 고칠 수 있는 게 아니고, LLM에게 규칙 기반 코드를 고치라고 시키면
    "결정론적으로 가능한 건 LLM에 맡기지 않는다" 원칙에 어긋난다. `pending_methods[screen_id]`가
    convert_all 시점에 뽑은 "LLM 포팅이 필요했던 F 메서드 목록"이라 이 필터의 기준이 된다.
    validators.py가 2026-09-03에 method_name을 채우기 시작해서 이 필터가 가능해졌다.
    """
    pending = state.get("pending_methods", {})
    validation_results = state.get("validation_results", {})
    grouped: dict[tuple[str, str], list[str]] = {}
    for screen_id, results in validation_results.items():
        llm_ported = set(pending.get(screen_id, []))
        if not llm_ported:
            continue
        for r in results:
            if r.check not in ("JAVA_STATIC", "CROSS_LAYER_REF"):
                continue
            for issue in r.issues:
                if issue.severity != "BLOCKER" or issue.method_name not in llm_ported:
                    continue
                # 포팅 자체가 안 된 스텁은 수리 대상이 아니다(2026-09-05). "포팅된 코드의 오류를
                # 고쳐라"라는 수리 프롬프트에 스텁 본문을 넣으면 고칠 대상이 없어 무의미한 호출이
                # 된다 - 포팅 실패는 route_after_splice_all의 max_retries 재시도가 담당한다.
                if issue.issue_type == "PORTING_INCOMPLETE":
                    continue
                grouped.setdefault((screen_id, issue.method_name), []).append(issue.message)
    return [(sid, m, " / ".join(msgs)) for (sid, m), msgs in grouped.items()]


def _dispatch_repairs(targets: list[tuple[str, str, str]], state: PipelineState) -> list[Send]:
    """수리 대상(화면, 메서드, 오류메시지)마다 현재(방금 포팅된, 오류 있는) 코드를 찾아
    port_one_screen_method로 재디스패치한다 - `_repair_error`가 실려 있으면 그 노드가 자동으로
    _repair_prompt를 쓴다."""
    files_by_screen = state.get("files", {})
    sends = []
    for screen_id, method, error_message in targets:
        prefix = to_prefix(screen_id)
        service_fname = f"{prefix}Service.java"
        screen_files = files_by_screen.get(screen_id, {})
        service_java = screen_files.get(service_fname, "")
        # TO-BE 산출물이므로 AS-IS용 extract_method_bodies를 쓰면 안 된다 - 그 함수는
        # `public IDataSet`만 인식해서 빈 dict를 돌려주고, 그러면 수리 프롬프트에 "현재 코드"가
        # 안 실려 LLM이 코드를 못 본 채 이름을 지어낸다(실측으로 확인, 2026-09-05).
        bodies = extract_tobe_method_bodies(service_java)
        # 이미 생성된 Store에 실제로 정의된 메서드 이름을 읽어 수리 프롬프트에 넘긴다 - 최초
        # 포팅에만 있던 의존 계약 주입을 수리에도 일관되게 적용하는 것이다(_repair_prompt 참고).
        available = sorted(extract_tobe_method_bodies(screen_files.get(f"{prefix}Store.java", "")))
        # 후보를 여러 갈래로 펼친다(ToT). 각 가지는 서로 다른 접근 방침을 받고, 나중에
        # select_repair_node가 **검증기로 채점해서** 하나만 고른다.
        n = max(1, min(len(_REPAIR_STRATEGIES), state.get("repair_candidates_n", 2)))
        for idx in range(n):
            label, strategy = _REPAIR_STRATEGIES[idx]
            sends.append(Send("repair_candidate", {
                "_screen_id": screen_id, "_method": method, "_method_body": bodies.get(method, ""),
                "_repair_error": error_message, "_callees": available,
                "_strategy": strategy, "_strategy_label": label,
            }))
    return sends


def repair_candidate_node(state: dict) -> dict:
    """수리 후보 1개를 생성한다(ToT의 가지 하나). 채점은 하지 않는다 - select_repair_node가 한다."""
    screen_id, method = state["_screen_id"], state["_method"]
    label = state.get("_strategy_label", "")
    prompt = _repair_prompt(method, state["_method_body"], state.get("_repair_error", ""),
                            state.get("_callees"), state.get("_strategy", ""))
    log.tool("LLM Gateway", f"{screen_id}.{method}", f"수리 후보 [{label}] · 프롬프트 {len(prompt):,}자")
    try:
        raw = chat(messages=[{"role": "user", "content": prompt}])
        return {"repair_candidates": [(screen_id, method, label, strip_code_fence(raw))]}
    except Exception as e:
        log.block(f"{screen_id}.{method} 후보[{label}] 생성 실패", str(e))
        return {"port_errors": [(screen_id, method, str(e))]}


def select_repair_node(state: PipelineState) -> dict:
    """생성된 수리 후보들을 **결정론적 검증기로 채점해** 메서드마다 하나만 고른다.

    일반적인 Tree-of-Thoughts는 모델이 자기 가지를 자기가 평가해서 신뢰도가 낮다. 여기서는
    후보마다 실제로 Service에 splice한 **사본**을 만들어 `validate_screen()`을 돌리고, 그
    메서드에 귀속된 BLOCKER 수로 채점한다 - 평가자가 LLM이 아니라 이미 있는 검증기다.
    동점이면 원본에서 덜 벗어난 쪽(라인 수 차이가 작은 쪽)을 고른다.
    """
    candidates = state.get("repair_candidates", [])
    if not candidates:
        return {"repair_candidates": []}

    files = {sid: dict(f) for sid, f in state.get("files", {}).items()}
    grouped: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for screen_id, method, label, code in candidates:
        grouped.setdefault((screen_id, method), []).append((label, code))

    newly: list[tuple[str, str]] = []
    for (screen_id, method), cands in grouped.items():
        prefix = to_prefix(screen_id)
        service_fname = f"{prefix}Service.java"
        screen_files = files.get(screen_id)
        if not screen_files or service_fname not in screen_files:
            continue
        base = screen_files[service_fname]
        scored = []
        for label, code in cands:
            trial_files = dict(screen_files)
            trial_files[service_fname] = splice_ported_method(base, method, code)
            blockers = 0
            for r in validate_screen(trial_files, prefix):
                blockers += sum(
                    1 for i in r.issues
                    if i.severity == "BLOCKER" and i.method_name == method
                )
            delta = abs(code.count("\n") - base.count("\n"))
            scored.append((blockers, delta, label, code, trial_files[service_fname]))
            log.reflect(f"후보 [{label}] 채점 — 잔여 BLOCKER {blockers}건",
                        "검증기로 실제 splice 후 측정(LLM 자기평가 아님)")
        scored.sort(key=lambda x: (x[0], x[1]))
        best = scored[0]
        if len(scored) > 1:
            log.decide(f"{screen_id}.{method} 수리 후보 {len(scored)}개",
                       f"[{best[2]}] 채택",
                       f"잔여 BLOCKER {best[0]}건으로 최소 "
                       f"(탈락: {', '.join(f'[{s[2]}]={s[0]}건' for s in scored[1:])})")
        if best[4] != base:
            screen_files[service_fname] = best[4]
            newly.append((screen_id, method))

    # 다음 라운드에 이전 후보가 다시 섞이지 않도록 비운다(리듀서가 누적 리스트라 명시적 초기화).
    return {"files": files, "ported_methods": newly, "repair_candidates": []}


def repair_gate_node(state: PipelineState) -> dict:
    """validate_all 직후 항상 거치는 게이트 - 수리할 게 있고 라운드 예산이 남았으면 라운드를
    1 증가시켜 repair_targets를 채우고, 아니면 빈 채로 둔다(라우팅 함수는 상태를 못 바꾸므로
    "카운터 증가"는 반드시 노드에서 해야 한다 - route_after_repair_gate는 여기서 채운 값을 읽기만
    한다).
    """
    targets = _find_repairable_targets(state)
    round_used = state.get("repair_round", 0)
    max_repair = state.get("max_repair_retries", 2)

    log.stage(5, 7, "REFLECT", f"자기 수정 게이트 — 라운드 {round_used}/{max_repair} 사용")
    if not targets:
        log.reflect("수리 불필요 → 다음 단계로 진행",
                    "LLM이 포팅한 메서드에 귀속된 BLOCKER 0건 "
                    "(규칙 기반 생성물의 BLOCKER는 대상에서 제외 — LLM이 고칠 문제가 아님)")
        log.end_stage("수리 0라운드")
        return {"repair_targets": []}
    if round_used >= max_repair:
        log.reflect(f"수리 대상 {len(targets)}건이 남았으나 **예산 소진 → 포기**",
                    "무한 재분석은 자율 탐색이 되어버린다 — 상한을 넘기지 않고 미해소로 보고한다")
        for sid, m, err in targets:
            log.block(f"미해소: {sid}.{m}", err[:160])
        log.end_stage(f"수리 {round_used}라운드 종료 — 미해소 {len(targets)}건")
        return {"repair_targets": []}

    log.reflect(f"수리 대상 {len(targets)}건 확정 → 라운드 {round_used + 1} 진입",
                "검증 실패 메시지를 프롬프트에 피드백해 해당 메서드만 재생성한다 "
                "(MatchFixAgent/ACToR 패턴: 검증·수리를 변환기와 분리)")
    for sid, m, err in targets:
        log.repair(f"{sid}.{m} 재생성 요청", err[:160])
    return {"repair_round": round_used + 1, "repair_targets": targets}


def route_after_repair_gate(state: PipelineState):
    targets = state.get("repair_targets") or []
    if not targets:
        return "scan_all"
    return _dispatch_repairs(targets, state)


def scan_all_node(state: PipelineState) -> dict:
    """Stage 4: 화면마다 run_review()를 그대로 호출한다(로직 변경 없음)."""
    log.stage(6, 7, "TOOL", "품질·취약점 스캔 — 검증기와 분리된 스캐너")
    results = {}
    n = 0
    for screen_id, screen_files in state.get("files", {}).items():
        results[screen_id] = run_review(screen_files, to_prefix(screen_id))
        n += sum(len(v) for v in results[screen_id].values())
    log.end_stage(f"품질 스캔 완료 — 화면 {len(results)}건, 지적 {n}건")
    return {"review_findings": results}


def _dispatch_ai_recommend_all(state: PipelineState) -> list[Send]:
    """Stage 5 대상(화면, nctRid) 조합을 전부 뽑아 병렬 디스패치한다. extract_dto_fields()로
    이미 계산돼 있던 요청/응답 필드 목록을 그대로 재사용한다(chatui/react_variant.py와 동일하게
    - 필드 재추출 없음).
    """
    from skeleton_gen import extract_dto_fields

    screens = state.get("screens", {})
    files_by_screen = state.get("files", {})
    sends = []
    for screen_id, buckets in screens.items():
        p_java = buckets.get("P", {}).get("java")
        if not p_java:
            continue
        entries = extract_dto_fields(p_java, buckets.get("F", {}).get("java"), buckets.get("P", {}).get("bizunit"))
        prefix = to_prefix(screen_id)
        api_java = files_by_screen.get(screen_id, {}).get(f"{prefix}Api.java")
        for entry in entries:
            sends.append(Send("ai_recommend_one", {
                "_screen_id": screen_id, "_p_method": entry["p_method"], "_nctrid": entry["nctrid"],
                "_request_fields": entry["request_fields"], "_response_fields": entry["response_fields"],
                "_api_java": api_java,
            }))
    return sends


def route_after_scan_all(state: PipelineState):
    if not state.get("include_ai_recommend", True):
        log.stage(7, 7, "DECIDE", "AI 추천 건너뜀 (opt-in 미선택)")
        log.end_stage("파이프라인 완료 — 사람 승인 대기")
        return END
    sends = _dispatch_ai_recommend_all(state)
    if not sends:
        log.stage(7, 7, "DECIDE", "AI 추천 대상 없음")
        log.end_stage("파이프라인 완료 — 사람 승인 대기")
        return END
    log.stage(7, 7, "TOOL", f"AI 추천 — {len(sends)}건 병렬 디스패치 (nctRid 단위, opt-in)")
    return sends


def ai_recommend_one_node(state: dict) -> dict:
    """Stage 5 병렬 실행 노드 - (화면, nctRid) 1개를 chatui/react_variant.recommend_react_variant()
    그대로 호출한다(로직 재구현 없음, LLM 호출 1회/nctRid)."""
    from react_variant import recommend_react_variant

    result = recommend_react_variant(
        screen_id=state["_screen_id"], p_method=state["_p_method"], nctrid=state["_nctrid"],
        request_fields=state["_request_fields"], response_fields=state["_response_fields"],
        api_java=state.get("_api_java"),
    )
    return {"ai_recommend_results": [(state["_screen_id"], state["_p_method"], result)]}


def build_pipeline_graph():
    builder = StateGraph(PipelineState)
    builder.add_node("plan_all", plan_all_node)
    builder.add_node("convert_all", convert_all_node)
    builder.add_node("port_one_screen_method", port_one_screen_method_node)
    builder.add_node("splice_all", splice_all_node)
    builder.add_node("validate_all", validate_all_node)
    builder.add_node("repair_gate", repair_gate_node)
    builder.add_node("repair_candidate", repair_candidate_node)
    builder.add_node("select_repair", select_repair_node)
    builder.add_node("scan_all", scan_all_node)
    builder.add_node("ai_recommend_one", ai_recommend_one_node)

    builder.add_edge(START, "plan_all")
    builder.add_edge("plan_all", "convert_all")
    builder.add_conditional_edges("convert_all", route_after_convert_all, ["port_one_screen_method", "validate_all"])
    builder.add_edge("port_one_screen_method", "splice_all")
    builder.add_conditional_edges("splice_all", route_after_splice_all, ["port_one_screen_method", "validate_all"])
    # validate_all은 이제 곧장 scan_all로 안 가고 항상 repair_gate를 거친다 - 방금 검증한 BLOCKER
    # 중 LLM이 포팅한 메서드에 귀속된 게 있으면(그리고 라운드 예산이 남으면) port_one_screen_method로
    # 되돌아가 오류만 고치게 하고, 그 결과는 splice_all -> validate_all로 다시 흘러 재검증된다
    # (2026-09-04 추가, MatchFixAgent/ACToR식 검증-수리 루프 - docs/06-mentor-feedback.md §D).
    builder.add_edge("validate_all", "repair_gate")
    builder.add_conditional_edges("repair_gate", route_after_repair_gate, ["repair_candidate", "scan_all"])
    # 수리 후보는 splice_all이 아니라 select_repair로 모인다 - 여러 후보를 그대로 겹쳐 쓰면
    # 서로를 덮어쓰기 때문에, 채점해서 하나만 고른 뒤 반영해야 한다.
    builder.add_edge("repair_candidate", "select_repair")
    builder.add_edge("select_repair", "validate_all")
    builder.add_conditional_edges("scan_all", route_after_scan_all, ["ai_recommend_one", END])
    builder.add_edge("ai_recommend_one", END)
    return builder.compile()


_PIPELINE_GRAPH = None


def get_pipeline_graph():
    global _PIPELINE_GRAPH
    if _PIPELINE_GRAPH is None:
        _PIPELINE_GRAPH = build_pipeline_graph()
    return _PIPELINE_GRAPH


# Stage 번호(1~5) <-> 실제 LangGraph 노드 이름 매핑 - app.py의 st.status() 스테퍼가 "지금 몇 번째
# 단계인지"를 노드 이름만 보고 알 수 있게 한다. port_one_screen_method/ai_recommend_one은 화면×
# 메서드/nctRid 단위로 여러 번 실행되므로 진행 카운터("N/M 완료")로 따로 집계한다(app.py 쪽 책임).
STAGE_BY_NODE = {
    "plan_all": (0, "변환 계획 수립"),
    "convert_all": (1, "1단계 규칙기반 변환"),
    "port_one_screen_method": (2, "2단계 LLM 포팅"),
    "splice_all": (2, "2단계 LLM 포팅"),
    "validate_all": (3, "정적 검증"),
    "repair_gate": (3, "정적 검증(수리 판단)"),
    "scan_all": (4, "품질·취약점 스캔"),
    "ai_recommend_one": (5, "AI 추천 변환 소스"),
}


def run_pipeline_part_a(
    screens: dict[str, dict],
    package_map: dict[str, tuple[str, str]],
    include_ai_recommend: bool = True,
    max_retries: int = 2,
    max_repair_retries: int = 2,
    repair_candidates_n: int = 2,
    all_paths: dict[str, dict] | None = None,
    progress_cb=None,
) -> PipelineState:
    """폴더 안 화면 전체를 1~5단계까지 LangGraph로 진행한다(저장 안 함 - 사람 승인 후 app.py가
    별도로 저장 + Part B(6~7단계)를 실행한다).

    progress_cb(node_name, partial_update)가 있으면 그래프가 노드를 하나 끝낼 때마다 호출된다 -
    app.py가 이걸로 st.status() 스테퍼를 실시간 갱신한다(STAGE_BY_NODE로 노드명 -> 단계 번호 매핑).
    반환값은 LangGraph가 리듀서로 정확히 합친 최종 state 전체다("values" 스트림 모드의 마지막
    항목을 그대로 씀 - 수동으로 다시 합치지 않는다, 리듀서 로직을 직접 흉내내면 실수하기 쉬움).

    max_repair_retries: 정적 검증에서 BLOCKER가 난 "LLM이 포팅한 메서드"를 다시 LLM에게 보여주고
    고치게 하는 라운드 수 상한(repair_gate_node 참고, 2026-09-04 추가) - 화면당이 아니라 그래프
    전체에서 공유하는 라운드 수라는 점이 max_retries(호출 실패 재시도)와 같다. 라운드마다 LLM
    호출이 추가로 늘어나니(수리 대상 메서드 수만큼) 기본값 2로 낮게 잡았다.
    """
    initial: PipelineState = {
        "screens": screens, "package_map": package_map, "all_paths": all_paths or {},
        "include_ai_recommend": include_ai_recommend, "max_retries": max_retries,
        "max_repair_retries": max_repair_retries,
        "port_results": [], "port_errors": [], "ported_methods": [], "ai_recommend_results": [],
        "repair_candidates": [], "repair_candidates_n": repair_candidates_n,
    }
    log.banner(
        "G-SCM 차세대 전환 Agent — 추론 로그",
        f"대상 화면 {len(screens)}건 · 수리 라운드 상한 {max_repair_retries} · "
        f"AI 추천 {'포함' if include_ai_recommend else '제외'}",
    )
    graph = get_pipeline_graph()
    final_state: PipelineState = dict(initial)  # type: ignore[assignment]
    for mode, chunk in graph.stream(initial, stream_mode=["updates", "values"]):
        if mode == "values":
            final_state = chunk
        elif progress_cb:
            for node_name, partial in chunk.items():
                progress_cb(node_name, partial)

    if log.enabled:
        n_block = sum(
            len([i for r in results for i in r.issues if i.severity == "BLOCKER"])
            for results in final_state.get("validation_results", {}).values()
        )
        est = [p.get("estimated_llm_calls", {}) for p in final_state.get("plans", {}).values()]
        rule_skipped = sum(e.get("porting_skipped_rule_based", 0) for e in est)
        llm_planned = sum(e.get("porting", 0) for e in est)
        denom = llm_planned + rule_skipped
        log.summary([
            ("처리 화면", f"{len(final_state.get('files', {}))}건"),
            ("생성 파일", f"{sum(len(f) for f in final_state.get('files', {}).values())}종"),
            ("LLM 포팅 호출", f"{llm_planned}건 (규칙 기반으로 회피 {rule_skipped}건"
                            + (f", 결정론 처리 비중 {rule_skipped * 100 // denom}%)" if denom else ")")),
            ("자기 수정 라운드", f"{final_state.get('repair_round', 0)}회"),
            ("잔여 BLOCKER", f"{n_block}건"),
            ("반영 여부", "미반영 — 사람이 '승인하고 저장'을 눌러야 산출물에 기록됨"),
        ])
    return final_state
