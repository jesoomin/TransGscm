"""결정론적 규칙 기반 변환기: iBatis(XSQL) -> MyBatis, BizUnit -> Controller/Service/Store 골격.

CLAUDE.md 핵심 원칙: 결정론적으로 풀리는 변환에는 LLM을 쓰지 않는다. 이 모듈은 순수
정규식/문자열 치환이고 SQL·업무 로직 자체는 절대 바꾸지 않는다 - 문법만 바꾼다.

멘토 코멘트(docs/06-mentor-feedback.md §2) 규칙 그대로:
    #var# -> #{var},  $var$ -> ${var}
    <isEqual>/<isNotEqual>/<isNull>/<isNotNull>/<isGreaterThan> 등 -> <if test="...">
    <isNotEmpty>+<iterate> -> <if>+<foreach>
    <dynamic prepend="WHERE"> -> <where>,  <dynamic prepend="SET"> -> <set>

PLA047 화면 XSQL(3,405행)에서 실제로 검증된 것은 isEqual/isNotEqual/isNotEmpty+iterate 뿐이고
나머지 태그는 이번 화면엔 없어서 룰만 준비해뒀다 - 다른 화면에 적용할 때 결과를 반드시 확인할 것.
"""
from __future__ import annotations

import re
import xml.dom.minidom as minidom
from dataclasses import dataclass, field


@dataclass
class ConversionResult:
    mybatis_xml: str
    warnings: list[str] = field(default_factory=list)


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
_COMPARISON_OPS = {
    "isEqual": "==",
    "isNotEqual": "!=",
    "isGreaterThan": ">",
    "isGreaterEqual": ">=",
    "isLessThan": "<",
    "isLessEqual": "<=",
}


def _replace_comparison_tags(text: str, warnings: list[str]) -> str:
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
def _replace_simple_empty_tags(text: str, warnings: list[str]) -> str:
    prepend_leftover = re.findall(r'<isNotEmpty\s+prepend="([^"]*)"\s+property="([A-Za-z0-9_.]+)"\s*>', text)
    for prepend, prop in prepend_leftover:
        warnings.append(
            f'<isNotEmpty prepend="{prepend}" property="{prop}"> - iterate 없이 쓰인 prepend 패턴은 '
            f"자동 변환 안 함(원본 유지). MyBatis는 prepend를 지원하지 않으니 <if>+<where> 조합으로 수동 변환 필요"
        )
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
    warnings: list[str] = []
    text = xsql_text

    text = _replace_isnotempty_iterate(text)
    text = _replace_comparison_tags(text, warnings)
    text = _replace_null_tags(text)
    text = _replace_simple_empty_tags(text, warnings)
    text = _replace_dynamic_tags(text)
    text = _replace_standalone_iterate(text)
    text = _replace_bind_vars(text)

    for tag in _KNOWN_REMAINING_TAGS:
        if re.search(rf"</?{tag}\b", text):
            warnings.append(
                f"<{tag}> 태그가 변환 후에도 남아있습니다 - 자동 규칙이 이 화면의 실제 사용 패턴과 "
                f"다를 수 있으니 원본과 대조해서 수동 확인하세요."
            )

    # remapresults 등 iBatis 전용 속성은 MyBatis에 대응이 없어 제거하고 경고만 남긴다.
    if "remapresults" in text:
        warnings.append(
            "remapresults 속성 발견 - MyBatis에 대응 기능 없음, 제거 예정. 결과 컬럼명 중복 여부 확인 필요"
        )
        text = re.sub(r'\s*remapresults="[^"]*"', "", text)
    if 'parameterClass="' in text:
        text = text.replace('parameterClass="', 'parameterType="')
    if 'resultClass="hmap"' in text:
        text = text.replace('resultClass="hmap"', 'resultType="hashmap"')
    elif 'resultClass="' in text:
        text = re.sub(r'resultClass="([^"]*)"', r'resultType="\1"', text)

    xml_error = _check_well_formed(text)
    if xml_error:
        warnings.append(
            f"변환 결과가 유효한 XML이 아닙니다: {xml_error}. 원본 XSQL 자체의 태그 짝이 안 맞을 수 있습니다 "
            f"(문법 치환 규칙 문제가 아니라 원본 데이터 문제일 가능성이 높음) - 원본과 대조해서 확인하세요."
        )

    return ConversionResult(mybatis_xml=text, warnings=warnings)


def _check_well_formed(text: str) -> str | None:
    """변환 결과의 태그 짝이 맞는지 확인한다. 이 함수는 결과를 바꾸지 않고 오류 메시지만 돌려준다.

    입력이 전체 문서(<?xml ...?>/<!DOCTYPE ...> 포함)든 <select> 하나짜리 조각이든 상관없이
    확인할 수 있도록, 선언부를 떼어내고 더미 루트로 감싸서 검사한다.
    """
    body = re.sub(r"<\?xml[^>]*\?>", "", text)
    body = re.sub(r"<!DOCTYPE[^>]*>", "", body)
    try:
        minidom.parseString(f"<root>{body}</root>".encode("utf-8"))
        return None
    except Exception as e:  # noqa: BLE001 - 사용자에게 그대로 보여줄 진단 메시지라 광범위하게 잡는다
        return str(e)
