"""조회 패널 전용 도구 — 사용법 안내와 AS-IS 소스 열람.

**왜 MCP 서버에 넣지 않았나.** `agents/mcp_server.py`의 4종은 *외부 클라이언트*에 여는 표면이고,
거기 노출하는 건 콜그래프·매핑 같은 **메타데이터**다. 여기 두 도구는 **소스 본문**과 화면별
리포트를 돌려주므로 성격이 다르다 - 사내 소스를 범용 프로토콜 엔드포인트로 흘려보내지 않는다는
게 이 프로젝트의 보안 전제다(CLAUDE.md "소스코드 외부 전송" 항목). 그래서 로컬 UI 패널에서만
쓴다. 도구 정의는 여전히 **한 곳에만** 있다.

세 도구 모두 **읽기만 한다.** 쓰기·삭제·변환 실행 경로가 없다.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN_DIR = ROOT / "tracking" / "conversion-plans"
REPORT_DIR = ROOT / "tracking" / "conversion-reports"

MAX_SOURCE_CHARS = 6000  # 메서드 본문이 3만 자를 넘는 사례가 있어 상한을 둔다

# 사용법 기준 문서. 여기 숫자가 바뀌면 파이프라인도 바뀐 것이므로 함께 고쳐야 한다
# (tests/test_query_tools.py가 판정 6종·단계 8개를 대조한다).
USAGE = {
    "파이프라인": """폴더를 지정하면 8단계가 순서대로 진행된다.
  1 계획 수립 — 메서드마다 규칙/LLM을 가르고 계획 파일로 고정한다 (LLM 미사용)
  2 규칙 기반 변환 — SQL 문법 치환, 코드 뼈대·DTO 생성 (LLM 미사용)
  3 LLM 포팅 — 계산·분기가 있는 본문만. 계획이 지목한 대상에만 호출한다
  4 정적 검증 — 변환기와 분리된 검증기
  5 자가 교정 — 검증 실패 시에만. 회차 상한 2
  6 동작 일치 검증 — AS-IS/TO-BE를 같은 입력으로 실행해 비교
  7 품질·취약점 스캔
  8 AI 추천 (선택 실행)
승인 전에는 산출물 폴더와 DB에 아무것도 쓰지 않는다. '승인하고 저장'을 눌러야 반영된다.""",
    "판정체계": """판정은 6종이다.
  PASS      통과
  WARNING   주의 — 저장은 가능하지만 사람이 읽어야 한다
  BLOCKER   차단 — 이 상태로는 정상 동작을 보장할 수 없다. 하나라도 있으면 저장이 막힌다
  FAIL      검사 자체가 실패
  SKIPPED   미지원·미측정 — PASS로 집계하지 않는다
  APPROVED  사람이 승인함
원본 결함은 도구의 실패와 구분해 따로 표시한다.""",
    "승인게이트": """1~8단계는 자동으로 진행되지만 반영은 사람이 결정한다.
  · 승인 전 검증은 임시 사본에서 하고 끝나면 항상 지운다 — 실제 산출물 폴더는 그대로다
  · BLOCKER가 하나라도 남으면 저장 버튼이 열리지 않는다
  · git 커밋·배포는 이 도구가 하지 않는다. 사람이 직접 한다""",
    "소스세트": """세트를 섞어 인용하면 틀린 주장이 된다.
  · 실제 전환 대상   PLA045~050 — 운영 소스 트리. 정답이 없어 채점은 불가
  · 매핑 검증 세트   50화면 — 메타 파일이 있어 트랜잭션 확정률을 잰다
  · 정답키 평가 세트 30화면 — 결함과 중복의 정답키가 있어 탐지 성능을 채점한다""",
    "조회기능": """이 패널이 답할 수 있는 것
  · 영향 범위   이 함수를 고치면 어디가 영향받나 (호출 관계도 역추적)
  · 미사용 함수 아무도 호출하지 않는 함수 후보
  · 중복 함수   화면 경계를 넘어 본문이 같은 함수
  · 매핑 조회   화면↔트랜잭션 매핑
  · 화면 리포트 화면별 변환 계획과 원본 상태
  · 소스 열람   AS-IS 원본의 메서드 본문
할 수 없는 것: 코드 수정·저장·변환 실행. 이 패널은 조회 전용이다.""",
}


def tools() -> list[dict]:
    """이 모듈이 제공하는 도구 스펙(MCP와 같은 모양)."""
    return [
        {
            "name": "how_to_use",
            "description": "이 전환 도구의 사용법·단계·판정 체계·소스 세트 구분을 설명합니다. "
                           "'어떻게 쓰나', 'BLOCKER가 뭔가', '언제 저장하나' 같은 질문에 씁니다.",
            "inputSchema": {"type": "object", "properties": {"topic": {
                "type": "string",
                "enum": sorted(USAGE.keys()),
                "description": "주제. 생략하면 전체를 돌려줍니다."}}},
        },
        {
            "name": "screen_report",
            "description": "화면 하나의 변환 계획과 원본 상태를 조회합니다 — 구성 파일, LLM 포팅 "
                           "대상, 미지원 DB 동사, 원본이 컴파일되는지 여부(중괄호 불균형) 등. "
                           "'이 화면 왜 안 되나', '무엇을 LLM이 옮겼나'에 씁니다.",
            "inputSchema": {"type": "object", "properties": {
                "screen_id": {"type": "string", "description": "화면 ID (예: PLA047)"}},
                "required": ["screen_id"]},
        },
        {
            "name": "read_screen_source",
            "description": "AS-IS 원본의 메서드 본문을 읽습니다. 함수가 실제로 무엇을 하는지 "
                           "물을 때 씁니다. 변환 계획이 기록해 둔 파일만 읽습니다.",
            "inputSchema": {"type": "object", "properties": {
                "screen_id": {"type": "string", "description": "화면 ID (예: PLA047)"},
                "fragment": {"type": "string", "enum": ["P.java", "F.java", "D.java", "D.xsql"],
                             "description": "읽을 구성 파일"},
                "method_name": {"type": "string",
                                "description": "메서드 하나만 볼 때. 생략하면 메서드 목록만 돌려줍니다."}},
                "required": ["screen_id", "fragment"]},
        },
    ]


def _load_plan(screen_id: str) -> dict:
    path = PLAN_DIR / f"{screen_id}-conversion-plan.json"
    if not path.exists():
        available = sorted(p.name.split("-")[0] for p in PLAN_DIR.glob("*-conversion-plan.json"))
        raise FileNotFoundError(
            f"{screen_id}의 변환 계획이 없습니다. 파이프라인을 먼저 돌려야 합니다. "
            f"지금 있는 화면: {', '.join(available) or '없음'}")
    return json.loads(path.read_text(encoding="utf-8"))


def call(name: str, args: dict) -> dict:
    """도구 하나를 실행한다. **읽기 전용** — 쓰기 경로가 없다."""
    if name == "how_to_use":
        topic = args.get("topic")
        if topic and topic in USAGE:
            return {"topic": topic, "text": USAGE[topic]}
        return {"topic": "전체", "text": "\n\n".join(
            f"[{k}]\n{v}" for k, v in USAGE.items())}

    if name == "screen_report":
        plan = _load_plan(args["screen_id"])
        sig = plan.get("track_signals", {})
        out = {
            "screen_id": plan.get("screen_id"),
            "구성_파일": {k: {"있음": v.get("present"), "줄수": v.get("lines")}
                       for k, v in plan.get("fragments", {}).items()},
            "트랜잭션": plan.get("nctrids", []),
            "LLM_포팅_대상": plan.get("llm_porting_targets", []),
            "LLM_포팅_대상_Api": plan.get("llm_porting_targets_api", []),
            "규칙_기반_위임": plan.get("rule_based_delegations", {}),
            "미지원_DB_동사": plan.get("unsupported_db_verbs", {}),
            "원본이_컴파일되지_않음": sig.get("as_is_source_broken"),
            "중괄호_불균형": sig.get("as_is_unbalanced_braces", {}),
            "트랙": plan.get("track"),
        }
        report = REPORT_DIR / f"{args['screen_id']}-handoff.md"
        if report.exists():
            out["인수인계_문서_앞부분"] = report.read_text(encoding="utf-8")[:1500]
        return out

    if name == "read_screen_source":
        plan = _load_plan(args["screen_id"])
        frag = args["fragment"]
        info = plan.get("fragments", {}).get(frag)
        if not info or not info.get("present"):
            have = [k for k, v in plan.get("fragments", {}).items() if v.get("present")]
            return {"error": f"{args['screen_id']}에 {frag}가 없습니다. 있는 것: {have}"}

        # **계획서가 기록한 경로만 읽는다.** 사용자가 준 경로를 그대로 열지 않으므로
        # 경로 탐색으로 .env 같은 파일에 닿을 길이 없다.
        path = Path(info["as_is_path"])
        if not path.exists():
            return {"error": f"기록된 원본 경로가 지금은 없습니다: {path.name}"}
        text = path.read_text(encoding="utf-8", errors="replace")

        if frag.endswith(".xsql"):
            return {"file": path.name, "길이": len(text), "본문": text[:MAX_SOURCE_CHARS]}

        import sys
        sys.path.insert(0, str(ROOT / "chatui"))
        from skeleton_gen import extract_method_bodies, extract_methods

        names = extract_methods(text)
        wanted = args.get("method_name")
        if not wanted:
            return {"file": path.name, "메서드": names,
                    "안내": "method_name을 지정하면 그 본문을 돌려줍니다."}
        if wanted not in names:
            return {"error": f"{path.name}에 {wanted}가 없습니다. 있는 메서드: {names}"}
        body = extract_method_bodies(text).get(wanted, "")
        return {"file": path.name, "method": wanted, "길이": len(body),
                "본문": body[:MAX_SOURCE_CHARS],
                "잘림": len(body) > MAX_SOURCE_CHARS}

    raise ValueError(f"알 수 없는 도구: {name}")
