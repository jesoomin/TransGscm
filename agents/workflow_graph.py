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
- **피드백 루프**: 지금 구현한 재시도는 "LLM 호출 자체가 실패한 메서드"(타임아웃/네트워크
  오류 등)만 `max_retries`(기본 2)까지 다시 시도하는 좁은 범위다. "정적 검증에서 BLOCKER가
  나온 코드를 LLM에게 다시 보여주고 고치게 하는" 수리 루프(Reflection)는 docs/06-mentor-feedback.md
  §J가 6번(LLM 파이프라인) 다음 7번으로 명시적으로 미룬 단계라 여기서 새로 만들지 않았다 -
  범위를 부풀려 말하지 않는다.
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
from skeleton_gen import (  # noqa: E402
    extract_method_bodies,
    extract_methods,
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


def _port_prompt(method: str, body: str) -> str:
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
        "완성된 메서드 코드 하나만 출력하고, 코드 펜스나 다른 설명은 붙이지 마라.\n\n"
        f"원본 메서드 본문:\n```\n{body}\n```"
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
    pending = extract_methods(f_java) if f_java and service_fname in files else []

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


def _merge_dicts(a: dict, b: dict) -> dict:
    """화면ID를 키로 쓰는 dict 필드용 리듀서. convert_all/validate_all/scan_all은 각각 단일
    노드라 실제로 동시 쓰기 충돌은 없지만, 재실행/체크포인트 재생 시에도 안전하게 합쳐지도록
    Annotated 리듀서로 선언해둔다.
    """
    return {**(a or {}), **(b or {})}


class PipelineState(TypedDict, total=False):
    # 입력 (읽기 전용)
    screens: dict[str, dict]  # {screen_id: {"P": {...}, "F": {...}, "D": {...}}} - agents/source_scan.scan_folder() 결과
    package_map: dict[str, tuple[str, str]]  # {screen_id: (package_p1, package_p2)}
    include_ai_recommend: bool
    max_retries: int

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

    # Stage 5 (ai_recommend_one: Send 병렬 (화면, nctRid) 단위)
    ai_recommend_results: Annotated[list[tuple[str, str, object]], operator.add]  # (screen_id, p_method, ReactVariantResult)


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

    return {
        "files": files, "skel_issues": skel_issues, "mapper_issues": mapper_issues, "dto_issues": dto_issues,
        "pending_methods": pending, "skel_methods": skel_methods, "skel_method_calls": skel_method_calls,
        "attempt_count": 0,
    }


def _dispatch_ports_all(screen_method_pairs: list[tuple[str, str]], state: PipelineState) -> list[Send]:
    """대상 (화면, F메서드) 조합을 전부 독립된 port_one_screen_method 실행으로 병렬 디스패치한다."""
    screens = state.get("screens", {})
    body_cache: dict[str, dict[str, str]] = {}
    sends = []
    for screen_id, method in screen_method_pairs:
        if screen_id not in body_cache:
            f_java = screens.get(screen_id, {}).get("F", {}).get("java") or ""
            body_cache[screen_id] = extract_method_bodies(f_java)
        sends.append(Send("port_one_screen_method", {
            "_screen_id": screen_id, "_method": method, "_method_body": body_cache[screen_id].get(method, ""),
        }))
    return sends


def route_after_convert_all(state: PipelineState):
    pairs = [(sid, m) for sid, methods in state.get("pending_methods", {}).items() for m in methods]
    if not pairs:
        return "validate_all"
    return _dispatch_ports_all(pairs, state)


def port_one_screen_method_node(state: dict) -> dict:
    """병렬 실행 노드 - (화면, 메서드) 조합 1개를 LLM Gateway에 보내 포팅한다. port_one_method_node와
    로직은 동일하고, 결과에 screen_id만 같이 실어 나른다(여러 화면이 섞여서 디스패치되므로)."""
    screen_id = state["_screen_id"]
    method = state["_method"]
    body = state["_method_body"]
    try:
        raw = chat(messages=[{"role": "user", "content": _port_prompt(method, body)}])
        return {"port_results": [(screen_id, method, strip_code_fence(raw))]}
    except Exception as e:  # LLM Gateway 타임아웃/네트워크 오류 등 - 코드 자체의 버그가 아니다
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
        spliced = splice_ported_method(screen_files[service_fname], method, code)
        if spliced != screen_files[service_fname]:
            newly_ported.append((screen_id, method))
        screen_files[service_fname] = spliced
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
    results = {}
    for screen_id, screen_files in state.get("files", {}).items():
        results[screen_id] = validate_screen(screen_files, to_prefix(screen_id))
    return {"validation_results": results}


def scan_all_node(state: PipelineState) -> dict:
    """Stage 4: 화면마다 run_review()를 그대로 호출한다(로직 변경 없음)."""
    results = {}
    for screen_id, screen_files in state.get("files", {}).items():
        results[screen_id] = run_review(screen_files, to_prefix(screen_id))
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
        return END
    sends = _dispatch_ai_recommend_all(state)
    return sends if sends else END


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
    builder.add_node("convert_all", convert_all_node)
    builder.add_node("port_one_screen_method", port_one_screen_method_node)
    builder.add_node("splice_all", splice_all_node)
    builder.add_node("validate_all", validate_all_node)
    builder.add_node("scan_all", scan_all_node)
    builder.add_node("ai_recommend_one", ai_recommend_one_node)

    builder.add_edge(START, "convert_all")
    builder.add_conditional_edges("convert_all", route_after_convert_all, ["port_one_screen_method", "validate_all"])
    builder.add_edge("port_one_screen_method", "splice_all")
    builder.add_conditional_edges("splice_all", route_after_splice_all, ["port_one_screen_method", "validate_all"])
    builder.add_edge("validate_all", "scan_all")
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
    "convert_all": (1, "1단계 규칙기반 변환"),
    "port_one_screen_method": (2, "2단계 LLM 포팅"),
    "splice_all": (2, "2단계 LLM 포팅"),
    "validate_all": (3, "정적 검증"),
    "scan_all": (4, "품질·취약점 스캔"),
    "ai_recommend_one": (5, "AI 추천 변환 소스"),
}


def run_pipeline_part_a(
    screens: dict[str, dict],
    package_map: dict[str, tuple[str, str]],
    include_ai_recommend: bool = True,
    max_retries: int = 2,
    progress_cb=None,
) -> PipelineState:
    """폴더 안 화면 전체를 1~5단계까지 LangGraph로 진행한다(저장 안 함 - 사람 승인 후 app.py가
    별도로 저장 + Part B(6~7단계)를 실행한다).

    progress_cb(node_name, partial_update)가 있으면 그래프가 노드를 하나 끝낼 때마다 호출된다 -
    app.py가 이걸로 st.status() 스테퍼를 실시간 갱신한다(STAGE_BY_NODE로 노드명 -> 단계 번호 매핑).
    반환값은 LangGraph가 리듀서로 정확히 합친 최종 state 전체다("values" 스트림 모드의 마지막
    항목을 그대로 씀 - 수동으로 다시 합치지 않는다, 리듀서 로직을 직접 흉내내면 실수하기 쉬움).
    """
    initial: PipelineState = {
        "screens": screens, "package_map": package_map,
        "include_ai_recommend": include_ai_recommend, "max_retries": max_retries,
        "port_results": [], "port_errors": [], "ported_methods": [], "ai_recommend_results": [],
    }
    graph = get_pipeline_graph()
    final_state: PipelineState = dict(initial)  # type: ignore[assignment]
    for mode, chunk in graph.stream(initial, stream_mode=["updates", "values"]):
        if mode == "values":
            final_state = chunk
        elif progress_cb:
            for node_name, partial in chunk.items():
                progress_cb(node_name, partial)
    return final_state
