"""영향도 분석: 미사용 함수·오류 함수 탐지 + 통합 대시보드 (2026-09-02 신설,
2026-09-03 오류 함수/대시보드 추가 - 사용자 요청).

새 정적분석기를 만들지 않는다 - `chatui/skeleton_gen.py`(파이프라인 저장 경로)와
`agents/nctrid_graph.py`(CLI 경로)가 이미 채워둔 콜그래프(`CONV_METHOD`/`CONV_METHOD_CALL`)와
이슈 테이블(`CONV_ISSUE`)을 조회/조합하는 것뿐이다.

- **미사용 함수** = P 계층(nctRid로 외부 호출되는 진입점)에서 시작해 콜그래프를 타고 내려가도
  한 번도 CALLEE로 등장하지 않는 F/D 메서드 - 전형적인 도달 가능성(reachability) 분석.
- **오류 함수** = 메서드 단위로 귀속된 BLOCKER 이슈(중괄호 불일치, 미해결 호출 등)나 원본 버그
  보존(ORIGINAL_BUG) 표시가 붙은 메서드 - "안 불린다"가 아니라 "불리기는 하는데 내용에 문제가
  있다"는, 미사용과는 다른 축이다.
- **대시보드** = 위 둘을 화면·메서드 단위로 합쳐 위험도 순으로 정렬한 표 - 항목을 따로따로
  긁는 게 아니라 "뭐부터 봐야 하는지"를 보여주는 게 목적이다(2026-09-02 사용자 피드백: "의미없는
  탐지보다는 실제로 미사용함수 및 오류 함수 등 대시보드 형태로").

**해소된 한계(2026-09-03)**: 예전엔 F->F, D->D 내부 호출이 콜그래프에 전혀 없어서 미사용 탐지가
자주 오탐이었다 - `chatui/skeleton_gen.py`의 `find_bare_calls()`(한정자 없는 동일 계층 호출
탐지)를 `generate_skeletons()`(파이프라인 저장 경로)와 `agents/nctrid_graph.py`(CLI 경로)
양쪽에 추가해서 해소했다. **더 크게 해소된 한계**: 파이프라인 저장 경로(`generate_skeletons()`)가
그동안 "단순 위임 1건"만 콜그래프에 기록해서(코드 생성용 로직을 그대로 재사용했기 때문), F
메서드 하나가 D 메서드를 여러 개 부르는 실제로 흔한 경우(예: 실제 `fPLA047QrySelectMainList`가
D 메서드 4개를 부름) 그 호출들이 전부 콜그래프에서 빠져 있었다 - `find_all_calls()`로 전체
호출을 다시 훑어 채우도록 고쳤다(실 PLA047 소스로 검증: 이전엔 5개 엣지만 잡히던 게 9개로,
빠졌던 D 메서드 4개가 전부 채워짐).

**여전히 남은 한계**: 메서드 이름이 우연히 같은 다른 클래스의 메서드를 호출로 오인할 수 있다
(정적 분석의 근본 한계 - 타입 체크 없이 이름만 봄). 확정 판정이 아니라 검토 후보로 취급한다.
"""
from __future__ import annotations


def find_unused_methods(screen_id: str | None = None) -> list[dict]:
    """CONV_METHOD_CALL에서 CALLEE로 한 번도 등장하지 않는 F/D 메서드를 찾는다.

    screen_id를 주면 그 화면만, 안 주면 전체 화면 대상. 삭제/변경은 하지 않는다 - 조회 전용.
    반환 각 행: {method_id, method_name, method_name_tobe, screen_id, as_is_layer, mapper_stmt_id}.
    """
    from agents import db

    where_screen = "AND cf.SCREEN_ID = :screen_id" if screen_id else ""
    params = {"screen_id": screen_id} if screen_id else {}

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT cm.METHOD_ID, cm.METHOD_NAME, cm.METHOD_NAME_TOBE, cf.SCREEN_ID,
                   cf.AS_IS_LAYER, cm.MAPPER_STMT_ID
            FROM CONV_METHOD cm
            JOIN CONV_FILE cf ON cf.FILE_ID = cm.FILE_ID
            WHERE cf.AS_IS_LAYER IN ('F(JAVA)', 'D(JAVA)')
              {where_screen}
              AND cm.METHOD_ID NOT IN (
                  SELECT CALLEE_METHOD_ID FROM CONV_METHOD_CALL WHERE CALLEE_METHOD_ID IS NOT NULL
              )
            ORDER BY cf.SCREEN_ID, cf.AS_IS_LAYER, cm.METHOD_NAME
            """,
            params,
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip([c.lower() for c in cols], row)) for row in cur.fetchall()]


def _load_reverse_edges(cur) -> dict[int, list[int]]:
    """{callee_method_id: [caller_method_id, ...]} 역방향 인접 리스트를 한 번에 읽어온다.

    Oracle 재귀 쿼리(CONNECT BY) 대신 파이썬에서 BFS를 돈다 - 콜그래프가 작고(실측 890엣지)
    한 번에 메모리에 올려도 부담이 없어서, DB 방언에 얽히지 않고 로직을 눈으로 검증할 수 있는
    쪽을 택했다.
    """
    cur.execute(
        "SELECT CALLER_METHOD_ID, CALLEE_METHOD_ID FROM CONV_METHOD_CALL "
        "WHERE CALLEE_METHOD_ID IS NOT NULL"
    )
    reverse: dict[int, list[int]] = {}
    for caller, callee in cur.fetchall():
        reverse.setdefault(callee, []).append(caller)
    return reverse


def _method_info(cur, method_ids: list[int]) -> dict[int, dict]:
    """METHOD_ID -> {method_name, screen_id, layer, nctrid, mapper_stmt_id}."""
    if not method_ids:
        return {}
    info: dict[int, dict] = {}
    ids = list(method_ids)
    for i in range(0, len(ids), 500):  # Oracle IN 절 1000개 제한 회피
        chunk = ids[i:i + 500]
        binds = {f"m{j}": mid for j, mid in enumerate(chunk)}
        placeholders = ", ".join(f":{k}" for k in binds)
        cur.execute(
            f"""
            SELECT cm.METHOD_ID, cm.METHOD_NAME, cf.SCREEN_ID, cf.AS_IS_LAYER,
                   cm.NCTRID, cm.MAPPER_STMT_ID
            FROM CONV_METHOD cm JOIN CONV_FILE cf ON cf.FILE_ID = cm.FILE_ID
            WHERE cm.METHOD_ID IN ({placeholders})
            """,
            binds,
        )
        for mid, name, screen, layer, nctrid, stmt in cur.fetchall():
            info[mid] = {
                "method_id": mid, "method_name": name, "screen_id": screen,
                "layer": layer, "nctrid": nctrid, "mapper_stmt_id": stmt,
            }
    return info


def resolve_method_identity(method_name: str, screen_id: str | None = None) -> list[dict]:
    """같은 이름의 메서드를 **본문 내용 기준으로** 묶는다.

    이 프로젝트에서 메서드 이름은 화면 간에 겹친다 - `fCommonCodeQry`/`fAuthCheck`처럼 화면마다
    같은 이름으로 존재하는 공통 함수가 많다. 그래서 "이 함수를 바꾸면 어디가 영향받나"를
    **이름만으로** 답하면 서로 무관한 화면까지 한 덩어리로 묶여 범위가 부풀려진다.

    여기서는 `BODY_HASH`(공백 정규화한 본문 해시)로 묶어서, 같은 이름이라도 **내용이 다르면 다른
    것으로** 취급한다. D 계층 메서드는 실행하는 쿼리가 본질이므로 `MAPPER_STMT_ID`도 함께 묶음
    키에 넣는다.

    **한계(그대로 적는다)**: DB에는 Mapper.xml의 SQL 텍스트 자체가 아니라 statement id만 있다.
    따라서 "id는 같은데 SQL 본문이 다른" 경우는 여기서 구분하지 못한다 - 그런 화면은 결과의
    `notes`로 알린다. SQL 본문까지 비교하려면 Mapper.xml을 읽어야 하는데, 그건 저장된 산출물이
    있어야 가능하므로 이 조회 함수의 범위 밖이다.
    """
    from agents import db

    with db.get_connection() as conn:
        cur = conn.cursor()
        sql = (
            "SELECT cm.METHOD_ID, cf.SCREEN_ID, cm.METHOD_NAME, NVL(cm.BODY_HASH_NORM, cm.BODY_HASH), "
            "cm.MAPPER_STMT_ID, cf.AS_IS_LAYER "
            "FROM CONV_METHOD cm JOIN CONV_FILE cf ON cf.FILE_ID = cm.FILE_ID "
            "WHERE cm.METHOD_NAME = :m"
        )
        params = {"m": method_name}
        if screen_id:
            sql += " AND cf.SCREEN_ID = :s"
            params["s"] = screen_id
        cur.execute(sql, **params)
        rows = cur.fetchall()

    groups: dict[tuple, dict] = {}
    for mid, screen, name, body_hash, stmt_id, layer in rows:
        # 내용 키: 본문 해시 + (D 계층이면) 참조 쿼리 id. 본문 해시가 없으면 묶지 않고 개별 취급.
        key = (body_hash or f"__no_hash__{mid}", stmt_id or "")
        g = groups.setdefault(key, {
            "body_hash": body_hash, "mapper_stmt_id": stmt_id,
            "members": [], "method_ids": [],
        })
        g["members"].append({"screen_id": screen, "method_name": name, "layer": layer,
                             "method_id": mid})
        g["method_ids"].append(mid)
    out = sorted(groups.values(), key=lambda g: -len(g["members"]))
    for i, g in enumerate(out, 1):
        g["group_no"] = i
        g["screens"] = sorted({m["screen_id"] for m in g["members"]})
    return out


def find_impact_of_method(
    method_name: str, screen_id: str | None = None, max_depth: int = 10,
) -> dict:
    """"이 메서드를 고치면 무엇이 영향받는가" - 콜그래프를 **역방향으로** 타고 올라간다.

    `find_unused_methods()`가 "아무도 안 부르는 것"을 찾는 정방향 도달 가능성 분석이라면, 이건
    반대 방향이다(변경 파급 범위, blast radius). 멘토 코멘트 §1이 매핑 그래프를 최우선으로 둔
    이유가 바로 이 질의를 가능하게 하는 것이었다.

    반환: {targets, callers(전이적, depth 포함), affected_screens, affected_nctrids, notes}.
    조회 전용이며, 판정이 아니라 **검토 범위**를 알려주는 용도다 - notes에 한계를 같이 담는다.
    """
    from agents import db

    with db.get_connection() as conn:
        cur = conn.cursor()
        # **내용 기준으로 묶는다.** 이름만으로 잡으면 화면 간 동명이인(fCommonCodeQry 등)이
        # 전부 한 덩어리가 돼 영향 범위가 부풀려진다(resolve_method_identity 참고).
        sql = (
            "SELECT cm.METHOD_ID, NVL(cm.BODY_HASH_NORM, cm.BODY_HASH), cm.MAPPER_STMT_ID, cf.SCREEN_ID "
            "FROM CONV_METHOD cm JOIN CONV_FILE cf ON cf.FILE_ID = cm.FILE_ID "
            "WHERE cm.METHOD_NAME = :m"
        )
        params = {"m": method_name}
        if screen_id:
            sql += " AND cf.SCREEN_ID = :s"
            params["s"] = screen_id
        cur.execute(sql, **params)
        rows = cur.fetchall()

        content_groups: dict[tuple, list[int]] = {}
        group_screens: dict[tuple, set] = {}
        for mid, body_hash, stmt_id, screen in rows:
            key = (body_hash or f"__no_hash__{mid}", stmt_id or "")
            content_groups.setdefault(key, []).append(mid)
            group_screens.setdefault(key, set()).add(screen)

        # 화면을 지정하지 않았고 내용이 여러 갈래면, **가장 많은 화면이 공유하는 내용**을 기본
        # 대상으로 삼고 나머지는 notes로 알린다 - 조용히 전부 합치지 않는다.
        content_note = None
        if len(content_groups) > 1:
            ordered = sorted(content_groups.items(), key=lambda kv: -len(kv[1]))
            chosen_key, target_ids = ordered[0]
            others = [
                f"{len(v)}건({', '.join(sorted(group_screens[k])[:4])}"
                f"{'...' if len(group_screens[k]) > 4 else ''})"
                for k, v in ordered[1:]
            ]
            content_note = (
                f"'{method_name}'는 이름이 같지만 **본문 내용이 {len(content_groups)}가지**입니다. "
                f"가장 많은 화면({len(group_screens[chosen_key])}개)이 공유하는 내용을 대상으로 "
                f"분석했습니다. 나머지 내용 그룹: {'; '.join(others)}. "
                "특정 화면 기준으로 보려면 screen_id를 지정하세요."
            )
        else:
            target_ids = [mid for ids in content_groups.values() for mid in ids]
        if not target_ids:
            return {
                "targets": [], "callers": [], "affected_screens": [], "affected_nctrids": [],
                "notes": [f"'{method_name}' 메서드를 CONV_METHOD에서 찾지 못했습니다 - 화면 분석이 "
                          "DB에 적재됐는지(저장 또는 nctrid_graph 실행) 확인하세요."],
            }

        extra_notes: list[str] = []
        reverse = _load_reverse_edges(cur)

        # 역방향 BFS - 자기 자신을 다시 방문하지 않으므로 순환 호출이 있어도 멈춘다.
        depth_by_id: dict[int, int] = {}
        frontier = list(target_ids)
        seen = set(target_ids)
        depth = 0
        while frontier and depth < max_depth:
            depth += 1
            nxt = []
            for mid in frontier:
                for caller in reverse.get(mid, []):
                    if caller in seen:
                        continue
                    seen.add(caller)
                    depth_by_id[caller] = depth
                    nxt.append(caller)
            frontier = nxt

        info = _method_info(cur, target_ids + list(depth_by_id))

        # CONV_METHOD.NCTRID가 비어 있는 P 메서드는 NCTRID_MAP으로 보완한다. 두 테이블이 서로
        # 다른 시점/경로로 채워져서(NCTRID_MAP은 .bizunit 완전본 기준 300행, CONV_METHOD.NCTRID는
        # 화면을 언제 어떤 소스로 분석했는지에 따라 비어 있을 수 있다) 실제로 PLA001에서 P 계층까지
        # 역추적이 닿았는데도 nctRid가 안 나오는 걸 확인해서 붙였다(2026-09-04).
        missing_nctrid = [
            v for v in info.values() if not v.get("nctrid") and (v.get("layer") or "").startswith("P")
        ]
        if missing_nctrid:
            cur.execute("SELECT SCREEN_ID, P_METHOD, NCTRID FROM NCTRID_MAP")
            by_screen_method = {(s, p): n for s, p, n in cur.fetchall()}
            for v in missing_nctrid:
                found = by_screen_method.get((v["screen_id"], v["method_name"]))
                if found:
                    v["nctrid"] = found
                    v["nctrid_source"] = "NCTRID_MAP"

    targets = [info[mid] for mid in target_ids if mid in info]
    callers = [
        {**info[mid], "depth": d} for mid, d in sorted(depth_by_id.items(), key=lambda kv: kv[1])
        if mid in info
    ]
    affected_screens = sorted({c["screen_id"] for c in callers} | {t["screen_id"] for t in targets})
    affected_nctrids = sorted({c["nctrid"] for c in callers if c.get("nctrid")})

    notes = [
        "콜그래프는 P→F, F→D 계층 간 호출과 같은 계층 내부 호출을 정적 분석(정규식)으로 잡은 "
        "것입니다 - 이름이 같은 다른 클래스의 메서드를 호출로 오인할 수 있어 **확정이 아니라 검토 "
        "범위**로 보세요.",
        "대상은 **이름이 아니라 본문 내용(BODY_HASH, D 계층은 참조 쿼리 id 포함)** 기준으로 "
        "묶었습니다 - 화면 간에 같은 이름의 함수가 흔해서, 이름만으로 묶으면 무관한 화면까지 "
        "영향 범위에 들어옵니다.",
    ]
    if content_note:
        notes.append(content_note)
    if not callers:
        notes.append(
            "이 메서드를 호출하는 곳을 콜그래프에서 찾지 못했습니다 - 정말 미사용이거나, 아직 "
            "분석되지 않은 호출 경로(예: 화면 밖 공통/배치 호출)일 수 있습니다."
        )
    if not affected_nctrids and callers:
        notes.append(
            "영향받는 nctRid를 특정하지 못했습니다 - 호출자 중 P 계층(진입점)까지 연결이 안 "
            "닿았다는 뜻입니다."
        )
    return {
        "targets": targets, "callers": callers,
        "affected_screens": affected_screens, "affected_nctrids": affected_nctrids,
        "notes": notes,
    }


def find_error_methods(screen_id: str | None = None) -> list[dict]:
    """메서드 단위로 귀속된(METHOD_ID가 채워진) BLOCKER 이슈 또는 ORIGINAL_BUG 이슈가 있는
    메서드를 모아 메서드별로 집계해서 돌려준다.

    파일 전체에 걸린 이슈(METHOD_ID가 NULL - XML 파싱 오류, Maven 컴파일 실패 등)는 여기 안
    잡힌다 - 그건 이미 화면별 정적 검증 탭(`_render_validation_issue_list`)에서 파일 단위로
    보여주고 있다. 이 함수는 "여러 화면에 걸쳐 어떤 *함수*가 문제인지"를 새로 집계하는 용도다.
    반환 각 행: {method_id, method_name, method_name_tobe, screen_id, layer, blocker_count,
    warning_count, has_original_bug, sample_messages}.
    """
    from agents import db

    where_screen = "AND cf.SCREEN_ID = :screen_id" if screen_id else ""
    params = {"screen_id": screen_id} if screen_id else {}

    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT cm.METHOD_ID, cm.METHOD_NAME, cm.METHOD_NAME_TOBE, cf.SCREEN_ID, cf.AS_IS_LAYER,
                   ci.SEVERITY, ci.ISSUE_TYPE, ci.MESSAGE
            FROM CONV_ISSUE ci
            JOIN CONV_METHOD cm ON cm.METHOD_ID = ci.METHOD_ID
            JOIN CONV_FILE cf ON cf.FILE_ID = cm.FILE_ID
            WHERE (ci.SEVERITY = 'BLOCKER' OR ci.ISSUE_TYPE = 'ORIGINAL_BUG')
              {where_screen}
            ORDER BY cf.SCREEN_ID, cm.METHOD_NAME
            """,
            params,
        )
        rows = cur.fetchall()

    grouped: dict[int, dict] = {}
    for method_id, method_name, method_name_tobe, screen, layer, severity, issue_type, message in rows:
        row = grouped.setdefault(method_id, {
            "method_id": method_id, "method_name": method_name, "method_name_tobe": method_name_tobe,
            "screen_id": screen, "layer": layer, "blocker_count": 0, "warning_count": 0,
            "has_original_bug": False, "sample_messages": [],
        })
        if severity == "BLOCKER":
            row["blocker_count"] += 1
        elif severity == "WARNING":
            row["warning_count"] += 1
        if issue_type == "ORIGINAL_BUG":
            row["has_original_bug"] = True
        if len(row["sample_messages"]) < 3 and message:
            row["sample_messages"].append(f"[{severity}/{issue_type}] {message[:200]}")

    return sorted(grouped.values(), key=lambda r: (-r["blocker_count"], r["screen_id"], r["method_name"]))


def build_impact_dashboard(screen_id: str | None = None) -> list[dict]:
    """미사용 함수 + 오류 함수를 화면·메서드 단위로 합쳐 위험도 순으로 정렬한다.

    "리스트를 각각 따로 보여준다"가 아니라 "이 메서드가 왜(어떤 케이스로) 문제인지"를 `cases`에
    사람이 읽을 수 있는 문구로 남겨서, 대시보드 한 줄만 봐도 판단할 수 있게 한다. 위험도 점수는
    정교한 모델이 아니라 "0보다 크면 검토가 필요하다"는 신호일 뿐이다:
        risk_score = BLOCKER건수*3 + WARNING건수*1 + (미사용이면 +2) + (원본 버그면 +1)
    삭제/수정은 하지 않는다 - 조회 전용, 최종 판단은 사람 몫이다.
    """
    unused = find_unused_methods(screen_id)
    errors = find_error_methods(screen_id)

    rows: dict[int, dict] = {}

    def _ensure(method_id, method_name, method_name_tobe, screen, layer) -> dict:
        return rows.setdefault(method_id, {
            "method_id": method_id, "method_name": method_name, "method_name_tobe": method_name_tobe,
            "screen_id": screen, "layer": layer, "cases": [],
            "blocker_count": 0, "warning_count": 0, "has_original_bug": False, "sample_messages": [],
        })

    for u in unused:
        row = _ensure(u["method_id"], u["method_name"], u.get("method_name_tobe"), u["screen_id"], u["as_is_layer"])
        row["cases"].append("미사용 후보(콜그래프에서 호출 안 됨)")

    for e in errors:
        row = _ensure(e["method_id"], e["method_name"], e.get("method_name_tobe"), e["screen_id"], e["layer"])
        row["blocker_count"] = e["blocker_count"]
        row["warning_count"] = e["warning_count"]
        row["has_original_bug"] = e["has_original_bug"]
        row["sample_messages"] = e["sample_messages"]
        if e["blocker_count"]:
            row["cases"].append(f"오류 BLOCKER {e['blocker_count']}건")
        if e["warning_count"]:
            row["cases"].append(f"오류 WARNING {e['warning_count']}건")
        if e["has_original_bug"]:
            row["cases"].append("원본 버그 보존(의도적)")

    for row in rows.values():
        row["risk_score"] = (
            row["blocker_count"] * 3 + row["warning_count"] * 1
            + (2 if any(c.startswith("미사용") for c in row["cases"]) else 0)
            + (1 if row["has_original_bug"] else 0)
        )

    return sorted(rows.values(), key=lambda r: (-r["risk_score"], r["screen_id"], r["method_name"]))
