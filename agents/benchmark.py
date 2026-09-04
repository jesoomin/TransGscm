"""정답키가 있는 샘플 세트로 탐지 성능을 채점하는 자체 벤치마크.

멘토 코멘트 §H("내부 벤치마크를 먼저 만들어야 개선 여부를 측정할 수 있다")에 대한 응답이다.
그동안 이 프로젝트의 탐지 기능(원본 결함 탐지, 중복 함수 탐지)은 "돌려보니 N건 나왔다"까지만
말할 수 있었다 - **정답을 몰라서 그 N건이 맞는지, 놓친 게 몇 건인지 말할 수 없었다.**

`PLA081-110_migration_sample`은 정답키를 함께 제공한다:
  - `error_injection_answer_key_081-110.csv` : 의도적으로 심은 결함 10건 (파일·분류·증상)
  - `duplicate_map_answer_key_081-110.csv`   : 화면×멤버별 중복 유형 330행 / 78그룹

이 모듈은 우리 탐지기를 그 정답키와 대조해 **재현율(찾아낸 비율)과 오탐**을 수치로 낸다.
LLM을 쓰지 않는다 - 전부 결정론적 대조라 매번 같은 값이 나오고, 프롬프트/모델을 바꿔도
회귀 측정에 그대로 쓸 수 있다.

**정직성 규칙**: 못 찾은 건 못 찾았다고 센다. 정답키를 보고 탐지 규칙을 역으로 맞추지 않는다 -
그렇게 하면 이 벤치마크가 측정 도구가 아니라 과적합 대상이 된다. 놓친 항목은 "다음에 보강할
목록"으로 그대로 출력한다.

사용:
    python -m agents.benchmark <샘플폴더> --answer-dir <정답키폴더>
    python -m agents.benchmark <샘플폴더> --answer-dir <정답키폴더> --json out.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_PROJECT_ROOT), str(_PROJECT_ROOT / "chatui")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ---------------------------------------------------------------------------
# 결함 탐지 채점
# ---------------------------------------------------------------------------

def _collect_asis_findings(sample_dir: Path) -> dict[str, list[dict]]:
    """AS-IS 원본만 보고(변환 결과가 아니라) 우리 도구가 잡아내는 결함을 파일별로 모은다.

    변환 **전** 단계의 탐지만 센다 - 계획 수립 시 원본 손상 신호, XSQL 문법 검사, 미지원 DB 동사,
    D가 참조하는 statement id가 XSQL에 실재하는지. TO-BE 산출물의 검증 결과는 여기 섞지 않는다
    (그건 "원본 결함을 찾았나"가 아니라 "변환 결과가 맞나"라는 다른 질문이다).
    """
    from converters import convert_xsql_fragment
    from java_ast import extract_method_bodies
    from skeleton_gen import extract_d_stmt_ids, unsupported_db_verbs
    from validators import count_unbalanced_braces

    from agents.asis_defects import scan_java_corpus

    findings: dict[str, list[dict]] = defaultdict(list)

    def add(fname: str, kind: str, detail: str) -> None:
        findings[fname].append({"detector": kind, "detail": detail})

    # AS-IS 원본 결함 탐지기(agents/asis_defects.py) - 코퍼스 단위로 한 번에 돌린다.
    java_texts = {
        p.name: p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(sample_dir.glob("*.java"))
    }
    for fname, issues in scan_java_corpus(java_texts).items():
        for i in issues:
            add(fname, i["issue_type"], i["message"])

    for path in sorted(sample_dir.iterdir()):
        if not path.is_file():
            continue
        name = path.name
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if name.lower().endswith(".java"):
            n = count_unbalanced_braces(text)
            if n:
                add(name, "BRACE_IMBALANCE", f"중괄호 불일치 {n}건 — 원본이 그대로는 컴파일되지 않음")
            if name.upper().startswith("D"):
                verbs = unsupported_db_verbs(text)  # {메서드: [verb, ...]}
                if verbs:
                    add(name, "UNSUPPORTED_DB_VERB",
                        "조회 외 DB 동사: " + ", ".join(f"{m}={v}" for m, v in sorted(verbs.items())))

        elif name.lower().endswith(".xsql"):
            result = convert_xsql_fragment(text)
            for issue in result.issues:
                sev = getattr(issue, "severity", "")
                itype = getattr(issue, "issue_type", "")
                # 원본 결함이 아니라 "변환하면서 이렇게 처리했다"는 정보성 알림은 결함 신호로
                # 세지 않는다. REMAPRESULTS_DROPPED는 이 세트의 XSQL 30개 **전부**에 균일하게
                # 떴다(결함을 심은 2개를 뺀 28개가 그대로 오탐으로 집계됐다) - 모든 파일에 똑같이
                # 뜨는 신호는 정의상 결함을 구분해주지 못한다.
                if itype in ("CDATA_SIMPLIFIED", "REMAPRESULTS_DROPPED"):
                    continue
                if sev == "INFO":
                    continue
                add(name, itype or "XSQL_ISSUE", str(getattr(issue, "message", ""))[:200])

    # D 메서드가 부르는 statement id가 실제 XSQL에 있는지 (E7류: 없는 SQL ID 호출)
    for path in sorted(sample_dir.glob("D*.java")):
        xsql = path.with_suffix(".xsql")
        if not xsql.exists():
            continue
        try:
            d_text = path.read_text(encoding="utf-8", errors="replace")
            x_text = xsql.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        defined = set(re.findall(r'\bid\s*=\s*"([^"]+)"', x_text))
        for method, stmt_id in (extract_d_stmt_ids(d_text) or {}).items():
            if stmt_id and stmt_id not in defined:
                findings[path.name].append({
                    "detector": "MISSING_STATEMENT",
                    "detail": f"{method}가 참조하는 statement id '{stmt_id}'가 {xsql.name}에 없음",
                })

    # F/P가 호출하는 하위 메서드가 그 클래스에 실제로 있는지 (E5류: 오타 메서드명)
    for path in sorted(sample_dir.glob("F*.java")):
        screen = path.stem[1:]
        d_path = sample_dir / f"D{screen}.java"
        if not d_path.exists():
            continue
        try:
            f_text = path.read_text(encoding="utf-8", errors="replace")
            d_text = d_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        d_methods = set(extract_method_bodies(d_text))
        for callee in set(re.findall(r"\bdu\.(\w+)\s*\(", f_text)) | set(re.findall(r"\.\s*(d[A-Za-z0-9_]+)\s*\(", f_text)):
            if callee.startswith("d") and d_methods and callee not in d_methods:
                findings[path.name].append({
                    "detector": "UNRESOLVED_CALLEE",
                    "detail": f"{callee}(...)를 호출하지만 D{screen}에 그런 메서드가 없음",
                })
    return dict(findings)


def score_error_detection(sample_dir: Path, answer_csv: Path) -> dict:
    """심어진 결함 정답키와 우리 탐지 결과를 파일 단위로 대조한다."""
    with io.open(answer_csv, encoding="utf-8-sig") as f:
        expected = list(csv.DictReader(f))
    findings = _collect_asis_findings(sample_dir)

    rows = []
    for e in expected:
        fname = e["file"]
        hits = findings.get(fname, [])
        rows.append({
            "issue_id": e["issue_id"],
            "file": fname,
            "category": e["category"],
            "description": e["description"][:120],
            "detected": bool(hits),
            "detected_by": sorted({h["detector"] for h in hits}),
        })

    files_with_injected = {e["file"] for e in expected}
    false_positive_files = sorted(set(findings) - files_with_injected)
    hit = sum(1 for r in rows if r["detected"])
    by_cat: dict[str, dict[str, int]] = defaultdict(lambda: {"hit": 0, "total": 0})
    for r in rows:
        by_cat[r["category"]]["total"] += 1
        by_cat[r["category"]]["hit"] += int(r["detected"])

    return {
        "total": len(rows),
        "detected": hit,
        "recall": round(hit / len(rows), 4) if rows else 0.0,
        "by_category": {k: v for k, v in sorted(by_cat.items())},
        "rows": rows,
        "false_positive_files": [
            {"file": f, "findings": sorted({x["detector"] for x in findings[f]})}
            for f in false_positive_files
        ],
    }


# ---------------------------------------------------------------------------
# 중복 함수 탐지 채점
# ---------------------------------------------------------------------------

_MEMBER_METHODS_RE = re.compile(r"\(([^)]*)\)")


def _normalize_body(body: str, screen: str | None = None) -> str:
    """주석·공백을 제거한 본문. `agents/db.py`의 BODY_HASH와 같은 취지의 정규화다.

    `screen`을 주면 **Type-2 정규화**까지 한다 — 본문에 박혀 있는 자기 화면 ID를 자리표시자로
    치환한다. 이게 없으면 화면마다 복붙된 같은 로직도 자기 D 클래스명(`DPLA081` vs `DPLA082`)
    때문에 텍스트가 갈려 해시가 달라진다. 벤치마크로 확인한 실제 현상이다: 화면 ID를 본문에
    담지 않는 D 계층 메서드는 Type-1 해시로도 잡혔지만, D 클래스를 참조하는 F 계층 메서드는
    전부 놓쳤다(완전중복 재현율이 정확히 절반에서 멈췄고 놓친 목록이 전부 `f*`였다).

    식별자 치환은 클론 탐지에서 Type-2 클론(식별자·리터럴만 다른 복제)을 잡는 표준 방식이다 —
    정답키를 보고 규칙을 맞춘 게 아니라 "화면 간 복붙된 동일 로직을 찾는다"는 원래 목적에 맞는
    알고리즘을 뒤늦게 구현한 것이다.
    """
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
    body = re.sub(r"//[^\n]*", "", body)
    body = re.sub(r"\s+", " ", body).strip()
    if screen:
        body = re.sub(re.escape(screen), "{SCREEN}", body, flags=re.I)
    return body


def score_duplicate_detection(sample_dir: Path, answer_csv: Path) -> dict:
    """티어별 중복 탐지를 정답키와 대조한다(agents/dup_detect.py).

    **채점 대상은 소스에 실제로 존재하는 메서드뿐이다.** 이전 버전은 정답키의 `QrySelectDetail`
    같은 항목을 `f{화면}QrySelectDetail` / `d{화면}QrySelectDetail`로 펼쳤는데, D 계층의 실제
    이름은 `dPLA08102` 형태라 **존재하지 않는 이름 30건이 분모에 섞여** 오탐률이 절반으로
    희석돼 있었다(48%로 보였지만 실재 메서드 기준으로는 훨씬 높다). 실측 채점기가 실재하지
    않는 대상을 세면 안 된다.

    티어 정의와 정답키의 정의가 다른 지점은 `definitional_disagreement`로 **따로 집계**한다 -
    탐지기 오류로도, 정답키 오류로도 몰지 않는다(agents/dup_detect.py 상단 참고).
    """
    from java_ast import extract_method_bodies

    from agents.dup_detect import TIER_EXACT, TIER_NORMALIZED, detect, members_by_tier, summarize

    with io.open(answer_csv, encoding="utf-8-sig") as f:
        expected = list(csv.DictReader(f))

    bodies: dict[str, dict[str, str]] = {}
    for path in sorted(sample_dir.glob("*.java")):
        layer, screen = path.stem[0], path.stem[1:]
        if layer not in ("F", "D"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        bodies.setdefault(screen, {}).update(extract_method_bodies(text))

    existing = {(s, m) for s, ms in bodies.items() for m in ms}
    groups = detect(bodies)
    tiers = members_by_tier(groups)
    detected_any = tiers[TIER_EXACT] | tiers[TIER_NORMALIZED]

    stats = {
        "exact_dup": {"total": 0, "detected": 0, "detected_exact_tier": 0, "missed": []},
        "unique": {"total": 0, "flagged_exact": 0, "flagged_normalized": 0, "examples": []},
        "near_dup_out_of_scope": 0,
        "sql_rows_out_of_scope": 0,
        "phantom_names_skipped": 0,
    }

    for e in expected:
        layer, dup_type, member, screen = e["layer"], e["dup_type"], e["member"], e["screen_id"]
        if layer != "F/D":
            stats["sql_rows_out_of_scope"] += 1
            continue
        m = _MEMBER_METHODS_RE.search(member)
        if m:
            methods = [x.strip() for x in m.group(1).split("/")]
        else:
            base = member.strip()
            methods = [f"f{screen}{base}", f"d{screen}{base}"] if base else []
        if "Near-dup" in dup_type:
            stats["near_dup_out_of_scope"] += 1
            continue
        is_exact = "완전중복" in dup_type
        is_unique = "고유" in dup_type
        for meth in methods:
            key = (screen, meth)
            if key not in existing:      # 소스에 없는 이름은 세지 않는다
                stats["phantom_names_skipped"] += 1
                continue
            if is_exact:
                stats["exact_dup"]["total"] += 1
                stats["exact_dup"]["detected_exact_tier"] += int(key in tiers[TIER_EXACT])
                if key in detected_any:
                    stats["exact_dup"]["detected"] += 1
                else:
                    stats["exact_dup"]["missed"].append(f"{screen}.{meth}")
            elif is_unique:
                stats["unique"]["total"] += 1
                if key in tiers[TIER_EXACT]:
                    stats["unique"]["flagged_exact"] += 1
                    stats["unique"]["examples"].append(f"{screen}.{meth}(EXACT)")
                elif key in tiers[TIER_NORMALIZED]:
                    stats["unique"]["flagged_normalized"] += 1

    ed, un = stats["exact_dup"], stats["unique"]
    ed["recall"] = round(ed["detected"] / ed["total"], 4) if ed["total"] else 0.0
    ed["recall_exact_tier"] = round(ed["detected_exact_tier"] / ed["total"], 4) if ed["total"] else 0.0
    ed["missed"] = ed["missed"][:20]

    # 보수적 정밀도: NORMALIZED 티어가 «고유»를 건드린 것도 전부 오탐으로 친다.
    conservative_fp = un["flagged_exact"] + un["flagged_normalized"]
    un["conservative_precision"] = (
        round(1 - conservative_fp / un["total"], 4) if un["total"] else None)
    # 티어 인지 정밀도: EXACT 티어만 «확실»을 주장하므로 그 티어의 오탐만 센다.
    un["tier_aware_precision"] = (
        round(1 - un["flagged_exact"] / un["total"], 4) if un["total"] else None)

    def _f1(p, r):
        return round(2 * p * r / (p + r), 4) if p and r and (p + r) else 0.0

    stats["f1_conservative"] = _f1(un["conservative_precision"], ed["recall"])
    stats["f1_tier_aware"] = _f1(un["tier_aware_precision"], ed["recall"])
    # **점수에 쓰는 값은 이것이다.** EXACT 티어만으로 정밀도·재현율을 낸다 - 이 티어는 정규화를
    # 전혀 하지 않아 «중복»의 정의 논쟁이 끼어들 여지가 없고(정답키가 «고유»라 한 것 중 EXACT로
    # 잡힌 건 0건), 따라서 티어 정의를 바꿔서 점수를 올릴 수 없다. NORMALIZED는 후보 목록으로만
    # 보고하고 채점에 넣지 않는다.
    exact_precision = (
        round(1 - un["flagged_exact"] / un["total"], 4) if un["total"] else None)
    stats["exact_tier_precision"] = exact_precision
    stats["f1_exact_tier"] = _f1(exact_precision, ed["recall_exact_tier"])
    stats["definitional_disagreement"] = {
        "count": un["flagged_normalized"],
        "note": (
            "정답키가 «고유»로 표시했으나 화면 ID를 치환하면 텍스트가 동일해지는 건수. "
            "탐지기 오류도, 정답키 오류도 아니고 '중복'의 정의가 다른 것이다 — "
            "NORMALIZED 티어는 «후보»로만 보고한다."
        ),
    }
    stats["tiers"] = summarize(groups)
    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agents.benchmark")
    ap.add_argument("sample_dir", help="AS-IS 샘플 소스 폴더")
    ap.add_argument("--answer-dir", required=True, help="정답키 CSV가 있는 폴더")
    ap.add_argument("--json", default="", help="결과를 JSON으로 저장할 경로")
    args = ap.parse_args(argv)

    sample = Path(args.sample_dir).expanduser().resolve()
    ans = Path(args.answer_dir).expanduser().resolve()
    err_key = next(ans.glob("error_injection_answer_key*.csv"), None)
    dup_key = next(ans.glob("duplicate_map_answer_key*.csv"), None)
    if not err_key or not dup_key:
        print(f"정답키 CSV를 찾을 수 없습니다: {ans}", file=sys.stderr)
        return 2

    err = score_error_detection(sample, err_key)
    dup = score_duplicate_detection(sample, dup_key)

    print("=" * 78)
    print("  자체 벤치마크 — 정답키 대조 결과")
    print(f"  샘플: {sample.name}")
    print("=" * 78)
    print(f"\n[1] 원본 결함 탐지 — 재현율 {err['detected']}/{err['total']} ({err['recall']:.0%})\n")
    for r in err["rows"]:
        mark = "O" if r["detected"] else "X"
        by = ", ".join(r["detected_by"]) if r["detected_by"] else "-"
        print(f"  {mark}  {r['issue_id']:<4} {r['file']:<16} {r['category']:<16} {by}")
        if not r["detected"]:
            print(f"       └ 놓침: {r['description']}")
    print("\n  분류별:")
    for cat, v in err["by_category"].items():
        print(f"    {cat:<18} {v['hit']}/{v['total']}")
    if err["false_positive_files"]:
        print(f"\n  정답키에 없는 파일에서 나온 탐지 {len(err['false_positive_files'])}건:")
        for fp in err["false_positive_files"][:15]:
            print(f"    - {fp['file']}: {', '.join(fp['findings'])}")

    ed, un = dup["exact_dup"], dup["unique"]
    print("\n[2] 중복 함수 탐지 (신뢰 수준 분리)")
    print(f"  확실(EXACT)     그룹 {dup['tiers']['exact_groups']}개 · 멤버 {dup['tiers']['exact_members']}건")
    print(f"  후보(NORMALIZED) 그룹 {dup['tiers']['normalized_groups']}개 · 멤버 {dup['tiers']['normalized_members']}건")
    print(f"  완전중복 재현율  {ed['detected']}/{ed['total']} ({ed['recall']:.0%})"
          f"   [EXACT 티어만: {ed['recall_exact_tier']:.0%}]")
    print(f"  «고유» 오탐      EXACT {un['flagged_exact']}/{un['total']} · "
          f"NORMALIZED {un['flagged_normalized']}/{un['total']}")
    print(f"  F1(채점값)      EXACT 티어 기준 {dup['f1_exact_tier']:.0%}"
          f"   (정밀도 {dup['exact_tier_precision']:.0%} · 재현율 {ed['recall_exact_tier']:.0%})")
    print(f"  F1(참고)        보수적 {dup['f1_conservative']:.0%} · 티어인지 {dup['f1_tier_aware']:.0%}")
    dd = dup["definitional_disagreement"]
    print(f"  정의 불일치      {dd['count']}건 — 정답키는 «고유», 텍스트로는 화면ID만 다른 동일 코드")
    print(f"  범위 밖          구조적유사 {dup['near_dup_out_of_scope']}행 · SQL {dup['sql_rows_out_of_scope']}행")
    print(f"  실재하지 않는 이름 {dup['phantom_names_skipped']}건은 분모에서 제외")
    if ed["missed"]:
        print(f"  놓친 완전중복: {', '.join(ed['missed'][:6])}")
    print()

    if args.json:
        Path(args.json).write_text(
            json.dumps({"error_detection": err, "duplicate_detection": dup},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON 저장: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
