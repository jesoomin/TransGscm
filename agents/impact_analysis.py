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
