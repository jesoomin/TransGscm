"""전환 분석 결과를 MCP(Model Context Protocol)로 노출하는 **읽기 전용** 서버.

**왜 읽기 전용인가 — 이게 이 모듈의 핵심 설계 결정이다.**

CLAUDE.md와 멘토 코멘트 §I가 똑같이 "완전 자율 탐색형 에이전트를 만들지 않는다(1,416회 반복
작업엔 고정 파이프라인이 낫다)"고 못 박고 있다. MCP의 핵심 가치는 모델이 도구를 동적으로 고르는
것이라, **변환 파이프라인에 MCP를 얹으면 그 원칙과 정면으로 충돌한다.**

그래서 범위를 갈랐다:
  - **변환 실행**: 고정 파이프라인 유지. MCP로 노출하지 않는다. 모델이 "이 화면을 변환해"를
    스스로 호출할 수 있게 만들지 않는다 - 승인 게이트를 우회할 길을 열지 않기 위해서다.
  - **분석 조회**: MCP로 노출한다. 개발자가 IDE에서 "이 함수 바꾸면 어디가 영향받아?"라고
    물으면 모델이 이 도구를 불러 **결정론적 그래프 조회 결과**를 가져온다. 부작용이 없고,
    답에 근거(어느 테이블의 어느 행에서 왔는지)를 그대로 붙일 수 있다.

즉 MCP를 "에이전트에게 자율성을 준다"가 아니라 **"사람이 쓰는 조회 창구를 표준 프로토콜로
연다"** 로 쓴다. 노출하는 함수는 전부 이미 있는 순수 함수라(`agents/*.py`는 Streamlit 의존이
없다) 얇은 어댑터만 씌운다 - 분석 로직을 다시 짜지 않는다.

**노출 도구 4종 (전부 조회, 쓰기 없음)**
  - `impact_of_method`   : 함수 하나를 바꿀 때 영향받는 상위 함수·화면·트랜잭션 (역방향 BFS)
  - `unused_methods`     : 아무도 호출하지 않는 함수 후보
  - `duplicate_methods`  : 화면 경계를 넘는 중복 함수
  - `nctrid_map`         : 화면↔트랜잭션 매핑

**실행**
    python -m agents.mcp_server            # stdio 트랜스포트
의존성: `pip install mcp`. 설치돼 있지 않으면 임포트 시점에 안내 메시지를 낸다.

**한계(그대로 노출한다)**
  - DB에 적재된 내용만 답한다. 아직 저장하지 않은 배치 결과는 보이지 않는다.
  - 콜그래프가 P→F, F→D와 한정자 없는 호출까지만 잡으므로 "호출자 0건"이 곧 미사용을 뜻하지
    않는다. 결과에 이 한계를 같이 실어 보낸다.
"""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_PROJECT_ROOT), str(_PROJECT_ROOT / "chatui")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_CAVEAT = (
    "이 결과는 DB에 적재된 분석분 기준이며, 아직 저장되지 않은 변환 배치는 포함되지 않습니다. "
    "콜그래프는 P→F·F→D 및 한정자 없는 호출까지만 잡으므로 '호출자 0건'이 곧 미사용을 뜻하지 "
    "않습니다 — 확정 판정이 아니라 검토 후보로 다루세요."
)


def _tools() -> list[dict]:
    """노출할 도구의 스펙. 서버 구현과 분리해 두면 테스트에서 그대로 검사할 수 있다."""
    return [
        {
            "name": "impact_of_method",
            "description": "지정한 함수를 변경할 때 영향받는 상위 함수·화면·트랜잭션을 콜그래프 "
                           "역방향 BFS로 조회합니다. LLM 추론이 아니라 결정론적 그래프 순회입니다.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "method_name": {"type": "string", "description": "대상 함수명 (예: dPLA04702)"},
                    "screen_id": {"type": "string", "description": "화면 ID로 범위를 좁힐 때"},
                    "max_depth": {"type": "integer", "description": "역추적 최대 깊이 (기본 5)"},
                },
                "required": ["method_name"],
            },
        },
        {
            "name": "unused_methods",
            "description": "진입점에서 콜그래프를 타고 내려가도 한 번도 호출되지 않는 F/D 함수 "
                           "후보를 조회합니다. 삭제하지 않고 후보만 반환합니다.",
            "inputSchema": {"type": "object", "properties": {
                "screen_id": {"type": "string", "description": "화면 ID로 범위를 좁힐 때"}}},
        },
        {
            "name": "duplicate_methods",
            "description": "본문 해시가 같아 화면 경계를 넘어 중복된 함수 그룹을 조회합니다.",
            "inputSchema": {"type": "object", "properties": {
                "min_group_size": {"type": "integer", "description": "최소 그룹 크기 (기본 2)"}}},
        },
        {
            "name": "nctrid_map",
            "description": "화면↔트랜잭션(nctRid) 매핑을 조회합니다. 값의 출처(확정/파생)도 함께 "
                           "반환합니다.",
            "inputSchema": {"type": "object", "properties": {
                "screen_id": {"type": "string", "description": "화면 ID로 범위를 좁힐 때"}}},
        },
    ]


def call_tool(name: str, args: dict) -> dict:
    """도구 하나를 실행한다. **조회만 한다 — 쓰기·삭제 경로가 없다.**

    서버 트랜스포트와 분리해 둬서, MCP 패키지가 없는 환경에서도 이 함수만 직접 호출해
    동작을 확인할 수 있다.
    """
    from agents import db, impact_analysis

    if name == "impact_of_method":
        result = impact_analysis.find_impact_of_method(
            method_name=args["method_name"],
            screen_id=args.get("screen_id"),
            max_depth=int(args.get("max_depth", 5)),
        )
        return {"result": result, "caveat": _CAVEAT}

    if name == "unused_methods":
        rows = impact_analysis.find_unused_methods(screen_id=args.get("screen_id"))
        return {"count": len(rows), "rows": rows[:200], "caveat": _CAVEAT}

    if name == "duplicate_methods":
        rows = db.find_duplicate_methods(min_group_size=int(args.get("min_group_size", 2)))
        return {"count": len(rows), "rows": rows[:200], "caveat": _CAVEAT}

    if name == "nctrid_map":
        rows = db.get_nctrid_map(screen_id=args.get("screen_id"))
        return {"count": len(rows), "rows": rows[:500], "caveat": _CAVEAT}

    raise ValueError(f"알 수 없는 도구: {name}")


def main() -> int:
    """stdio 트랜스포트로 서버를 띄운다.

    설치된 SDK가 mcp 2.x라 `MCPServer`(구 FastMCP)를 쓴다 - 1.x의 `Server` + 수동 데코레이터
    방식은 이 버전에 `list_tools` 속성이 없어 그대로는 뜨지 않는다(실제로 겪어서 고쳤다).
    도구 본체는 `call_tool()` 하나로 모아 두고 여기서는 얇게 감싸기만 한다 - 조회 로직을
    트랜스포트에 섞지 않기 위해서다.
    """
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError:
        print(
            "MCP 패키지가 없거나 버전이 맞지 않습니다. `pip install mcp` 후 다시 실행하세요.\n"
            "설치 없이 도구 동작만 확인하려면 agents.mcp_server.call_tool()을 직접 호출하면 됩니다.",
            file=sys.stderr,
        )
        return 2

    server = MCPServer(name="gscm-conversion-analysis")
    specs = {t["name"]: t for t in _tools()}

    @server.tool(name="impact_of_method", description=specs["impact_of_method"]["description"])
    def impact_of_method(method_name: str, screen_id: str | None = None,
                         max_depth: int = 5) -> dict:
        return call_tool("impact_of_method", {
            "method_name": method_name, "screen_id": screen_id, "max_depth": max_depth})

    @server.tool(name="unused_methods", description=specs["unused_methods"]["description"])
    def unused_methods(screen_id: str | None = None) -> dict:
        return call_tool("unused_methods", {"screen_id": screen_id})

    @server.tool(name="duplicate_methods", description=specs["duplicate_methods"]["description"])
    def duplicate_methods(min_group_size: int = 2) -> dict:
        return call_tool("duplicate_methods", {"min_group_size": min_group_size})

    @server.tool(name="nctrid_map", description=specs["nctrid_map"]["description"])
    def nctrid_map(screen_id: str | None = None) -> dict:
        return call_tool("nctrid_map", {"screen_id": screen_id})

    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
