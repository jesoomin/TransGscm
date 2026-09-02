"""차등 테스트용 더미 데이터 자동 생성 (2026-09-01, 멘토 피드백 반영).

피드백: "실제 전환 완료된 건지, AS-IS와 TO-BE 수행 결과가 같은지 확인할 방법이 없다."
`agents/diff_test.py`가 AS-IS XSQL과 TO-BE Mapper SQL을 로컬 Oracle에서 직접 비교하긴 하지만,
바인드 파라미터를 사람이 손으로 넣어줘야 의미있는 비교가 된다(안 넣으면 둘 다 0행 나와서
"같다"는 게 trivial하게 참이 되는 문제가 있음 - PLA047 S001을 이 방식으로 검증할 때 테스트
행을 손으로 INSERT/DELETE했었다). 이 모듈은 그 손작업을 자동화한다: WHERE 절을 정적으로
읽어서 "이 조건을 만족하는 더미 행"을 스스로 만들고, 같은 값으로 바인드해서 실행한 뒤 지운다.

**범위를 의도적으로 좁혔다** - 안전하게 확신할 수 있는 경우만 자동화하고, 나머지는 추측하지
않고 SKIPPED로 넘긴다:
  - FROM 절에 테이블 하나만 있는 SELECT만 지원(JOIN/콤마 다중 테이블은 컬럼이 어느 테이블
    소속인지 애매해져서 자동 생성 안 함)
  - `컬럼 = 'literal'`, `컬럼 = #bind#`, `컬럼 != 'literal'` 형태의 단순 조건만 인식한다
    (BETWEEN/서브쿼리/OR 조합/함수 호출된 컬럼 등은 인식 못 하면 그냥 무시하고 넘어간다 -
    즉 그 컬럼은 "아무 값이나 넣어도 됨"으로 취급되는데, 이러면 결과가 우연히 늘어날 수
    있으니 이 하네스가 하는 일은 어디까지나 "정황 증거"지 완전한 증명은 아니다)
  - DATE/TIMESTAMP 타입 바인드 컬럼은 지원 안 함(값 생성 규칙이 애매해서 추측하지 않음)
  - 더미 행은 전부 `ZZDIFFTEST_<8자리 랜덤>` 접두어로 태그해서 실수로 남아도 바로 식별
    가능하게 하고, INSERT 직후 실행 → 비교 → **항상 finally에서 DELETE**한다.
"""
from __future__ import annotations

import re
import secrets
import string
from dataclasses import dataclass, field

_FROM_RE = re.compile(r"\bFROM\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE)
_EQ_BIND_RE = re.compile(r"(\w+)\s*=\s*#(\w+)#")
_EQ_LITERAL_RE = re.compile(r"(\w+)\s*=\s*'([^']*)'")
_NEQ_LITERAL_RE = re.compile(r"(\w+)\s*(?:!=|<>)\s*'([^']*)'")

# 이 뒤에 뭐가 오면 FROM 절이 다중 테이블이라 자동 생성을 포기한다.
_MULTI_TABLE_TAIL_RE = re.compile(r"^\s*(,|INNER\s+JOIN|LEFT\s+JOIN|RIGHT\s+JOIN|FULL\s+JOIN|JOIN)\b", re.IGNORECASE)


def new_sentinel() -> str:
    """실행마다 새로 만드는, 절대 실제 데이터와 안 겹치는 테스트 태그."""
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    return f"ZZDIFFTEST_{suffix}"


def extract_primary_table(sql_text: str) -> str | None:
    """SELECT의 FROM 절에서 테이블명 하나만 뽑는다. 다중 테이블(JOIN/콤마)이면 None."""
    m = _FROM_RE.search(sql_text)
    if not m:
        return None
    table = m.group(1)
    tail = sql_text[m.end():m.end() + 60]
    if _MULTI_TABLE_TAIL_RE.match(tail):
        return None
    return table.upper()


def get_column_info(conn, table_name: str) -> dict[str, dict]:
    """user_tab_columns에서 컬럼별 타입/길이/NOT NULL/기본값 여부를 읽는다."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT column_name, data_type, data_length, nullable, data_default
        FROM user_tab_columns WHERE table_name = :t ORDER BY column_id
        """,
        t=table_name.upper(),
    )
    cols: dict[str, dict] = {}
    for name, dtype, dlen, nullable, default in cur.fetchall():
        cols[name] = {
            "data_type": dtype,
            "data_length": dlen,
            "nullable": nullable == "Y",
            "has_default": default is not None,
        }
    return cols


def _dummy_value(col_info: dict, sentinel: str) -> object | None:
    """타입별 더미 값. DATE/TIMESTAMP는 None을 돌려줘서 호출부가 "지원 안 함"으로 처리하게 한다."""
    dtype = (col_info.get("data_type") or "").upper()
    if dtype in ("VARCHAR2", "CHAR", "NVARCHAR2", "NCHAR"):
        max_len = col_info.get("data_length") or len(sentinel)
        return sentinel[:max_len]
    if dtype in ("NUMBER", "FLOAT", "INTEGER", "BINARY_DOUBLE", "BINARY_FLOAT"):
        return 0
    if "DATE" in dtype or "TIMESTAMP" in dtype:
        return None
    return sentinel[: col_info.get("data_length") or len(sentinel)]


@dataclass
class DummyPlan:
    table: str
    row_values: dict[str, object] = field(default_factory=dict)  # bind-insert할 컬럼=값
    date_columns: list[str] = field(default_factory=list)  # SYSDATE로 채울 컬럼(값 목록엔 안 넣음)
    bind_params: dict[str, object] = field(default_factory=dict)  # SELECT 실행 시 쓸 바인드 값
    skipped_reason: str | None = None


def build_dummy_plan(sql_text: str, columns: dict[str, dict], sentinel: str) -> DummyPlan:
    """SQL의 단순 WHERE 조건을 읽어서, 그 조건을 만족하는 최소한의 더미 행 계획을 만든다.

    지원 못 하는 경우(다중 테이블, DATE 바인드 등)는 skipped_reason을 채워 돌려준다 -
    호출부는 이 필드가 있으면 실제 INSERT를 하지 않고 SKIPPED로 처리해야 한다.
    """
    table = extract_primary_table(sql_text)
    if not table:
        return DummyPlan(table="", skipped_reason="FROM 절에 테이블이 하나가 아님(JOIN/콤마) - 자동 더미 데이터 생성 미지원")
    if not columns:
        return DummyPlan(table=table, skipped_reason=f"{table} 테이블 컬럼 정보를 못 찾음(테이블이 이 스키마에 없을 수 있음)")

    eq_bind = _EQ_BIND_RE.findall(sql_text)
    eq_lit = _EQ_LITERAL_RE.findall(sql_text)
    neq_lit: dict[str, list[str]] = {}
    for col, lit in _NEQ_LITERAL_RE.findall(sql_text):
        neq_lit.setdefault(col.upper(), []).append(lit)

    row_values: dict[str, object] = {}
    bind_params: dict[str, object] = {}

    for col, lit in eq_lit:
        col_u = col.upper()
        if col_u in columns:
            row_values[col_u] = lit

    for col, bindname in eq_bind:
        col_u = col.upper()
        if col_u not in columns:
            continue
        if col_u in row_values:
            value = row_values[col_u]
        else:
            value = _dummy_value(columns[col_u], sentinel)
            if value is None:
                return DummyPlan(table=table, skipped_reason=f"{col_u}이 DATE/TIMESTAMP 바인드라 자동 지원 안 함")
            row_values[col_u] = value
        bind_params[bindname] = value

    date_columns: list[str] = []
    for col_u, info in columns.items():
        if col_u in row_values or info["nullable"] or info["has_default"]:
            continue
        dtype = (info.get("data_type") or "").upper()
        if "DATE" in dtype or "TIMESTAMP" in dtype:
            date_columns.append(col_u)
            continue
        value = _dummy_value(info, sentinel)
        if col_u in neq_lit and value in neq_lit[col_u]:
            value = (sentinel + "_X")[: info.get("data_length") or len(sentinel) + 2]
        row_values[col_u] = value

    return DummyPlan(table=table, row_values=row_values, date_columns=date_columns, bind_params=bind_params)


def insert_dummy_row(conn, plan: DummyPlan) -> None:
    cols = list(plan.row_values.keys()) + plan.date_columns
    placeholders = [f":{c}" for c in plan.row_values.keys()] + ["SYSDATE"] * len(plan.date_columns)
    sql = f"INSERT INTO {plan.table} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
    cur = conn.cursor()
    cur.execute(sql, plan.row_values)
    conn.commit()


def delete_dummy_row(conn, plan: DummyPlan) -> int:
    """삽입한 행을 정확히 그 컬럼=값 조합으로 지운다. 지운 행 수를 돌려준다(0이면 이상 신호)."""
    if not plan.row_values:
        return 0
    where = " AND ".join(f"{c} = :{c}" for c in plan.row_values.keys())
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {plan.table} WHERE {where}", plan.row_values)
    deleted = cur.rowcount
    conn.commit()
    return deleted
