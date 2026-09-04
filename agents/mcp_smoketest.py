"""MCP 서버를 **실제 클라이언트로 붙여서** 도구 목록과 호출을 확인하는 스모크 테스트.

`agents/mcp_server.py`의 `call_tool()`을 직접 부르는 것과 이건 다르다 - 여기서는 stdio
트랜스포트로 별도 프로세스를 띄우고, MCP 클라이언트 세션을 열어 `list_tools()` / `call_tool()`을
프로토콜을 통해 주고받는다. "만들었다"와 "붙여봤다"를 구분하기 위한 검증이다.

실행:
    python -m agents.mcp_smoketest
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


async def _run() -> int:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        print("mcp 패키지가 없습니다. `pip install mcp` 후 실행하세요.", file=sys.stderr)
        return 2

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "agents.mcp_server"],
        cwd=str(_PROJECT_ROOT),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listed = await session.list_tools()
            names = [t.name for t in listed.tools]
            print(f"[1] list_tools  → {len(names)}종: {', '.join(names)}")
            expected = {"impact_of_method", "unused_methods", "duplicate_methods", "nctrid_map"}
            if set(names) != expected:
                print(f"    기대와 다름: {expected - set(names)} 누락", file=sys.stderr)
                return 1

            # 조회 도구를 실제로 프로토콜 너머로 호출한다.
            checks = [
                ("impact_of_method", {"method_name": "dPLA04702"}),
                ("unused_methods", {}),
                ("duplicate_methods", {}),
                ("nctrid_map", {"screen_id": "PLA047"}),
            ]
            for name, args in checks:
                res = await session.call_tool(name, args)
                text = res.content[0].text if res.content else "{}"
                payload = json.loads(text)
                if "error" in payload:
                    print(f"[!] {name} → 오류: {payload['error']}", file=sys.stderr)
                    return 1
                summary = (
                    f"count={payload['count']}" if "count" in payload
                    else f"keys={sorted(payload.get('result', {}))[:4]}"
                )
                has_caveat = "caveat" in payload
                print(f"[2] call_tool  {name:<20} → {summary} · 한계문구 {'포함' if has_caveat else '없음'}")

            print("\nMCP 클라이언트 연결 확인 완료 — 프로토콜 너머로 4종 전부 응답")
            return 0


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    raise SystemExit(main())
