"""nctRid 매핑 그래프 빌더: 화면ID/nctRid <-> P->F->D BizUnit <-> XSQL statement 콜체인을
정적 분석만으로 추출해 테이블(행 목록)로 만든다.

사용자 확인(2026-08-27, 실무 경험 기반) - CLAUDE.md/03-kickoff-plan.md Phase 1 갱신 근거:
    nctRid는 UI에서 발생하는 트랜잭션 ID이며, P BizUnit(PU) 소스의 public 메서드명과 사실상
    동일하다 - 예: PPLA047.java의 pPLA04701 메서드가 nctRid "RPLA04701" 트랜잭션 하나에 대응한다.
    화면ID는 "U-{P클래스명}"(예: U-PPLA047) 형식. 하나의 PU가 여러 FU를 호출할 수 있는 구조다.
이 사실에 따라 Phase 1이 전제했던 ".xjs transaction() 추출"과 "NEXCORE 설정에서 nctRid->P 클래스
매핑"은 더 이상 선행 조건이 아니다 - P/F/D BizUnit Java 소스(파일명 규칙 + 메서드 호출부)만으로
nctRid<->P<->F<->D<->XSQL 콜그래프를 전부 구성할 수 있다.

결정론적 정적 분석만 쓴다(LLM 아님) - CLAUDE.md 핵심 원칙("결정론적으로 가능한 변환은 LLM에
맡기지 않는다"). chatui/skeleton_gen.py가 이미 검증한 추출 함수(extract_methods 등)를 그대로
재사용하고, 그 결과물을 손대지 않는다(Translator/Validator 분리와 같은 이유로 이 모듈도 읽기만
한다 - 골격 생성에 영향을 주지 않는다).
"""
from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "chatui"))
from skeleton_gen import (  # noqa: E402
    extract_d_statement_ids,
    extract_method_bodies,
    extract_methods,
    extract_nctrid_map,
)

CSV_COLUMNS = [
    "화면ID", "nctRid", "P클래스", "P메서드", "F클래스", "F메서드",
    "D클래스", "D메서드", "XSQL_STMT_ID", "비고",
]


@dataclass
class NctridMapRow:
    """nctRid 매핑 그래프의 한 행. P 메서드(nctRid 1개)가 F/D 여러 개로 뻗어나가면 행도 여러 개가 된다."""
    screen_id: str
    nctrid: str
    p_class: str
    p_method: str
    f_class: str | None = None
    f_method: str | None = None
    d_class: str | None = None
    d_method: str | None = None
    xsql_stmt_id: str | None = None
    note: str = ""

    def as_csv_row(self) -> list[str]:
        return [
            self.screen_id, self.nctrid, self.p_class, self.p_method,
            self.f_class or "", self.f_method or "",
            self.d_class or "", self.d_method or "",
            self.xsql_stmt_id or "", self.note,
        ]


def _find_all_calls(body: str, candidate_method_names: list[str]) -> list[str]:
    """본문에서 후보 메서드명 중 실제로 호출된 것 전부를 찾는다.

    호출 변수명(fu/du 등)은 일부러 보지 않는다 - AS-IS 원본이 lookupFunctionUnit()으로 D 유닛을
    조회하거나(FPLA047.java 35행 실제 사례), fu/du 변수명이 메서드마다 뒤섞이는 등 원본 자체의
    관례 불일치·버그가 있어도 "이 메서드명이 어떤 변수를 거치든 호출됐는가"만 보면 안전하게
    동작한다 - 변수 바인딩을 추적하는 것보다 이 방식이 원본 결함에 더 강건하다.
    """
    return [name for name in candidate_method_names if re.search(rf"\.{re.escape(name)}\s*\(", body)]


def build_nctrid_map(
    screen_id: str,
    p_class: str,
    p_java_text: str,
    p_bizunit_text: str | None,
    f_sources: dict[str, str],
    d_sources: dict[str, str],
) -> list[NctridMapRow]:
    """화면 1개 분량의 P/F/D 소스로 nctRid 매핑 테이블(행 목록)을 만든다.

    f_sources/d_sources는 {클래스명: java 소스} - 화면 하나가 F(또는 D) 클래스를 여러 개 부를 수
    있는 구조를 반영해 dict로 받는다(사용자 확인). F/D가 각각 1개뿐인 화면(PLA047 등)은 원소
    1개짜리 dict를 넘기면 된다.
    """
    rows: list[NctridMapRow] = []

    p_methods = extract_methods(p_java_text)
    p_bodies = extract_method_bodies(p_java_text)
    nctrid_map = extract_nctrid_map(p_bizunit_text) if p_bizunit_text else {}

    f_methods_by_class = {cls: extract_methods(text) for cls, text in f_sources.items()}
    f_bodies_by_class = {cls: extract_method_bodies(text) for cls, text in f_sources.items()}
    d_methods_by_class = {cls: extract_methods(text) for cls, text in d_sources.items()}
    d_stmt_by_class = {cls: extract_d_statement_ids(text) for cls, text in d_sources.items()}
    all_f_methods = [m for methods in f_methods_by_class.values() for m in methods]
    all_d_methods = [m for methods in d_methods_by_class.values() for m in methods]

    for p_method in p_methods:
        p_body = p_bodies.get(p_method, "")
        # .bizunit에 nctRid가 없으면(XML 손상 등) P 메서드명 자체를 nctRid로 잠정 사용한다 -
        # 사용자 확인: nctRid는 P 메서드명과 사실상 동일하므로 이 대체가 추측이 아니다.
        nctrid = nctrid_map.get(p_method) or p_method
        matched_f = _find_all_calls(p_body, all_f_methods)

        if not matched_f:
            rows.append(NctridMapRow(
                screen_id=screen_id, nctrid=nctrid, p_class=p_class, p_method=p_method,
                note="F 메서드 호출을 찾지 못함 - 원본 확인 필요",
            ))
            continue

        for f_method in matched_f:
            f_class = next(cls for cls, methods in f_methods_by_class.items() if f_method in methods)
            f_body = f_bodies_by_class[f_class].get(f_method, "")
            matched_d = _find_all_calls(f_body, all_d_methods)

            if not matched_d:
                rows.append(NctridMapRow(
                    screen_id=screen_id, nctrid=nctrid, p_class=p_class, p_method=p_method,
                    f_class=f_class, f_method=f_method,
                    note="D 메서드 호출을 찾지 못함 - 원본 확인 필요",
                ))
                continue

            for d_method in matched_d:
                d_class = next(cls for cls, methods in d_methods_by_class.items() if d_method in methods)
                stmt_id = d_stmt_by_class[d_class].get(d_method)
                rows.append(NctridMapRow(
                    screen_id=screen_id, nctrid=nctrid, p_class=p_class, p_method=p_method,
                    f_class=f_class, f_method=f_method,
                    d_class=d_class, d_method=d_method,
                    xsql_stmt_id=stmt_id,
                    note="" if stmt_id else "dbSelect statement id를 못 찾음 - 원본 확인 필요",
                ))
    return rows


def write_csv(rows: list[NctridMapRow], out_path: str | Path) -> None:
    """tracking/conversion-verification.csv와 같은 형태(사람이 보는 요약 테이블)로 저장한다."""
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_COLUMNS)
        for row in rows:
            w.writerow(row.as_csv_row())
