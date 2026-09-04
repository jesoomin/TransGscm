"""결정론적 규칙 기반 골격 생성기: P/F/D BizUnit 메서드 시그니처 -> Api/Service/Store 골격.

docs/07-tobe-structure.xlsx로 확정된 명명 규칙만 쓴다:
    P{화면} -> {Prefix}Api      (Controller/ 폴더)
    F{화면} -> {Prefix}Service  (service/ 폴더)
    D{화면} -> {Prefix}Store    (store/ 폴더)
패키지(com.skhynix.gscm.r.{p1}.{p2})의 p1/p2는 파일 내용만으로는 알 수 없어 UI에서 입력받는다.

메서드 "본문"은 채우지 않는다 - CLAUDE.md 원칙("스켈레톤 먼저, LLM은 빈 본문만 채운다")대로
시그니처까지만 규칙 기반으로 만들고, 실제 로직 포팅은 이 모듈이 하지 않는다(app.py의 LLM 단계에서).
"""
from __future__ import annotations

import hashlib
import re

from rule_port import detect_passthrough_query, render_passthrough_method
from dataclasses import dataclass, field

from converters import ConversionIssue, dto_name_for_method
from java_ast import extract_method_bodies, extract_methods  # noqa: F401 (재수출 - app.py가 여기서 import)


def method_body_hash(body: str) -> str:
    """메서드 본문의 공백 정규화 후 SHA-256 - agents/db.py의 CONV_METHOD.BODY_HASH,
    find_duplicate_methods()가 이 값으로 화면 간 동일/유사 로직을 묶는다. 공백만 다른(들여쓰기,
    줄바꿈) 메서드를 서로 다른 걸로 취급하지 않기 위해 정규화 후 해시한다.
    """
    normalized = re.sub(r"\s+", " ", body).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass
class SkeletonResult:
    files: dict[str, str] = field(default_factory=dict)
    issues: list[ConversionIssue] = field(default_factory=list)
    # D BizUnit의 dbSelect("S00N", ...) 호출에서 뽑은 {원본 statement id: D 메서드명} 매핑
    # (예: {"S001": "dPLA04701"}) - Mapper.xml의 <select id="S00N">을 D 메서드명 기준으로
    # 다시 붙이는 converters.finalize_mapper_document()에 그대로 넘겨서 쓴다.
    stmt_id_to_method: dict[str, str] = field(default_factory=dict)
    # 파일(CONV_FILE) 단위보다 한 단계 더 내려간 메서드 단위 레지스트리. 각 원소:
    # {"layer": "P"|"F"|"D", "method_name": AS-IS명, "method_name_tobe": TO-BE명(모르면 None),
    #  "body_hash": method_body_hash() 결과, "conversion_method": ..., "mapper_stmt_id": D만 해당}
    # agents/db.py의 CONV_METHOD에 그대로 적재한다(app.py가 file_id를 붙여서).
    methods: list[dict] = field(default_factory=list)
    # 콜그래프 엣지(P->F, F->D 위임). {"caller_layer","caller_method","callee_layer","callee_method"}.
    # agents/db.py의 CONV_METHOD_CALL에 적재해서 영향도 분석(콜그래프 역추적)에 쓴다.
    method_calls: list[dict] = field(default_factory=list)

    @property
    def warnings(self) -> list[str]:
        return [i.message for i in self.issues]


def to_prefix(screen_id: str) -> str:
    """PLA047 -> Pla047"""
    screen_id = screen_id.strip()
    return screen_id[:1].upper() + screen_id[1:].lower()


def tobe_relpath(filename: str, package_p1: str, package_p2: str) -> str:
    """docs/07-tobe-structure.xlsx로 확정된 TO-BE 폴더 구조에 맞는 상대경로를 만든다.

        gscm/src/main/java/com/skhynix/gscm/r/{p1}/{p2}/Controller/{화면}Api.java
        gscm/src/main/java/com/skhynix/gscm/r/{p1}/{p2}/dto/{화면}Dto.java
        gscm/src/main/java/com/skhynix/gscm/r/{p1}/{p2}/service/{화면}Service.java
        gscm/src/main/java/com/skhynix/gscm/r/{p1}/{p2}/store/{화면}Store.java
        gscm/src/main/resources/mapper/r/{p1}/{p2}/{화면}Mapper.xml

    CLAUDE.md AS-IS->TO-BE 매핑표 그대로: Controller만 대문자로 시작하고 dto/service/store는
    소문자다(엑셀 원본 표기 그대로, 임의로 통일하지 않음).
    """
    java_base = f"gscm/src/main/java/com/skhynix/gscm/r/{package_p1}/{package_p2}"
    if filename.endswith("Api.java"):
        return f"{java_base}/Controller/{filename}"
    if filename.endswith("Dto.java"):
        return f"{java_base}/dto/{filename}"
    if filename.endswith("Service.java"):
        return f"{java_base}/service/{filename}"
    if filename.endswith("Store.java"):
        return f"{java_base}/store/{filename}"
    if filename.endswith("Mapper.xml"):
        return f"gscm/src/main/resources/mapper/r/{package_p1}/{package_p2}/{filename}"
    # 알 수 없는 파일 종류는 추측해서 위치를 정하지 않고 루트에 그대로 둔다
    return filename


_BIZUNIT_METHOD_RE = re.compile(
    r'<method\s+id="([^"]+)"\s*>.*?<transactionId>([^<]*)</transactionId>', re.DOTALL
)

# extract_methods/extract_method_bodies는 java_ast.py로 옮겼다(tree-sitter 우선 + 정규식 폴백,
# 자세한 이유는 그 모듈 docstring 참고) - 위 import에서 재수출하므로 이 모듈을 쓰던 다른 코드는
# 그대로 skeleton_gen에서 import해도 동작한다.


def find_delegate_call(p_method_body: str, f_method_names: list[str]) -> str | None:
    """P 메서드 본문에서 실제로 호출하는 F 메서드 이름을 찾는다(있는 것만 신뢰, 추측 안 함).

    첫 번째로 매칭되는 이름 하나만 돌려준다 - Api 골격 생성은 "위임 대상 F 메서드 1개"만 있으면
    되기 때문. 메서드 하나가 여러 F/D 메서드를 호출하는 경우까지 전부 보려면 find_all_calls를 쓴다
    (agents/nctrid_graph.py의 콜그래프 빌더가 이 용도로 씀).
    """
    for name in f_method_names:
        if re.search(rf"\.{re.escape(name)}\s*\(", p_method_body):
            return name
    return None


def find_all_calls(method_body: str, candidate_names: list[str]) -> list[str]:
    """메서드 본문에서 실제로 호출되는 후보 메서드 이름을 전부(등장 순서대로) 찾는다.

    find_delegate_call은 "위임 대상 1개"만 필요한 골격 생성용이라 첫 매치에서 멈추지만, 콜그래프
    분석은 한 메서드가 여러 메서드를 호출하는 경우(계산/분기가 있는 F 메서드가 D 메서드를 2개 이상
    부르는 등)까지 전부 알아야 해서 이 함수를 따로 둔다.
    """
    found = []
    for name in candidate_names:
        if re.search(rf"\.{re.escape(name)}\s*\(", method_body):
            found.append(name)
    return found


def find_bare_calls(method_body: str, candidate_names: list[str]) -> list[str]:
    """메서드 본문에서 한정자 없이(같은 클래스 안의 메서드를 부르듯 `method(...)` 그대로, 앞에
    `.`이 없는 형태로) 호출되는 후보 이름을 찾는다.

    find_all_calls()는 `du.dXXX(...)`처럼 다른 객체를 거치는 계층 간 위임 호출만 잡도록
    일부러 `.` 뒤에 오는 이름만 본다 - 그래서 같은 클래스 안에서 서로를 부르는 경우(P가 다른
    P를, F가 다른 F를, D가 다른 D를 직접 호출)는 지금까지 콜그래프 어디에도 안 잡혔다
    (agents/impact_analysis.py에 명시된 알려진 한계). 이 함수가 그 빈자리를 메운다 - 앞에 '.'이
    오면(다른 객체의 동명 메서드) 제외해서 find_all_calls와 겹치지 않게 한다.
    """
    found = []
    for name in candidate_names:
        if re.search(rf"(?<!\.)\b{re.escape(name)}\s*\(", method_body):
            found.append(name)
    return found


def extract_d_stmt_ids(d_java_text: str) -> dict[str, str]:
    """D BizUnit 소스에서 {D 메서드명: dbSelect("S00N", ...)에 쓴 원본 statement id} 매핑을 뽑는다."""
    return dict(re.findall(r'(\w+)\s*\([^)]*?\)\s*\{\s*[^}]*?dbSelect\("(\w+)"', d_java_text, re.DOTALL))


# `dbSelect("S001", ...)` / `dbInsert("S010", ...)` 같은 호출에서 verb와 statement id를 같이 뽑는다.
# verb를 화이트리스트로 정해두지 않는 게 핵심이다 - 우리가 실제로 본 건 dbSelect뿐이라(PLA047:
# dbSelect 6개, 그 외 0개) 다른 verb가 어떤 이름으로 존재하는지 확인된 바가 없다. 있는 그대로
# 잡아서 "dbSelect가 아닌 게 나왔다"는 사실만 보고한다(CLAUDE.md: 확인 안 된 규칙은 추측 금지).
_DB_CALL_RE = re.compile(r'\bdb([A-Z]\w*)\s*\(\s*"(\w+)"')

SUPPORTED_DB_VERBS = frozenset({"Select"})


def extract_d_db_calls(d_java_text: str) -> dict[str, list[tuple[str, str]]]:
    """D BizUnit 메서드별로 본문에서 실제로 쓴 db*(...) 호출을 {메서드: [(verb, statement_id), ...]}로 뽑는다.

    `extract_d_stmt_ids()`는 dbSelect만 보지만, 이 함수는 verb를 가리지 않는다 - 이 변환기가 아직
    다루지 못하는 verb(dbInsert/dbUpdate/dbDelete 등)를 **변환 전에 이름을 붙여 드러내기** 위한
    용도다. 지원을 추측으로 만들어 넣지 않고, 미지원이라는 사실만 정확히 알린다.
    """
    calls: dict[str, list[tuple[str, str]]] = {}
    for method, body in extract_method_bodies(d_java_text).items():
        found = [(m.group(1), m.group(2)) for m in _DB_CALL_RE.finditer(body)]
        if found:
            calls[method] = found
    return calls


def unsupported_db_verbs(d_java_text: str | None) -> dict[str, list[str]]:
    """{D 메서드: 이 변환기가 못 다루는 verb 목록}. 전부 dbSelect면 빈 dict."""
    if not d_java_text:
        return {}
    result: dict[str, list[str]] = {}
    for method, calls in extract_d_db_calls(d_java_text).items():
        bad = sorted({verb for verb, _ in calls if verb not in SUPPORTED_DB_VERBS})
        if bad:
            result[method] = bad
    return result


# F BizUnit 메서드가 "D 메서드 하나 호출하고 recordset 하나를 그대로 응답에 담아 돌려주는" 순수
# 위임(delegation) 모양인지 판별한다. 예(실제 FPLA047 소스에서 확인):
#
#   public IDataSet fPLA047QrySelectRev(IDataSet requestData, IOnlineContext onlineCtx){
#       IDataSet responseData = new DataSet();
#       try{
#           DPLA047 du = (DPLA047) lookupDataUnit(DPLA047.class);
#           IRecordSet rs = du.dPLA04701(requestData, onlineCtx).getRecordSet("REV_LIST");
#           responseData.putRecordset("REV_LIST", rs);
#       } catch (BizRuntimeException be){ throw be; }
#       catch (Exception e){ throw new BizRuntimeException("E0052", e); }
#       return responseData;
#   }
#
# 이 모양이면 계산/분기 로직이 전혀 없으므로 LLM 포팅 없이 곧바로 Store 위임 한 줄로 옮길 수 있다:
#
#   public List<Pla04701Dto> pla04701(Pla04701Dto dto){ return pla047Store.dPLA04701(dto); }
#
# 정규식은 이 정확한 모양(lookupDataUnit 1회 + getRecordSet/putRecordset이 같은 이름 1쌍)만
# 매칭하고, 다른 statement가 하나라도 더 있으면(계산·분기·여러 D 메서드 호출 등) 매칭시키지
# 않는다 - 애매하면 기존 LLM 포팅 스텁으로 그대로 떨어지는 게 안전하다(추측으로 로직을 지어내지
# 않는다는 CLAUDE.md 원칙).
_SIMPLE_DELEGATION_RE = re.compile(
    r"""
    \{\s*
    IDataSet\s+(?P<resp>\w+)\s*=\s*new\s+DataSet\(\)\s*;\s*
    try\s*\{\s*
    \w+\s+(?P<du>\w+)\s*=\s*\(\s*\w+\s*\)\s*lookupDataUnit\(\s*\w+\.class\s*\)\s*;\s*
    IRecordSet\s+(?P<rs>\w+)\s*=\s*(?P=du)\s*\.\s*(?P<dmethod>\w+)\s*\(\s*\w+\s*,\s*\w+\s*\)\s*
        \.\s*getRecordSet\(\s*"(?P<rsname1>\w+)"\s*\)\s*;\s*
    (?P=resp)\s*\.\s*putRecordset\(\s*"(?P<rsname2>\w+)"\s*,\s*(?P=rs)\s*\)\s*;\s*
    \}\s*catch\s*\(\s*\w+\s+\w+\s*\)\s*\{\s*throw\s+\w+\s*;\s*\}\s*
    catch\s*\(\s*\w+\s+\w+\s*\)\s*\{\s*throw\s+new\s+\w+\([^;]*\)\s*;\s*\}\s*
    return\s+(?P=resp)\s*;\s*
    \}
    """,
    re.VERBOSE | re.DOTALL,
)


def detect_simple_delegation(f_body: str) -> str | None:
    """단순 위임 모양이면 위임 대상 D 메서드명(예: dPLA04701)을, 아니면 None을 돌려준다.

    getRecordSet/putRecordset의 recordset 이름이 서로 다르면(원본이 실제로 이름을 바꿔치기하는
    경우일 수 있어) 단순 위임으로 보지 않는다 - 안전한 쪽으로만 자동화한다.

    끝에 \\Z(문자열 끝)를 강제하지 않는다 - java_ast.extract_method_bodies가 파일에 문법 오류가
    있어 tree-sitter 경계를 못 쓰는 메서드는 정규식 근사치("다음 시그니처 전까지")로 경계를
    잡는데, 이때 메서드 진짜 닫는 중괄호 뒤에 다음 메서드의 JavaDoc 주석까지 같이 딸려온다
    (실측 확인: FPLA047.java의 fPLA047QrySelectRev가 실제로 이랬다) - 여기서 \\Z를 요구하면
    이런 흔한 케이스를 전부 놓친다. match()가 이미 시작 위치는 고정하므로, 끝은 열어둬도
    "본문 앞부분이 이 모양과 다르면 매칭 안 됨"이라는 안전성은 그대로 유지된다.
    """
    m = _SIMPLE_DELEGATION_RE.match(f_body.strip())
    if not m or m.group("rsname1") != m.group("rsname2"):
        return None
    return m.group("dmethod")


def strip_code_fence(text: str) -> str:
    """LLM이 하지 말라고 해도 ```java ... ``` 로 감싸서 줄 때가 있어 방어적으로 벗겨낸다."""
    text = text.strip()
    m = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text, re.DOTALL)
    return m.group(1) if m else text


def splice_ported_method(service_java: str, method: str, ported_body_code: str) -> str:
    """generate_skeletons가 만든 스텁(PORT_START/PORT_END 마커 사이)을 LLM이 포팅한 코드로 교체한다.

    마커를 못 찾으면(수동 편집 등으로 지워진 경우) 원본을 그대로 돌려주고 아무 것도 하지 않는다 -
    엉뚱한 위치에 잘못 끼워 넣는 것보다 안전하다.

    **교체 후에도 PORT_START/PORT_END 마커는 남긴다**(2026-09-04) - 마커를 지워버리면 이 함수가
    한 메서드에 대해 딱 한 번만 동작해서, 정적 검증 실패 후 다시 포팅시키는 수리 루프
    (agents/workflow_graph.repair_gate_node)의 결과가 조용히 버려진다(실측으로 확인). 마커는 Java
    주석이라 컴파일에 영향이 없고, "아직 포팅 안 된 스텁"인지 여부는 마커가 아니라 스텁 본문
    (UnsupportedOperationException)으로 판별한다(validators._check_unspliced_markers 참고).
    """
    pattern = re.compile(
        rf"    // PORT_START:{re.escape(method)}\n.*?    // PORT_END:{re.escape(method)}\n",
        re.DOTALL,
    )
    if not pattern.search(service_java):
        return service_java
    replacement = (
        f"    // PORT_START:{method}\n"
        f"    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)\n"
        f"{ported_body_code.rstrip()}\n"
        f"    // PORT_END:{method}\n"
    )
    return pattern.sub(lambda _m: replacement, service_java, count=1)


def extract_nctrid_map(bizunit_text: str) -> dict[str, str]:
    """.bizunit에서 method id -> transactionId(nctRid 또는 내부 트랜잭션 ID) 매핑을 뽑는다.

    XML 선언이 깨져 있어도(PLA047에서 실제로 겪음) 정규식이라 파싱 가능하다.
    """
    return {m.group(1): m.group(2) for m in _BIZUNIT_METHOD_RE.finditer(bizunit_text)}


_GETFIELD_RE = re.compile(r'\.getField\("([A-Za-z0-9_]+)"\)')
_PUTRECORDSET_RE = re.compile(r'\.putRecordset\("([A-Za-z0-9_]+)"')


def _snake_to_camel(name: str) -> str:
    parts = [p for p in name.split("_") if p]
    if not parts:
        return name.lower()
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def _snake_to_pascal(name: str) -> str:
    camel = _snake_to_camel(name)
    return camel[:1].upper() + camel[1:]


def extract_dto_fields(
    p_java_text: str,
    f_java_text: str | None,
    p_bizunit_text: str | None,
) -> list[dict]:
    """P 메서드(=nctRid 1개=엔드포인트 1개) 단위로 요청/응답 필드를 역추출한다.

    .BIZUNIT의 <fields/>가 비어있을 때 쓰는 대체 규칙(CLAUDE.md AS-IS->TO-BE 매핑표 참고):
    요청 필드는 P가 위임하는 F 메서드 본문의 `.getField("X")` 실사용값, 응답 필드는 P 메서드
    본문의 `.putRecordset("X", ...)` 실사용값에서 뽑는다. 추측하지 않고 코드에 없으면 issue로 남긴다.
    """
    entries: list[dict] = []
    p_methods = extract_methods(p_java_text)
    p_bodies = extract_method_bodies(p_java_text)
    f_methods = extract_methods(f_java_text) if f_java_text else []
    f_bodies = extract_method_bodies(f_java_text) if f_java_text else {}
    nctrid_map = extract_nctrid_map(p_bizunit_text) if p_bizunit_text else {}

    for p_method in p_methods:
        p_body = p_bodies.get(p_method, "")
        delegate = find_delegate_call(p_body, f_methods)
        request_fields: list[str] = []
        issues: list[str] = []
        if delegate:
            request_fields = sorted(set(_GETFIELD_RE.findall(f_bodies.get(delegate, ""))))
            if not request_fields:
                issues.append(
                    f"{delegate}에서 개별 getField 호출을 찾지 못했습니다 "
                    "(getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요."
                )
        else:
            issues.append(f"{p_method}의 delegate F 메서드를 찾지 못해 요청 필드를 추출하지 못했습니다.")
        response_fields = sorted(set(_PUTRECORDSET_RE.findall(p_body)))
        if not response_fields:
            issues.append(f"{p_method}에서 putRecordset 호출을 찾지 못했습니다 - 응답 필드를 수동으로 확인하세요.")
        entries.append({
            "p_method": p_method,
            "nctrid": nctrid_map.get(p_method, ""),
            "request_fields": request_fields,
            "response_fields": response_fields,
            "issues": issues,
        })
    return entries


def generate_dto(
    screen_id: str,
    package_p1: str,
    package_p2: str,
    p_java_text: str | None,
    f_java_text: str | None,
    p_bizunit_text: str | None,
) -> SkeletonResult:
    """nctRid(P 메서드)별 Request/Response 이너 클래스를 담은 `{화면}Dto.java`를 생성한다.

    필드 타입은 전부 String(응답 레코드셋은 List<Map<String, Object>>)으로 잠정 지정한다 -
    NEXCORE Dataset 컬럼의 실제 타입이 원본 어디에도 선언돼 있지 않아 추측하지 않기 위함이다.
    """
    result = SkeletonResult()
    prefix = to_prefix(screen_id)
    base_pkg = f"com.skhynix.gscm.r.{package_p1}.{package_p2}"

    if not p_java_text:
        result.issues.append(ConversionIssue(
            issue_type="MISSING_INPUT_FILE", severity="INFO",
            message="P(Java) 파일이 없어 Dto를 생성하지 않았습니다.",
        ))
        return result

    entries = extract_dto_fields(p_java_text, f_java_text, p_bizunit_text)
    if not entries:
        result.issues.append(ConversionIssue(
            issue_type="NO_METHODS_FOUND", severity="BLOCKER",
            message="P 파일에서 메서드를 찾지 못해 Dto를 생성하지 않았습니다.",
        ))
        return result

    lines = [
        f"package {base_pkg}.dto;",
        "",
        "import java.util.List;",
        "import java.util.Map;",
        "",
        "// .BIZUNIT의 <fields/>가 비어있어 AS-IS 코드의 getField/putRecordset 실사용값에서",
        "// 역추출했다(CLAUDE.md AS-IS->TO-BE 매핑표 참고). 필드 타입은 전부 String/List<Map<>>로",
        "// 잠정 지정했다 - 원본에 실제 타입이 선언돼 있지 않아 사람 확인이 필요하다.",
        f"public class {prefix}Dto {{",
        "",
    ]
    for entry in entries:
        p_method = entry["p_method"]
        nctrid = entry["nctrid"]
        class_base = _snake_to_pascal(nctrid) if nctrid and re.match(r"^[A-Za-z0-9_]+$", nctrid) else _snake_to_pascal(p_method)
        for msg in entry["issues"]:
            result.issues.append(ConversionIssue(
                issue_type="DTO_FIELD_EXTRACT_INCOMPLETE", severity="WARNING",
                message=f"{p_method}: {msg}", method_name=p_method,
            ))

        lines.append(f"    // ===== {nctrid or '(nctRid 미확인)'} ({p_method}) =====")
        lines.append(f"    public static class {class_base}Request {{")
        if entry["request_fields"]:
            for f in entry["request_fields"]:
                lines.append(f"        private String {_snake_to_camel(f)}; // AS-IS: {f}")
            lines.append("")
            for f in entry["request_fields"]:
                camel = _snake_to_camel(f)
                pascal = camel[:1].upper() + camel[1:]
                lines.append(f"        public String get{pascal}() {{ return {camel}; }}")
                lines.append(f"        public void set{pascal}(String {camel}) {{ this.{camel} = {camel}; }}")
        else:
            lines.append("        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것")
        lines.append("    }")
        lines.append("")

        lines.append(f"    public static class {class_base}Response {{")
        if entry["response_fields"]:
            for f in entry["response_fields"]:
                lines.append(f"        private List<Map<String, Object>> {_snake_to_camel(f)}; // AS-IS recordset: {f}")
            lines.append("")
            for f in entry["response_fields"]:
                camel = _snake_to_camel(f)
                pascal = camel[:1].upper() + camel[1:]
                lines.append(f"        public List<Map<String, Object>> get{pascal}() {{ return {camel}; }}")
                lines.append(f"        public void set{pascal}(List<Map<String, Object>> {camel}) {{ this.{camel} = {camel}; }}")
        else:
            lines.append("        // TODO: 응답 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것")
        lines.append("    }")
        lines.append("")
    lines.append("}")
    result.files[f"{prefix}Dto.java"] = "\n".join(lines)
    return result


def generate_skeletons(
    screen_id: str,
    package_p1: str,
    package_p2: str,
    p_java_text: str | None,
    f_java_text: str | None,
    d_java_text: str | None,
    p_bizunit_text: str | None,
) -> SkeletonResult:
    result = SkeletonResult()
    prefix = to_prefix(screen_id)
    base_pkg = f"com.skhynix.gscm.r.{package_p1}.{package_p2}"

    nctrid_map: dict[str, str] = {}
    if p_bizunit_text:
        nctrid_map = extract_nctrid_map(p_bizunit_text)
        if not nctrid_map:
            result.issues.append(ConversionIssue(
                issue_type="NCTRID_MAP_EMPTY",
                severity="WARNING",
                message=(
                    ".bizunit에서 <method>/<transactionId> 쌍을 찾지 못했습니다 "
                    "(XML이 심하게 깨져있거나 구조가 예상과 다를 수 있음) - Api 골격에 nctRid 주석이 비어있을 수 있습니다."
                ),
            ))

    f_methods_for_delegation = extract_methods(f_java_text) if f_java_text else []
    f_bodies_for_delegation = extract_method_bodies(f_java_text) if f_java_text else {}

    # F 메서드 원래 이름 -> (Service에 새로 붙일 이름, 위임 대상 D 메서드명). Api 생성과 Service
    # 생성 둘 다 이 매핑이 있어야 한다 - Service 메서드명이 바뀌면 Api가 부르는 이름도 같이
    # 바꿔야 컴파일이 되기 때문에 여기서 미리 한 번만 계산해서 공유한다.
    simple_delegations: dict[str, tuple[str, str]] = {}
    for f_method in f_methods_for_delegation:
        d_method = detect_simple_delegation(f_bodies_for_delegation.get(f_method, ""))
        if d_method:
            renamed = d_method[1:].lower() if d_method[:1].lower() == "d" else d_method.lower()
            simple_delegations[f_method] = (renamed, d_method)

    # ---- Api (Controller) ----
    if p_java_text:
        p_methods = extract_methods(p_java_text)
        p_bodies = extract_method_bodies(p_java_text)
        if not p_methods:
            result.issues.append(ConversionIssue(
                issue_type="NO_METHODS_FOUND", severity="BLOCKER",
                message="P 파일에서 `public IDataSet 메서드(...)` 시그니처를 찾지 못했습니다.",
            ))
        lines = [
            f"package {base_pkg}.Controller;",
            "",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "import org.springframework.http.ResponseEntity;",
            "import org.springframework.web.bind.annotation.*;",
            "",
        ]
        if simple_delegations:
            lines.append(f"import {base_pkg}.dto.*;")
            lines.append("import java.util.List;")
        lines += [
            "import java.util.Map;",
            "",
            f"// TODO: 원본 P BizUnit의 화면 검증 로직 유무를 다시 한번 확인할 것(PLA047은 순수 위임이었음, 다른 화면은 표본 확대 전)",
            f"@RestController",
            f'@RequestMapping("/api/{package_p1}/{package_p2}")',
            f"public class {prefix}Api {{",
            "",
            f"    @Autowired",
            f"    private {prefix}Service service;",
            "",
        ]
        for method in p_methods:
            nctrid = nctrid_map.get(method, "")
            # 메서드명이 전부 대문자 화면코드를 포함해서(pPLA04701) 일반적인 camelCase->kebab
            # 변환을 쓰면 글자마다 대시가 붙는 이상한 slug가 나온다. nctRid가 있으면 그걸 쓰고,
            # 없으면 화면 접두어를 떼어낸 나머지만 소문자로 slug화한다 - 둘 다 최종 URL 설계는
            # 사람이 확정해야 하는 자리라 주석에도 nctRid를 남겨 대조할 수 있게 한다.
            if nctrid:
                slug = nctrid.lower()
            else:
                stripped = re.sub(rf"^[a-z]{re.escape(screen_id)}", "", method, flags=re.IGNORECASE)
                slug = (stripped or method).lower()
            delegate = find_delegate_call(p_bodies.get(method, ""), f_methods_for_delegation)
            if delegate is None and f_methods_for_delegation:
                result.issues.append(ConversionIssue(
                    issue_type="DELEGATE_CALL_NOT_FOUND",
                    severity="WARNING",
                    message=(
                        f"{method}의 본문에서 F 메서드 호출을 찾지 못했습니다 - Api가 존재하지 않을 수도 있는 "
                        f"service.{method}(...)를 임시로 호출하도록 생성했습니다. 원본을 직접 대조해서 고치세요."
                    ),
                    method_name=method,
                ))
            result.methods.append({
                "layer": "P", "method_name": method, "method_name_tobe": method,
                "body_hash": method_body_hash(p_bodies.get(method, "")),
                "conversion_method": "RULE_BASED_SKELETON", "mapper_stmt_id": None,
                "nctrid": nctrid or None,
            })
            if delegate:
                result.method_calls.append({
                    "caller_layer": "P", "caller_method": method,
                    "callee_layer": "F", "callee_method": delegate,
                })
            call_target = delegate or method
            # delegate가 단순 위임 F 메서드면 Service 쪽 메서드명이 이미 D 메서드 기준으로 바뀌었으니
            # (예: fPLA047QrySelectRev -> pla04701) Api도 같은 이름으로 불러야 컴파일된다 - 동시에
            # 파라미터/응답 타입도 Map<String,Object> 대신 실제 DTO로 맞춘다.
            param_type, return_type, arg_name = "Map<String, Object>", "Map<String, Object>", "request"
            if delegate and delegate in simple_delegations:
                renamed, d_method = simple_delegations[delegate]
                call_target = renamed
                dto_name = dto_name_for_method(d_method)
                param_type, return_type, arg_name = dto_name, f"List<{dto_name}>", "dto"
            lines += [
                f"    // nctRid: {nctrid or '미확인 - .bizunit에서 못 찾음'}",
                f'    @PostMapping("/{slug}")',
                f"    public ResponseEntity<{return_type}> {method}(@RequestBody {param_type} {arg_name}) {{",
                f"        return ResponseEntity.ok(service.{call_target}({arg_name}));",
                f"    }}",
                "",
            ]
        lines.append("}")
        result.files[f"{prefix}Api.java"] = "\n".join(lines)
    else:
        result.issues.append(ConversionIssue(
            issue_type="MISSING_INPUT_FILE", severity="INFO",
            message="P(Java) 파일이 없어 Api 골격을 생성하지 않았습니다.",
        ))

    # ---- Service ----
    if f_java_text:
        f_methods = extract_methods(f_java_text)
        f_bodies = extract_method_bodies(f_java_text)
        if not f_methods:
            result.issues.append(ConversionIssue(
                issue_type="NO_METHODS_FOUND", severity="BLOCKER",
                message="F 파일에서 `public IDataSet 메서드(...)` 시그니처를 찾지 못했습니다.",
            ))

        # 순수 위임(F가 D 메서드 하나만 부르고 recordset을 그대로 돌려주는 모양, 계산/분기 없음)인
        # 메서드는 LLM 포팅 없이 곧바로 Store 위임 한 줄로 생성한다 - simple_delegations는 위
        # Api 생성 단계와 공유하는 {F 원래 이름: (새 이름, D 메서드명)} 매핑(detect_simple_delegation 참고).

        lines = [
            f"package {base_pkg}.service;",
            "",
            "import org.springframework.stereotype.Service;",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "",
        ]
        if simple_delegations:
            lines.append(f"import {base_pkg}.dto.*;")
        lines += [
            "import java.util.HashMap;",
            "import java.util.List;",
            "import java.util.Map;",
            "",
            f"@Service",
            f"public class {prefix}Service {{",
            "",
            f"    @Autowired",
            f"    private {prefix}Store store;",
            "",
        ]
        # 배관 규칙은 호출 대상이 실재할 때만 적용한다(rule_port.detect_passthrough_query 참고).
        known_d_methods = set(extract_methods(d_java_text)) if d_java_text else set()
        for method in f_methods:
            delegation = simple_delegations.get(method)
            body = f_bodies_for_delegation.get(method, "")
            if delegation:
                renamed, d_method = delegation
                dto_name = dto_name_for_method(d_method)
                lines += [
                    f"    // 원본 {method}가 {d_method} 하나만 호출하고 recordset을 그대로 돌려주는 단순",
                    f"    // 위임이라(계산/분기 없음) LLM 포팅 없이 규칙 기반으로 바로 옮겼다 - 원본과",
                    f"    // 다르게 동작한다고 판단되면 사람이 확인할 것.",
                    f"    public List<{dto_name}> {renamed}({dto_name} dto) {{",
                    f"        return store.{d_method}(dto);",
                    f"    }}",
                    "",
                ]
                result.methods.append({
                    "layer": "F", "method_name": method, "method_name_tobe": renamed,
                    "body_hash": method_body_hash(body),
                    "conversion_method": "RULE_BASED_DELEGATION", "mapper_stmt_id": None,
                })
                result.method_calls.append({
                    "caller_layer": "F", "caller_method": method,
                    "callee_layer": "D", "callee_method": d_method,
                })
                continue

            # 단순 위임은 아니지만 분기/계산이 전혀 없는 배관 패턴이면 여기서도 규칙 기반으로
            # 옮긴다(chatui/rule_port.py). 업무 로직(분기·산술)이 하나라도 있으면 잡히지 않고
            # 아래 LLM 포팅 경로로 내려간다 - 비중을 올리려고 로직까지 규칙으로 밀지 않는다.
            passthrough = detect_passthrough_query(body, known_d_methods)
            if passthrough:
                lines += render_passthrough_method(method, passthrough)
                result.methods.append({
                    "layer": "F", "method_name": method, "method_name_tobe": method,
                    "body_hash": method_body_hash(body),
                    "conversion_method": "RULE_BASED_PASSTHROUGH", "mapper_stmt_id": None,
                })
                result.method_calls.append({
                    "caller_layer": "F", "caller_method": method,
                    "callee_layer": "D", "callee_method": passthrough.d_method,
                })
                continue

            lines += [
                f"    // PORT_START:{method}",
                f"    // TODO(LLM 포팅 필요): 원본 F{screen_id}.{method}의 계산/분기 로직을 그대로 옮길 것.",
                f"    // NEXCORE 의존(IDataSet/IOnlineContext/lookupDataUnit)만 제거하고 로직은 새로 짜지 않는다.",
                f"    public Map<String, Object> {method}(Map<String, Object> request) {{",
                f"        throw new UnsupportedOperationException(\"TODO: {method} 포팅 필요\");",
                f"    }}",
                f"    // PORT_END:{method}",
                "",
            ]
            result.methods.append({
                "layer": "F", "method_name": method, "method_name_tobe": None,
                "body_hash": method_body_hash(body),
                "conversion_method": "LLM_PENDING", "mapper_stmt_id": None,
            })
        lines.append("}")
        result.files[f"{prefix}Service.java"] = "\n".join(lines)
    else:
        result.issues.append(ConversionIssue(
            issue_type="MISSING_INPUT_FILE", severity="INFO",
            message="F(Java) 파일이 없어 Service 골격을 생성하지 않았습니다.",
        ))

    # ---- Store ----
    if d_java_text:
        d_methods = extract_methods(d_java_text)
        d_bodies = extract_method_bodies(d_java_text)
        if not d_methods:
            result.issues.append(ConversionIssue(
                issue_type="NO_METHODS_FOUND", severity="BLOCKER",
                message="D 파일에서 `public IDataSet 메서드(...)` 시그니처를 찾지 못했습니다.",
            ))
        # dbSelect("S00N", ...) 호출에서 실제 매핑 statement id를 뽑아 Store가 참조할 수 있게 한다.
        # Mapper.xml의 <select id="S00N">은 converters.finalize_mapper_document()가 이 D 메서드명
        # 자체로 다시 붙이므로(예: S001 -> dPLA04701), Store도 처음부터 D 메서드명으로 참조한다.
        stmt_ids = extract_d_stmt_ids(d_java_text)
        result.stmt_id_to_method = {old_id: method for method, old_id in stmt_ids.items()}
        namespace = f"{base_pkg}.store.{prefix}Store"
        lines = [
            f"package {base_pkg}.store;",
            "",
            "import org.mybatis.spring.SqlSessionTemplate;",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "import org.springframework.stereotype.Repository;",
            "",
            "import java.util.Map;",
            "",
            f"// TODO: MyBatis 연동 방식(SqlSessionTemplate 직접 호출 vs @Mapper 인터페이스)이 아직 사내 컨벤션으로",
            f"// 확정되지 않아 SqlSessionTemplate 방식으로 임시 작성했다 - 실제 컨벤션 확인 후 조정할 것.",
            f"@Repository",
            f"public class {prefix}Store {{",
            "",
            f'    private static final String NS = "{namespace}.";',
            "",
            f"    @Autowired",
            f"    private SqlSessionTemplate sqlSession;",
            "",
        ]
        # 이 변환기가 못 다루는 verb(dbInsert/dbUpdate/dbDelete 등)를 쓰는 D 메서드를 먼저 잡아둔다.
        # 지금까지 확보한 원본(PLA047)이 전부 조회 전용이라 이 경로는 **한 번도 검증된 적이 없다** -
        # 그래서 지원을 추측으로 만들지 않고, 생성물에 주석 + BLOCKER 이슈로 이름 붙여 드러낸다
        # (멘토 코멘트 §6의 insert/update/delete 리스크와 같은 자리).
        bad_verbs = unsupported_db_verbs(d_java_text)
        for method in d_methods:
            stmt_id = method if method in stmt_ids else ""
            mapper_ref = f"NS + \"{stmt_id}\"" if stmt_id else f'NS + "TODO_확인필요_{method}"'
            if method in bad_verbs:
                verbs = ", ".join(f"db{v}" for v in bad_verbs[method])
                lines.append(
                    f"    // TODO(미지원 verb: {verbs}): 이 변환기는 dbSelect만 다룬다 - 아래 selectOne 호출은"
                )
                lines.append(
                    f"    // 맞지 않으니 사람이 insert/update/delete에 맞는 MyBatis 호출로 직접 고쳐야 한다."
                )
                result.issues.append(ConversionIssue(
                    issue_type="UNSUPPORTED_DB_VERB", severity="BLOCKER",
                    message=(
                        f"{method}가 {verbs}를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 "
                        "selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, "
                        "Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다."
                    ),
                    method_name=method,
                ))
            lines += [
                f"    public Map<String, Object> {method}(Map<String, Object> params) {{",
                f"        return sqlSession.selectOne({mapper_ref}, params);",
                f"    }}",
                "",
            ]
            result.methods.append({
                "layer": "D", "method_name": method, "method_name_tobe": method,
                "body_hash": method_body_hash(d_bodies.get(method, "")),
                "conversion_method": "RULE_BASED_SKELETON",
                "mapper_stmt_id": stmt_id or None,
            })
        lines.append("}")
        result.files[f"{prefix}Store.java"] = "\n".join(lines)
    else:
        result.issues.append(ConversionIssue(
            issue_type="MISSING_INPUT_FILE", severity="INFO",
            message="D(Java) 파일이 없어 Store 골격을 생성하지 않았습니다.",
        ))

    # ---- 콜그래프 완전성 보강 (2026-09-03, 영향도 분석 정확도 개선) ----
    # 위에서 method_calls에 넣은 엣지는 "코드 생성에 실제로 쓴" 단순 위임 1건뿐이다
    # (find_delegate_call/detect_simple_delegation - 첫 번째 매치에서 멈추거나 아예 특정 패턴만
    # 찾는다). 계산/분기가 있어 LLM 포팅이 필요한 메서드(대부분의 실제 업무 로직)는 이 위에서
    # method_calls에 아무 것도 안 남았다 - 예를 들어 F 메서드 하나가 D 메서드 4개를 부르는 경우
    # (실제 PLA047의 fPLA047QrySelectMainList) 이 골격 생성 로직만으로는 그 4개 호출 중 하나도
    # 기록되지 않는다. `agents/impact_analysis.py`의 미사용 함수 탐지가 이 콜그래프를 그대로 쓰기
    # 때문에, 엣지가 이렇게 비면 실제로는 호출되는 D 메서드가 "미사용"으로 오탐된다.
    #
    # 그래서 코드 생성과는 별개로, 실제로 존재하는 호출 전부를 find_all_calls()(계층 간,
    # `.method(` 패턴 - agents/nctrid_graph.py의 콜그래프 빌더와 동일 로직)와 find_bare_calls()
    # (같은 계층 내부, 한정자 없는 호출 - 지금까지 아무 데도 없던 신규 탐지)로 다시 훑어서
    # method_calls를 채운다. 위에서 이미 넣은 엣지와 겹치면 건너뛴다(중복 삽입 방지).
    p_methods_full = extract_methods(p_java_text) if p_java_text else []
    p_bodies_full = extract_method_bodies(p_java_text) if p_java_text else {}
    d_methods_full = extract_methods(d_java_text) if d_java_text else []
    d_bodies_full = extract_method_bodies(d_java_text) if d_java_text else {}

    _seen_edges = {
        (c["caller_layer"], c["caller_method"], c["callee_layer"], c["callee_method"])
        for c in result.method_calls
    }

    def _add_call_edge(caller_layer: str, caller_method: str, callee_layer: str, callee_method: str) -> None:
        key = (caller_layer, caller_method, callee_layer, callee_method)
        if key in _seen_edges:
            return
        _seen_edges.add(key)
        result.method_calls.append({
            "caller_layer": caller_layer, "caller_method": caller_method,
            "callee_layer": callee_layer, "callee_method": callee_method,
        })

    for method in p_methods_full:
        body = p_bodies_full.get(method, "")
        for f in find_all_calls(body, f_methods_for_delegation):
            _add_call_edge("P", method, "F", f)
        for sibling in find_bare_calls(body, [m for m in p_methods_full if m != method]):
            _add_call_edge("P", method, "P", sibling)

    for method in f_methods_for_delegation:
        body = f_bodies_for_delegation.get(method, "")
        for d in find_all_calls(body, d_methods_full):
            _add_call_edge("F", method, "D", d)
        for sibling in find_bare_calls(body, [m for m in f_methods_for_delegation if m != method]):
            _add_call_edge("F", method, "F", sibling)

    for method in d_methods_full:
        body = d_bodies_full.get(method, "")
        for sibling in find_bare_calls(body, [m for m in d_methods_full if m != method]):
            _add_call_edge("D", method, "D", sibling)

    return result
