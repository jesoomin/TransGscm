"""전환 작업 추적 DB(Oracle, agents/db_schema.sql의 CONV_FILE/CONV_ISSUE) 연동.

python-oracledb thin 모드를 쓴다 - 별도 Oracle 클라이언트 설치 없이 순수 파이썬으로 접속 가능.
자격증명은 .env에서만 읽는다(CLAUDE.md 원칙) - 여기 값을 직접 적지 않는다.
"""
from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager

import oracledb
from dotenv import load_dotenv

load_dotenv()


def content_hash(text: str) -> str:
    """AS-IS 원본 내용의 SHA-256 - 재실행 시 '이전과 내용이 같은지' 스킵 판단에 쓴다."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        # 스키마 파일 자체는 CREATE TABLE 시점 기준이라, 이미 만들어진 테이블에 나중에 추가된
        # 컬럼(AS_IS_CONTENT_HASH 등)은 CREATE TABLE이 스킵되면서 같이 스킵된다 - 여기서 별도로
        # ALTER TABLE을 시도하고 "이미 있음"(ORA-01430) 오류만 무시한다.
        try:
            cur.execute("ALTER TABLE CONV_FILE ADD (AS_IS_CONTENT_HASH VARCHAR2(64))")
        except oracledb.DatabaseError as e:
            (error,) = e.args
            if error.code != 1430:  # ORA-01430: column being added already exists in table
                raise
        conn.commit()


def get_cached_status_bulk(screen_ids: list[str]) -> dict[tuple[str, str, str], dict]:
    """여러 화면의 캐시 상태를 한 번의 쿼리로 가져온다(폴더에 화면이 많을 때 화면당 쿼리를 피하기 위함).

    반환 키는 (SCREEN_ID, AS_IS_LAYER, AS_IS_FILENAME) 튜플. AS_IS_FILENAME이 NULL인 행은
    스킵 판단 대상이 아니라서(파생 산출물 등) 여기서는 제외한다.
    """
    if not screen_ids:
        return {}
    with get_connection() as conn:
        cur = conn.cursor()
        placeholders = ", ".join(f":s{i}" for i in range(len(screen_ids)))
        params = {f"s{i}": sid for i, sid in enumerate(screen_ids)}
        cur.execute(
            f"""
            SELECT SCREEN_ID, AS_IS_LAYER, AS_IS_FILENAME, AS_IS_CONTENT_HASH, BUILD_CHECK
            FROM CONV_FILE
            WHERE SCREEN_ID IN ({placeholders}) AND AS_IS_FILENAME IS NOT NULL
            """,
            params,
        )
        result: dict[tuple[str, str, str], dict] = {}
        for sid, layer, filename, chash, build_check in cur.fetchall():
            result[(sid, layer, filename)] = {"content_hash": chash, "build_check": build_check}
        return result


def get_cached_status(screen_id: str, as_is_layer: str, as_is_filename: str | None) -> dict | None:
    """이전 실행에서 기록된 (콘텐츠 해시, BUILD_CHECK)를 돌려준다. 없으면 None.

    폴더 스캔 시 원본 파일의 현재 해시와 비교해서, 내용이 그대로고 지난번 정적 검증이 PASS였다면
    사람이 "스킵"을 선택할 수 있게 하기 위함(자동 스킵은 아님 - 변환기 자체가 바뀌었을 수도 있어서
    최종 판단은 사람에게 맡긴다).
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT AS_IS_CONTENT_HASH, BUILD_CHECK, TOBE_PATH, UPDATED_AT
            FROM CONV_FILE
            WHERE SCREEN_ID = :screen_id AND AS_IS_LAYER = :layer
              AND NVL(AS_IS_FILENAME, '-') = NVL(:filename, '-')
            """,
            screen_id=screen_id, layer=as_is_layer, filename=as_is_filename,
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "content_hash": row[0],
            "build_check": row[1],
            "tobe_path": row[2],
            "updated_at": row[3],
        }


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
    build_check: str = "NOT_RUN",
    as_is_content_hash: str | None = None,
) -> int:
    """CONV_FILE 행을 만들거나(없으면) 갱신하고(있으면) FILE_ID를 돌려준다.

    build_check는 chatui/validators.py의 정적 검증 결과(PASS/FAIL/NOT_RUN/NA)를 담는다 -
    진짜 컴파일/실행 검증은 아직 없어서(Maven/Spring 빌드 환경 미구축) 이 값이 그 대리 지표다.
    as_is_content_hash는 content_hash()로 계산한 AS-IS 원본 해시 - get_cached_status()의 스킵
    캐싱 판단 기준이 된다.
    """
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
                    CONVERSION_STATUS = :conversion_status, BUILD_CHECK = :build_check,
                    AS_IS_CONTENT_HASH = :content_hash,
                    UPDATED_AT = SYSTIMESTAMP
                WHERE FILE_ID = :file_id
                """,
                tobe_filename=tobe_filename, tobe_path=tobe_path,
                parse_status=parse_status, compile_status=compile_status,
                conversion_method=conversion_method, track=track,
                conversion_status=conversion_status, build_check=build_check,
                content_hash=as_is_content_hash, file_id=file_id,
            )
        else:
            file_id_var = cur.var(int)
            cur.execute(
                """
                INSERT INTO CONV_FILE (
                    SCREEN_ID, AS_IS_LAYER, AS_IS_FILENAME, AS_IS_PATH,
                    TOBE_FILENAME, TOBE_PATH, PARSE_STATUS, COMPILE_STATUS,
                    CONVERSION_METHOD, TRACK, CONVERSION_STATUS, BUILD_CHECK, AS_IS_CONTENT_HASH
                ) VALUES (
                    :screen_id, :layer, :filename, :path,
                    :tobe_filename, :tobe_path, :parse_status, :compile_status,
                    :conversion_method, :track, :conversion_status, :build_check, :content_hash
                )
                RETURNING FILE_ID INTO :file_id
                """,
                screen_id=screen_id, layer=as_is_layer, filename=as_is_filename, path=as_is_path,
                tobe_filename=tobe_filename, tobe_path=tobe_path,
                parse_status=parse_status, compile_status=compile_status,
                conversion_method=conversion_method, track=track,
                conversion_status=conversion_status, build_check=build_check,
                content_hash=as_is_content_hash, file_id=file_id_var,
            )
            file_id = file_id_var.getvalue()[0]
        conn.commit()
        return file_id


def get_screen_summary() -> list[dict]:
    """화면(SCREEN_ID)별로 CONV_FILE 행을 집계한다 - 전체 현황 그리드(성공/실패/전환율)의 기초 데이터.

    화면 하나는 P/F/D/XSQL/DTO 등 여러 CONV_FILE 행(파일)으로 구성된다. BUILD_CHECK='FAIL'인
    파일이 하나라도 있으면 그 화면 전체를 실패로 센다(CLAUDE.md: 빌드 통과해야 완료로 인정 -
    파일 하나만 깨져도 화면은 아직 완료가 아니다).
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT SCREEN_ID,
                   COUNT(*) AS TOTAL_FILES,
                   SUM(CASE WHEN BUILD_CHECK = 'FAIL' THEN 1 ELSE 0 END) AS FAIL_FILES,
                   SUM(CASE WHEN BUILD_CHECK = 'PASS' THEN 1 ELSE 0 END) AS PASS_FILES
            FROM CONV_FILE
            GROUP BY SCREEN_ID
            ORDER BY SCREEN_ID
            """
        )
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_failed_files() -> list[dict]:
    """BUILD_CHECK='FAIL'인 CONV_FILE 행 전부(화면ID/계층/파일명/경로)를 돌려준다.

    "전환 실패 건수" 클릭 시 여는 상세 팝업 그리드의 기본 행 - 화면 하나에서 파일 여러 개가
    실패할 수 있어 파일 단위로 한 행씩 낸다. 실패 사유(이슈 상세)는 FILE_ID로 get_issues_for_files()를
    따로 호출해서 채운다 - 한 번의 복잡한 조인 SQL 대신 단순한 쿼리 두 번으로 나눠 오류 가능성을 줄인다.
    """
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT FILE_ID, SCREEN_ID, AS_IS_LAYER, AS_IS_FILENAME, TOBE_FILENAME, TOBE_PATH, UPDATED_AT
            FROM CONV_FILE
            WHERE BUILD_CHECK = 'FAIL'
            ORDER BY SCREEN_ID, AS_IS_LAYER
            """
        )
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_issues_for_files(file_ids: list[int]) -> dict[int, list[dict]]:
    """주어진 FILE_ID들의 CONV_ISSUE를 한 번에 가져와 FILE_ID별로 묶어서 돌려준다."""
    if not file_ids:
        return {}
    with get_connection() as conn:
        cur = conn.cursor()
        placeholders = ", ".join(f":f{i}" for i in range(len(file_ids)))
        params = {f"f{i}": fid for i, fid in enumerate(file_ids)}
        cur.execute(
            f"""
            SELECT FILE_ID, ISSUE_TYPE, SEVERITY, LINE_NO, MESSAGE
            FROM CONV_ISSUE
            WHERE FILE_ID IN ({placeholders})
            ORDER BY FILE_ID, ISSUE_ID
            """,
            params,
        )
        result: dict[int, list[dict]] = {}
        for fid, issue_type, severity, line_no, message in cur.fetchall():
            result.setdefault(fid, []).append({
                "issue_type": issue_type, "severity": severity, "line_no": line_no, "message": message,
            })
        return result


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
