"""결정론적 규칙 기반 변환기: iBatis(XSQL) -> MyBatis, BizUnit -> Controller/Service/Store 골격.

CLAUDE.md 핵심 원칙: 결정론적으로 풀리는 변환에는 LLM을 쓰지 않는다. 이 모듈은 순수
정규식/문자열 치환이고 SQL·업무 로직 자체는 절대 바꾸지 않는다 - 문법만 바꾼다.

멘토 코멘트(docs/06-mentor-feedback.md §2) 규칙 그대로:
    #var# -> #{var},  $var$ -> ${var}
    <isEqual>/<isNotEqual>/<isNull>/<isNotNull>/<isGreaterThan> 등 -> <if test="...">
    <isNotEmpty>+<iterate> -> <if>+<foreach>
    <dynamic prepend="WHERE"> -> <where>,  <dynamic prepend="SET"> -> <set>
    <![CDATA[ ... ]]> 는 꼭 필요한 곳(안에 &/</> 같은 XML 예약문자가 실제로 있는 경우)에만 남긴다.
    MyBatis는 CDATA를 그대로 지원하니 그런 경우는 억지로 엔티티 이스케이프로 바꾸지 않는다 -
    특수문자가 하나도 없어서 애초에 CDATA가 불필요했던 블록만 벗겨내서 정리한다.

PLA047 화면 XSQL(3,405행)에서 실제로 검증된 것은 isEqual/isNotEqual/isNotEmpty+iterate 뿐이고
나머지 태그는 이번 화면엔 없어서 룰만 준비해뒀다 - 다른 화면에 적용할 때 결과를 반드시 확인할 것.

발견한 이슈는 문자열 경고가 아니라 ConversionIssue로 구조화해서 만든다 - tracking/conversion-verification.csv
나 DB(agents/db.py의 CONV_ISSUE 테이블)로 그대로 옮길 수 있게 하기 위함.
"""
from __future__ import annotations

import re
import xml.dom.minidom as minidom
from dataclasses import dataclass, field


@dataclass
class ConversionIssue:
    issue_type: str  # 예: TAG_MISMATCH, UNSUPPORTED_TAG, REMAPRESULTS_DROPPED, CDATA_SIMPLIFIED, XML_PARSE_ERROR
    severity: str  # BLOCKER | WARNING | INFO
    message: str
    line_no: int | None = None


@dataclass
class ConversionResult:
    mybatis_xml: str
    issues: list[ConversionIssue] = field(default_factory=list)

    @property
    def warnings(self) -> list[str]:
        """app.py 등에서 문자열 목록만 필요할 때 쓰는 뷰. issues가 원본이다."""
        return [i.message for i in self.issues]


_NUMERIC_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _compare_literal(value: str) -> str:
    """compareValue를 OGNL 리터럴로 만든다. 숫자면 그대로, 아니면 따옴표를 씌운다."""
    return value if _NUMERIC_RE.match(value) else f"'{value}'"


# --- 1) isNotEmpty(prepend="AND col", property="ARR_x") + iterate(...) -> if + foreach ------
_ISNOTEMPTY_ITERATE_RE = re.compile(
    r'<isNotEmpty\s+prepend="AND\s+([A-Za-z0-9_]+)"\s+property="([A-Za-z0-9_]+)"\s*>'
    r'\s*<iterate\s+prepend="IN"\s+property="\2"\s+open="\("\s+close="\)"\s+conjunction=","\s*>'
    r'\s*(?:<!\[CDATA\[\s*)?#\2\[\]#\s*(?:\]\]>\s*)?'
    r'</iterate>\s*</isNotEmpty>',
    re.DOTALL,
)


def _replace_isnotempty_iterate(text: str) -> str:
    def _sub(m: re.Match) -> str:
        col, arr = m.group(1), m.group(2)
        return (
            f'<if test="{arr} != null and {arr}.size() > 0">\n'
            f'    AND {col} IN\n'
            f'    <foreach item="item" collection="{arr}" open="(" close=")" separator=",">'
            f'#{{item}}</foreach>\n'
            f'</if>'
        )

    return _ISNOTEMPTY_ITERATE_RE.sub(_sub, text)


# --- 2) 단순 비교 태그: isEqual/isNotEqual/isGreaterThan/isGreaterEqual/isLessThan/isLessEqual --
# XML 속성값 안에서 <, &는 이스케이프해야 한다(>는 스펙상 필수는 아니지만 관례상 같이 이스케이프).
# isLessThan/isLessEqual을 &lt;/&lt;= 없이 그대로 넣으면(<if test="X < 5">) 안 닫힌 태그로
# 오인되어 파싱이 깨진다 - 실제로 겪은 버그라 항상 이스케이프한다.
_COMPARISON_OPS = {
    "isEqual": "==",
    "isNotEqual": "!=",
    "isGreaterThan": "&gt;",
    "isGreaterEqual": "&gt;=",
    "isLessThan": "&lt;",
    "isLessEqual": "&lt;=",
}


def _replace_comparison_tags(text: str) -> str:
    for tag, op in _COMPARISON_OPS.items():
        open_re = re.compile(rf'<{tag}\s+property="([A-Za-z0-9_.]+)"\s+compareValue="([^"]*)"\s*>')

        def _sub(m: re.Match, _op=op) -> str:
            prop, value = m.group(1), m.group(2)
            return f'<if test="{prop} {_op} {_compare_literal(value)}">'

        before = text
        text = open_re.sub(_sub, text)
        if before != text:
            text = re.sub(rf"</{tag}>", "</if>", text)
    return text


# --- 3) isNull / isNotNull -----------------------------------------------------------------
def _replace_null_tags(text: str) -> str:
    text = re.sub(
        r'<isNull\s+property="([A-Za-z0-9_.]+)"\s*>', r'<if test="\1 == null">', text
    )
    text = re.sub(r"</isNull>", "</if>", text)
    text = re.sub(
        r'<isNotNull\s+property="([A-Za-z0-9_.]+)"\s*>', r'<if test="\1 != null">', text
    )
    text = re.sub(r"</isNotNull>", "</if>", text)
    return text


# --- 4) isEmpty / isNotEmpty (단순형, iterate 없이 쓰인 경우) -------------------------------
def _replace_simple_empty_tags(text: str, issues: list[ConversionIssue]) -> str:
    for m in re.finditer(r'<isNotEmpty\s+prepend="([^"]*)"\s+property="([A-Za-z0-9_.]+)"\s*>', text):
        prepend, prop = m.group(1), m.group(2)
        line_no = text.count("\n", 0, m.start()) + 1
        issues.append(ConversionIssue(
            issue_type="UNSUPPORTED_TAG",
            severity="WARNING",
            line_no=line_no,
            message=(
                f'{line_no}행: <isNotEmpty prepend="{prepend}" property="{prop}"> - iterate 없이 쓰인 prepend 패턴은 '
                f"자동 변환 안 함(원본 유지). MyBatis는 prepend를 지원하지 않으니 <if>+<where> 조합으로 수동 변환 필요"
            ),
        ))
    text = re.sub(
        r'<isEmpty\s+property="([A-Za-z0-9_.]+)"\s*>',
        r'<if test="\1 == null or \1 == \'\'">',
        text,
    )
    text = re.sub(r"</isEmpty>", "</if>", text)
    return text


# --- 5) dynamic prepend="WHERE"/"SET" -> <where>/<set> -------------------------------------
def _replace_dynamic_tags(text: str) -> str:
    text = re.sub(r'<dynamic\s+prepend="WHERE"\s*>', "<where>", text)
    text = re.sub(r'<dynamic\s+prepend="SET"\s*>', "<set>", text)
    # 열린 태그가 where/set으로 바뀐 만큼, 대응하는 </dynamic>도 순서대로 닫아줘야 하는데
    # 정규식만으로는 어떤 </dynamic>이 어떤 open과 짝인지 확정할 수 없어 여기서는 처리하지 않는다.
    # (WHERE/SET 다이나믹을 쓴 화면이 나오면 그때 실제 구조를 보고 처리)
    return text


# --- 6) 남은 <iterate>(단독으로 쓰인 것) -> <foreach> ---------------------------------------
_STANDALONE_ITERATE_RE = re.compile(
    r'<iterate\s+property="([A-Za-z0-9_]+)"([^>]*)\s*>', re.DOTALL
)


def _replace_standalone_iterate(text: str) -> str:
    def _sub(m: re.Match) -> str:
        prop, rest = m.group(1), m.group(2)
        open_m = re.search(r'open="([^"]*)"', rest)
        close_m = re.search(r'close="([^"]*)"', rest)
        conj_m = re.search(r'conjunction="([^"]*)"', rest)
        attrs = [f'item="item"', f'collection="{prop}"']
        if open_m:
            attrs.append(f'open="{open_m.group(1)}"')
        if close_m:
            attrs.append(f'close="{close_m.group(1)}"')
        if conj_m:
            attrs.append(f'separator="{conj_m.group(1)}"')
        return f'<foreach {" ".join(attrs)}>'

    text = _STANDALONE_ITERATE_RE.sub(_sub, text)
    text = re.sub(r"</iterate>", "</foreach>", text)
    # #prop[]# -> #{item}  (foreach 내부 관례상 item으로 참조)
    text = re.sub(r"#[A-Za-z0-9_]+\[\]#", "#{item}", text)
    return text


# --- 7) 바인드 변수 / 텍스트치환 변수 ---------------------------------------------------------
def _replace_bind_vars(text: str) -> str:
    text = re.sub(r"#([A-Za-z_][A-Za-z0-9_]*)#", r"#{\1}", text)
    text = re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)\$", r"${\1}", text)
    return text


# CDATA 블록 안에 이게 있으면 정확성 버그다: <![CDATA[...]]> 안에서는 XML 파서가 <if>/<where>/
# <foreach>/<choose> 같은 태그를 더 이상 태그로 해석하지 않고 문자 그대로 취급한다. 앞선 단계에서
# isNotEmpty/isEqual/dynamic 등을 이 태그들로 막 변환했는데 그 결과가 CDATA 안에 남아있다면,
# 정적 XML 검증(well-formed)은 통과해도 실행 시점에 SQL 안에 태그 텍스트가 그대로 섞여 들어가는
# "빌드는 통과하는데 의미가 틀린" 버그가 된다 - 원본 iBatis에서도 이 조합은 애초에 동작하지
# 않았을 조합이라 실제로는 드물어야 하지만, 방어적으로 반드시 잡아낸다.
_DYNAMIC_TAG_MARKER_RE = re.compile(r"</?(?:if|where|foreach|choose|when|otherwise)\b")


# --- 8) CDATA 섹션 - 꼭 필요한 곳만 남기고 정리 ------------------------------------------------
def _strip_cdata(text: str, issues: list[ConversionIssue]) -> str:
    """<![CDATA[ ... ]]> 를 무조건 다 벗기지 않는다 - 안에 & < > 같은 XML 예약문자가 실제로 있어서
    CDATA가 진짜 필요한 블록은 그대로 둔다(MyBatis는 CDATA를 그대로 지원한다).

    특수문자가 하나도 없어서 애초에 CDATA로 감쌀 이유가 없었던 블록만 마커를 벗겨내고 일반
    텍스트로 정리한다 - 이 경우는 이스케이프도 필요 없다(벗겨낼 내용에 이스케이프 대상이 없으므로).

    예외: 그 블록 안에 우리가 방금 만든 동적 태그(<if>/<where>/<foreach>/<choose> 등)가 섞여
    있으면 CDATA로 남겨두면 안 된다(태그가 무력화됨) - 이 경우는 강제로 벗겨내고 이스케이프하되,
    사람이 반드시 확인하도록 BLOCKER를 남긴다.
    """
    stripped_count = 0
    kept_count = 0

    def _sub(m: re.Match) -> str:
        nonlocal stripped_count, kept_count
        inner = m.group(1)
        has_dynamic_tag = _DYNAMIC_TAG_MARKER_RE.search(inner)
        if has_dynamic_tag:
            line_no = text.count("\n", 0, m.start()) + 1
            issues.append(ConversionIssue(
                issue_type="DYNAMIC_TAG_INSIDE_CDATA",
                severity="BLOCKER",
                line_no=line_no,
                message=(
                    f"{line_no}행: CDATA 블록 안에 동적 태그(<if>/<where>/<foreach>/<choose> 등)가 "
                    "섞여 있습니다 - CDATA 안에서는 XML 파서가 이 태그를 해석하지 않고 문자 그대로 "
                    "취급해 실행 시점에 SQL이 깨집니다. 강제로 CDATA를 벗기고 특수문자만 이스케이프"
                    "했지만, 원본 구조 자체가 비정상일 수 있으니 반드시 원본과 대조해서 확인하세요."
                ),
            ))
            stripped_count += 1
            return inner.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if re.search(r"[&<>]", inner):
            kept_count += 1
            return m.group(0)  # 특수문자가 있어 CDATA가 실제로 필요함 - 그대로 유지
        stripped_count += 1
        return inner  # 특수문자 없음 - CDATA가 애초에 불필요했으므로 벗겨내도 안전

    result = re.sub(r"<!\[CDATA\[(.*?)\]\]>", _sub, text, flags=re.DOTALL)
    if stripped_count:
        issues.append(ConversionIssue(
            issue_type="CDATA_SIMPLIFIED",
            severity="INFO",
            message=(
                f"특수문자(&/</>)가 없어 불필요했던 CDATA 블록 {stripped_count}개를 일반 텍스트로 "
                f"정리했습니다. 특수문자가 있어 실제로 필요한 CDATA {kept_count}개는 MyBatis가 CDATA를 "
                "그대로 지원하므로 그대로 유지했습니다(엔티티 이스케이프로 억지 변환하지 않음)."
            ),
        ))
    return result


_KNOWN_REMAINING_TAGS = [
    "isEqual",
    "isNotEqual",
    "isGreaterThan",
    "isGreaterEqual",
    "isLessThan",
    "isLessEqual",
    "isNull",
    "isNotNull",
    "isEmpty",
    "isNotEmpty",
    "iterate",
    "dynamic",
]


def convert_xsql_fragment(xsql_text: str) -> ConversionResult:
    """XSQL(iBatis) 문자열 하나(<sql>/<select> 블록 등)를 MyBatis 문법으로 변환한다.

    SQL 자체(컬럼/조건/조인)는 절대 건드리지 않는다 - 태그와 바인드 변수 문법만 치환한다.
    """
    issues: list[ConversionIssue] = []
    text = xsql_text

    text = _replace_isnotempty_iterate(text)
    text = _replace_comparison_tags(text)
    text = _replace_null_tags(text)
    text = _replace_simple_empty_tags(text, issues)
    text = _replace_dynamic_tags(text)
    text = _replace_standalone_iterate(text)
    text = _replace_bind_vars(text)
    text = _strip_cdata(text, issues)

    for tag in _KNOWN_REMAINING_TAGS:
        m = re.search(rf"</?{tag}\b", text)
        if m:
            line_no = text.count("\n", 0, m.start()) + 1
            issues.append(ConversionIssue(
                issue_type="UNSUPPORTED_TAG",
                severity="WARNING",
                line_no=line_no,
                message=(
                    f"{line_no}행: <{tag}> 태그가 변환 후에도 남아있습니다(첫 등장 위치만 표시) - 자동 규칙이 "
                    f"이 화면의 실제 사용 패턴과 다를 수 있으니 원본과 대조해서 수동 확인하세요."
                ),
            ))

    # remapresults 등 iBatis 전용 속성은 MyBatis에 대응이 없어 제거하고 경고만 남긴다.
    if "remapresults" in text:
        issues.append(ConversionIssue(
            issue_type="REMAPRESULTS_DROPPED",
            severity="WARNING",
            message="remapresults 속성 발견 - MyBatis에 대응 기능 없음, 제거 예정. 결과 컬럼명 중복 여부 확인 필요",
        ))
        text = re.sub(r'\s*remapresults="[^"]*"', "", text)
    if 'parameterClass="' in text:
        text = text.replace('parameterClass="', 'parameterType="')
    if 'resultClass="hmap"' in text:
        text = text.replace('resultClass="hmap"', 'resultType="hashmap"')
    elif 'resultClass="' in text:
        text = re.sub(r'resultClass="([^"]*)"', r'resultType="\1"', text)

    xml_error, line_no = _check_well_formed(text)
    if xml_error:
        issues.append(ConversionIssue(
            issue_type="XML_PARSE_ERROR",
            severity="BLOCKER",
            line_no=line_no,
            message=(
                f"변환 결과가 유효한 XML이 아닙니다: {xml_error}. 원본 XSQL 자체의 태그 짝이 안 맞을 수 있습니다 "
                f"(문법 치환 규칙 문제가 아니라 원본 데이터 문제일 가능성이 높음) - 원본과 대조해서 확인하세요."
            ),
        ))

    return ConversionResult(mybatis_xml=text, issues=issues)


_LINE_NO_RE = re.compile(r"line (\d+)")


def _check_well_formed(text: str) -> tuple[str | None, int | None]:
    """변환 결과의 태그 짝이 맞는지 확인한다. 이 함수는 결과를 바꾸지 않고 (오류메시지, 줄번호)만 돌려준다.

    입력이 전체 문서(<?xml ...?>/<!DOCTYPE ...> 포함)든 <select> 하나짜리 조각이든 상관없이
    확인할 수 있도록, 선언부를 떼어내고 더미 루트로 감싸서 검사한다.
    """
    body = re.sub(r"<\?xml[^>]*\?>", "", text)
    body = re.sub(r"<!DOCTYPE[^>]*>", "", body)
    try:
        minidom.parseString(f"<root>{body}</root>".encode("utf-8"))
        return None, None
    except Exception as e:  # noqa: BLE001 - 사용자에게 그대로 보여줄 진단 메시지라 광범위하게 잡는다
        msg = str(e)
        m = _LINE_NO_RE.search(msg)
        # <root> 래퍼 한 줄을 앞에 안 붙였으므로(f-string이라 줄바꿈 없음) 원본 줄번호와 그대로 대응한다.
        return msg, (int(m.group(1)) if m else None)
