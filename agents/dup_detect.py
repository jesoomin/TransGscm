"""화면 경계를 넘는 중복 함수 탐지 — **신뢰 수준을 나눠서** 보고한다.

기존 탐지는 "중복이다/아니다" 이진 판정이었다. 그런데 실측해보니 두 종류가 섞여 있었다:

  - **EXACT**: 주석·공백만 빼면 텍스트가 그대로 같다. 복붙이 확실하다.
  - **NORMALIZED**: 화면 ID를 자리표시자로 바꾸면 같아진다. 화면마다 자기 D 클래스명을 담고 있을
    뿐 로직은 동일한 경우인데, "정말 같은 로직"일 수도 있고 "구조만 같고 의도는 다른" 경우일
    수도 있다.
  - **STRUCTURAL**: 이름·값을 전부 버리고 AST 형태만 같다. **이 코퍼스에서는 쓸모가 없었다** -
    메서드 330개를 전부(커버리지 100%) 5그룹으로 묶어버려서 무엇이 무엇과 같은지 말해주지
    못한다. 티어 자체는 남겨두되 `low_information` 플래그로 표시한다(아래 참고).

둘을 한 덩어리로 보고하면 쓸 수가 없다 — 삭제·공통화 후보로 올리려면 확실한 것과 검토할 것을
구분해야 한다. 그래서 티어로 나눈다. **자동 삭제는 하지 않는다**(조회 전용).

---

**정답키와의 정의 불일치 (숨기지 않고 기록한다)**

`PLA081-110` 정답키는 `QrySelectDetail`을 «완전 고유(중복 없음)»으로 표시한다. 그런데 실제
소스를 대조하면 `fPLA081QrySelectDetail`과 `fPLA087QrySelectDetail`은 **화면 ID를 치환하면
차이가 0**이다(리터럴 `METRIC_TYPE`까지 같은 그룹 기준). 즉 텍스트로는 명백한 Type-2 클론이다.

이건 탐지기의 오탐이 아니라 **"중복"의 정의가 다른 것**이다:
  - 정답키: 화면마다 고유한 업무 조회 → 업무 관점의 고유성
  - 탐지기: 식별자만 다른 동일 코드 → 텍스트 관점의 클론

어느 쪽이 맞다고 우기지 않는다. 대신 ① EXACT 티어는 정답키와 다투지 않는 확실한 것만 담고
② NORMALIZED 티어는 «후보»로 표시하며 ③ 이 불일치 건수를 **별도로 집계해 보고**한다.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.S)
_COMMENT_LINE_RE = re.compile(r"//[^\n]*")
_WS_RE = re.compile(r"\s+")

TIER_EXACT = "EXACT"
TIER_NORMALIZED = "NORMALIZED"
TIER_STRUCTURAL = "STRUCTURAL"

# 한 티어가 코퍼스의 이 비율 이상을 덮으면 **변별력이 없다**고 보고 저정보 신호로 표시한다.
# 근거: 이 프로젝트에서 두 번 겪었다 - `REMAPRESULTS_DROPPED`가 XSQL 30개 전부에 떠서 결함
# 채점에서 빼야 했고, AST 구조 지문이 메서드 330개를 전부(100%) 5그룹으로 묶어 "중복 후보"로는
# 쓸 수 없었다. 모든 것에 뜨는 신호는 정의상 아무것도 구분해주지 못한다.
LOW_INFORMATION_COVERAGE = 0.90


@dataclass
class DupGroup:
    tier: str
    members: list[tuple[str, str]] = field(default_factory=list)  # (screen_id, method)

    @property
    def size(self) -> int:
        return len(self.members)


def normalize(body: str, screen: str | None = None) -> str:
    """주석·공백 제거. `screen`을 주면 화면 ID까지 자리표시자로 바꾼다(Type-2 정규화)."""
    body = _COMMENT_BLOCK_RE.sub("", body)
    body = _COMMENT_LINE_RE.sub("", body)
    body = _WS_RE.sub(" ", body).strip()
    if screen:
        body = re.sub(re.escape(screen), "{SCREEN}", body, flags=re.I)
    return body


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def structural_fingerprint(body: str) -> str | None:
    """식별자·리터럴을 전부 버리고 **AST 노드 타입 순서**만 해시한다(가장 거친 티어).

    `NORMALIZED`가 화면 ID 문자열만 치환하는 데 반해 이건 이름과 값을 통째로 추상화한다.
    그래서 "같은 틀로 찍어낸 코드"를 잡아낸다 - 정답키의 «구조적 유사(Near-dup)» 범주가 여기
    해당하며, 지금까지는 **탐지 범위 밖**이었다(30행 전부 미커버).

    **변별력의 한계를 그대로 적는다.** 실측 결과 이 지문은 «전역 완전중복»·«도메인 완전중복»·
    «완전 고유»를 **구분하지 못한다** - 셋 다 구조가 같기 때문이다(예: `fHistoryQry`는 도메인별
    6개씩 묶여야 하는데 30개가 한 그룹으로 뭉친다). 따라서 이 티어는 "같은 코드다"가 아니라
    **"같은 틀이니 공통 템플릿 후보다"** 를 뜻하며, 중복 채점(C2)에는 넣지 않는다.
    반대로 `fExcelDownQry`는 정확히 15개(홀수 화면)로 묶여 정답키의 «부분 완전중복»과 일치했다.
    """
    try:
        import java_ast
    except ImportError:
        return None
    if not getattr(java_ast, "TREE_SITTER_AVAILABLE", False):
        return None
    parsed = java_ast._parse(("class X { " + body + " }").encode("utf-8"))
    if parsed is None:
        return None
    tree, _ = parsed
    seq: list[str] = []

    def walk(node) -> None:
        seq.append(node.type)
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return _digest("|".join(seq))


def detect(bodies_by_screen: dict[str, dict[str, str]]) -> dict[str, list[DupGroup]]:
    """{화면: {메서드: 본문}} → 티어별 중복 그룹.

    EXACT에 이미 잡힌 멤버는 NORMALIZED에서 제외한다 - 같은 사실을 두 번 세지 않기 위해서다.
    """
    exact: dict[str, list[tuple[str, str]]] = {}
    norm: dict[str, list[tuple[str, str]]] = {}
    struct: dict[str, list[tuple[str, str]]] = {}
    for screen, methods in bodies_by_screen.items():
        for method, body in methods.items():
            e = normalize(body)
            if not e:
                continue
            exact.setdefault(_digest(e), []).append((screen, method))
            norm.setdefault(_digest(normalize(body, screen)), []).append((screen, method))
            s = structural_fingerprint(body)
            if s:
                struct.setdefault(s, []).append((screen, method))

    exact_groups = [DupGroup(TIER_EXACT, v) for v in exact.values() if len(v) >= 2]
    seen = {m for g in exact_groups for m in g.members}
    norm_groups = [
        DupGroup(TIER_NORMALIZED, [m for m in v if m not in seen])
        for v in norm.values() if len(v) >= 2
    ]
    norm_groups = [g for g in norm_groups if g.size >= 2]
    seen |= {m for g in norm_groups for m in g.members}
    struct_groups = [
        DupGroup(TIER_STRUCTURAL, [m for m in v if m not in seen])
        for v in struct.values() if len(v) >= 2
    ]
    struct_groups = [g for g in struct_groups if g.size >= 2]
    return {TIER_EXACT: exact_groups, TIER_NORMALIZED: norm_groups,
            TIER_STRUCTURAL: struct_groups}


def tier_information(groups: dict[str, list[DupGroup]], corpus_size: int) -> dict[str, dict]:
    """티어별 커버리지·그룹 수와 **저정보 여부**를 판정한다.

    커버리지가 높다고 좋은 게 아니다 - 코퍼스 전체를 소수 그룹으로 묶으면 "무엇이 무엇과 같은지"를
    말해주지 못한다. 숨기지 않고 `low_information` 플래그로 표시해서, 읽는 사람이 변별력 있는
    신호로 착각하지 않게 한다.
    """
    out: dict[str, dict] = {}
    for tier, gs in groups.items():
        members = sum(g.size for g in gs)
        coverage = members / corpus_size if corpus_size else 0.0
        out[tier] = {
            "groups": len(gs),
            "members": members,
            "coverage": round(coverage, 4),
            "avg_group_size": round(members / len(gs), 1) if gs else 0.0,
            "low_information": coverage >= LOW_INFORMATION_COVERAGE,
        }
    return out


def members_by_tier(groups: dict[str, list[DupGroup]]) -> dict[str, set[tuple[str, str]]]:
    return {tier: {m for g in gs for m in g.members} for tier, gs in groups.items()}


def summarize(groups: dict[str, list[DupGroup]]) -> dict:
    ex, no = groups[TIER_EXACT], groups[TIER_NORMALIZED]
    st = groups.get(TIER_STRUCTURAL, [])
    return {
        "exact_groups": len(ex),
        "exact_members": sum(g.size for g in ex),
        "normalized_groups": len(no),
        "normalized_members": sum(g.size for g in no),
        "structural_groups": len(st),
        "structural_members": sum(g.size for g in st),
        "note": (
            "EXACT는 주석·공백만 다른 확실한 복붙, NORMALIZED는 화면 ID를 치환하면 같아지는 "
            "**검토 후보**, STRUCTURAL은 이름·값을 전부 추상화했을 때 같은 틀인 **공통 템플릿 "
            "후보**다(같은 코드라는 뜻이 아니다). 어느 티어도 자동 삭제하지 않는다."
        ),
    }
