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

import re
from dataclasses import dataclass, field

from converters import ConversionIssue


@dataclass
class SkeletonResult:
    files: dict[str, str] = field(default_factory=dict)
    issues: list[ConversionIssue] = field(default_factory=list)

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


_METHOD_SIG_RE = re.compile(
    r"public\s+IDataSet\s+(\w+)\s*\(([^)]*)\)", re.DOTALL
)

_BIZUNIT_METHOD_RE = re.compile(
    r'<method\s+id="([^"]+)"\s*>.*?<transactionId>([^<]*)</transactionId>', re.DOTALL
)


def extract_methods(java_text: str) -> list[str]:
    """P/F/D java 소스에서 `public IDataSet xxx(...)` 형태의 메서드 이름을 뽑는다.

    원본이 컴파일 안 되는 상태(PLA047에서 실제로 겪음)여도 정규식 기반이라 동작한다 -
    문법 오류가 있어도 시그니처 텍스트 자체는 대개 온전하기 때문.
    """
    return [m.group(1) for m in _METHOD_SIG_RE.finditer(java_text)]


def extract_method_bodies(java_text: str) -> dict[str, str]:
    """각 메서드 시그니처 시작 지점부터 다음 메서드(또는 파일 끝)까지를 "본문"으로 대략 자른다.

    중괄호 매칭을 정확히 하는 대신 다음 시그니처 등장 위치를 경계로 쓰는 근사치다 -
    이 화면들처럼 클래스 안에 메서드 여러 개가 나란히 있는 전형적인 BizUnit 구조에는 충분하다.
    """
    matches = list(_METHOD_SIG_RE.finditer(java_text))
    bodies: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(java_text)
        bodies[m.group(1)] = java_text[start:end]
    return bodies


def find_delegate_call(p_method_body: str, f_method_names: list[str]) -> str | None:
    """P 메서드 본문에서 실제로 호출하는 F 메서드 이름을 찾는다(있는 것만 신뢰, 추측 안 함)."""
    for name in f_method_names:
        if re.search(rf"\.{re.escape(name)}\s*\(", p_method_body):
            return name
    return None


def splice_ported_method(service_java: str, method: str, ported_body_code: str) -> str:
    """generate_skeletons가 만든 스텁(PORT_START/PORT_END 마커 사이)을 LLM이 포팅한 코드로 교체한다.

    마커를 못 찾으면(수동 편집 등으로 지워진 경우) 원본을 그대로 돌려주고 아무 것도 하지 않는다 -
    엉뚱한 위치에 잘못 끼워 넣는 것보다 안전하다.
    """
    pattern = re.compile(
        rf"    // PORT_START:{re.escape(method)}\n.*?    // PORT_END:{re.escape(method)}\n",
        re.DOTALL,
    )
    if not pattern.search(service_java):
        return service_java
    replacement = (
        f"    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)\n"
        f"{ported_body_code.rstrip()}\n"
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
                message=f"{p_method}: {msg}",
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
            "import com.skhynix.gscm.common.ApiResponse;",
            "",
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
                ))
            call_target = delegate or method
            lines += [
                f"    // nctRid: {nctrid or '미확인 - .bizunit에서 못 찾음'}",
                f'    @PostMapping("/{slug}")',
                f"    public ResponseEntity<ApiResponse<Object>> {method}(@RequestBody Map<String, Object> request) {{",
                f"        // 실패는 BizException으로만 표현한다(GlobalExceptionHandler가 유일한 실패",
                f"        // 응답 생성 지점) - docs/09-common-conventions.md 참고.",
                f"        return ResponseEntity.ok(ApiResponse.success(service.{call_target}(request)));",
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
        if not f_methods:
            result.issues.append(ConversionIssue(
                issue_type="NO_METHODS_FOUND", severity="BLOCKER",
                message="F 파일에서 `public IDataSet 메서드(...)` 시그니처를 찾지 못했습니다.",
            ))
        lines = [
            f"package {base_pkg}.service;",
            "",
            "import org.springframework.stereotype.Service;",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "",
            "import java.util.Map;",
            "",
            f"@Service",
            f"public class {prefix}Service {{",
            "",
            f"    @Autowired",
            f"    private {prefix}Store store;",
            "",
        ]
        for method in f_methods:
            lines += [
                f"    // PORT_START:{method}",
                f"    // TODO(LLM 포팅 필요): 원본 F{screen_id}.{method}의 계산/분기 로직을 그대로 옮길 것.",
                f"    // NEXCORE 의존(IDataSet/IOnlineContext/lookupDataUnit)만 제거하고 로직은 새로 짜지 않는다.",
                f"    // 원본의 BizRuntimeException(code, args, cause)은 com.skhynix.gscm.common.BizException으로",
                f"    // 그대로 대응(docs/09-common-conventions.md) - 실패를 새로운 방식으로 표현하지 않는다.",
                f"    public Map<String, Object> {method}(Map<String, Object> request) {{",
                f"        throw new UnsupportedOperationException(\"TODO: {method} 포팅 필요\");",
                f"    }}",
                f"    // PORT_END:{method}",
                "",
            ]
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
        if not d_methods:
            result.issues.append(ConversionIssue(
                issue_type="NO_METHODS_FOUND", severity="BLOCKER",
                message="D 파일에서 `public IDataSet 메서드(...)` 시그니처를 찾지 못했습니다.",
            ))
        # dbSelect("S00N", ...) 호출에서 실제 매핑 statement id를 뽑아 Store가 참조할 수 있게 한다.
        stmt_ids = dict(re.findall(r'(\w+)\s*\([^)]*?\)\s*\{\s*[^}]*?dbSelect\("(\w+)"', d_java_text, re.DOTALL))
        lines = [
            f"package {base_pkg}.store;",
            "",
            "import org.mybatis.spring.SqlSessionTemplate;",
            "import org.springframework.beans.factory.annotation.Autowired;",
            "import org.springframework.stereotype.Repository;",
            "",
            "import java.util.Map;",
            "",
            f"// MyBatis 연동 방식: SqlSessionTemplate 직접 호출로 확정(docs/09-common-conventions.md #5).",
            f"// docs/07-tobe-structure.xlsx 확정 구조에 없는 별도 Mapper 인터페이스는 도입하지 않는다.",
            f"@Repository",
            f"public class {prefix}Store {{",
            "",
            f"    @Autowired",
            f"    private SqlSessionTemplate sqlSession;",
            "",
        ]
        for method in d_methods:
            stmt_id = stmt_ids.get(method, "")
            mapper_ref = f'"{prefix}Mapper.{stmt_id}"' if stmt_id else f'"{prefix}Mapper.TODO_확인필요"'
            lines += [
                f"    public Map<String, Object> {method}(Map<String, Object> params) {{",
                f"        return sqlSession.selectOne({mapper_ref}, params);",
                f"    }}",
                "",
            ]
        lines.append("}")
        result.files[f"{prefix}Store.java"] = "\n".join(lines)
    else:
        result.issues.append(ConversionIssue(
            issue_type="MISSING_INPUT_FILE", severity="INFO",
            message="D(Java) 파일이 없어 Store 골격을 생성하지 않았습니다.",
        ))

    return result
