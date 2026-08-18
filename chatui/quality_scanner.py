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


def scan_mapper_sql_injection(mapper_xml: str) -> list[ConversionIssue]:
    """MyBatis `${...}`(문자열 그대로 치환, 바인드 아님)를 전부 찾아 잠재 SQL 인젝션 지점으로 표시한다.

    `#{...}`(파라미터 바인딩, 안전)와 달리 `${...}`는 값을 SQL 텍스트에 직접 끼워넣는다 - 그 값이
    외부 입력 경로를 타면 진짜 인젝션이 된다. 여기서는 값의 출처까지는 정적으로 알 수 없어서
    "위험 지점 후보"로만 표시하고 확정 판단은 사람이 한다.
    """
    issues: list[ConversionIssue] = []
    for m in _MYBATIS_TEXT_SUBST_RE.finditer(mapper_xml):
        var = m.group(1)
        line_no = mapper_xml.count("\n", 0, m.start()) + 1
        issues.append(ConversionIssue(
            issue_type="SQL_INJECTION_RISK", severity="WARNING", line_no=line_no,
            message=(
                f"{line_no}행: ${{{var}}}는 MyBatis에서 값을 SQL 텍스트에 그대로 치환한다(바인드 아님) - "
                f"이 값이 외부 입력 경로를 타면 SQL 인젝션 위험이 있다. 가능하면 #{{{var}}}(파라미터 "
                f"바인딩)로 바꿀 수 있는지 검토할 것."
            ),
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
    """
    issues: list[ConversionIssue] = []
    for m in _DEPRECATED_NEXCORE_API_RE.finditer(java_text):
        api_name = m.group(1)
        line_no = java_text.count("\n", 0, m.start()) + 1
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
        if found:
            result[service_name] = found

    store_name = f"{prefix}Store.java"
    if store_name in files:
        found = (
            scan_dynamic_sql_concat(files[store_name])
            + scan_hardcoded_credentials(files[store_name])
            + scan_deprecated_nexcore_calls(files[store_name])
        )
        if found:
            result[store_name] = found

    api_name = f"{prefix}Api.java"
    if api_name in files:
        found = scan_hardcoded_credentials(files[api_name]) + scan_deprecated_nexcore_calls(files[api_name])
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
