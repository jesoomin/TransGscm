"""nctRid 매핑 그래프를 실제 로컬 Oracle DB에 반영하는 스크립트.

.env에 DB_HOST/DB_PORT/DB_SERVICE_NAME(또는 DB_SID)/DB_USER/DB_PASSWORD를 채운 뒤 직접 실행:
    python agents/nctrid_map_apply.py

하는 일(화면 하나 = PLA047, /legacy 소스 기준):
    1. ensure_schema() - NCTRID_MAP 테이블이 없으면 생성(agents/db_schema.sql)
    2. agents/nctrid_mapper.py로 P/F/D 소스를 정적 분석해 nctRid 매핑 행을 만듦
    3. tracking/nctrid-map.csv를 최신 결과로 재작성(사람이 보는 요약본)
    4. replace_nctrid_map()으로 DB에도 반영(재실행 시 이 화면 행만 지우고 다시 넣음)

이 개발 환경(클라우드 원격 실행)에는 로컬 Oracle DB로 가는 네트워크 경로가 없어(.env도 없음)
이 스크립트는 작성 + CSV 출력 로직만 검증했고, DB 반영 자체는 실행하지 못했다 - 실제 DB 반영은
사용자님 로컬 환경에서 이 스크립트를 직접 돌려서 확인할 것.
"""
from pathlib import Path

from db import ensure_schema, replace_nctrid_map
from nctrid_mapper import build_nctrid_map, write_csv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LEGACY = PROJECT_ROOT / "legacy"
CSV_OUT = PROJECT_ROOT / "tracking" / "nctrid-map.csv"


def main() -> None:
    p_java = (LEGACY / "PPLA047.java").read_text(encoding="utf-8")
    f_java = (LEGACY / "FPLA047.java").read_text(encoding="utf-8")
    d_java = (LEGACY / "DPLA047.java").read_text(encoding="utf-8")
    p_bizunit = (LEGACY / "PPLA047.bizunit").read_text(encoding="utf-8", errors="replace")

    rows = build_nctrid_map(
        screen_id="U-PPLA047",
        p_class="PPLA047",
        p_java_text=p_java,
        p_bizunit_text=p_bizunit,
        f_sources={"FPLA047": f_java},
        d_sources={"DPLA047": d_java},
    )
    print(f"정적 분석 결과: {len(rows)}행")

    write_csv(rows, CSV_OUT)
    print(f"CSV 갱신: {CSV_OUT}")

    print("DB 스키마 확인/생성 중 (ensure_schema)...")
    ensure_schema()

    print("DB에 반영 중 (replace_nctrid_map)...")
    replace_nctrid_map("U-PPLA047", rows)
    print("완료: NCTRID_MAP 테이블에 U-PPLA047 화면 행 반영됨")


if __name__ == "__main__":
    main()
