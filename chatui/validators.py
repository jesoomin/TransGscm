"""검증기(Validator): 생성된 TO-BE 코드가 "실행 가능한 상태에 가까운지" 정적으로 확인한다.

CLAUDE.md 핵심 원칙: "변환기(Translator)와 검증기(Validator)는 분리한다 - 검증 로직이
변환 로직에 섞이면 변환기를 바꿀 때마다 검증 자산도 같이 깨진다." 이 모듈은
converters.py/skeleton_gen.py가 만든 결과물을 입력으로만 받고, 그 파일들을 절대 고치지 않는다.

이 개발 환경엔 실제 Maven/Spring 빌드(pom.xml, 의존성 jar)가 아직 없어서 진짜 `javac` 컴파일이나
Spring 컨텍스트 기동은 못 한다. 대신 지금 할 수 있는 정적 검증만 한다:
  - Java: 중괄호 균형(문자열/주석 인식), LLM 포팅이 안 끝나고 남은 PORT_START 스텁 탐지
  - 계층 간 실제 호출 대상 존재 확인: Api의 service.xxx() -> Service에 정의돼 있는지,
    Service의 store.xxx() -> Store에 정의돼 있는지, Store가 참조하는 매퍼 statement id ->
    Mapper.xml에 있는지
  - Mapper.xml: XML well-formed 여부, statement id 중복, #{..}/${..} 바인드 표현식 짝
PASS는 "돌아간다"가 아니라 "이 정적 검사를 통과했다"는 뜻이다 - 실제 실행 검증(차등 테스트)은
docs/02-architecture.md의 별도 단계다.
"""
from __future__ import annotations

import re
import xml.dom.minidom as minidom
from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    issue_type: str
    severity: str  # BLOCKER | WARNING | INFO
    message: str
    line_no: int | None = None
    method_name: str | None = None  # 특정 메서드에 귀속되면 채운다(agents/db.py record_issues의
    # method_id_by_name 연결에 씀, CONV_ISSUE.METHOD_ID) - 파일 전체 이슈는 None으로 둔다


@dataclass
class ValidationResult:
    file_name: str
    check: str  # 예: JAVA_STATIC, MAPPER_XML, CROSS_LAYER_REF
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)


def _brace_delta(java_text: str) -> int:
    """문자열/주석을 건너뛰고 (여는 중괄호 수 - 닫는 중괄호 수)를 센다.

    메서드 본문 조각 하나만 떼어 검사하는 용도다 - 조각의 delta가 양수면 그 조각 안에서 '{'가
    안 닫혔다는 뜻이라 "이 메서드가 범인"이라고 귀속시킬 수 있다. 파일 전체 스택 검사
    (_check_brace_balance)는 어느 메서드가 깨졌는지 구조적으로 알 수 없다 - 중괄호 하나가 빠지면
    그 뒤의 '}'들이 역할을 한 칸씩 당겨쓰게 돼서, 결국 미닫힘으로 남는 건 거의 항상 맨 바깥
    클래스 '{'가 되기 때문이다(2026-09-04 실측 확인).
    """
    delta = 0
    i = 0
    n = len(java_text)
    in_string = in_char = in_line_comment = in_block_comment = False
    while i < n:
        c = java_text[i]
        nxt = java_text[i + 1] if i + 1 < n else ""
        if c == "\n":
            in_line_comment = False
        if in_line_comment:
            i += 1
            continue
        if in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if in_char:
            if c == "\\":
                i += 2
                continue
            if c == "'":
                in_char = False
            i += 1
            continue
        if c == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if c == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if c == '"':
            in_string = True
        elif c == "'":
            in_char = True
        elif c == "{":
            delta += 1
        elif c == "}":
            delta -= 1
        i += 1
    return delta


def count_unbalanced_braces(java_text: str) -> int:
    """파일 전체에서 (여는 중괄호 - 닫는 중괄호) 개수. 0이면 균형이 맞는다.

    AS-IS 원본이 애초에 컴파일 안 되는 상태인지 싸게 판별하는 용도로 공개했다
    (agents/conversion_plan.py가 Refactor/Reimagine 트랙 판단 신호로 쓴다 - CLAUDE.md가
    "원본 자체가 이미 망가진 화면"을 Reimagine 후보로 명시한 그 기준).
    """
    return _brace_delta(java_text)


def _check_method_brace_balance(java_text: str) -> list[ValidationIssue]:
    """메서드별로 중괄호 균형을 따로 봐서 "어느 메서드가 깨졌는지"까지 짚어준다.

    delta > 0(그 메서드 조각 안에서 '{'가 안 닫힘)인 메서드만 범인으로 본다. delta < 0은
    무시한다 - 마지막 메서드 조각에는 클래스를 닫는 '}'가 딸려 들어와서 정상인데도 -1이 나오기
    때문이다(_method_line_ranges가 "다음 메서드 시그니처 직전까지"를 범위로 잡는 근사치라서).

    이 귀속이 있어야 CONV_ISSUE.METHOD_ID가 채워지고, 그래야
    agents/impact_analysis.find_error_methods()의 오류 함수 집계와
    agents/workflow_graph.repair_gate_node()의 수리 루프가 이 이슈를 대상으로 잡을 수 있다.
    """
    lines = java_text.split("\n")
    issues: list[ValidationIssue] = []
    for name, start, end in _method_line_ranges(java_text):
        chunk = "\n".join(lines[start - 1:end - 1])
        delta = _brace_delta(chunk)
        if delta > 0:
            issues.append(ValidationIssue(
                issue_type="BRACE_MISMATCH", severity="BLOCKER",
                message=(
                    f"{name} 메서드({start}행부터) 안에서 중괄호 '{{' {delta}개가 닫히지 않았습니다 - "
                    "이 파일은 컴파일되지 않습니다."
                ),
                line_no=start, method_name=name,
            ))
    return issues


def _check_brace_balance(java_text: str) -> list[ValidationIssue]:
    """문자열/문자 리터럴, 라인/블록 주석 안의 중괄호는 건너뛰고 짝을 맞춘다.

    닫히지 않은 '{'는 여는 위치를 스택으로 추적해서 정확히 몇 행에서 시작됐는지 알려준다 -
    "N개가 안 닫혔다"는 메시지만으로는 원본에서 어디를 봐야 할지 알 수 없기 때문이다.
    """
    issues: list[ValidationIssue] = []
    open_line_stack: list[int] = []
    i = 0
    n = len(java_text)
    line = 1
    in_string = in_char = in_line_comment = in_block_comment = False
    while i < n:
        c = java_text[i]
        nxt = java_text[i + 1] if i + 1 < n else ""
        if c == "\n":
            line += 1
            in_line_comment = False
        if in_line_comment:
            i += 1
            continue
        if in_block_comment:
            if c == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if in_char:
            if c == "\\":
                i += 2
                continue
            if c == "'":
                in_char = False
            i += 1
            continue
        if c == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if c == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if c == '"':
            in_string = True
            i += 1
            continue
        if c == "'":
            in_char = True
            i += 1
            continue
        if c == "{":
            open_line_stack.append(line)
        elif c == "}":
            if open_line_stack:
                open_line_stack.pop()
            else:
                issues.append(ValidationIssue(
                    issue_type="BRACE_MISMATCH", severity="BLOCKER",
                    message=f"{line}행에서 짝이 맞지 않는 '}}'를 발견했습니다.",
                    line_no=line,
                ))
        i += 1
    if open_line_stack:
        shown = open_line_stack[:5]
        more = f" 외 {len(open_line_stack) - 5}개" if len(open_line_stack) > 5 else ""
        lines_str = ", ".join(f"{ln}행" for ln in shown)
        # line_no는 가장 **안쪽**(마지막에 열린) 중괄호를 가리킨다. 예전엔 가장 바깥쪽
        # (open_line_stack[0])을 썼는데, 그건 거의 항상 `public class X {`(파일 1행)이라
        # _attribute_methods()가 어느 메서드에도 못 붙였다 - 그래서 CONV_ISSUE.METHOD_ID가 비고,
        # agents/impact_analysis.find_error_methods()와 수리 루프(workflow_graph.repair_gate_node)가
        # 정작 가장 흔한 BLOCKER인 이 이슈를 통째로 놓쳤다(2026-09-04 실측 확인). 메서드 본문에서
        # 중괄호가 빠지면 가장 안쪽 미닫힘이 그 메서드 안(또는 시그니처 줄)에 있으므로 훨씬
        # 정확하게 귀속된다. 전체 목록은 메시지에 그대로 남겨 정보는 잃지 않는다.
        issues.append(ValidationIssue(
            issue_type="BRACE_MISMATCH", severity="BLOCKER",
            message=(
                f"닫히지 않은 중괄호 '{{' {len(open_line_stack)}개가 있습니다(시작 위치: {lines_str}{more}) - "
                "이 파일은 컴파일되지 않습니다."
            ),
            line_no=open_line_stack[-1],
        ))
    return issues


def _check_unspliced_markers(java_text: str) -> list[ValidationIssue]:
    issues = []
    # 마커(PORT_START)가 아니라 **스텁 본문**으로 판별한다(2026-09-04) - 마커는 포팅 후에도
    # 남기도록 바뀌었기 때문(skeleton_gen.splice_ported_method 참고). 스텁일 때만 있는
    # `throw new UnsupportedOperationException("TODO: {메서드} 포팅 필요")`가 정확한 신호다.
    for m in re.finditer(r'UnsupportedOperationException\("TODO: (\w+) 포팅 필요"\)', java_text):
        line_no = java_text.count("\n", 0, m.start()) + 1
        issues.append(ValidationIssue(
            # BLOCKER인 이유(2026-09-05 WARNING에서 승격): 스텁이 남아 있으면 컴파일은 되지만
            # 런타임에 UnsupportedOperationException을 던진다 - "이 상태로는 정상 동작을 보장할 수
            # 없음"이라는 BLOCKER 정의에 정확히 해당한다. WARNING이던 동안에는 LLM 포팅이 전부
            # 실패해도 파이프라인 요약이 "잔여 BLOCKER 0건"으로 나와 성공처럼 읽혔다(추론 로그를
            # 붙이고 dry-run으로 돌려보다가 발견). 다만 이 이슈는 수리 루프 대상이 아니다 -
            # "포팅된 코드의 오류를 고치는 것"과 "포팅 자체가 안 된 것"은 다른 문제이고, 후자는
            # route_after_splice_all의 max_retries 재시도가 담당한다(_find_repairable_targets 참고).
            issue_type="PORTING_INCOMPLETE", severity="BLOCKER",
            message=f"{m.group(1)}가 아직 LLM 포팅되지 않고 스텁(UnsupportedOperationException) 상태입니다.",
            line_no=line_no, method_name=m.group(1),
        ))
    return issues


_SERVICE_CALL_RE = re.compile(r"service\.(\w+)\s*\(")
_STORE_CALL_RE = re.compile(r"store\.(\w+)\s*\(")
_METHOD_DEF_RE = re.compile(r"public\s+[\w<>\[\],\s]+?\s(\w+)\s*\(")
_MAPPER_REF_RE = re.compile(r'sqlSession\.\w+\(\s*"[\w]+\.(\w+)"')
_MAPPER_STMT_ID_RE = re.compile(r'<(?:select|insert|update|delete)\s+id="([^"]+)"')
# converters.py의 동일 이름 패턴과 같은 것 - 여기서 다시 정의하는 이유는 이 검증기가 converters.py의
# 변환 결과와 독립적으로 동작해야 하기 때문(CLAUDE.md "변환기/검증기 분리" 원칙, import로 결합하지 않음).
_DYNAMIC_TAG_MARKER_RE = re.compile(r"</?(?:if|where|foreach|choose|when|otherwise)\b")


def _defined_methods(java_text: str | None) -> set[str]:
    if not java_text:
        return set()
    return set(_METHOD_DEF_RE.findall(java_text))


def _method_line_ranges(java_text: str) -> list[tuple[str, int, int]]:
    """TO-BE Java 파일에서 메서드별 (이름, 시작행, 끝행) 근사 범위를 뽑는다 - 다음 메서드 정의
    직전까지를 그 메서드 범위로 본다(완벽한 AST 경계는 아니지만, 이슈를 어느 메서드에 귀속시킬지
    판단하는 용도로는 충분하다 - 이 검증기 자체가 애초에 정규식 기반이라는 설계와 같은 수준이다).
    """
    matches = list(_METHOD_DEF_RE.finditer(java_text))
    ranges: list[tuple[str, int, int]] = []
    for i, m in enumerate(matches):
        start_line = java_text.count("\n", 0, m.start()) + 1
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(java_text)
        end_line = java_text.count("\n", 0, end_pos) + 1
        ranges.append((m.group(1), start_line, end_line))
    return ranges


def _attribute_methods(issues: list[ValidationIssue], java_text: str) -> None:
    """line_no는 있는데 method_name이 아직 없는 이슈에, 그 줄이 속한 메서드 이름을 채운다(제자리
    수정). 이게 없으면 agents/db.py의 record_issues()가 CONV_ISSUE.METHOD_ID를 못 채우고,
    agents/impact_analysis.py의 find_error_methods()가 "어떤 함수가 문제인지" 아무 것도 못
    찾는다(2026-09-03 실제로 이렇게 비어있는 걸 확인하고 추가함).
    """
    ranges = _method_line_ranges(java_text)
    for issue in issues:
        if issue.method_name or not issue.line_no:
            continue
        for name, start, end in ranges:
            if start <= issue.line_no < end:
                issue.method_name = name
                break


def check_cross_layer_refs(
    api_java: str | None,
    service_java: str | None,
    store_java: str | None,
    mapper_xml: str | None,
) -> list[ValidationIssue]:
    """Api->Service->Store->Mapper 순으로 실제 호출 대상이 상대 계층에 있는지 대조한다.

    시그니처(파라미터/리턴 타입)까지 보는 진짜 컴파일이 아니라 "이름이 존재하는가" 수준이지만,
    골격 생성/포팅 과정에서 흔한 실수(오타, 연결 누락)는 이 정도로도 잡힌다.
    """
    issues: list[ValidationIssue] = []
    service_methods = _defined_methods(service_java)
    store_methods = _defined_methods(store_java)
    mapper_ids = set(_MAPPER_STMT_ID_RE.findall(mapper_xml)) if mapper_xml else set()

    if api_java and service_java:
        reported: set[str] = set()
        for m in _SERVICE_CALL_RE.finditer(api_java):
            called = m.group(1)
            if called in service_methods or called in reported:
                continue
            reported.add(called)
            line_no = api_java.count("\n", 0, m.start()) + 1
            issues.append(ValidationIssue(
                issue_type="UNRESOLVED_SERVICE_CALL", severity="BLOCKER",
                message=f"{line_no}행: Api가 호출하는 service.{called}(...)가 Service에 정의돼 있지 않습니다.",
                line_no=line_no,
            ))
        _attribute_methods([i for i in issues if i.issue_type == "UNRESOLVED_SERVICE_CALL"], api_java)

    if service_java and store_java:
        reported = set()
        for m in _STORE_CALL_RE.finditer(service_java):
            called = m.group(1)
            if called in store_methods or called in reported:
                continue
            reported.add(called)
            line_no = service_java.count("\n", 0, m.start()) + 1
            issues.append(ValidationIssue(
                issue_type="UNRESOLVED_STORE_CALL", severity="BLOCKER",
                message=f"{line_no}행: Service가 호출하는 store.{called}(...)가 Store에 정의돼 있지 않습니다.",
                line_no=line_no,
            ))
        _attribute_methods([i for i in issues if i.issue_type == "UNRESOLVED_STORE_CALL"], service_java)

    if store_java and mapper_xml:
        reported = set()
        for m in _MAPPER_REF_RE.finditer(store_java):
            stmt = m.group(1)
            if stmt in mapper_ids or stmt in reported:
                continue
            reported.add(stmt)
            line_no = store_java.count("\n", 0, m.start()) + 1
            issues.append(ValidationIssue(
                issue_type="MISSING_STATEMENT", severity="BLOCKER",
                message=f"{line_no}행: Store가 참조하는 매퍼 statement id '{stmt}'가 Mapper.xml에 없습니다.",
                line_no=line_no,
            ))
        _attribute_methods([i for i in issues if i.issue_type == "MISSING_STATEMENT"], store_java)
    return issues


def check_mapper_xml(mapper_xml: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    body = re.sub(r"<\?xml[^>]*\?>", "", mapper_xml)
    body = re.sub(r"<!DOCTYPE[^>]*>", "", body)
    try:
        minidom.parseString(f"<root>{body}</root>".encode("utf-8"))
    except Exception as e:  # noqa: BLE001 - 사용자에게 그대로 보여줄 진단 메시지라 광범위하게 잡는다
        msg = str(e)
        m = re.search(r"line (\d+)", msg)
        issues.append(ValidationIssue(
            issue_type="XML_PARSE_ERROR", severity="BLOCKER",
            message=f"유효한 XML이 아닙니다: {msg}",
            line_no=int(m.group(1)) if m else None,
        ))

    first_seen: dict[str, int] = {}
    for m in re.finditer(r'<(?:select|insert|update|delete)\s+id="([^"]+)"', mapper_xml):
        stmt_id = m.group(1)
        line_no = mapper_xml.count("\n", 0, m.start()) + 1
        if stmt_id in first_seen:
            issues.append(ValidationIssue(
                issue_type="DUPLICATE_STATEMENT_ID", severity="BLOCKER",
                message=(
                    f"{line_no}행: statement id '{stmt_id}'가 중복 정의되어 있습니다"
                    f"(처음 정의: {first_seen[stmt_id]}행) - MyBatis 로드 시 오류가 납니다."
                ),
                line_no=line_no,
            ))
        else:
            first_seen[stmt_id] = line_no

    for m in re.finditer(r"[#$]\{", mapper_xml):
        if mapper_xml.find("}", m.end()) == -1:
            line_no = mapper_xml.count("\n", 0, m.start()) + 1
            issues.append(ValidationIssue(
                issue_type="UNCLOSED_BIND_EXPR", severity="BLOCKER",
                message=f"{line_no}행: '#{{'/'${{' 바인드 표현식이 닫히지 않았습니다.",
                line_no=line_no,
            ))

    # 이중 안전장치: converters.py가 놓쳐도 여기서 다시 잡는다. CDATA 블록 안에 <if>/<where>/
    # <foreach>/<choose> 같은 동적 태그가 남아있으면 XML 파서가 그걸 문자 그대로 취급해서 실행
    # 시점에 SQL이 깨진다 - well-formed 검사만으로는 못 잡는 "빌드는 통과하는데 의미가 틀린" 버그.
    for m in re.finditer(r"<!\[CDATA\[(.*?)\]\]>", mapper_xml, flags=re.DOTALL):
        if _DYNAMIC_TAG_MARKER_RE.search(m.group(1)):
            line_no = mapper_xml.count("\n", 0, m.start()) + 1
            issues.append(ValidationIssue(
                issue_type="DYNAMIC_TAG_INSIDE_CDATA", severity="BLOCKER",
                message=(
                    f"{line_no}행: CDATA 블록 안에 동적 태그(<if>/<where>/<foreach>/<choose> 등)가 "
                    "남아있습니다 - CDATA 안에서는 태그로 해석되지 않고 문자 그대로 SQL에 섞여 들어갑니다."
                ),
                line_no=line_no,
            ))
    return issues


def validate_java_file(file_name: str, java_text: str) -> ValidationResult:
    # 메서드 단위로 범인을 짚을 수 있으면 그걸 쓰고(귀속 O), 못 짚으면 파일 전체 스택 검사
    # 결과를 쓴다(귀속 X). 둘 다 내보내면 같은 결함 하나가 BLOCKER 2건으로 세어져서 영향도
    # 대시보드의 위험도 점수가 부풀려진다 - 실제 결함 1개당 이슈 1건을 유지한다.
    method_level = _check_method_brace_balance(java_text)
    brace_issues = method_level if method_level else _check_brace_balance(java_text)
    issues = brace_issues + _check_unspliced_markers(java_text)
    _attribute_methods(issues, java_text)
    passed = not any(i.severity == "BLOCKER" for i in issues)
    return ValidationResult(file_name=file_name, check="JAVA_STATIC", passed=passed, issues=issues)


def validate_mapper_file(file_name: str, mapper_xml: str) -> ValidationResult:
    issues = check_mapper_xml(mapper_xml)
    passed = not any(i.severity == "BLOCKER" for i in issues)
    return ValidationResult(file_name=file_name, check="MAPPER_XML", passed=passed, issues=issues)


def validate_screen(files: dict[str, str], prefix: str) -> list[ValidationResult]:
    """generate_skeletons/generate_dto/convert_xsql_fragment가 만든 파일 dict 전체를 검증한다.

    파일별 개별 검증(중괄호 균형/XML well-formed/포팅 완료 여부) + 계층 간 교차 참조 검증을
    합쳐서 돌려준다. 입력 files/prefix는 읽기만 하고 수정하지 않는다.
    """
    results: list[ValidationResult] = []
    for fname, content in files.items():
        if fname.endswith(".xml"):
            results.append(validate_mapper_file(fname, content))
        elif fname.endswith(".java"):
            results.append(validate_java_file(fname, content))

    cross_issues = check_cross_layer_refs(
        files.get(f"{prefix}Api.java"),
        files.get(f"{prefix}Service.java"),
        files.get(f"{prefix}Store.java"),
        files.get(f"{prefix}Mapper.xml"),
    )
    results.append(ValidationResult(
        file_name="(계층 간 참조: Api→Service→Store→Mapper)",
        check="CROSS_LAYER_REF",
        passed=not any(i.severity == "BLOCKER" for i in cross_issues),
        issues=cross_issues,
    ))
    return results


def _find_local_mvn_and_java_home() -> tuple[str | None, str | None]:
    """PATH에 mvn/java가 없을 때 이 PC에 실제로 설치돼 있는 걸 찾는다(전역 설치 없이도 동작하게).

    2026-08-28 확인: 이 PC엔 `C:\\sqldeveloper\\jdk\\jre`에 SQL Developer가 번들로 깐 JDK 17
    (java/javac 둘 다 실제로 동작함, 이름은 jre지만 javac이 있어 완전한 JDK임)이 이미 있었고,
    Maven은 어디에도 없어서 공식 배포본(apache-maven-3.9.9)을 받아 `~/dev-tools/`에 풀어뒀다 -
    관리자 권한/설치 프로그램 없이 압축 풀기만으로 동작하는 방식을 택했다(전역 PATH도 안 건드림,
    다른 프로그램에 영향 없음). 여기서 그 두 경로를 안다.
    """
    import shutil
    from pathlib import Path

    mvn_bin = shutil.which("mvn") or shutil.which("mvn.cmd")
    if not mvn_bin:
        for candidate in (
            Path.home() / "dev-tools" / "apache-maven-3.9.9" / "bin" / "mvn.cmd",
            Path.home() / "dev-tools" / "apache-maven-3.9.9" / "bin" / "mvn",
        ):
            if candidate.exists():
                mvn_bin = str(candidate)
                break

    java_home = None
    if not (shutil.which("java") and shutil.which("javac")):
        for candidate in (Path("C:/sqldeveloper/jdk/jre"),):
            if (candidate / "bin" / "java.exe").exists() or (candidate / "bin" / "java").exists():
                java_home = str(candidate)
                break

    return mvn_bin, java_home


def check_maven_build(pom_path, timeout_sec: int = 300) -> ValidationResult:
    """`mvn -q compile`을 실제로 돌려서 진짜 javac 컴파일이 되는지 확인한다.

    validate_screen()의 나머지 검사와 달리 이건 파일 dict(메모리)가 아니라 디스크에 이미
    "저장"된 pilot/gscm 트리 전체를 대상으로 한다 - Maven은 모듈 단위로 빌드하지, 화면 하나만
    떼어서 컴파일할 수 없기 때문이다(여러 화면이 pilot/gscm 아래 한 트리로 합쳐지는 구조라
    화면별 저장이 끝날 때마다 이 검사를 다시 돌리면 그 시점까지 저장된 전체 화면이 같이
    컴파일된다).

    PATH에 mvn/java가 없으면 `_find_local_mvn_and_java_home()`으로 이 PC에 실제 설치된 걸
    찾아서 쓴다(2026-08-28부터 - 이전엔 PATH에 없으면 바로 포기하고 INFO만 남겼다). 그래도
    둘 다 못 찾으면 그때만 "코드가 잘못됐다"와 구분되는 INFO로 남긴다.
    """
    import os
    import subprocess

    pom_path = str(pom_path)
    mvn_bin, java_home = _find_local_mvn_and_java_home()
    if not mvn_bin:
        return ValidationResult(
            file_name="(Maven 빌드)", check="MAVEN_BUILD", passed=True,
            issues=[ValidationIssue(
                issue_type="MAVEN_NOT_AVAILABLE", severity="INFO",
                message=(
                    "이 PC의 PATH와 알려진 설치 위치(~/dev-tools/apache-maven-*)에서도 mvn을 "
                    "찾지 못해 실제 컴파일 검증을 건너뜁니다 - mvn을 설치한 뒤 이 버튼을 다시 누르세요."
                ),
            )],
        )

    env = os.environ.copy()
    if java_home:
        env["JAVA_HOME"] = java_home
        env["PATH"] = os.path.join(java_home, "bin") + os.pathsep + env.get("PATH", "")

    try:
        proc = subprocess.run(
            [mvn_bin, "-q", "-f", pom_path, "-DskipTests", "compile"],
            capture_output=True, text=True, timeout=timeout_sec, env=env,
        )
    except subprocess.TimeoutExpired:
        return ValidationResult(
            file_name="(Maven 빌드)", check="MAVEN_BUILD", passed=False,
            issues=[ValidationIssue(
                issue_type="MAVEN_TIMEOUT", severity="BLOCKER",
                message=f"mvn compile이 {timeout_sec}초 안에 끝나지 않았습니다(첫 실행은 의존성 다운로드로 느릴 수 있음 - 다시 시도해보세요).",
            )],
        )
    except Exception as e:  # noqa: BLE001 - mvn 실행 자체가 실패하는 경우(권한 등)도 BLOCKER로 남긴다
        return ValidationResult(
            file_name="(Maven 빌드)", check="MAVEN_BUILD", passed=False,
            issues=[ValidationIssue(issue_type="MAVEN_EXEC_ERROR", severity="BLOCKER", message=str(e))],
        )

    passed = proc.returncode == 0
    issues: list[ValidationIssue] = []
    if not passed:
        output = (proc.stdout or "") + (proc.stderr or "")
        # mvn -q는 성공하면 거의 조용하고 실패하면 [ERROR] 라인들에 실제 컴파일 에러가 담긴다.
        # Maven이 같은 에러 목록을 "COMPILATION ERROR" 섹션과 "Failed to execute goal" 섹션에
        # 두 번 반복해서 찍기 때문에(2026-08-28 실사용 확인 - 화면에서 똑같은 내용이 두 배로
        # 보여서 읽기 어렵다는 피드백) 중복 줄과 도움말 잡음("[Help 1]" 등)을 걸러낸다.
        _NOISE_MARKERS = (
            "[Help 1]", "To see the full stack trace", "Re-run Maven using the -X switch",
            "For more information about the errors",
        )
        seen: set[str] = set()
        error_lines: list[str] = []
        for ln in output.splitlines():
            if "[ERROR]" not in ln:
                continue
            stripped = ln.strip()
            if any(marker in stripped for marker in _NOISE_MARKERS) or not stripped:
                continue
            if stripped in seen:
                continue
            seen.add(stripped)
            error_lines.append(stripped)
        detail = "\n".join(error_lines) if error_lines else output[-4000:]
        issues.append(ValidationIssue(
            issue_type="MAVEN_COMPILE_FAILED", severity="BLOCKER",
            message=f"mvn compile 실패(exit {proc.returncode}):\n{detail}",
        ))
    return ValidationResult(file_name="(Maven 빌드)", check="MAVEN_BUILD", passed=passed, issues=issues)
