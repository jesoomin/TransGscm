"""SQL/Store 계층 차등 테스트 하네스 (Phase 1, docs/06-mentor-feedback.md §3/§J-2).

"변환된다"와 "맞다"는 다른 문제라는 원칙에 따라, AS-IS XSQL과 TO-BE MyBatis Mapper가 **실제로
같은 결과를 내는지**를 로컬 Oracle DB에 둘 다 실행해서 비교한다.

**범위를 의도적으로 좁혔다.** CLAUDE.md/docs/02-architecture.md가 그려둔 최종 그림은 "레거시
nctRid 호출 vs 신규 REST API 호출"의 HTTP 레벨 diff인데, 그러려면 NEXCORE 레거시 서버와 Spring
Boot 신규 서버가 둘 다 떠 있어야 한다 - 이 개발 환경엔 mvn/java 자체가 없어(docs/03-kickoff-plan.md
Phase 2 기록 참고) 그 어느 쪽도 띄울 수 없다. 대신 **SQL 텍스트를 직접 실행**하는 한 단계
아래(Store/Mapper) 레벨로 내렸다 - 이건 python-oracledb로 로컬 Oracle에 바로 붙을 수 있어서
지금 이 환경에서도 실제로 동작하고 검증 가능하다. 그리고 SQL 번역이 이 프로젝트에서 가장 손이
많이 가고 실수가 나기 쉬운 지점이라(iBatis 동적 태그 -> MyBatis 변환), 상위 계층(Service/API)
diff보다 먼저 여기부터 실제로 맞는지 아는 게 우선순위도 더 높다.

**추가로 좁힌 부분**: 이번 버전은 동적 태그(`<if>`/`<isEqual>`/`<iterate>` 등)가 없는 정적
바인드 전용 SELECT만 지원한다(`#var#`/`#{var}` 단순 치환). 동적 태그가 있는 statement는
SKIPPED로 표시하고 이유를 남긴다 - "정적/동적 케이스를 다 지원한다"고 범위를 부풀리지 않는다.
동적 태그까지 실행하려면 이 하네스가 자체적으로 OGNL(MyBatis)과 iBatis 조건식을 둘 다 평가하는
미니 템플릿 엔진이 있어야 하는데, 아직 없다(다음 단계).

사용 예:
    from agents import diff_test
    results = diff_test.diff_screen(
        screen_id="PLA047", package_p1="pm", package_p2="pla",
        d_java_text=..., d_xsql_text=...,
        params_by_stmt={"dPLA04701": {"PLN_YW": "202601"}},
    )
    for r in results:
        print(r.stmt_id, r.status, r.message)
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CHATUI_DIR = _PROJECT_ROOT / "chatui"
for _p in (str(_PROJECT_ROOT), str(_CHATUI_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from converters import convert_xsql_fragment, finalize_mapper_document  # noqa: E402
from skeleton_gen import extract_d_stmt_ids  # noqa: E402

_DYNAMIC_TAG_RE = re.compile(
    r"<(if|isEqual|isNotEqual|isNull|isNotNull|isGreaterThan|isGreaterEqual|"
    r"isLessThan|isLessEqual|isNotEmpty|isEmpty|iterate|foreach|dynamic|where|set)\b",
    re.IGNORECASE,
)
_LITERAL_BIND_RE = re.compile(r"\$\w+\$")  # iBatis $var$ (문자열 그대로 치환) - 바인드가 아니라서 미지원
_IBATIS_BIND_RE = re.compile(r"#(\w+)#")
_MYBATIS_BIND_RE = re.compile(r"#\{(\w+)\}")
_CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)


@dataclass
class DiffResult:
    stmt_id: str
    status: str  # PASS | FAIL | SKIPPED | ERROR
    legacy_row_count: int | None = None
    new_row_count: int | None = None
    message: str = ""
    legacy_sql: str = ""
    new_sql: str = ""


def extract_select_block(xml_text: str, stmt_id: str) -> str | None:
    m = re.search(rf'<select\s+id="{re.escape(stmt_id)}"[^>]*>(.*?)</select>', xml_text, re.DOTALL)
    return m.group(1) if m else None


def is_static(select_body: str) -> bool:
    return not _DYNAMIC_TAG_RE.search(select_body)


def extract_sql_text(select_body: str) -> str:
    m = _CDATA_RE.search(select_body)
    return (m.group(1) if m else select_body).strip()


def to_oracle_bind(sql_text: str, style: str) -> tuple[str, list[str]]:
    """iBatis(#var#)/MyBatis(#{var}) 바인드 표기를 Oracle 바인드(:var)로 바꾼다. 로직은 안 바꾼다."""
    if style == "ibatis":
        names = _IBATIS_BIND_RE.findall(sql_text)
        sql = _IBATIS_BIND_RE.sub(lambda m: f":{m.group(1)}", sql_text)
    else:
        names = _MYBATIS_BIND_RE.findall(sql_text)
        sql = _MYBATIS_BIND_RE.sub(lambda m: f":{m.group(1)}", sql_text)
    return sql, names


def run_select(conn, sql_text: str, bind_names: list[str], params: dict) -> list[dict]:
    cur = conn.cursor()
    bind_values = {n: params.get(n) for n in bind_names}
    cur.execute(sql_text, bind_values)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _normalize_rows(rows: list[dict]) -> list[tuple]:
    """값 비교용 정규화 - 타입(Decimal/float/None 등) 차이로 오탐하지 않게 전부 문자열로 맞춘다.
    ORDER BY가 원본 SQL에 그대로 있으므로 행 순서는 보존한다(정렬해서 비교하지 않음 - 순서 자체도
    로직의 일부라 순서가 달라지면 그것도 진짜 불일치로 잡아야 한다).
    """
    return [tuple(("" if v is None else str(v)) for v in r.values()) for r in rows]


def diff_one_statement(
    conn, legacy_xsql_text: str, new_mapper_text: str, stmt_id_old: str, stmt_id_new: str, params: dict
) -> DiffResult:
    legacy_block = extract_select_block(legacy_xsql_text, stmt_id_old)
    new_block = extract_select_block(new_mapper_text, stmt_id_new)
    if legacy_block is None or new_block is None:
        return DiffResult(
            stmt_id_new, "ERROR",
            message=f"statement 블록을 못 찾음 (AS-IS id={stmt_id_old!r} 찾음={legacy_block is not None}, "
                    f"TO-BE id={stmt_id_new!r} 찾음={new_block is not None})",
        )
    if not is_static(legacy_block) or not is_static(new_block):
        return DiffResult(stmt_id_new, "SKIPPED", message="동적 태그 포함 - 이 하네스는 정적 바인드 전용 SELECT만 지원")

    legacy_sql = extract_sql_text(legacy_block)
    new_sql = extract_sql_text(new_block)
    if _LITERAL_BIND_RE.search(legacy_sql):
        return DiffResult(stmt_id_new, "SKIPPED", message="$var$ 리터럴 치환 바인드 포함 - 미지원")

    legacy_sql_bound, legacy_names = to_oracle_bind(legacy_sql, "ibatis")
    new_sql_bound, new_names = to_oracle_bind(new_sql, "mybatis")
    try:
        legacy_rows = run_select(conn, legacy_sql_bound, legacy_names, params)
        new_rows = run_select(conn, new_sql_bound, new_names, params)
    except Exception as e:  # noqa: BLE001 - 실행 실패 자체가 결과다(SKIPPED와 구분해 ERROR로 남김)
        return DiffResult(
            stmt_id_new, "ERROR", message=f"실행 실패: {e}",
            legacy_sql=legacy_sql_bound, new_sql=new_sql_bound,
        )

    legacy_norm = _normalize_rows(legacy_rows)
    new_norm = _normalize_rows(new_rows)
    result = DiffResult(
        stmt_id_new,
        "PASS" if legacy_norm == new_norm else "FAIL",
        len(legacy_rows), len(new_rows),
        legacy_sql=legacy_sql_bound, new_sql=new_sql_bound,
    )
    if result.status == "FAIL":
        result.message = f"결과 불일치: AS-IS {len(legacy_rows)}행 vs TO-BE {len(new_rows)}행"
    return result


def diff_screen(
    screen_id: str,
    package_p1: str,
    package_p2: str,
    d_java_text: str,
    d_xsql_text: str,
    params_by_stmt: dict[str, dict] | None = None,
) -> list[DiffResult]:
    """화면 하나의 D BizUnit이 쓰는 모든 XSQL statement에 대해 AS-IS vs TO-BE(MyBatis) 결과를 비교한다.

    params_by_stmt: {D 메서드명(TO-BE statement id): {바인드변수명: 값}}. 안 주면 해당 바인드
    변수는 전부 NULL로 실행한다 - 실행 자체는 되지만(SQL 문법 검증은 됨) 의미있는 결과 비교는
    안 된다는 뜻이므로, 실제 값 검증이 필요하면 반드시 넘겨야 한다.
    """
    from agents import db

    params_by_stmt = params_by_stmt or {}
    stmt_ids = extract_d_stmt_ids(d_java_text)  # {D 메서드명: AS-IS statement id, 예: {"dPLA04701": "S001"}}
    mapper_result = convert_xsql_fragment(d_xsql_text)
    doc_result = finalize_mapper_document(
        mapper_result.mybatis_xml, screen_id=screen_id, package_p1=package_p1, package_p2=package_p2,
        stmt_id_to_method={old_id: method for method, old_id in stmt_ids.items()},
    )
    new_mapper_text = doc_result.mybatis_xml

    results: list[DiffResult] = []
    with db.get_connection() as conn:
        for d_method, old_id in stmt_ids.items():
            results.append(
                diff_one_statement(
                    conn, d_xsql_text, new_mapper_text, old_id, d_method,
                    params_by_stmt.get(d_method, {}),
                )
            )
    return results


def run_dummy_diff_test(
    screen_id: str,
    package_p1: str,
    package_p2: str,
    d_java_text: str,
    d_xsql_text: str,
) -> list[DiffResult]:
    """더미 데이터를 자동으로 만들어서 diff_screen()을 돌리고, 끝나면 지운다(2026-09-01,
    멘토 피드백 반영 - "AS-IS/TO-BE가 실제로 같은 값을 내는지 확인할 방법이 없다").

    diff_screen()은 바인드 파라미터를 사람이 채워줘야 의미 있는 비교가 된다(안 채우면 둘 다
    0행 나와서 "같다"가 trivial하게 참이 됨). 이 함수는 각 statement의 WHERE 절을 읽어서
    조건을 만족하는 최소한의 더미 행을 agents/dummy_data.py로 만들고, 같은 값으로 실행 →
    비교 → 반드시 삭제한다. 다중 테이블 JOIN, DATE 바인드 등 안전하게 못 만드는 경우는
    SKIPPED로 정직하게 넘긴다(추측으로 잘못된 더미 데이터를 넣지 않는다).
    """
    from agents import db
    from agents import dummy_data

    stmt_ids = extract_d_stmt_ids(d_java_text)
    mapper_result = convert_xsql_fragment(d_xsql_text)
    doc_result = finalize_mapper_document(
        mapper_result.mybatis_xml, screen_id=screen_id, package_p1=package_p1, package_p2=package_p2,
        stmt_id_to_method={old_id: method for method, old_id in stmt_ids.items()},
    )
    new_mapper_text = doc_result.mybatis_xml

    results: list[DiffResult] = []
    with db.get_connection() as conn:
        for d_method, old_id in stmt_ids.items():
            legacy_block = extract_select_block(d_xsql_text, old_id)
            if legacy_block is None or not is_static(legacy_block):
                results.append(DiffResult(
                    d_method, "SKIPPED",
                    message="statement를 못 찾았거나 동적 태그 포함 - 정적 바인드 전용만 지원",
                ))
                continue
            sql_text = extract_sql_text(legacy_block)
            table = dummy_data.extract_primary_table(sql_text)
            if not table:
                results.append(DiffResult(
                    d_method, "SKIPPED",
                    message="FROM 절이 단일 테이블이 아님(JOIN/콤마) - 더미 데이터 자동 생성 미지원",
                ))
                continue

            columns = dummy_data.get_column_info(conn, table)
            sentinel = dummy_data.new_sentinel()
            plan = dummy_data.build_dummy_plan(sql_text, columns, sentinel)
            if plan.skipped_reason:
                results.append(DiffResult(d_method, "SKIPPED", message=plan.skipped_reason))
                continue

            inserted = False
            try:
                dummy_data.insert_dummy_row(conn, plan)
                inserted = True
                r = diff_one_statement(conn, d_xsql_text, new_mapper_text, old_id, d_method, plan.bind_params)
                r.message = (
                    f"[더미 데이터: {table}에 {sentinel} 태그로 행 1개 삽입 후 실행·삭제] " + r.message
                ).strip()
                results.append(r)
            except Exception as e:  # noqa: BLE001 - 더미 삽입/실행 자체가 실패해도 다음 statement는 계속 진행
                results.append(DiffResult(
                    d_method, "ERROR",
                    message=f"더미 데이터 준비/실행 중 오류: {e} (테이블: {table}, 태그: {sentinel})",
                ))
            finally:
                if inserted:
                    try:
                        deleted = dummy_data.delete_dummy_row(conn, plan)
                        if deleted != 1:
                            results.append(DiffResult(
                                d_method, "ERROR",
                                message=f"더미 행 삭제 결과가 이상함(삭제 {deleted}건, 기대 1건) - "
                                        f"{table}에서 {sentinel} 태그를 사람이 직접 확인/정리하세요.",
                            ))
                    except Exception as e:  # noqa: BLE001 - 삭제 실패는 반드시 알려야 하는 사고
                        results.append(DiffResult(
                            d_method, "ERROR",
                            message=f"더미 행 삭제 실패: {e} - {table}에서 {sentinel} 태그를 "
                                    "사람이 직접 확인/정리하세요.",
                        ))
    return results


def record_diff_results(screen_id: str, results: list[DiffResult]) -> None:
    """결과를 CONV_FILE.DIFF_TEST_CHECK(XSQL 행)에 요약 기록하고, FAIL/ERROR는 CONV_ISSUE로 남긴다."""
    from agents import db
    from converters import ConversionIssue

    db.ensure_schema()
    overall = "PASS"
    if any(r.status == "FAIL" for r in results):
        overall = "FAIL"
    elif all(r.status in ("SKIPPED", "ERROR") for r in results):
        overall = "NOT_RUN" if all(r.status == "SKIPPED" for r in results) else "FAIL"

    file_id = db.upsert_conv_file(
        screen_id=screen_id, as_is_layer="XSQL",
        as_is_filename=f"D{screen_id}.xsql", as_is_path=None,
        tobe_filename=None, tobe_path=None,
        conversion_method=None, conversion_status="IN_PROGRESS",
        build_check="NOT_RUN",
    )
    # DIFF_TEST_CHECK는 CONV_FILE upsert 시그니처에 없어 별도 UPDATE로 반영한다.
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE CONV_FILE SET DIFF_TEST_CHECK = :v WHERE FILE_ID = :fid",
            v=overall, fid=file_id,
        )
        conn.commit()

    issues = [
        ConversionIssue(
            issue_type="DIFF_TEST_FAIL" if r.status == "FAIL" else "DIFF_TEST_ERROR",
            severity="BLOCKER" if r.status == "FAIL" else "WARNING",
            message=f"{r.stmt_id}: {r.message}",
        )
        for r in results if r.status in ("FAIL", "ERROR")
    ]
    if issues:
        db.record_issues(file_id, issues, "agents/diff_test.py")
