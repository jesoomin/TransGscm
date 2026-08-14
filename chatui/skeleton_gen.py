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


def extract_nctrid_map(bizunit_text: str) -> dict[str, str]:
    """.bizunit에서 method id -> transactionId(nctRid 또는 내부 트랜잭션 ID) 매핑을 뽑는다.

    XML 선언이 깨져 있어도(PLA047에서 실제로 겪음) 정규식이라 파싱 가능하다.
    """
    return {m.group(1): m.group(2) for m in _BIZUNIT_METHOD_RE.finditer(bizunit_text)}


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
                f"    public ResponseEntity<Map<String, Object>> {method}(@RequestBody Map<String, Object> request) {{",
                f"        return ResponseEntity.ok(service.{call_target}(request));",
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
                f"    // TODO(LLM 포팅 필요): 원본 F{screen_id}.{method}의 계산/분기 로직을 그대로 옮길 것.",
                f"    // NEXCORE 의존(IDataSet/IOnlineContext/lookupDataUnit)만 제거하고 로직은 새로 짜지 않는다.",
                f"    public Map<String, Object> {method}(Map<String, Object> request) {{",
                f"        throw new UnsupportedOperationException(\"TODO: {method} 포팅 필요\");",
                f"    }}",
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
            f"// TODO: MyBatis 연동 방식(SqlSessionTemplate 직접 호출 vs @Mapper 인터페이스)이 아직 사내 컨벤션으로",
            f"// 확정되지 않아 SqlSessionTemplate 방식으로 임시 작성했다 - 실제 컨벤션 확인 후 조정할 것.",
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
