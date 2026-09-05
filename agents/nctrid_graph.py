"""nctRid <-> P/F/D BizUnit <-> XSQL 매핑 그래프 빌더 (Phase 1, docs/06-mentor-feedback.md §1/§J-1).

멘토 코멘트가 "가장 먼저 풀어야 할 것"으로 지목한 선행 정적 분석 과제 - 이게 없으면 이후 단계가
화면마다 코드베이스를 헤매며 추측하게 된다. 화면 폴더를 스캔해서 각 화면의

    nctRid(.bizunit) -> P 메서드 -> F 메서드(실제 호출되는 전부, "안전하게 자동 포팅 가능한
    단순 위임"만이 아니라) -> D 메서드 -> XSQL statement id

를 정적으로 추출해 agents/db.py의 CONV_FILE/CONV_METHOD/CONV_METHOD_CALL에 적재한다.

**범위를 의도적으로 좁혔다** - CLAUDE.md 원칙("확인되지 않은 nctRid 매핑 규칙을 추측으로
하드코딩하지 않는다")에 따라, 멘토 코멘트 4단계 중 아래 것만 다룬다:

    NEXCORE 설정   -> nctRid ─→ P BizUnit 클래스   (.bizunit의 <method>/<transactionId>로 대체)
    파서(P/F/D)    -> P -> F -> D 콜그래프 추적
    D BizUnit      -> XSQL namespace + queryId

`.xjs` 스크립트의 `transaction()` 호출부 -> nctRid 문자열 추출(멘토 코멘트 1단계)은 **여기서
하지 않는다** - 이 리포지토리에도, 로컬에 붙어있는 AS-IS 소스 트리(`C:/project/gscm/workspace`)
에도 `.xjs` 실제 샘플이 하나도 없어(2026-08-28 확인) 검증할 방법이 없는 채로 정규식 규칙을
짜면 그 자체가 추측이 된다. `.bizunit`이 있는 화면(nctRid를 확정할 수 있는 화면)만 RESOLVED로
표시하고, 없는 화면은 UNRESOLVED로 남겨 사람이 채울 목록으로 보고한다(멘토 코멘트: "실패 목록만
사람이 채우면 된다").

실행:
    python agents/nctrid_graph.py <소스폴더> [--package-p1 pm --package-p2 pla] [--no-db]

<소스폴더>는 재귀적으로 스캔한다(agents/source_scan.py) - P{screen}.java/.bizunit,
F{screen}.java, D{screen}.java/.xsql 패턴 파일을 화면ID별로 묶는다. --package-p1/--package-p2를
안 주면 경로에서(.../r/{p1}/{p2}/{p2}b/...) 화면마다 최선 추정한다.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CHATUI_DIR = _PROJECT_ROOT / "chatui"
for _p in (str(_PROJECT_ROOT), str(_CHATUI_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skeleton_gen import (  # noqa: E402
    extract_d_stmt_ids,
    extract_method_bodies,
    extract_methods,
    extract_nctrid_map,
    find_all_calls,
    find_bare_calls,
    method_body_hash,
    method_body_hash_norm,
)

from agents.source_scan import guess_package, scan_folder  # noqa: E402


def analyze_screen(screen_id: str, buckets: dict) -> dict:
    """화면 하나(P/F/D java + P bizunit + D xsql)를 정적 분석해서 매핑 그래프 조각을 돌려준다.

    실제로 코드에서 확인되는 것만 담는다 - 호출부를 못 찾으면 추측으로 잇지 않고
    unresolved 목록에 이유와 함께 남긴다.
    """
    p_java = buckets.get("P", {}).get("java", "")
    f_java = buckets.get("F", {}).get("java", "")
    d_java = buckets.get("D", {}).get("java", "")
    p_bizunit = buckets.get("P", {}).get("bizunit", "")

    p_methods = extract_methods(p_java) if p_java else []
    p_bodies = extract_method_bodies(p_java) if p_java else {}
    f_methods = extract_methods(f_java) if f_java else []
    f_bodies = extract_method_bodies(f_java) if f_java else {}
    d_methods = extract_methods(d_java) if d_java else []
    d_bodies = extract_method_bodies(d_java) if d_java else {}
    stmt_ids = extract_d_stmt_ids(d_java) if d_java else {}

    nctrid_map = extract_nctrid_map(p_bizunit) if p_bizunit else {}

    methods: list[dict] = []
    calls: list[dict] = []
    unresolved: list[str] = []

    for m in p_methods:
        nctrid = nctrid_map.get(m)
        methods.append({
            "layer": "P", "method_name": m,
            "body_hash": method_body_hash(p_bodies.get(m, "")),
            "body_hash_norm": method_body_hash_norm(p_bodies.get(m, ""), screen_id),
            "nctrid": nctrid,
        })
        if not nctrid:
            unresolved.append(
                f"{screen_id}/P.{m}: nctRid를 못 찾음 (.bizunit이 없거나 <method>/<transactionId> 매칭 실패)"
            )
        callees = find_all_calls(p_bodies.get(m, ""), f_methods)
        if not callees and f_methods:
            unresolved.append(f"{screen_id}/P.{m}: 본문에서 F 메서드 호출을 찾지 못함")
        for f in callees:
            calls.append({"caller_layer": "P", "caller_method": m, "callee_layer": "F", "callee_method": f})
        # 같은 P 클래스 안에서 다른 P 메서드를 직접 부르는 경우(한정자 없는 호출) - 지금까지
        # 콜그래프 어디에도 없던 사각지대(agents/impact_analysis.py에 명시된 한계)를 메운다.
        for sibling in find_bare_calls(p_bodies.get(m, ""), [x for x in p_methods if x != m]):
            calls.append({"caller_layer": "P", "caller_method": m, "callee_layer": "P", "callee_method": sibling})

    for m in f_methods:
        methods.append({"layer": "F", "method_name": m,
                        "body_hash": method_body_hash(f_bodies.get(m, "")),
                        "body_hash_norm": method_body_hash_norm(f_bodies.get(m, ""), screen_id)})
        callees = find_all_calls(f_bodies.get(m, ""), d_methods)
        if not callees and d_methods:
            unresolved.append(
                f"{screen_id}/F.{m}: 본문에서 D 메서드 호출을 찾지 못함 "
                "(계산만 하고 D를 안 쓰는 메서드일 수도 있음 - 원본 확인 필요)"
            )
        for d in callees:
            calls.append({"caller_layer": "F", "caller_method": m, "callee_layer": "D", "callee_method": d})
        for sibling in find_bare_calls(f_bodies.get(m, ""), [x for x in f_methods if x != m]):
            calls.append({"caller_layer": "F", "caller_method": m, "callee_layer": "F", "callee_method": sibling})

    for m in d_methods:
        stmt_id = stmt_ids.get(m)
        methods.append({"layer": "D", "method_name": m, "mapper_stmt_id": stmt_id,
                        "body_hash": method_body_hash(d_bodies.get(m, "")),
                        "body_hash_norm": method_body_hash_norm(d_bodies.get(m, ""), screen_id)})
        if not stmt_id:
            unresolved.append(
                f"{screen_id}/D.{m}: dbSelect(\"S00N\", ...) 호출을 못 찾음 "
                "(dbInsert/dbUpdate 등 다른 verb를 쓸 수도 있음 - 이 분석기는 dbSelect만 인식, 원본 확인 필요)"
            )
        for sibling in find_bare_calls(d_bodies.get(m, ""), [x for x in d_methods if x != m]):
            calls.append({"caller_layer": "D", "caller_method": m, "callee_layer": "D", "callee_method": sibling})

    return {"methods": methods, "calls": calls, "unresolved": unresolved}


def ui_id_for_screen(screen_id: str) -> str:
    """화면ID(PLA047) -> UI_ID(U-PPLA047). 2026-08-28 사용자 확인: UI 화면ID는 "U-" + P BizUnit
    클래스명(PPLA047) 표기를 쓴다.
    """
    return f"U-P{screen_id}"


def build_nctrid_map_rows(screen_id: str, graph: dict, buckets: dict) -> list[dict]:
    """analyze_screen() 결과를 UI_ID/nctRid 평탄화 테이블(NCTRID_MAP) 행으로 변환한다.

    PU_ID/FU_ID/DU_ID/XSQL_ID(2026-08-28 사용자 요청): 화면당 P/F/D BizUnit 파일과 XSQL 파일은
    각각 1개씩이라(CLAUDE.md AS-IS 구조) "P"/"F"/"D" + screen_id로 기계적으로 결정된다. 다만
    실제로 그 파일이 없으면(buckets에 내용이 없으면) NULL로 남겨 있지도 않은 파일을 있는 것처럼
    보여주지 않는다.

    nctRid 결정 규칙(2026-08-28 사용자 확인): `.bizunit`의 `<transactionId>`가 있으면 그 값을
    CONFIRMED_BIZUNIT으로 쓴다(PLA047의 pPLA04701 -> RPLA04701처럼). 없으면 P 메서드 이름 자체를
    nctRid로 본다(예: pPLA04701) - DERIVED_FROM_METHOD_NAME으로 출처를 남겨 나중에 실제
    NEXCORE 설정/`.bizunit`으로 확인되면 구분해서 갱신할 수 있게 한다.

    한 P 메서드가 F를 못 찾으면 F_METHOD=None인 행 1개, F는 찾았는데 D를 못 찾으면 D_METHOD=None인
    행 1개를 만든다(콜 체인이 끊긴 지점까지는 정직하게 보여준다) - F 하나가 D를 여러 개 부르면
    (예: fPLA047QrySelectMainList -> D 4개) 그만큼 행이 늘어난다(팬아웃을 그대로 반영).

    MAPPER_STMT_ID는 **AS-IS XSQL 원본의 statement id**(예: "S002")다 - D 메서드 본문의
    `dbSelect("S00N", ...)` 호출에서 그대로 뽑은 값이라 원본 .xsql 파일에서 바로 grep할 수 있다.
    TO-BE Mapper.xml에서는 skeleton_gen.finalize_mapper_document()가 이 id를 D 메서드명 자체로
    다시 붙이므로(예: S002 -> dPLA04704) 최종 Mapper.xml의 `<select id=...>`와는 값이 다르다 -
    혼동하지 않도록 여기 남겨둔다.

    참고(자동 적용은 안 함): `.bizunit`이 있는 PLA047 한 건으로 보면 CONFIRMED_BIZUNIT 값이
    "R" + P메서드에서 앞의 소문자 p를 뗀 나머지 대문자(pPLA04701 -> RPLA04701)와 정확히
    일치한다 - 우연일 수도 있고 실제 NEXCORE nctRid 명명 규칙일 수도 있는데, 표본이 1건뿐이라
    나머지 49화면에 이 규칙을 추측으로 적용하지 않았다(CLAUDE.md 원칙). 표본이 늘어나 규칙이
    재확인되면 DERIVED_FROM_METHOD_NAME 대신 이 변환을 적용하도록 바꿀 수 있다.
    """
    ui_id = ui_id_for_screen(screen_id)
    pu_id = f"P{screen_id}" if buckets.get("P", {}).get("java") else None
    fu_id = f"F{screen_id}" if buckets.get("F", {}).get("java") else None
    du_id = f"D{screen_id}" if buckets.get("D", {}).get("java") else None
    xsql_id = f"D{screen_id}" if buckets.get("D", {}).get("xsql") else None

    p_to_f: dict[str, list[str]] = {}
    f_to_d: dict[str, list[str]] = {}
    for c in graph["calls"]:
        if c["caller_layer"] == "P":
            p_to_f.setdefault(c["caller_method"], []).append(c["callee_method"])
        elif c["caller_layer"] == "F":
            f_to_d.setdefault(c["caller_method"], []).append(c["callee_method"])
    d_stmt = {m["method_name"]: m.get("mapper_stmt_id") for m in graph["methods"] if m["layer"] == "D"}

    rows: list[dict] = []
    for m in graph["methods"]:
        if m["layer"] != "P":
            continue
        p_method = m["method_name"]
        confirmed = m.get("nctrid")
        nctrid, source = (confirmed, "CONFIRMED_BIZUNIT") if confirmed else (p_method, "DERIVED_FROM_METHOD_NAME")
        for f_method in p_to_f.get(p_method, [None]):
            d_methods = f_to_d.get(f_method, [None]) if f_method else [None]
            for d_method in d_methods:
                rows.append({
                    "ui_id": ui_id, "screen_id": screen_id,
                    "pu_id": pu_id, "fu_id": fu_id, "du_id": du_id, "xsql_id": xsql_id,
                    "nctrid": nctrid, "nctrid_source": source,
                    "p_method": p_method, "f_method": f_method, "d_method": d_method,
                    "mapper_stmt_id": d_stmt.get(d_method) if d_method else None,
                })
    return rows


def persist_screen(db, screen_id: str, buckets: dict, paths: dict, graph: dict) -> dict:
    """analyze_screen() 결과를 CONV_FILE/CONV_METHOD/CONV_METHOD_CALL에 적재한다.

    db는 agents/db.py 모듈(호출부가 import해서 넘긴다 - 이 모듈은 DB 접속을 강제하지 않는다,
    --no-db로 분석 리포트만 뽑을 수도 있어야 해서).
    """
    layer_as_is = {
        "P": ("P(JAVA)", f"P{screen_id}.java", paths.get("P.java"), buckets.get("P", {}).get("java")),
        "F": ("F(JAVA)", f"F{screen_id}.java", paths.get("F.java"), buckets.get("F", {}).get("java")),
        "D": ("D(JAVA)", f"D{screen_id}.java", paths.get("D.java"), buckets.get("D", {}).get("java")),
        "XSQL": ("XSQL", f"D{screen_id}.xsql", paths.get("D.xsql"), buckets.get("D", {}).get("xsql")),
    }
    file_ids: dict[str, int] = {}
    for key, (as_is_layer, as_is_filename, as_is_path, content) in layer_as_is.items():
        if not content:
            continue
        file_id = db.upsert_conv_file(
            screen_id=screen_id, as_is_layer=as_is_layer,
            as_is_filename=as_is_filename, as_is_path=as_is_path,
            tobe_filename=None, tobe_path=None,
            conversion_method=None, conversion_status="NOT_STARTED",
            build_check="NOT_RUN", as_is_content_hash=db.content_hash(content),
        )
        file_ids[key] = file_id

    method_ids: dict[str, dict[str, int]] = {"P": {}, "F": {}, "D": {}}
    for m in graph["methods"]:
        file_id = file_ids.get(m["layer"])
        if not file_id:
            continue
        method_id = db.upsert_conv_method(
            file_id=file_id, method_name=m["method_name"],
            body_hash=m.get("body_hash"), body_hash_norm=m.get("body_hash_norm"), mapper_stmt_id=m.get("mapper_stmt_id"),
            nctrid=m.get("nctrid"), conversion_method="ANALYZED",
        )
        method_ids[m["layer"]][m["method_name"]] = method_id

    for c in graph["calls"]:
        caller_id = method_ids.get(c["caller_layer"], {}).get(c["caller_method"])
        if not caller_id:
            continue
        callee_id = method_ids.get(c["callee_layer"], {}).get(c["callee_method"])
        db.link_method_call(
            caller_method_id=caller_id, callee_method_id=callee_id,
            callee_name_raw=None if callee_id else c["callee_method"],
        )

    db.replace_nctrid_map(screen_id, build_nctrid_map_rows(screen_id, graph, buckets))

    return {"file_ids": file_ids, "method_ids": method_ids}


def analyze_folder(
    folder: Path,
    package_p1: str | None = None,
    package_p2: str | None = None,
    persist: bool = True,
) -> dict:
    """폴더를 스캔해 화면마다 analyze_screen()을 돌리고(옵션에 따라 DB에 적재), 요약 리포트를 만든다."""
    screens, paths, problems = scan_folder(folder)
    report: dict = {
        "screens": {},
        "problems": problems,
        "totals": {"screens": 0, "nctrid_resolved": 0, "nctrid_unresolved": 0, "unresolved_items": 0},
    }

    db = None
    if persist:
        from agents import db as _db
        _db.ensure_schema()
        db = _db

    for screen_id in sorted(screens):
        buckets = screens[screen_id]
        screen_paths = paths.get(screen_id, {})
        try:
            graph = analyze_screen(screen_id, buckets)
        except Exception as e:  # noqa: BLE001 - 화면 하나가 깨져도 나머지는 계속 분석해야 한다
            report["screens"][screen_id] = {"error": str(e)}
            continue

        if persist:
            try:
                persist_screen(db, screen_id, buckets, screen_paths, graph)
            except Exception as e:  # noqa: BLE001
                report["screens"].setdefault(screen_id, {})["db_error"] = str(e)

        n_p = sum(1 for m in graph["methods"] if m["layer"] == "P")
        n_resolved = sum(1 for m in graph["methods"] if m["layer"] == "P" and m.get("nctrid"))
        report["screens"].setdefault(screen_id, {}).update({
            "package_guess": guess_package(screen_paths),
            "nctrid_resolved": n_resolved, "nctrid_total": n_p,
            "method_count": len(graph["methods"]), "call_count": len(graph["calls"]),
            "unresolved": graph["unresolved"],
        })
        report["totals"]["screens"] += 1
        report["totals"]["nctrid_resolved"] += n_resolved
        report["totals"]["nctrid_unresolved"] += (n_p - n_resolved)
        report["totals"]["unresolved_items"] += len(graph["unresolved"])

    return report


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path, help="AS-IS 소스 폴더(재귀 스캔)")
    parser.add_argument("--package-p1", default=None, help="미지정 시 경로에서 화면마다 추정")
    parser.add_argument("--package-p2", default=None)
    parser.add_argument("--no-db", action="store_true", help="DB에 적재하지 않고 리포트만 출력")
    args = parser.parse_args()

    report = analyze_folder(
        args.folder, package_p1=args.package_p1, package_p2=args.package_p2, persist=not args.no_db
    )

    if report["problems"]:
        print("[문제]")
        for p in report["problems"]:
            print(" -", p)

    for screen_id, info in report["screens"].items():
        if "error" in info:
            print(f"{screen_id}: 분석 실패 - {info['error']}")
            continue
        print(
            f"{screen_id}: nctRid {info['nctrid_resolved']}/{info['nctrid_total']} 확정, "
            f"메서드 {info['method_count']}개, 콜엣지 {info['call_count']}개, "
            f"미해결 {len(info['unresolved'])}건"
        )
        for u in info["unresolved"]:
            print("    -", u)

    t = report["totals"]
    print(
        f"\n=== 요약: 화면 {t['screens']}개, nctRid 확정 {t['nctrid_resolved']}건 / "
        f"미확정 {t['nctrid_unresolved']}건, 그 외 미해결 항목 {t['unresolved_items']}건 ==="
    )


if __name__ == "__main__":
    _main()
