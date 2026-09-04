"""파이프라인 실행 결과를 지표로 환산하고 점수로 집계한다.

**왜 만들었나**: 그동안 내세운 수치(매핑 확정률·LLM 호출 감소·결함 탐지율)는 전부 "도구가 잘
돈다"는 얘기지 **"전환이 됐다"** 가 아니었다. 전환 Agent인데 정작 전환 성공률이 없었고,
"개발자가 얼마나 편해졌나"를 말하는 지표도 없었다. 이 모듈이 그 두 구멍을 메운다.

**점수 체계 (총 100점)** — 가중치는 임의값이 아니라 아래 근거로 정했다.

| 축 | 배점 | 왜 이 배점인가 |
|---|---|---|
| A. 전환 성공률 | 40 | 이 도구의 존재 이유. 산출물이 안 나오거나 안 컴파일되면 나머지는 의미 없다 |
| B. 사용자 체감 | 30 | 공수 절감의 대리 지표. 실측(사람 수정 라인)이 불가능한 동안 이걸로 대신한다 |
| C. 탐지 정확성 | 30 | 원본 결함·중복을 찾아주는 부수 가치. 정답키로 채점 가능 |

**정직성 규칙**
- 측정하지 못한 항목은 0점이 아니라 **`미측정`으로 빼고 분모에서도 제외**한다. 못 잰 것을
  0점으로 깎으면 "낮은 점수"가 되고, 만점으로 치면 거짓이 된다. 둘 다 하지 않는다.
- 기능 동등성(L3)과 사람 수정 라인 비율(L4)은 여전히 **미측정**이다. 이 점수는 L1~L2 층과
  그 대리 지표에 대한 것이지 "전환이 기능적으로 맞다"는 뜻이 아니다.

사용:
    python -m agents.scorecard <AS-IS 폴더> --screens PLA087,... [--json 경로]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_PROJECT_ROOT), str(_PROJECT_ROOT / "chatui")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# 지표 계산
# ---------------------------------------------------------------------------

from java_ast import extract_tobe_method_bodies  # noqa: E402
from skeleton_gen import to_prefix  # noqa: E402


def _count_lines(text: str) -> int:
    return text.count("\n") + 1 if text else 0


def conversion_success(state: dict) -> dict:
    """A. 전환 성공률 — 계획한 산출물이 실제로 나왔고, 검증을 통과했는가."""
    plans = state.get("plans", {})
    files = state.get("files", {})
    validation = state.get("validation_results", {})

    # A-1 산출물 생성률: 계획서가 예고한 파일이 실제로 생성됐는가
    expected = produced = 0
    missing: list[str] = []
    for screen_id, plan in plans.items():
        made = set(files.get(screen_id, {}))
        for out in plan.get("expected_outputs", []):
            expected += 1
            if out["file"] in made:
                produced += 1
            else:
                missing.append(f"{screen_id}/{out['file']}")

    # A-2 정적 검증 통과율: BLOCKER가 하나도 없는 파일의 비율
    #     WARNING은 통과로 친다(판정 체계상 저장 가능). SKIPPED는 애초에 파일 판정이 아니다.
    checked = passed = 0
    blocker_files: list[str] = []
    for screen_id, results in validation.items():
        for r in results:
            checked += 1
            if any(i.severity == "BLOCKER" for i in r.issues):
                blocker_files.append(f"{screen_id}/{r.file_name}")
            else:
                passed += 1

    return {
        "outputs_expected": expected,
        "outputs_produced": produced,
        "outputs_rate": round(produced / expected, 4) if expected else None,
        "outputs_missing": missing[:10],
        "checks_total": checked,
        "checks_passed": passed,
        "static_pass_rate": round(passed / checked, 4) if checked else None,
        "blocker_files": blocker_files[:10],
    }


def developer_experience(state: dict) -> dict:
    """B. 사용자 체감 — 개발자가 실제로 덜 하게 된 일의 양.

    사람 수정 라인 비율(L4)을 실측할 수 없는 동안 쓰는 **대리 지표**다. 자동 생성된 코드 중
    사람이 실제로 들여다봐야 하는 지점이 얼마나 적은지를 잰다.
    """
    files = state.get("files", {})
    validation = state.get("validation_results", {})
    review = state.get("review_findings", {})
    plans = state.get("plans", {})

    total_lines = sum(_count_lines(t) for f in files.values() for t in f.values())

    # B-1 리뷰 대상 축소율.
    #
    # **정정(2026-09-05)**: 처음엔 "이슈가 귀속된 줄"만 리뷰 대상으로 셌더니 1,786줄 중 6줄,
    # 축소율 99.7%가 나왔다. 이건 과장이다 - **LLM이 포팅한 메서드는 이슈가 하나도 없어도
    # 사람이 전부 읽어야 한다**(이 프로젝트의 인수인계 문서도 "LLM 포팅 메서드는 반드시 사람
    # 리뷰 필요"로 따로 뽑아준다). 규칙 기반 생성물은 템플릿이 결정론적으로 찍어낸 것이라
    # 같은 수준의 정독이 필요 없지만, LLM 출력은 다르다.
    #
    # 그래서 리뷰 대상 = (LLM이 포팅한 메서드의 전체 라인) ∪ (이슈가 귀속된 줄) 로 센다.
    pending = state.get("pending_methods", {})
    review_lines = 0
    for screen_id, methods in pending.items():
        if not methods:
            continue
        prefix = to_prefix(screen_id)
        service = files.get(screen_id, {}).get(f"{prefix}Service.java", "")
        bodies = extract_tobe_method_bodies(service)
        for m in methods:
            review_lines += _count_lines(bodies.get(m, ""))

    flagged: set[tuple[str, str, int]] = set()
    for screen_id, results in validation.items():
        for r in results:
            for i in r.issues:
                if i.line_no:
                    flagged.add((screen_id, r.file_name, i.line_no))
    for screen_id, per_file in review.items():
        for fname, findings in (per_file or {}).items():
            for f in findings:
                line_no = getattr(f, "line_no", None)
                if line_no:
                    flagged.add((screen_id, fname, line_no))

    # B-2 결정론 처리 비중: 포팅 대상 중 규칙으로 처리해 LLM을 아예 안 부른 비율
    llm = rule = 0
    for plan in plans.values():
        est = plan.get("estimated_llm_calls", {})
        llm += est.get("porting", 0)
        rule += est.get("porting_skipped_rule_based", 0)

    # B-3 추적 작업 제거: 화면당 사람이 열어봐야 했던 AS-IS 파일 수 -> 그래프 조회 1회
    fragments_per_screen = [
        sum(1 for v in plan.get("fragments", {}).values() if v.get("present"))
        for plan in plans.values()
    ]
    avg_fragments = (
        round(sum(fragments_per_screen) / len(fragments_per_screen), 2)
        if fragments_per_screen else None
    )

    # 이슈 줄 중 이미 LLM 포팅 메서드 안에 있는 것은 중복 계산이 될 수 있으나, 보수적으로
    # (=축소율을 낮게 잡는 쪽으로) 그냥 더한다. 과소평가는 감수해도 과대평가는 하지 않는다.
    review_target = review_lines + len(flagged)
    # B-4 사람 수정 라인 비율 (멘토 §H "가장 중요") - 생성 시점 스냅샷이 있어야 측정된다.
    #     스냅샷이 없으면 0%가 아니라 **미측정**이다. "안 고쳤다"와 "못 쟀다"는 다르다.
    from agents.human_edit import load_pilot_files, measure_all
    he = measure_all({sid: load_pilot_files(sid) for sid in files})

    return {
        "human_edit_ratio": he["human_edit_ratio"],
        "human_edit_measured_screens": he["measured_screens"],
        "human_edit_unmeasured_screens": he["unmeasured_screens"],
        "review_acceptance": (1 - he["human_edit_ratio"]) if he["human_edit_ratio"] is not None else None,
        "generated_lines": total_lines,
        "llm_ported_lines": review_lines,
        "flagged_lines": len(flagged),
        "review_target_lines": review_target,
        "review_ratio": round(review_target / total_lines, 4) if total_lines else None,
        "review_reduction": round(1 - review_target / total_lines, 4) if total_lines else None,
        "llm_calls": llm,
        "rule_handled": rule,
        "deterministic_ratio": round(rule / (llm + rule), 4) if (llm + rule) else None,
        "asis_files_per_screen": avg_fragments,
    }


def _load_benchmark(path: Path | None) -> dict | None:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def detection_accuracy(bench: dict | None) -> dict:
    """C. 탐지 정확성 — 정답키가 있는 세트에서만 산출된다. 없으면 미측정."""
    if not bench:
        return {"measured": False}
    err = bench.get("error_detection", {})
    dup = bench.get("duplicate_detection", {}).get("exact_dup", {})
    uni = bench.get("duplicate_detection", {}).get("unique", {})
    # C2는 **EXACT 티어 기준 F1**을 쓴다 - 정규화를 전혀 하지 않는 티어라 «중복»의 정의 논쟁이
    # 점수에 끼어들지 않는다(agents/dup_detect.py 상단 참고). NORMALIZED 티어는 후보 목록으로만
    # 보고하고 채점하지 않는다.
    f1 = bench.get("duplicate_detection", {}).get("f1_exact_tier")
    recall = dup.get("recall_exact_tier")
    precision = bench.get("duplicate_detection", {}).get("exact_tier_precision")
    return {
        "measured": True,
        "defect_recall": err.get("recall"),
        "defect_detected": err.get("detected"),
        "defect_total": err.get("total"),
        "defect_false_positives": len(err.get("false_positive_files", [])),
        "dup_recall_exact_tier": recall,
        "dup_precision_exact_tier": precision,
        "dup_f1_proxy": f1,
        "dup_recall_any_tier": dup.get("recall"),
        "dup_definitional_disagreement":
            bench.get("duplicate_detection", {}).get("definitional_disagreement", {}).get("count"),
    }


# ---------------------------------------------------------------------------
# 점수 집계
# ---------------------------------------------------------------------------

_WEIGHTS = [
    # (축, 항목, 배점, 지표 키, 어디서)
    ("A. 전환 성공률", "산출물 생성률", 15, "outputs_rate", "conversion"),
    ("A. 전환 성공률", "정적 검증 통과율", 25, "static_pass_rate", "conversion"),
    ("B. 사용자 체감", "리뷰 대상 축소율", 14, "review_reduction", "dx"),
    ("B. 사용자 체감", "결정론 처리 비중", 8, "deterministic_ratio", "dx"),
    # 멘토 §H가 "가장 중요"라 한 지표라 B축에서 가장 큰 배점을 준다. 스냅샷이 없으면 미측정으로
    # 빠지고 분모에서도 제외된다 - 지금은 사람 리뷰가 시작되지 않아 대개 미측정이다.
    ("B. 사용자 체감", "사람 수정 수용률", 8, "review_acceptance", "dx"),
    ("C. 탐지 정확성", "원본 결함 재현율", 15, "defect_recall", "detect"),
    ("C. 탐지 정확성", "중복 탐지 F1", 15, "dup_f1_proxy", "detect"),
]


def build_scorecard(state: dict, bench: dict | None = None) -> dict:
    conv = conversion_success(state)
    dx = developer_experience(state)
    det = detection_accuracy(bench)
    src = {"conversion": conv, "dx": dx, "detect": det}

    rows = []
    earned = available = 0.0
    for axis, name, weight, key, where in _WEIGHTS:
        value = src[where].get(key)
        if value is None:
            rows.append({"axis": axis, "item": name, "weight": weight,
                         "value": None, "score": None, "status": "미측정"})
            continue
        score = round(weight * float(value), 2)
        earned += score
        available += weight
        rows.append({"axis": axis, "item": name, "weight": weight,
                     "value": round(float(value), 4), "score": score, "status": "측정"})

    by_axis: dict[str, dict] = {}
    for r in rows:
        a = by_axis.setdefault(r["axis"], {"earned": 0.0, "available": 0.0, "unmeasured": 0})
        if r["score"] is None:
            a["unmeasured"] += r["weight"]
        else:
            a["earned"] += r["score"]
            a["available"] += r["weight"]

    return {
        "rows": rows,
        "by_axis": by_axis,
        "earned": round(earned, 2),
        "available": round(available, 2),
        # 미측정 배점은 분모에서 빼고 환산한다 - 0점 처리도, 만점 처리도 하지 않는다.
        "normalized_100": round(earned / available * 100, 1) if available else None,
        "unmeasured_weight": round(100 - available, 1),
        "detail": {"conversion": conv, "developer_experience": dx, "detection": det},
        "not_covered": [
            "L3 기능 동등성 — 포팅 코드를 실행할 환경이 없어 미측정",
            "L4 사람 수정 라인 비율 — **측정 수단은 구현됨**(agents/human_edit.py). "
            "생성 시점 스냅샷 대비 diff로 산출되며, 사람 리뷰가 시작되면 자동으로 채워진다",
        ],
    }


def render(sc: dict) -> str:
    out = []
    out.append("=" * 78)
    out.append("  전환 파이프라인 스코어카드")
    out.append("=" * 78)
    cur_axis = None
    for r in sc["rows"]:
        if r["axis"] != cur_axis:
            cur_axis = r["axis"]
            out.append(f"\n[{cur_axis}]")
        if r["score"] is None:
            out.append(f"  {r['item']:<18} 배점 {r['weight']:>2}   ─  (미측정)")
        else:
            out.append(f"  {r['item']:<18} 배점 {r['weight']:>2}   {r['value']:>7.1%}  →  {r['score']:>5.2f}점")
    out.append("")
    out.append("-" * 78)
    for axis, a in sc["by_axis"].items():
        if a["available"]:
            out.append(f"  {axis:<16} {a['earned']:>6.2f} / {a['available']:.0f}")
    out.append("-" * 78)
    out.append(f"  합계  {sc['earned']:.2f} / {sc['available']:.0f}"
               f"   →  환산 {sc['normalized_100']}점 / 100")
    if sc["unmeasured_weight"]:
        out.append(f"  (미측정 배점 {sc['unmeasured_weight']:.0f}점은 분모에서 제외 — "
                   f"0점 처리도 만점 처리도 하지 않는다)")
    out.append("=" * 78)

    d = sc["detail"]
    c, x = d["conversion"], d["developer_experience"]
    out.append("\n[근거 수치]")
    out.append(f"  산출물        {c['outputs_produced']}/{c['outputs_expected']}종 생성")
    out.append(f"  정적 검증     {c['checks_passed']}/{c['checks_total']}건 통과")
    if c["blocker_files"]:
        out.append(f"    BLOCKER 잔존: {', '.join(c['blocker_files'])}")
    out.append(f"  생성 라인     {x['generated_lines']:,}줄")
    out.append(f"  리뷰 대상     {x['review_target_lines']}줄 ({x['review_ratio']:.1%}) "
               f"= LLM 포팅 {x['llm_ported_lines']}줄 + 이슈 귀속 {x['flagged_lines']}줄")
    out.append(f"                → 사람이 정독할 곳이 {x['review_reduction']:.1%} 줄어듦 "
               f"(규칙 기반 생성물은 템플릿 결정론 출력)")
    out.append(f"  LLM/규칙      LLM {x['llm_calls']}건 · 규칙 {x['rule_handled']}건 "
               f"(결정론 {x['deterministic_ratio']:.0%})")
    out.append(f"  추적 제거     화면당 AS-IS 파일 평균 {x['asis_files_per_screen']}종 → 그래프 조회 1회")
    if x.get("human_edit_ratio") is not None:
        out.append(f"  사람 수정     {x['human_edit_ratio']:.1%} "
                   f"(측정 {x['human_edit_measured_screens']}화면 / 미측정 {x['human_edit_unmeasured_screens']}화면)")
    else:
        out.append(f"  사람 수정     미측정 — 생성 시점 스냅샷 없음 "
                   f"(대상 {x['human_edit_unmeasured_screens']}화면). 저장 시 스냅샷이 남아야 측정됨")
    out.append("\n[이 점수가 말하지 않는 것]")
    for n in sc["not_covered"]:
        out.append(f"  - {n}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agents.scorecard")
    ap.add_argument("folder")
    ap.add_argument("--screens", default="")
    ap.add_argument("--benchmark", default="tracking/benchmark-081-110.json")
    ap.add_argument("--json", default="")
    ap.add_argument("--no-ai-recommend", action="store_true", default=True)
    ap.add_argument("--quiet-log", action="store_true", help="추론 로그를 끄고 점수만 출력")
    args = ap.parse_args(argv)

    from agents.reasoning_log import log
    if not args.quiet_log:
        log.enable()

    from agents.source_scan import guess_package, scan_folder
    from agents.workflow_graph import run_pipeline_part_a

    folder = Path(args.folder).expanduser().resolve()
    screens, all_paths, _problems = scan_folder(folder)
    if args.screens:
        want = {s.strip().upper() for s in args.screens.split(",") if s.strip()}
        screens = {k: v for k, v in screens.items() if k.upper() in want}
    if not screens:
        print(f"대상 화면이 없습니다: {folder}", file=sys.stderr)
        return 1
    package_map = {sid: (guess_package(all_paths.get(sid, {})) or ("TODO", "TODO")) for sid in screens}

    state = run_pipeline_part_a(
        screens=screens, package_map=package_map,
        include_ai_recommend=False, all_paths=all_paths,
    )
    sc = build_scorecard(state, _load_benchmark(Path(args.benchmark)))
    print(render(sc))
    if args.json:
        Path(args.json).write_text(json.dumps(sc, ensure_ascii=False, indent=2, default=str),
                                   encoding="utf-8")
        print(f"\nJSON 저장: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
