"""결정론적 규칙 기반 변환기: iBatis(XSQL) -> MyBatis, BizUnit -> Controller/Service/Store 골격.

CLAUDE.md 핵심 원칙: 결정론적으로 풀리는 변환에는 LLM을 쓰지 않는다. 이 모듈은 순수
정규식/문자열 치환이고 SQL·업무 로직 자체는 절대 바꾸지 않는다 - 문법만 바꾼다.

멘토 코멘트(docs/06-mentor-feedback.md §2) 규칙 그대로:
    #var# -> #{var},  $var$ -> ${var}
    <isEqual>/<isNotEqual>/<isNull>/<isNotNull>/<isGreaterThan> 등 -> <if test="...">
    (isEqual/isNotEqual이 문자열과 비교할 때는 PROP == 'VALUE'가 아니라 "VALUE".equals(PROP)
     스타일로 만든다 - PROP가 null이어도 안전하고, 이 프로젝트 Mapper.xml 전체 관례와도 맞다)
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
    method_name: str | None = None  # 이슈가 특정 메서드에 귀속되면 AS-IS 메서드명(agents/db.py의
    # CONV_ISSUE.METHOD_ID 연결에 씀) - 파일 전체 이슈(XML 파싱 오류 등)는 None으로 둔다


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


def _compare_literal_dquote(value: str) -> str:
    """.equals() 스타일에서 쓸 문자열 리터럴 - 큰따옴표로 감싼다.

    <if> 태그의 속성 구분자는 작은따옴표(test='...')를 쓰기로 했으므로(이 프로젝트 Mapper.xml
    관례, 예: <if test='"UPPER2".equals(SRCTYPE)'>), 안쪽 OGNL 문자열 리터럴은 큰따옴표를 쓴다.
    """
    return f'"{value}"'


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
        # 이 프로젝트 Mapper.xml 전체 관례(ARR_TECH_CD != null and ARR_TECH_CD != "")를 따른다 -
        # List.size() > 0가 아니라 != ""로 빈 상태를 확인한다(원본 XSQL 화면들에서 실제로 쓰던 형태).
        return (
            f"<if test='{arr} != null and {arr} != \"\"'>\n"
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


def _replace_comparison_tags(text: str, issues: list[ConversionIssue]) -> str:
    for tag, op in _COMPARISON_OPS.items():
        open_re = re.compile(rf'<{tag}\s+property="([A-Za-z0-9_.]+)"\s+compareValue="([^"]*)"\s*>')

        def _sub(m: re.Match, _tag=tag, _op=op) -> str:
            prop, value = m.group(1), m.group(2)
            is_string_literal = not _NUMERIC_RE.match(value)
            # isEqual/isNotEqual이 문자열 리터럴과 비교하는 경우는 "VALUE".equals(PROP) 스타일로
            # 만든다 - 이 프로젝트 Mapper.xml 전체 관례(예: <if test='"COLCHG".equals(SRCTYPE)'>)와
            # 맞추기 위함. PROP가 null이어도 안전하고(리터럴.equals(null) == false), 숫자 비교
            # (isGreaterThan 등, .equals() 관용구가 없는 부등호 비교)는 건드리지 않는다.
            if _tag == "isEqual" and is_string_literal:
                return f"<if test='{_compare_literal_dquote(value)}.equals({prop})'>"
            if _tag == "isNotEqual" and is_string_literal:
                return f"<if test='!{_compare_literal_dquote(value)}.equals({prop})'>"
            return f'<if test="{prop} {_op} {_compare_literal(value)}">'

        before = text
        text = open_re.sub(_sub, text)
        if before == text:
            continue
        # **여는 태그가 하나라도 안 바뀌었으면 닫는 태그도 건드리지 않는다.**
        # 예전엔 "하나라도 바뀌었으면" 곧바로 `</tag>`를 전부 `</if>`로 치환했다. 그래서 같은
        # 파일 안에 변환된 태그와 안 된 태그가 섞이면 **여는 건 <isEqual>인데 닫는 건 </if>**가
        # 되어 XML이 깨졌다(DPLA046 실측: XML_PARSE_ERROR). 변환 실패보다 나쁜 결과다 -
        # 안 고치면 사람이 원본을 보고 고치면 되지만, 깨뜨리면 무엇이 원본이었는지도 잃는다.
        leftover = re.search(rf"<{tag}\b", text)
        if leftover:
            line_no = text.count("\n", 0, leftover.start()) + 1
            issues.append(ConversionIssue(
                issue_type="PARTIAL_TAG_CONVERSION",
                severity="WARNING",
                line_no=line_no,
                message=(
                    f"{line_no}행: <{tag}>가 일부만 변환 가능한 형태여서 **이 태그 전체를 원본 그대로 "
                    f"두었습니다**(닫는 태그도 안 바꿈 - 섞이면 XML이 깨집니다). 남은 <{tag}>를 "
                    f"수동으로 <if>로 옮기세요."
                ),
            ))
            text = before
            continue
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

    # prepend 없이 property 하나만 쓴 형태. isEmpty에는 규칙이 있었는데 **정반대인 isNotEmpty에는
    # 없어서** 그대로 남아 있었다(DPLA046에서 11회 사용). iBatis의 isNotEmpty는 "null도 아니고
    # 빈 문자열도 아님"이라 MyBatis <if>로 1:1 대응된다 - 추측이 아니라 정의가 같다.
    # prepend가 붙은 형태는 위에서 경고만 내고 그대로 두므로 여기 정규식이 가로채지 않는다.
    before = text
    text = re.sub(
        r'<isNotEmpty\s+property="([A-Za-z0-9_.]+)"\s*>',
        r'<if test="\1 != null and \1 != \'\'">',
        text,
    )
    if before != text and not re.search(r"<isNotEmpty\b", text):
        # 위 비교 태그와 같은 이유로, 전부 변환됐을 때만 닫는 태그를 바꾼다.
        text = re.sub(r"</isNotEmpty>", "</if>", text)
    elif before != text:
        text = before  # 일부만 바뀌는 상황이면 손대지 않는다(XML을 깨뜨리지 않기 위해)
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


# --- 7b) iBatis식 리터럴 # 이스케이프(##) 정리 --------------------------------------------------
# iBatis는 #var#가 바인드 변수라서, 문자열 안에 진짜 # 한 글자를 쓰려면 ##로 이스케이프해야 했다
# (예: LIKE '##%'). MyBatis는 #{...} 형태만 특별 취급하고 맨 # 하나는 그냥 문자라서 이스케이프가
# 필요 없다 - 그대로 두면 LIKE 패턴에 불필요한 #이 하나 더 남는 문법 오류가 된다.
def _simplify_escaped_hash(text: str) -> str:
    return text.replace("##", "#")


# --- 7c) SQL 본문에 그대로 남은 부등호(<=, >=, <, >)를 CDATA로 감싼다 --------------------------
# <if test="..."> 같은 태그의 속성값 안에 있는 &lt;/&gt;(isLessThan 등에서 이미 생성한 것)는
# 속성값이라 엔티티 이스케이프 그대로 둬야 하므로 건드리지 않는다(그 줄엔 test=가 있어 걸러진다).
# 원본 XSQL이 WHERE 절 등 SQL 본문에 &lt;=/&gt;= 형태로 이스케이프해둔 것만, 이 Mapper.xml 전체
# 관례(리터럴 부등호 + CDATA)에 맞게 되돌린다 - 연속된 줄들을 각각 따로 감싸면(<![CDATA[..]]>를
# 줄마다 여닫으면) 열고 닫는 지점이 계속 반복돼서 실제 관례(예: WHERE~AND 절 전체를 CDATA 하나로
# 감싸고 여는 줄/닫는 줄을 따로 둠)와 다르다 - 그래서 연속된 대상 줄을 묶어서 CDATA 하나로 열고,
# 마지막 대상 줄 다음에 닫는다(대상이 아닌 줄이나 <if>/test= 같은 보호 대상 줄을 만나면 거기서 끊는다).
_ENTITY_OP_RE = re.compile(r"&lt;=|&gt;=|&lt;|&gt;")


def _is_cdata_protected_line(line: str) -> bool:
    return "<![CDATA[" in line or "]]>" in line or "test=" in line or "<if" in line or "<when" in line


def _wrap_raw_comparison_operators(text: str) -> str:
    lines = text.split("\n")
    out_lines: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if _is_cdata_protected_line(line) or not _ENTITY_OP_RE.search(line):
            out_lines.append(line)
            i += 1
            continue
        # 여기서부터 부등호가 있는 줄이 연속되는 구간을 한 덩어리로 묶는다.
        leading_ws = line[: len(line) - len(line.lstrip())]
        group: list[str] = []
        while i < n and not _is_cdata_protected_line(lines[i]) and _ENTITY_OP_RE.search(lines[i]):
            unescaped = (
                lines[i].replace("&lt;=", "<=").replace("&gt;=", ">=")
                .replace("&lt;", "<").replace("&gt;", ">")
            )
            group.append(unescaped.strip())
            i += 1
        out_lines.append(f"{leading_ws}<![CDATA[")
        out_lines.extend(f"{leading_ws}{g}" for g in group)
        out_lines.append(f"{leading_ws}]]>")
    return "\n".join(out_lines)


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


# 이 변환기가 다루는 iBatis 동적 태그. 속성 표기 정규화(_normalize_tag_attrs)와 "남아있는
# 태그" 경고가 같은 목록을 봐야 둘이 어긋나지 않는다.
_IBATIS_TAGS = (
    "isEqual|isNotEqual|isGreaterThan|isGreaterEqual|isLessThan|isLessEqual"
    "|isNull|isNotNull|isEmpty|isNotEmpty|iterate|dynamic"
)
_TAG_DECL_RE = re.compile(rf"<(?:{_IBATIS_TAGS})\b[^>]*>")
_ATTR_SPACING_RE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"')


def _normalize_tag_attrs(text: str) -> str:
    """iBatis 태그 **선언부 안에서만** `속성 = "값"`을 `속성="값"`으로 정규화한다.

    **왜 필요한가**: 아래 변환 규칙들이 전부 `property="..."`처럼 등호에 공백이 없는 형태만
    매칭한다. 그런데 실제 원본(DPLA046.xsql)은 `compareValue = "Y"`처럼 띄어 쓴다 - XML
    스펙상 완전히 유효한 표기다. 규칙 8개의 정규식을 각각 고치는 대신, 들어올 때 한 번
    정규화한다.

    **SQL 본문은 절대 건드리지 않는다.** `<isEqual ...>` 같은 태그 선언 `<...>` 안쪽만 바꾸므로
    `WHERE COL = 'Y'` 같은 SQL 텍스트의 공백은 그대로 남는다 - 이 변환기의 대원칙(SQL 자체는
    건드리지 않는다)을 지키기 위해 범위를 이렇게 좁혔다.
    """
    return _TAG_DECL_RE.sub(lambda m: _ATTR_SPACING_RE.sub(r'\1="', m.group(0)), text)


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


def _unterminated_attr_hint(text: str) -> str:
    """안 닫힌 속성 따옴표를 찾아 구체적인 위치를 덧붙인다(없으면 빈 문자열).

    XML 파서 메시지("not well-formed")만으로는 사람이 원본의 어디를 봐야 할지 알 수 없다.
    실제 원본에서 가장 흔했던 형태 하나만 정확히 짚는다 - 없는 원인을 추측해 붙이지 않는다.
    """
    hits = []
    for m in _UNTERMINATED_ATTR_RE.finditer(text):
        line_no = text.count("\n", 0, m.start()) + 1
        hits.append(f'{line_no}행 <{m.group(1)} {m.group(2)}="{m.group(3)}...')
    if not hits:
        return ""
    return ("\n  ↳ 원본에 **닫는 따옴표가 빠진 속성**이 "
            f"{len(hits)}건 있습니다: {'; '.join(hits[:3])}"
            f"{f' 외 {len(hits) - 3}건' if len(hits) > 3 else ''}. "
            "이 부분을 먼저 고쳐야 나머지 검증이 의미를 갖습니다.")


def convert_xsql_fragment(xsql_text: str) -> ConversionResult:
    """XSQL(iBatis) 문자열 하나(<sql>/<select> 블록 등)를 MyBatis 문법으로 변환한다.

    SQL 자체(컬럼/조건/조인)는 절대 건드리지 않는다 - 태그와 바인드 변수 문법만 치환한다.
    """
    issues: list[ConversionIssue] = []
    text = xsql_text

    # 규칙들이 전부 `속성="값"`(공백 없음) 형태만 매칭하므로 먼저 표기를 통일한다.
    text = _normalize_tag_attrs(text)
    text = _replace_isnotempty_iterate(text)
    text = _replace_comparison_tags(text, issues)
    text = _replace_null_tags(text)
    text = _replace_simple_empty_tags(text, issues)
    text = _replace_dynamic_tags(text)
    text = _replace_standalone_iterate(text)
    text = _replace_bind_vars(text)
    text = _simplify_escaped_hash(text)
    text = _wrap_raw_comparison_operators(text)
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
                + _unterminated_attr_hint(text)
            ),
        ))

    return ConversionResult(mybatis_xml=text, issues=issues)


def dto_name_for_method(method: str) -> str:
    """D/F BizUnit 메서드명(예: dPLA04701)에서 DTO 클래스명(Pla04701Dto)을 만든다.

    앞의 계층 접두어(d/f/p 한 글자)만 떼고, skeleton_gen.to_prefix()와 같은 규칙(첫 글자만
    대문자, 나머지 소문자)을 적용한다 - Mapper.xml의 <select> parameterType과 Store/Service가
    참조하는 DTO 클래스명을 항상 같은 규칙으로 만들기 위해 한 곳에 모아뒀다(중복 구현 방지).
    """
    base = method[1:] if method[:1].lower() in ("d", "f", "p") else method
    return base[:1].upper() + base[1:].lower() + "Dto"


# --- 문서 구조(DOCTYPE/root/namespace/select id·parameterType·resultType) 정리 -----------------
# convert_xsql_fragment()는 SQL 본문(태그/바인드 변수) 문법만 다룬다 - 화면ID/패키지/D 메서드명
# 같은 컨텍스트가 있어야 아는 문서 뼈대 변환은 이 함수가 별도로 맡는다(app.py가 generate_skeletons
# 결과의 stmt_id_to_method와 함께 순서대로 호출).
_OLD_DOCTYPE_RE = re.compile(
    r'<!DOCTYPE\s+sqlMap\s+PUBLIC\s+"-//iBATIS\.com//DTD SQL MAP 2\.0//EN"\s*'
    r'"http://ibatis\.apache\.org/dtd/sql-map-2\.dtd">'
)
_NEW_DOCTYPE = (
    '<!DOCTYPE sqlMap PUBLIC "-//mybatid.org//DTD Mapper 3.0//EN" '
    '"http://mybatis.org/dtd/mybatis-3-mapper.dtd">'
)
_SELECT_OPEN_RE = re.compile(
    r'<select\s+id="(?P<id>\w+)"\s+parameterType="(?P<ptype>[^"]*)"\s+resultType="(?P<rtype>[^"]*)"'
    r'(?:\s+fetchSize="\d+")?\s*>'
)

# DML(<insert>/<update>/<delete>)은 resultType이 없다. 조회 전용 가정으로 만들어져 있던 이
# 변환기가 CRUD 화면(DPLA046: insert 7·update 5·delete 1)을 만나면서 필요해졌다 - 그전까진
# 이 태그들의 id가 원본 그대로(I001/U001/D001) 남아 Store가 참조하는 이름과 어긋났다.
_DML_OPEN_RE = re.compile(
    r'<(?P<tag>insert|update|delete)\s+id="(?P<id>\w+)"'
    r'(?P<rest>(?:\s+[A-Za-z_][\w.]*="[^"]*")*)\s*>'
)

# `<insert id="I005 parameterClass="map">`처럼 값의 닫는 따옴표가 빠진 형태. XML 파서는
# "not well-formed"라고만 말해서 원인을 짚기 어려운데, 실제 원본에 3건 있었다(DPLA046).
_UNTERMINATED_ATTR_RE = re.compile(r'<(\w+)\s+(\w+)="([^"\n]*?)\s+\w+="')


def finalize_mapper_document(
    mybatis_text: str,
    screen_id: str,
    package_p1: str,
    package_p2: str,
    stmt_id_to_method: dict[str, str],
    common_statements: set[str] | None = None,
) -> ConversionResult:
    """XSQL 문서 전체를 감싸는 뼈대를 TO-BE 관례로 맞춘다(SQL 본문은 건드리지 않음):

        <!DOCTYPE sqlMap ...iBATIS.com...>          -> <!DOCTYPE sqlMap ...mybatid.org...>
        <sqlMap namespace="DPLA047">                 -> <mapper namespace="{패키지}.store.{화면}Store">
        <select id="S001" parameterType="map" ...>   -> <select id="dPLA04701" parameterType="{패키지}.dto.Pla04701Dto" ...>

    DOCTYPE 문자열은 실제 mybatis.org 표준 표기가 아니라(root 이름이 mapper가 아니라 sqlMap,
    도메인도 mybatid.org로 오타처럼 보인다) - 하지만 이 프로젝트 Mapper.xml 전체가 이 정확한
    문자열을 관례로 쓰고 있어(사람이 명시적으로 확인) 임의로 "고치지" 않고 그대로 맞춘다.
    """
    prefix = screen_id[:1].upper() + screen_id[1:].lower()
    base_pkg = f"com.skhynix.gscm.r.{package_p1}.{package_p2}"
    namespace = f"{base_pkg}.store.{prefix}Store"
    issues: list[ConversionIssue] = []

    text = mybatis_text

    # 확정된 공통 statement(예: 사용자 권한 조회 S902)는 화면마다 똑같은 SQL이 복제돼 있다.
    # 여기서 걷어내고 공통 Mapper 한 곳에만 남긴다 - 안 그러면 나중에 권한 쿼리를 한 번 고칠 때
    # 1,416벌을 고쳐야 한다. 무엇이 공통인지는 config/common-methods.json(사람 확정)이 정한다.
    for stmt_id in sorted(common_statements or ()):
        pattern = re.compile(
            rf'[ \t]*<select\s+id="{re.escape(stmt_id)}".*?</select>\s*\n?',
            re.DOTALL | re.IGNORECASE,
        )
        text, n = pattern.subn("", text)
        if n:
            issues.append(ConversionIssue(
                issue_type="COMMON_STATEMENT_EXTRACTED", severity="INFO",
                message=(
                    f'<select id="{stmt_id}">는 화면 간 공통 SQL로 확정돼 있어 이 Mapper에서 '
                    f'제외했습니다 - 공통 Mapper 한 곳에서 관리합니다'
                    f'(config/common-methods.json).'
                ),
            ))

    # 4) DOCTYPE
    text = _OLD_DOCTYPE_RE.sub(_NEW_DOCTYPE, text)

    # 5) 루트 엘리먼트 + namespace
    text = re.sub(r'<sqlMap\s+namespace="[^"]*"\s*>', f'<mapper namespace="{namespace}">', text)
    stripped = text.rstrip()
    if stripped.endswith("</sqlMap>"):
        text = stripped[: -len("</sqlMap>")] + "</mapper>\n"

    # 6) <select id="S00N" parameterType="map" resultType="hashmap" fetchSize="N"> 정리
    had_fetch_size = "fetchSize=" in text

    def _select_sub(m: re.Match) -> str:
        old_id = m.group("id")
        method = stmt_id_to_method.get(old_id)
        if not method:
            issues.append(ConversionIssue(
                issue_type="STMT_ID_MAP_MISSING", severity="WARNING",
                message=(
                    f'<select id="{old_id}">를 D BizUnit의 dbSelect("{old_id}", ...) 호출과 매칭하지 '
                    "못했습니다 - id를 그대로 두었으니 D 메서드명 기준으로 수동 확인하세요."
                ),
            ))
            new_id = old_id
        else:
            new_id = method

        param_type = m.group("ptype").strip()
        if param_type == "map" and method:
            # D 메서드명이 화면ID+번호 패턴을 벗어나는 경우(드묾)는 사람이 확인할 것.
            param_type = f"{base_pkg}.dto.{dto_name_for_method(method)}"

        result_type = m.group("rtype").strip()
        if result_type.lower() == "hashmap":
            result_type = "map"

        return f'<select id="{new_id}" parameterType="{param_type}" resultType="{result_type}">'

    text = _SELECT_OPEN_RE.sub(_select_sub, text)

    def _dml_sub(m: re.Match) -> str:
        """DML은 id만 D 메서드명으로 맞추고 나머지 속성은 원본 그대로 둔다.

        조회와 달리 resultType을 만들어 붙이지 않는다 - MyBatis에서 insert/update/delete는
        영향 행 수(int)를 돌려주므로 결과 타입을 선언할 자리가 없다.
        """
        old_id = m.group("id")
        method = stmt_id_to_method.get(old_id)
        if not method:
            issues.append(ConversionIssue(
                issue_type="STMT_ID_MAP_MISSING", severity="WARNING",
                message=(
                    f'<{m.group("tag")} id="{old_id}">를 D BizUnit의 db*("{old_id}", ...) 호출과 '
                    "매칭하지 못했습니다 - id를 그대로 두었으니 D 메서드명 기준으로 수동 확인하세요."
                ),
            ))
            return m.group(0)
        rest = m.group("rest")
        rest = re.sub(r'\s+parameterType="map"', f' parameterType="map"', rest)
        return f'<{m.group("tag")} id="{method}"{rest}>'

    text = _DML_OPEN_RE.sub(_dml_sub, text)
    if had_fetch_size:
        issues.append(ConversionIssue(
            issue_type="FETCH_SIZE_DROPPED", severity="INFO",
            message="fetchSize 속성은 MyBatis 변환 시 제거했습니다 - 필요하면 <select>에 수동으로 다시 넣으세요.",
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
