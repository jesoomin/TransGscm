"""사람 리뷰 워크플로 — AI 생성물을 사람이 고치고, 그 수정을 실제로 반영·측정한다.

**왜 필요한가**: `agents/human_edit.py`는 "생성분 vs 현재 파일"을 줄 단위로 세는 *측정기*였지만,
그 «현재 파일»이 어디서 오는지는 아무도 관리하지 않았다. `tracking/reviewed/`는 지난 세션에
사람이 손으로 채운 폴더였고, 파이프라인을 다시 돌려 생성분이 바뀌어도 리뷰본은 그대로 남아서
**옛 리뷰본과 새 생성분을 비교한 엉뚱한 수치**가 나왔다(4.34% → 15.3% → 다시 4.34%로 오간
적이 있다). 즉 측정할 수단은 있었지만 **리뷰라는 절차 자체가 없었다.**

이 CLI가 그 절차다. 네 단계뿐이고, 각 단계가 하는 일은 파일 복사와 해시 비교가 전부다 —
LLM을 부르지 않고, `pilot/`을 건드리지 않는다(승인 게이트 보장 유지).

    python -m agents.review status                     # 화면별 리뷰 상태
    python -m agents.review open PLA096 --reviewer 홍길동   # 리뷰 작업본 펼치기
    (사람이 tracking/reviewed/PLA096/ 안의 파일을 에디터로 직접 수정)
    python -m agents.review measure --json tracking/human-edit-5screens.json
    python -m agents.review accept PLA096              # 리뷰 완료 표시

**낡음(stale) 판정**: `open` 시점에 생성 스냅샷의 파일별 해시를 `_review.json`에 적어둔다.
이후 파이프라인을 다시 돌려 생성분이 바뀌면 `measure`가 그 화면을 **미측정**으로 표시하고
이유를 말한다 — 0%로도, 큰 수치로도 보고하지 않는다. "안 고쳤다" / "못 쟀다" / "낡은 기준으로
쟀다"는 전부 다른 상태다.

**수정이 실제로 반영되는 지점**: `accept`된 리뷰본은 `load_current_files()`가 돌려주는 «현재»
산출물이 되고, L3 실행 하네스(`agents/equivalence_test.py --use-reviewed`)가 그걸 컴파일해
AS-IS와 비교한다. 사람이 고친 코드가 측정 대상이 된다는 뜻이다 — 고쳐놓고 아무도 안 돌려보는
상태를 만들지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agents.human_edit import (  # noqa: E402
    REVIEWED_DIR,
    SNAPSHOT_DIR,
    accept_review,
    load_current_files,
    measure_all,
    measure_screen,
    open_review,
    read_review_meta,
    review_staleness,
)


def _snapshot_screens() -> list[str]:
    if not SNAPSHOT_DIR.is_dir():
        return []
    return sorted(p.name for p in SNAPSHOT_DIR.iterdir() if p.is_dir())


def _resolve(screens: str) -> list[str]:
    known = _snapshot_screens()
    if not screens:
        return known
    want = {s.strip().upper() for s in screens.split(",") if s.strip()}
    return [s for s in known if s.upper() in want]


def _state(screen_id: str) -> tuple[str, str]:
    """(상태, 설명) — 리뷰 진행 상황을 한 단어로 요약한다."""
    meta = read_review_meta(screen_id)
    if meta is None:
        return "미시작", "생성분만 있고 리뷰 작업본이 없음"
    drift = review_staleness(screen_id)
    if drift:
        return "낡음", f"재생성으로 {len(drift)}개 파일이 바뀜 — open으로 다시 시작 필요"
    if meta.get("accepted_at"):
        who = meta.get("reviewer") or "미기재"
        return "완료", f"{meta['accepted_at']} · 리뷰어 {who}"
    return "진행중", f"{meta.get('opened_at')} 시작 · 아직 accept 안 됨"


def cmd_status(args) -> int:
    screens = _resolve(args.screens)
    if not screens:
        print(f"생성 스냅샷이 없습니다: {SNAPSHOT_DIR}", file=sys.stderr)
        return 1
    print("=" * 78)
    print("  사람 리뷰 상태")
    print("=" * 78)
    for sid in screens:
        state, note = _state(sid)
        edit = measure_screen(sid, load_current_files(sid))
        ratio = f"{edit.ratio:.1%}" if edit.ratio is not None else "—"
        print(f"  {sid:<10} {state:<6} 수정 {ratio:>6}  {note}")
    print("-" * 78)
    print(f"  작업본: {REVIEWED_DIR}")
    return 0


def cmd_open(args) -> int:
    screens = _resolve(args.screens)
    if not screens:
        print("대상 화면이 없습니다(생성 스냅샷 기준).", file=sys.stderr)
        return 1
    for sid in screens:
        dst, kept = open_review(sid, reviewer=args.reviewer, reset=args.reset)
        print(f"  {sid}: 리뷰 작업본 → {dst}")
        if kept:
            # 사람이 이미 손댄 파일을 새 생성분으로 덮어쓰지 않았다는 뜻이다. 조용히 넘기면
            # "왜 내 수정이 사라졌지"가 되거나 반대로 "왜 새 코드가 안 들어왔지"가 된다.
            print(f"      ! 기존 수정을 보존한 파일 {len(kept)}건: {', '.join(kept)}")
            print(f"        새 생성분으로 갈아엎으려면 --reset")
    print("\n  이제 위 폴더의 파일을 직접 수정한 뒤:")
    print("    python -m agents.review measure")
    print("    python -m agents.review accept <화면>")
    return 0


def cmd_measure(args) -> int:
    screens = _resolve(args.screens)
    result = measure_all({sid: load_current_files(sid) for sid in screens})
    print("=" * 78)
    print("  사람 수정 라인 비율 (HUMAN_EDIT_RATIO)")
    print("=" * 78)
    for sid in screens:
        per = result["per_screen"][sid]
        state, _ = _state(sid)
        if per["measured"]:
            print(f"  {sid:<10} {state:<6} {per['edited_lines']:>4}/{per['generated_lines']:<5}줄 "
                  f"({per['ratio']:.1%})")
        else:
            print(f"  {sid:<10} {state:<6} 미측정 — {per['note']}")
    print("-" * 78)
    if result["human_edit_ratio"] is not None:
        print(f"  전체: {result['edited_lines']:,}/{result['generated_lines']:,}줄 "
              f"({result['human_edit_ratio']:.2%}) · 측정 {result['measured_screens']}화면 / "
              f"미측정 {result['unmeasured_screens']}화면")
    else:
        print(f"  측정 가능한 화면이 없습니다 (미측정 {result['unmeasured_screens']}화면)")
    print("\n  ※ 미측정 화면은 분모에서 뺐습니다 — 0%로 섞으면 지표가 좋아 보이게 왜곡됩니다.")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON 저장: {args.json}")
    return 0


def cmd_accept(args) -> int:
    screens = _resolve(args.screens)
    if not screens:
        print("대상 화면이 없습니다.", file=sys.stderr)
        return 1
    rc = 0
    for sid in screens:
        drift = review_staleness(sid)
        if drift:
            # 낡은 리뷰본을 완료로 찍으면 그 뒤 측정이 전부 거짓이 된다 - 여기서 막는다.
            print(f"  {sid}: 거부 — 리뷰본이 이전 생성분 기준입니다({len(drift)}개 파일 변경). "
                  f"`review open {sid}`로 다시 시작하세요.", file=sys.stderr)
            rc = 1
            continue
        meta = accept_review(sid, reviewer=args.reviewer)
        edit = measure_screen(sid, load_current_files(sid))
        ratio = f"{edit.ratio:.1%}" if edit.ratio is not None else "—"
        print(f"  {sid}: 리뷰 완료 ({meta['accepted_at']}) · 수정 {ratio}")
    return rc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agents.review",
                                 description="AI 생성물에 대한 사람 리뷰 절차")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="화면별 리뷰 상태와 수정 비율")
    s.add_argument("screens", nargs="?", default="", help="쉼표로 구분(기본: 전체)")
    s.set_defaults(func=cmd_status)

    o = sub.add_parser("open", help="리뷰 작업본을 펼치고 기준선을 고정")
    o.add_argument("screens", nargs="?", default="")
    o.add_argument("--reviewer", default="", help="리뷰어 이름(기록용)")
    o.add_argument("--reset", action="store_true",
                   help="이미 수정한 파일도 새 생성분으로 덮어쓴다")
    o.set_defaults(func=cmd_open)

    m = sub.add_parser("measure", help="사람 수정 라인 비율 측정")
    m.add_argument("screens", nargs="?", default="")
    m.add_argument("--json", default="", help="결과를 JSON으로 저장")
    m.set_defaults(func=cmd_measure)

    a = sub.add_parser("accept", help="리뷰 완료로 표시")
    a.add_argument("screens", nargs="?", default="")
    a.add_argument("--reviewer", default="")
    a.set_defaults(func=cmd_accept)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
