"""AI 추천 (2026-08-29, 멘토 논의 반영).

**범위(사용자 확인)**: 백엔드(Java/Spring/MyBatis)는 그대로 두고, 응답 DTO의 "모양"(타입,
페이지네이션 래핑, 중첩)만 React 프론트엔드가 쓰기 편하게 재설계한 **대안 버전**을 Api/Service/
Store/Mapper/Dto 5개 파일 단위로 나눠 보여준다. 실제 React/TypeScript 코드나 xfdl 파싱은 하지
않는다 - CLAUDE.md v2의 "UI(xfdl/Nexacro)는 전환하지 않는다" 범위는 그대로 유지된다. 기존
결정론적 변환(`skeleton_gen.py`)과 나란히 비교해볼 수 있는 opt-in 추가 산출물일 뿐, 기존
파이프라인을 대체하지 않는다.

**핵심 제약**: "업무 로직/필드는 절대 바꾸지 않는다"를 프롬프트로만 지시하지 않고 코드로도
검증한다 - LLM이 원본에 없는 필드를 지어내면 BLOCKER 이슈로 걸러서 사람이 채택하지 못하게
표시한다(LLM이 지시를 항상 따른다고 가정하지 않는다). LLM 호출은 화면당 nctRid 1회뿐이다 -
Api/Service/Store/Mapper 추천은 그 결과(필드 타입·래핑 여부)로부터 결정론적으로 파생시킨다
(LLM을 5번 부르지 않음 - 속도/비용, 그리고 5개 파일이 서로 다른 얘기를 하는 걸 막기 위함).

**Store/Mapper의 정직한 한계**: 응답 필드는 레코드셋 이름(`MAIN_LIST` 등) 수준까지만 알고
실제 SELECT 컬럼 목록은 모른다. 그래서 Store는 "변경 없음"을 추천하고(Mapper의 resultType을
바꾸려면 컬럼 정렬이 정확해야 하는데 그걸 모름), Mapper는 구조 예시만 보여주고 "미검증 - 사람이
원본 SELECT 컬럼과 대조 필요"라고 명시한다 - 추측으로 컬럼을 지어내지 않는다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from converters import ConversionIssue

_REACT_VARIANT_PROMPT = """\
다음은 기존 NEXCORE 화면 하나의 요청/응답 필드 목록이다. 이 필드들의 이름과 의미는 절대 새로
만들거나 빼지 마라 - 이미 확정된 업무 데이터다. 대신 React 프론트엔드(React Query 등)가 쓰기
편하도록 "모양"만 다시 설계해라: 목록성 응답이면 페이지네이션 래핑(items/totalCount) 여부,
각 필드의 JSON 타입(string/number/boolean/array/object), 널 허용 여부를 제안해라.

화면: {screen_id} / nctRid: {nctrid}
요청 필드(원본 그대로, 전부 String으로 추정됨): {request_fields}
응답 필드(원본 그대로, 레코드셋 이름): {response_fields}

아래 JSON 스키마로만 답해라(다른 텍스트 없이 JSON 객체 하나만, 마크다운 코드펜스도 쓰지 마라):
{{
  "wrap_as_list": true 또는 false,
  "fields": [
    {{"name": "원본 응답 필드명 그대로", "json_type": "string|number|boolean|array|object", "nullable": true 또는 false}}
  ],
  "rationale": "왜 이 구조가 React에서 쓰기 편한지 2~3문장, 한국어로"
}}
"""

_JAVA_TYPE_MAP = {
    "string": "String",
    "number": "Double",
    "boolean": "Boolean",
    "array": "java.util.List<Object>",
    "object": "java.util.Map<String, Object>",
}


@dataclass
class ReactField:
    name: str
    camel: str
    java_type: str
    nullable: bool


@dataclass
class ReactVariantResult:
    class_name: str = ""
    dto_java: str = ""
    api_java: str = ""
    service_java: str = ""
    store_java: str = ""
    mapper_xml: str = ""
    rationale: str = ""
    issues: list[ConversionIssue] = field(default_factory=list)


def _snake_to_camel(name: str) -> str:
    parts = [p for p in re.split(r"[_\s]+", name) if p]
    if not parts:
        return name.lower()
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def _safe_class_name(nctrid: str | None, p_method: str) -> str:
    base = nctrid or p_method
    base = re.sub(r"[^A-Za-z0-9]", "", base)
    if not base or not base[0].isalpha():
        base = "X" + base
    return f"{base}ReactDto"


def _map_get_expr(field_name: str, java_type: str) -> str:
    """raw.get("FIELD")를 java_type으로 안전하게 바꾸는 식을 만든다.

    NEXCORE Dataset은 값을 전부 String으로 담는 관례가 있어(skeleton_gen.py 주석 참고), Double/
    Boolean은 바로 캐스팅하면 ClassCastException이 난다 - String으로 경유해서 파싱한다.
    """
    key = f'raw.get("{field_name}")'
    if java_type == "String":
        return f"(String) {key}"
    if java_type == "Double":
        return f"{key} == null ? null : Double.valueOf(String.valueOf({key}))"
    if java_type == "Boolean":
        return f"{key} == null ? null : Boolean.valueOf(String.valueOf({key}))"
    return f"({java_type}) {key}"


def _find_delegate_call(existing_java: str | None, method_name: str) -> str | None:
    """기존 생성 파일 텍스트에서 method_name 메서드가 실제로 위임하는 대상 식별자를 찾는다
    (있으면 정확한 이름을 쓰고, 없으면 호출부가 플레이스홀더로 대체한다 - 추측 안 함).
    """
    if not existing_java:
        return None
    idx = existing_java.find(f" {method_name}(")
    if idx == -1:
        idx = existing_java.find(f"{method_name}(")
    if idx == -1:
        return None
    window = existing_java[idx: idx + 600]
    m = re.search(r"(?:service|store)\.(\w+)\(", window)
    return m.group(1) if m else None


def _get_react_spec(
    screen_id: str, p_method: str, nctrid: str | None,
    request_fields: list[str], response_fields: list[str],
) -> tuple[dict | None, str, list[ConversionIssue]]:
    """LLM 호출 1회로 필드 모양 스펙을 받고, 원본 필드 목록과 대조 검증한다.

    반환: (spec dict 또는 None, rationale, issues). spec이 None이면 이후 단계(Api/Service/
    Store/Mapper 파생)를 진행할 근거가 없다는 뜻 - issues에 이유가 남는다.
    """
    from agents.llm_gateway import chat

    issues: list[ConversionIssue] = []
    if not response_fields:
        issues.append(ConversionIssue(
            issue_type="REACT_VARIANT_NO_FIELDS", severity="INFO",
            message=f"{p_method}: 응답 필드가 없어 AI 추천을 만들 수 없습니다.",
        ))
        return None, "", issues

    original_fields = {f.upper() for f in request_fields} | {f.upper() for f in response_fields}
    prompt = _REACT_VARIANT_PROMPT.format(
        screen_id=screen_id, nctrid=nctrid or "(미확인)",
        request_fields=", ".join(request_fields) or "(없음)",
        response_fields=", ".join(response_fields) or "(없음)",
    )
    try:
        raw = chat(messages=[{"role": "user", "content": prompt}])
    except Exception as e:  # noqa: BLE001 - LLM Gateway 호출 실패는 재시도 가능한 WARNING
        issues.append(ConversionIssue(
            issue_type="REACT_VARIANT_LLM_ERROR", severity="WARNING",
            message=f"{p_method}: LLM 호출 실패 - {e}",
        ))
        return None, "", issues

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        issues.append(ConversionIssue(
            issue_type="REACT_VARIANT_PARSE_ERROR", severity="WARNING",
            message=f"{p_method}: LLM 응답에서 JSON을 찾지 못했습니다 - 원문 앞부분: {raw[:300]}",
        ))
        return None, "", issues
    try:
        spec = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        issues.append(ConversionIssue(
            issue_type="REACT_VARIANT_PARSE_ERROR", severity="WARNING",
            message=f"{p_method}: LLM JSON 파싱 실패 - {e}",
        ))
        return None, "", issues

    spec_fields = spec.get("fields", [])
    if not isinstance(spec_fields, list):
        spec_fields = []
    unknown = [f.get("name", "?") for f in spec_fields if str(f.get("name", "")).upper() not in original_fields]
    if unknown:
        issues.append(ConversionIssue(
            issue_type="REACT_VARIANT_INVENTED_FIELD", severity="BLOCKER",
            message=(
                f"{p_method}: AI가 원본에 없는 필드를 추가했습니다({', '.join(unknown)}) - "
                "업무 로직/데이터가 바뀔 위험이 있어 이 추천은 채택하지 마세요."
            ),
        ))

    return spec, str(spec.get("rationale", "")).strip(), issues


def recommend_react_variant(
    screen_id: str,
    p_method: str,
    nctrid: str | None,
    request_fields: list[str],
    response_fields: list[str],
    api_java: str | None = None,
) -> ReactVariantResult:
    """Api/Service/Store/Mapper/Dto 5개 파일 단위로 AI 추천을 만든다.

    request_fields/response_fields는 chatui/skeleton_gen.py의 extract_dto_fields()가 이미
    뽑아둔 값을 그대로 받는다 - 필드 자체를 여기서 새로 추출하지 않는다(결정론적 추출과 AI
    추천을 분리 - 변환기/검증기 분리 원칙의 연장). api_java(선택)를 주면 실제 위임 메서드
    이름을 찾아 Api 추천에 그대로 쓴다 - 없으면 플레이스홀더로 대체한다(추측 안 함).
    """
    result = ReactVariantResult(class_name=_safe_class_name(nctrid, p_method))
    spec, rationale, issues = _get_react_spec(
        screen_id, p_method, nctrid, request_fields, response_fields,
    )
    result.issues = issues
    result.rationale = rationale
    if spec is None:
        return result

    class_name = result.class_name
    wrap_as_list = bool(spec.get("wrap_as_list"))
    spec_fields = spec.get("fields", [])
    if not isinstance(spec_fields, list):
        spec_fields = []

    fields: list[ReactField] = []
    for f in spec_fields:
        name = str(f.get("name", ""))
        if not name:
            continue
        fields.append(ReactField(
            name=name,
            camel=_snake_to_camel(name),
            java_type=_JAVA_TYPE_MAP.get(str(f.get("json_type", "string")).lower(), "String"),
            nullable=bool(f.get("nullable", True)),
        ))

    # ---- Dto.java ----
    dto_lines = [
        "import lombok.Data;",
        "",
        f"// [AI 추천 - 사람 검토 전 채택 금지] 원본: {p_method} / nctRid: {nctrid or '미확인'}",
        "// 업무 필드 이름·의미는 원본과 동일 - 아래는 '모양'(JSON 타입/페이지네이션 래핑)만 다시 제안한 것.",
        "@Data",
        f"public class {class_name} {{",
        "",
    ]
    field_lines = [
        f"    private {f.java_type} {f.camel}; // AS-IS: {f.name}" + ("" if f.nullable else "  // NOT NULL")
        for f in fields
    ]
    if wrap_as_list:
        dto_lines += [
            "    private java.util.List<Item> items;",
            "    private long totalCount;",
            "",
            "    @Data",
            "    public static class Item {",
            *[f"    {fl}" for fl in field_lines],
            "    }",
        ]
    else:
        dto_lines += field_lines
    dto_lines.append("}")
    result.dto_java = "\n".join(dto_lines)

    # ---- Api.java (반환 타입만 감싸는 안, 위임 대상은 원본에서 찾은 실제 이름) ----
    delegate = _find_delegate_call(api_java, p_method) or "<원본 Api.java의 위임 메서드>"
    result.api_java = "\n".join([
        f"// [AI 추천] {p_method}의 반환 타입만 CommonApiResponse<{class_name}>로 감싼다.",
        f"// 매핑 경로·파라미터·위임 대상({delegate})은 원본 Api.java와 동일 - 로직 변경 없음.",
        f"public ResponseEntity<CommonApiResponse<{class_name}>> {p_method}(@RequestBody Map<String, Object> request) {{",
        f"    return ResponseEntity.ok(CommonApiResponse.createSuccess(service.{delegate}React(request)));",
        "}",
    ])

    # ---- Service.java (내부 로직/쿼리 호출 재사용, 반환 모양만 어댑터로 변환) ----
    if wrap_as_list:
        service_body = [
            f"    Map<String, Object> raw = {delegate}(request); // 기존 메서드 그대로 재사용, 로직 변경 없음",
            f"    {class_name} dto = new {class_name}();",
            f"    // raw 안에 원본 레코드셋({', '.join(response_fields)})이 들어있지만, 이 화면 소스만으론",
            f"    // 정확한 키 이름과 컬럼 스키마를 몰라 items/totalCount 매핑은 사람이 채워야 한다.",
            f"    // dto.setItems(...); dto.setTotalCount(...);",
            f"    return dto;",
        ]
    else:
        service_body = [
            f"    Map<String, Object> raw = {delegate}(request); // 기존 메서드 그대로 재사용, 로직 변경 없음",
            f"    {class_name} dto = new {class_name}();",
            *[
                f"    dto.set{f.camel[0].upper()}{f.camel[1:]}({_map_get_expr(f.name, f.java_type)});"
                for f in fields
            ],
            f"    return dto;",
        ]
    result.service_java = "\n".join([
        f"// [AI 추천] {delegate}의 결과를 {class_name} 모양으로 감싸는 어댑터 메서드를 추가하는 안.",
        f"// {delegate} 자체(쿼리 호출/분기 로직)는 전혀 안 바뀐다 - 아래는 결과를 담는 그릇만 바꾼 것.",
        f"public {class_name} {delegate}React(Map<String, Object> request) {{",
        *service_body,
        "}",
    ])

    # ---- Store.java: 변경 없음 추천 (컬럼 스키마를 몰라 Mapper resultType을 안전하게 못 바꿈) ----
    result.store_java = "\n".join([
        "// [AI 추천] Store는 변경 없음을 추천합니다.",
        "// 이유: 응답 모양 변환은 Service 어댑터 계층에서 처리하는 게 안전합니다(Store/Mapper의",
        "// SQL·실행 경로를 안 건드리는 게 이번 추천의 핵심 제약). Store 자체를 타입화하려면",
        "// Mapper.xml의 resultType/resultMap도 같이 바뀌어야 하는데, 이 화면 소스만으로는 실제",
        "// SELECT 컬럼 목록을 몰라 안전하게 자동 추천할 수 없습니다(추측으로 컬럼을 지어내지 않음).",
    ])

    # ---- Mapper.xml: 구조 예시만(미검증) ----
    result.mapper_xml = "\n".join([
        f'<!-- [AI 추천 - 구조 제안, 미검증] resultType을 {class_name}(으)로 바꾸는 안. -->',
        "<!-- 주의: 실제 SELECT 컬럼 별칭이 아래 필드명과 정확히 일치하는지 원본 Mapper.xml과 -->",
        "<!-- 사람이 대조해야 합니다 - 안 맞으면 필드가 조용히 null로 빠집니다. SQL 로직(WHERE/JOIN/ -->",
        "<!-- 컬럼 목록)은 원본 그대로 유지하고 resultType만 바꾸는 것을 전제로 합니다. -->",
        f'<select id="{p_method}" resultType="....dto.{class_name}">',
        "    <!-- 원본 SELECT 절 그대로 (SQL 로직 변경 없음) -->",
        "</select>",
    ])

    return result
