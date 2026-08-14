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


@dataclass
class ValidationResult:
    file_name: str
    check: str  # 예: JAVA_STATIC, MAPPER_XML, CROSS_LAYER_REF
    passed: bool
    issues: list[ValidationIssue] = field(default_factory=list)


def _check_brace_balance(java_text: str) -> list[ValidationIssue]:
    """문자열/문자 리터럴, 라인/블록 주석 안의 중괄호는 건너뛰고 짝을 맞춘다."""
    issues: list[ValidationIssue] = []
    depth = 0
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
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                issues.append(ValidationIssue(
                    issue_type="BRACE_MISMATCH", severity="BLOCKER",
                    message=f"{line}행 부근에서 짝이 맞지 않는 '}}'를 발견했습니다.",
                    line_no=line,
                ))
                depth = 0
        i += 1
    if depth > 0:
        issues.append(ValidationIssue(
            issue_type="BRACE_MISMATCH", severity="BLOCKER",
            message=f"닫히지 않은 중괄호 '{{'가 {depth}개 있습니다 - 이 파일은 컴파일되지 않습니다.",
        ))
    return issues


def _check_unspliced_markers(java_text: str) -> list[ValidationIssue]:
    issues = []
    for method in re.findall(r"// PORT_START:(\w+)", java_text):
        issues.append(ValidationIssue(
            issue_type="PORTING_INCOMPLETE", severity="WARNING",
            message=f"{method}가 아직 LLM 포팅되지 않고 스텁(UnsupportedOperationException) 상태입니다.",
        ))
    return issues


_SERVICE_CALL_RE = re.compile(r"service\.(\w+)\s*\(")
_STORE_CALL_RE = re.compile(r"store\.(\w+)\s*\(")
_METHOD_DEF_RE = re.compile(r"public\s+[\w<>\[\],\s]+?\s(\w+)\s*\(")
_MAPPER_REF_RE = re.compile(r'sqlSession\.\w+\(\s*"[\w]+\.(\w+)"')
_MAPPER_STMT_ID_RE = re.compile(r'<(?:select|insert|update|delete)\s+id="([^"]+)"')


def _defined_methods(java_text: str | None) -> set[str]:
    if not java_text:
        return set()
    return set(_METHOD_DEF_RE.findall(java_text))


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
        for called in sorted(set(_SERVICE_CALL_RE.findall(api_java))):
            if called not in service_methods:
                issues.append(ValidationIssue(
                    issue_type="UNRESOLVED_SERVICE_CALL", severity="BLOCKER",
                    message=f"Api가 호출하는 service.{called}(...)가 Service에 정의돼 있지 않습니다.",
                ))

    if service_java and store_java:
        for called in sorted(set(_STORE_CALL_RE.findall(service_java))):
            if called not in store_methods:
                issues.append(ValidationIssue(
                    issue_type="UNRESOLVED_STORE_CALL", severity="BLOCKER",
                    message=f"Service가 호출하는 store.{called}(...)가 Store에 정의돼 있지 않습니다.",
                ))

    if store_java and mapper_xml:
        for stmt in sorted(set(_MAPPER_REF_RE.findall(store_java))):
            if stmt not in mapper_ids:
                issues.append(ValidationIssue(
                    issue_type="MISSING_STATEMENT", severity="BLOCKER",
                    message=f"Store가 참조하는 매퍼 statement id '{stmt}'가 Mapper.xml에 없습니다.",
                ))
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

    seen: set[str] = set()
    for stmt_id in re.findall(r'<(?:select|insert|update|delete)\s+id="([^"]+)"', mapper_xml):
        if stmt_id in seen:
            issues.append(ValidationIssue(
                issue_type="DUPLICATE_STATEMENT_ID", severity="BLOCKER",
                message=f"statement id '{stmt_id}'가 중복 정의되어 있습니다 - MyBatis 로드 시 오류가 납니다.",
            ))
        seen.add(stmt_id)

    for m in re.finditer(r"[#$]\{", mapper_xml):
        if mapper_xml.find("}", m.end()) == -1:
            line_no = mapper_xml.count("\n", 0, m.start()) + 1
            issues.append(ValidationIssue(
                issue_type="UNCLOSED_BIND_EXPR", severity="BLOCKER",
                message=f"{line_no}행: '#{{'/'${{' 바인드 표현식이 닫히지 않았습니다.",
                line_no=line_no,
            ))
    return issues


def validate_java_file(file_name: str, java_text: str) -> ValidationResult:
    issues = _check_brace_balance(java_text) + _check_unspliced_markers(java_text)
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
