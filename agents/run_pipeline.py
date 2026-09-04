"""터미널에서 변환 파이프라인을 돌리는 CLI 진입점.

**왜 필요한가**: 지금까지 파이프라인을 실행하는 유일한 경로가 Streamlit UI(`chatui/app.py`)였다.
그런데 파이프라인이 내리는 판단(어떤 메서드를 LLM에 보낼지, 검증 실패를 수리 루프로 되돌릴지,
예산을 소진했으니 포기할지)은 UI의 진행 바로는 드러나지 않는다 - 결과만 보이고 과정이 안 보인다.
이 CLI는 같은 `run_pipeline_part_a()`를 그대로 부르면서 `agents/reasoning_log`를 켜서, 그 판단
과정을 콘솔에 구조화해 출력한다.

**저장하지 않는다.** UI 경로와 동일하게 사람 승인 게이트 앞에서 멈춘다 - `pilot/`이나 DB에는
아무것도 쓰지 않는다(계획 파일과 인수인계 문서만 `tracking/` 아래에 기록된다. 이 둘은 정의상
승인 *이전에* 있어야 하는 산출물이다). 저장은 여전히 UI에서 사람이 눌러야 진행된다.

사용:
    python -m agents.run_pipeline <AS-IS 폴더>
    python -m agents.run_pipeline <폴더> --screens PLA047,PLA081 --no-ai-recommend
    python -m agents.run_pipeline <폴더> --dry-run     # LLM 호출 없이 규칙 기반 단계까지만

옵션:
    --screens A,B,C      대상 화면을 좁힌다(기본: 폴더 안 전체)
    --limit N            앞에서 N개 화면만
    --no-ai-recommend    7단계(AI 추천) 생략 - LLM 호출을 줄인다
    --repair-rounds N    자기 수정 라운드 상한(기본 2)
    --no-color           ANSI 색 끄기(녹화 도구가 색을 못 다룰 때)
    --dry-run            LLM을 호출하지 않는다(계획·규칙 기반 변환·검증 경로만 확인)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_PROJECT_ROOT), str(_PROJECT_ROOT / "chatui")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agents.run_pipeline")
    ap.add_argument("folder", help="AS-IS 소스 폴더 (P/F/D .java, .bizunit, .xsql)")
    ap.add_argument("--screens", default="", help="쉼표로 구분한 대상 화면 ID")
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N개 화면만")
    ap.add_argument("--no-ai-recommend", action="store_true")
    ap.add_argument("--repair-rounds", type=int, default=2)
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="LLM 호출 없이 규칙 기반 경로만")
    args = ap.parse_args(argv)

    if args.no_color:
        import os
        os.environ["GSCM_LOG_COLOR"] = "0"

    from agents.reasoning_log import log
    log.enable()

    folder = Path(args.folder).expanduser().resolve()
    if not folder.is_dir():
        print(f"폴더가 없습니다: {folder}", file=sys.stderr)
        return 2

    from agents.source_scan import guess_package, scan_folder

    screens, all_paths, problems = scan_folder(folder)
    for p in problems:
        log.observe(f"스캔 경고: {p}")

    if args.screens:
        want = {s.strip().upper() for s in args.screens.split(",") if s.strip()}
        screens = {k: v for k, v in screens.items() if k.upper() in want}
    if args.limit > 0:
        screens = dict(sorted(screens.items())[: args.limit])

    if not screens:
        print(f"대상 화면이 없습니다: {folder}", file=sys.stderr)
        return 1

    # 패키지 좌표는 AS-IS 경로에서 뽑는다. 못 뽑으면 TODO로 둔다 - 추측해서 채우지 않는다
    # (잘못된 패키지로 생성하면 계층 간 참조 검증이 엉뚱하게 통과/실패한다).
    package_map = {}
    for sid in screens:
        package_map[sid] = guess_package(all_paths.get(sid, {})) or ("TODO", "TODO")
    unknown = [s for s, pkg in package_map.items() if pkg == ("TODO", "TODO")]
    if unknown:
        log.observe(f"패키지 좌표 미확인 {len(unknown)}건 → TODO로 둠",
                    "AS-IS 경로에 r/{p1}/{p2} 패턴이 없다 — 추측해서 채우지 않는다")

    if args.dry_run:
        # LLM Gateway를 부르지 않고 "호출했다면 이런 프롬프트였다"만 남긴다. 네트워크·키 없이도
        # 계획→규칙기반변환→검증→게이트 경로 전체를 그대로 재현할 수 있어서 시연 리허설에 쓴다.
        import agents.workflow_graph as wg

        def _stub(messages, **_kw):
            raise RuntimeError("--dry-run: LLM 호출 안 함")

        wg.chat = _stub  # type: ignore[assignment]
        log.observe("--dry-run 모드", "LLM Gateway를 호출하지 않는다 — 포팅 대상은 실패로 기록된다")

    from agents.workflow_graph import run_pipeline_part_a

    state = run_pipeline_part_a(
        screens=screens,
        package_map=package_map,
        include_ai_recommend=not args.no_ai_recommend,
        max_repair_retries=args.repair_rounds,
        all_paths=all_paths,
    )

    n_block = sum(
        len([i for r in results for i in r.issues if i.severity == "BLOCKER"])
        for results in state.get("validation_results", {}).values()
    )
    return 1 if n_block else 0


if __name__ == "__main__":
    raise SystemExit(main())
