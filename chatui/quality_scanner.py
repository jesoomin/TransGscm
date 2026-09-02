"""코드 품질/취약점 분석기 - 변환기(converters.py/skeleton_gen.py), 검증기(validators.py)와는
또 다른 별도 단계다. 저 둘은 "변환이 되는가"/"실행 가능성이 있는가"를 보고, 이 모듈은 "포팅된
코드에 위험하거나 눈여겨봐야 할 패턴이 있는가"를 본다.

CLAUDE.md 원칙("결정론적으로 가능한 변환에는 LLM을 쓰지 않는다")과 같은 맥락에서, 규칙으로 잡을 수
있는 패턴(SQL 인젝션 위험, 원본 버그 집계)은 정규식으로만 처리하고 LLM은 쓰지 않는다. `llm_review()`
하나만 예외로 LLM을 쓰는데, 이건 "패턴 매칭으로 못 잡는 것"(가독성, 맥락상 위험)을 다루는 선택적
기능이라 기본은 꺼져있고 사람이 명시적으로 눌러야 실행된다 - 2단계 LLM 포팅과 같은 원칙.
"""
from __future__ import annotations

import re

from converters import ConversionIssue

_SQL_KEYWORDS_RE = re.compile(
    r"\b(SELECT|FROM|WHERE|CASE|WHEN|THEN|GROUP\s+BY|ORDER\s+BY|UNION|INSERT|UPDATE|DELETE|JOIN)\b",
    re.IGNORECASE,
)
_STRING_CONCAT_RE = re.compile(r'"[^"]*"\s*\+\s*\w')
_MYBATIS_TEXT_SUBST_RE = re.compile(r"\$\{([A-Za-z0-9_.]+)\}")
# ORDER BY/컬럼·테이블명 동적 치환은 NEXCORE 화면에서 아주 흔한 관용구고(값의 출처가 보통 코드
# 상수/고정 목록), 이런 것까지 매번 WARNING으로 잡으면 정말 봐야 할 항목이 노이즈에 묻힌다 -
# 변수명이 이 패턴과 끝나면 급을 낮춘다(휴리스틱, 확정 판정 아님 - 최종 판단은 사람이 한다).
_SAFE_DYNAMIC_NAME_RE = re.compile(
    r"(column|colname|order|sort|direction|table|tablename)$", re.IGNORECASE
)
# WHERE/AND/OR/LIKE/= 근처에서 쓰이면 검색조건에 값이 직접 섞여 들어간다는 뜻이라 실제 위험도가
# 높다 - 이런 조건절 문맥이 전혀 없는 나머지(예: SELECT 절 컬럼 나열)는 급을 낮춘다.
_CONDITION_CONTEXT_RE = re.compile(r"\b(WHERE|AND|OR|LIKE)\b|=\s*'?\$\{", re.IGNORECASE)
_FIXME_RE = re.compile(r"//\s*FIXME\(원본 버그\):\s*(.+)")
# 변수명에 password/secret/apikey류가 들어가고 오른쪽이 리터럴 문자열인 대입만 잡는다 - 값을 DB/설정에서
# 읽어오는 코드(getConfig(...) 등)는 매칭되지 않는다(false positive를 줄이려고 리터럴 대입만 본다).
_HARDCODED_CREDENTIAL_RE = re.compile(
    r'\b(\w*(?:password|passwd|pwd|secret|api[_]?key|access[_]?key)\w*)\s*=\s*"([^"]+)"',
    re.IGNORECASE,
)
# 포팅 후에도 NEXCORE 프레임워크 의존이 남아있으면 안 된다(CLAUDE.md 핵심 원칙: "NEXCORE 프레임워크
# 의존 코드는 Spring/MyBatis 방식으로 치환해야 한다") - 남아있으면 포팅이 불완전하다는 신호다.
_DEPRECATED_NEXCORE_API_RE = re.compile(
    r"\b(lookupFunctionUnit|lookupDataUnit|lookupProcessUnit|IOnlineContext|IDataSet|dbSelect|dbExecute)\b"
)
_TOBE_METHOD_SIG_RE = re.compile(r"public\s+[\w<>\[\],\s]+?\s(\w+)\s*\(")
# validators.py의 _METHOD_DEF_RE와 의도적으로 같은 패턴 - 두 모듈이 서로 import하지 않고 독립
# 동작해야 한다는 원칙(CLAUDE.md "변환기/검증기 분리"를 스캐너에도 같은 이유로 적용)이라 각자
# 따로 정의한다.


def _attribute_methods(issues: list[ConversionIssue], java_text: str) -> None:
    """line_no는 있는데 method_name이 없는 이슈에, 그 줄이 속한 메서드 이름을 채운다(제자리
    수정) - agents/db.py record_issues()가 CONV_ISSUE.METHOD_ID를 연결하는 데 쓴다. 이게 없으면
    agents/impact_analysis.py의 find_error_methods()(ORIGINAL_BUG 등 오류 함수 탐지)가 이 모듈이
    낸 이슈를 하나도 특정 메서드에 못 붙인다(2026-09-03 실제로 비어있는 걸 확인하고 추가함).
    """
    matches = list(_TOBE_METHOD_SIG_RE.finditer(java_text))
    ranges = []
    for i, m in enumerate(matches):
        start_line = java_text.count("\n", 0, m.start()) + 1
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(java_text)
        end_line = java_text.count("\n", 0, end_pos) + 1
        ranges.append((m.group(1), start_line, end_line))
    for issue in issues:
        if issue.method_name or not issue.line_no:
            continue
        for name, start, end in ranges:
            if start <= issue.line_no < end:
                issue.method_name = name
                break


def scan_mapper_sql_injection(mapper_xml: str) -> list[ConversionIssue]:
    """MyBatis `${...}`(문자열 그대로 치환, 바인드 아님)를 찾아 잠재 SQL 인젝션 지점으로 표시한다.

    `#{...}`(파라미터 바인딩, 안전)와 달리 `${...}`는 값을 SQL 텍스트에 직접 끼워넣는다 - 그 값이
    외부 입력 경로를 타면 진짜 인젝션이 된다. 다만 같은 변수가 한 Mapper에 수십~수백 번 등장하는
    경우가 흔해서(예: PLA047에서 339건) 발생 지점마다 개별 이슈로 뿌리면 정작 봐야 할 항목이
    파묻힌다 - 변수명 단위로 묶고, 조건절(WHERE/AND/OR/LIKE) 문맥에서 쓰였는지로 실제 위험도를
    가려 더 적고 더 신뢰할 수 있는 목록만 WARNING으로 남긴다(나머지는 INFO로 낮춰 보존).
    """
    lines = mapper_xml.split("\n")
    by_var: dict[str, list[int]] = {}
    for m in _MYBATIS_TEXT_SUBST_RE.finditer(mapper_xml):
        var = m.group(1)
        line_no = mapper_xml.count("\n", 0, m.start()) + 1
        by_var.setdefault(var, []).append(line_no)

    issues: list[ConversionIssue] = []
    for var, line_nos in by_var.items():
        in_condition = any(
            _CONDITION_CONTEXT_RE.search(lines[ln - 1]) for ln in line_nos if ln - 1 < len(lines)
        )
        looks_safe_name = bool(_SAFE_DYNAMIC_NAME_RE.search(var))
        severity = "WARNING" if (in_condition and not looks_safe_name) else "INFO"
        shown = line_nos[:5]
        line_desc = ", ".join(str(n) for n in shown)
        if len(line_nos) > 5:
            line_desc += f" 외 {len(line_nos) - 5}건"
        if severity == "WARNING":
            detail = (
                "조건절(WHERE/AND/OR/LIKE)에서 값이 SQL 텍스트에 직접 섞입니다 - 외부 입력 경로를 "
                f"타면 실제 인젝션으로 이어질 수 있습니다. 가능하면 #{{{var}}}(파라미터 바인딩)로 "
                "바꿀 수 있는지 우선 검토하세요."
            )
        else:
            detail = (
                "ORDER BY/컬럼·테이블명 동적 치환으로 보여 상대적으로 위험도가 낮게 분류했습니다 - "
                "값의 출처가 코드 상수/고정 목록이 아니라 외부 입력이라면 여전히 검토가 필요합니다."
            )
        issues.append(ConversionIssue(
            issue_type="SQL_INJECTION_RISK", severity=severity, line_no=line_nos[0],
            message=f"${{{var}}}가 {len(line_nos)}곳({line_desc}행)에서 발견됨: {detail}",
        ))
    return issues


def scan_dynamic_sql_concat(java_text: str) -> list[ConversionIssue]:
    """문자열 연결로 SQL 조각(SELECT/WHERE/CASE 등)을 조립하는 라인을 찾는다.

    실제로 이 프로젝트 FPLA047 포팅 결과에 `sCumSb.append(", CASE WHEN " + sListConvQty.get(i) + ...)`
    같은 패턴이 있다 - 값이 내부에서 계산된 것이라 지금 당장은 위험도가 낮을 수 있지만, 이런 조립 방식
    자체가 나중에 외부 입력이 섞여도 알아채기 어려운 구조라 후보로만 표시한다(확정 취약점 아님).
    """
    issues: list[ConversionIssue] = []
    for i, line in enumerate(java_text.split("\n"), start=1):
        if _STRING_CONCAT_RE.search(line) and _SQL_KEYWORDS_RE.search(line):
            issues.append(ConversionIssue(
                issue_type="DYNAMIC_SQL_STRING_CONCAT", severity="WARNING", line_no=i,
                message=(
                    f"{i}행: 문자열 연결로 SQL 조각을 조립하고 있다 - 값이 외부 입력에서 오는 경로가 "
                    f"있다면 SQL 인젝션 위험, 아니어도 유지보수 시 실수 유발 가능. 바인드 변수로 "
                    f"대체할 수 있는지 검토할 것."
                ),
            ))
    return issues


def scan_hardcoded_credentials(java_text: str) -> list[ConversionIssue]:
    """비밀번호/API 키로 보이는 변수에 문자열 리터럴이 직접 대입된 곳을 찾는다.

    BLOCKER로 잡는다 - 다른 스캔 결과(SQL 인젝션 후보 등)와 달리 이건 "즉시 사람이 확인해야
    하는" 성격이라, CLAUDE.md의 "원본 버그는 FIXME로 남기고 넘어간다" 원칙과 별개로 취급한다
    (자동 포팅 파이프라인이 조용히 지나치면 안 되는 항목).
    """
    issues: list[ConversionIssue] = []
    for m in _HARDCODED_CREDENTIAL_RE.finditer(java_text):
        var_name, value = m.group(1), m.group(2)
        line_no = java_text.count("\n", 0, m.start()) + 1
        issues.append(ConversionIssue(
            issue_type="HARDCODED_CREDENTIAL", severity="BLOCKER", line_no=line_no,
            message=(
                f"{line_no}행: {var_name}에 문자열이 그대로 대입되어 있습니다 - 비밀번호/키로 보이는 "
                "값이 하드코딩됐을 수 있습니다. 즉시 사람이 확인해서 설정 파일/시크릿 저장소로 옮길지 "
                "판단하세요(원본 버그라도 FIXME로 넘기지 않고 이 항목은 바로 검토 대상입니다)."
            ),
        ))
    return issues


def scan_deprecated_nexcore_calls(java_text: str) -> list[ConversionIssue]:
    """포팅됐어야 할 Java 파일에 NEXCORE 프레임워크 의존이 아직 남아있는지 찾는다.

    CLAUDE.md 핵심 원칙: "NEXCORE 프레임워크 의존 코드(IDataSet/IOnlineContext/lookupFunctionUnit
    등)는 Spring/MyBatis 방식으로 치환해야 한다." 이게 남아있다는 건 포팅이 불완전하다는 신호다 -
    validators.py의 계층 간 참조 체크와는 다른 각도(그쪽은 "존재하는 대상을 부르는가", 이쪽은
    "애초에 있으면 안 되는 게 남아있는가")라 여기서 별도로 잡는다.

    주석 라인은 건너뛴다(2026-09-03 발견) - `skeleton_gen.py`가 LLM 포팅 전 스텁마다 남기는
    TODO 주석 자체가 "NEXCORE 의존(IDataSet/IOnlineContext/lookupDataUnit)만 제거하고..."처럼
    이 API 이름들을 문자 그대로 언급한다. 주석까지 코드로 잡으면 아직 포팅 안 된 스텁 메서드마다
    전부 오탐이 뜬다(실 PLA047로 재현 확인) - 실제로는 아무 코드도 없는데 "NEXCORE 의존이
    남아있다"는 의미 없는 경고만 쌓인다.
    """
    issues: list[ConversionIssue] = []
    for line_no, line in enumerate(java_text.split("\n"), start=1):
        if line.strip().startswith("//"):
            continue
        for m in _DEPRECATED_NEXCORE_API_RE.finditer(line):
            api_name = m.group(1)
            issues.append(ConversionIssue(
                issue_type="DEPRECATED_NEXCORE_API", severity="WARNING", line_no=line_no,
                message=(
                    f"{line_no}행: NEXCORE 프레임워크 의존({api_name})이 아직 남아있습니다 - 포팅이 "
                    "불완전할 수 있습니다. Spring/MyBatis 방식으로 치환됐는지 확인하세요."
                ),
            ))
    return issues


def aggregate_original_bugs(service_java: str) -> list[ConversionIssue]:
    """포팅 시 `// FIXME(원본 버그): ...`로 표시해둔 것들을 모아 화면 단위 리포트로 만든다.

    개별 버그 자체는 포팅 단계에서 이미 고치지 않고 보존+표시했다(CLAUDE.md 원칙) - 여기서는
    흩어진 FIXME를 한곳에 모아서 "이 화면에 원본 버그가 몇 건, 어디에 있는지" 한눈에 보이게 한다.
    """
    issues: list[ConversionIssue] = []
    for m in _FIXME_RE.finditer(service_java):
        line_no = service_java.count("\n", 0, m.start()) + 1
        issues.append(ConversionIssue(
            issue_type="ORIGINAL_BUG", severity="INFO", line_no=line_no,
            message=f"{line_no}행: 원본 버그(포팅 시 보존, 임의 수정 안 함) - {m.group(1).strip()}",
        ))
    return issues


def run_review(files: dict[str, str], prefix: str) -> dict[str, list[ConversionIssue]]:
    """generate_skeletons/convert_xsql_fragment 등이 만든 파일 dict를 규칙 기반으로 스캔한다.

    반환값은 {파일명: [ConversionIssue, ...]} - app.py의 다른 이슈 목록들과 같은 방식으로
    DB(CONV_ISSUE, detected_by='chatui/quality_scanner.py')에 그대로 넣을 수 있다.
    """
    result: dict[str, list[ConversionIssue]] = {}

    mapper_name = f"{prefix}Mapper.xml"
    if mapper_name in files:
        found = scan_mapper_sql_injection(files[mapper_name])
        if found:
            result[mapper_name] = found

    service_name = f"{prefix}Service.java"
    if service_name in files:
        service_java = files[service_name]
        found = (
            scan_dynamic_sql_concat(service_java)
            + scan_hardcoded_credentials(service_java)
            + scan_deprecated_nexcore_calls(service_java)
            + aggregate_original_bugs(service_java)
        )
        _attribute_methods(found, service_java)
        if found:
            result[service_name] = found

    store_name = f"{prefix}Store.java"
    if store_name in files:
        found = (
            scan_dynamic_sql_concat(files[store_name])
            + scan_hardcoded_credentials(files[store_name])
            + scan_deprecated_nexcore_calls(files[store_name])
        )
        _attribute_methods(found, files[store_name])
        if found:
            result[store_name] = found

    api_name = f"{prefix}Api.java"
    if api_name in files:
        found = scan_hardcoded_credentials(files[api_name]) + scan_deprecated_nexcore_calls(files[api_name])
        _attribute_methods(found, files[api_name])
        if found:
            result[api_name] = found

    return result


def llm_review(java_text: str) -> str:
    """선택적 LLM 코드 리뷰 - 규칙으로 못 잡는 가독성/맥락상 위험을 짧은 불릿으로 지적만 한다.

    코드를 수정하지 않는다(포팅과 다른 목적). 기본으로 자동 실행되지 않고, UI에서 사람이 명시적으로
    눌러야 호출된다(LLM Gateway 비용 발생 + CLAUDE.md "LLM은 명시된 영역에만" 원칙).
    """
    from agents.llm_gateway import chat

    prompt = (
        "다음은 NEXCORE BizUnit에서 Spring 서비스로 포팅된 Java 코드다. 코드를 절대 고치지 말고, "
        "가독성/잠재적 버그/보안(특히 SQL 인젝션, null 처리)/성능 관점에서 우려되는 부분만 "
        "짧은 한국어 불릿 목록으로 지적해라. 이미 `// FIXME(원본 버그)`로 표시된 부분은 반복해서 "
        "언급하지 말고, 그 외에 새로 발견한 것만 말해라. 특별히 지적할 게 없으면 '특이사항 없음'이라고만 답해라.\n\n"
        f"```java\n{java_text}\n```"
    )
    return chat(messages=[{"role": "user", "content": prompt}])
