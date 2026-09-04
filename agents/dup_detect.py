"""화면 경계를 넘는 중복 함수 탐지 — **신뢰 수준을 나눠서** 보고한다.

기존 탐지는 "중복이다/아니다" 이진 판정이었다. 그런데 실측해보니 두 종류가 섞여 있었다:

  - **EXACT**: 주석·공백만 빼면 텍스트가 그대로 같다. 복붙이 확실하다.
  - **NORMALIZED**: 화면 ID를 자리표시자로 바꾸면 같아진다. 화면마다 자기 D 클래스명을 담고 있을
    뿐 로직은 동일한 경우인데, "정말 같은 로직"일 수도 있고 "구조만 같고 의도는 다른" 경우일
    수도 있다.

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


def detect(bodies_by_screen: dict[str, dict[str, str]]) -> dict[str, list[DupGroup]]:
    """{화면: {메서드: 본문}} → 티어별 중복 그룹.

    EXACT에 이미 잡힌 멤버는 NORMALIZED에서 제외한다 - 같은 사실을 두 번 세지 않기 위해서다.
    """
    exact: dict[str, list[tuple[str, str]]] = {}
    norm: dict[str, list[tuple[str, str]]] = {}
    for screen, methods in bodies_by_screen.items():
        for method, body in methods.items():
            e = normalize(body)
            if not e:
                continue
            exact.setdefault(_digest(e), []).append((screen, method))
            norm.setdefault(_digest(normalize(body, screen)), []).append((screen, method))

    exact_groups = [DupGroup(TIER_EXACT, v) for v in exact.values() if len(v) >= 2]
    seen = {m for g in exact_groups for m in g.members}
    norm_groups = [
        DupGroup(TIER_NORMALIZED, [m for m in v if m not in seen])
        for v in norm.values() if len(v) >= 2
    ]
    norm_groups = [g for g in norm_groups if g.size >= 2]
    return {TIER_EXACT: exact_groups, TIER_NORMALIZED: norm_groups}


def members_by_tier(groups: dict[str, list[DupGroup]]) -> dict[str, set[tuple[str, str]]]:
    return {tier: {m for g in gs for m in g.members} for tier, gs in groups.items()}


def summarize(groups: dict[str, list[DupGroup]]) -> dict:
    ex, no = groups[TIER_EXACT], groups[TIER_NORMALIZED]
    return {
        "exact_groups": len(ex),
        "exact_members": sum(g.size for g in ex),
        "normalized_groups": len(no),
        "normalized_members": sum(g.size for g in no),
        "note": (
            "EXACT는 주석·공백만 다른 확실한 복붙이고, NORMALIZED는 화면 ID를 치환하면 같아지는 "
            "**검토 후보**다. 자동 삭제하지 않는다."
        ),
    }
