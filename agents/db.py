"""전환 작업 추적 DB(Oracle, agents/db_schema.sql의 CONV_FILE/CONV_ISSUE) 연동.

python-oracledb thin 모드를 쓴다 - 별도 Oracle 클라이언트 설치 없이 순수 파이썬으로 접속 가능.
자격증명은 .env에서만 읽는다(CLAUDE.md 원칙) - 여기 값을 직접 적지 않는다.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

import oracledb
from dotenv import load_dotenv

load_dotenv()


class DBConfigError(RuntimeError):
    """DB_* 환경변수가 .env에 없거나 비어있을 때."""


def _dsn() -> str:
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    service = os.getenv("DB_SERVICE_NAME") or os.getenv("DB_SID")
    if not (host and port and service):
        raise DBConfigError(
            "DB_HOST/DB_PORT/DB_SERVICE_NAME(또는 DB_SID)이 .env에 설정되어 있지 않습니다."
        )
    return f"{host}:{port}/{service}"


@contextmanager
def get_connection():
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")
    if not (user and password):
        raise DBConfigError("DB_USER/DB_PASSWORD가 .env에 설정되어 있지 않습니다.")
    conn = oracledb.connect(user=user, password=password, dsn=_dsn())
    try:
        yield conn
    finally:
        conn.close()


def ensure_schema() -> None:
    """agents/db_schema.sql의 테이블이 없으면 만든다. 이미 있으면 조용히 넘어간다."""
    schema_path = os.path.join(os.path.dirname(__file__), "db_schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        ddl = f.read()
    # 줄 단위로 순수 주석 줄(-- 로 시작)만 먼저 걷어낸다. 문장 안에 딸려오는 줄 끝 주석
    # (예: CREATE TABLE 컬럼 옆 설명)은 살려두되, 세미콜론 분리 자체엔 영향 없다.
    code_lines = [ln for ln in ddl.splitlines() if not ln.strip().startswith("--")]
    statements = [s.strip() for s in "\n".join(code_lines).split(";") if s.strip()]

    with get_connection() as conn:
        cur = conn.cursor()
        for stmt in statements:
            try:
                cur.execute(stmt)
            except oracledb.DatabaseError as e:
                (error,) = e.args
                if error.code == 955:  # ORA-00955: name is already used by an existing object
                    continue
                raise
        conn.commit()


def upsert_conv_file(
    screen_id: str,
    as_is_layer: str,
    as_is_filename: str | None,
    as_is_path: str | None,
    tobe_filename: str | None,
    tobe_path: str | None,
    parse_status: str = "UNKNOWN",
    compile_status: str = "UNKNOWN",
    conversion_method: str | None = None,
    track: str = "UNDECIDED",
    conversion_status: str = "NOT_STARTED",
) -> int:
    """CONV_FILE 행을 만들거나(없으면) 갱신하고(있으면) FILE_ID를 돌려준다."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT FILE_ID FROM CONV_FILE
            WHERE SCREEN_ID = :screen_id AND AS_IS_LAYER = :layer
              AND NVL(AS_IS_FILENAME, '-') = NVL(:filename, '-')
            """,
            screen_id=screen_id, layer=as_is_layer, filename=as_is_filename,
        )
        row = cur.fetchone()
        if row:
            file_id = row[0]
            cur.execute(
                """
                UPDATE CONV_FILE SET
                    TOBE_FILENAME = :tobe_filename, TOBE_PATH = :tobe_path,
                    PARSE_STATUS = :parse_status, COMPILE_STATUS = :compile_status,
                    CONVERSION_METHOD = :conversion_method, TRACK = :track,
                    CONVERSION_STATUS = :conversion_status, UPDATED_AT = SYSTIMESTAMP
                WHERE FILE_ID = :file_id
                """,
                tobe_filename=tobe_filename, tobe_path=tobe_path,
                parse_status=parse_status, compile_status=compile_status,
                conversion_method=conversion_method, track=track,
                conversion_status=conversion_status, file_id=file_id,
            )
        else:
            file_id_var = cur.var(int)
            cur.execute(
                """
                INSERT INTO CONV_FILE (
                    SCREEN_ID, AS_IS_LAYER, AS_IS_FILENAME, AS_IS_PATH,
                    TOBE_FILENAME, TOBE_PATH, PARSE_STATUS, COMPILE_STATUS,
                    CONVERSION_METHOD, TRACK, CONVERSION_STATUS
                ) VALUES (
                    :screen_id, :layer, :filename, :path,
                    :tobe_filename, :tobe_path, :parse_status, :compile_status,
                    :conversion_method, :track, :conversion_status
                )
                RETURNING FILE_ID INTO :file_id
                """,
                screen_id=screen_id, layer=as_is_layer, filename=as_is_filename, path=as_is_path,
                tobe_filename=tobe_filename, tobe_path=tobe_path,
                parse_status=parse_status, compile_status=compile_status,
                conversion_method=conversion_method, track=track,
                conversion_status=conversion_status, file_id=file_id_var,
            )
            file_id = file_id_var.getvalue()[0]
        conn.commit()
        return file_id


def record_issues(file_id: int, issues, detected_by: str) -> None:
    """chatui/converters.py, chatui/skeleton_gen.py가 만든 ConversionIssue 목록을 CONV_ISSUE에 적재한다."""
    if not issues:
        return
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(
            """
            INSERT INTO CONV_ISSUE (FILE_ID, ISSUE_TYPE, SEVERITY, LINE_NO, MESSAGE, DETECTED_BY)
            VALUES (:file_id, :issue_type, :severity, :line_no, :message, :detected_by)
            """,
            [
                {
                    "file_id": file_id,
                    "issue_type": i.issue_type,
                    "severity": i.severity,
                    "line_no": i.line_no,
                    "message": i.message,
                    "detected_by": detected_by,
                }
                for i in issues
            ],
        )
        conn.commit()
