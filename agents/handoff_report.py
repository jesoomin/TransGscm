"""화면별 "미변환 사유 + 수동 처리 가이드" 인수인계 문서 생성 (2026-09-04 추가).

멘토 코멘트 §A(AlphaTrans 차용점): **"변환 실패를 예외가 아닌 정상 산출물로 취급. '미변환 사유 +
수동 처리 가이드'를 화면별로 자동 생성"**. 지금까지 이슈는 DB(CONV_ISSUE)와 Streamlit UI에만
있었는데, 실제로 뒷일을 하는 사람에게 필요한 건 "이 화면에서 자동으로 안 된 게 뭐고 내가 뭘
해야 하는가"가 한 파일에 정리된 것이다(이 팀은 산출물을 zip으로 주고받는다).

**새로 계산하는 값이 없다.** 파이프라인이 이미 만든 것(계획서, 생성 이슈, 정적 검증 결과, 품질
스캔, LLM 호출 실패)을 사람이 읽을 순서로 재구성할 뿐이다 - 여기서 판정을 새로 하지 않는다.

**가이드 문구는 실제로 존재하는 issue_type에만 붙인다.** 코드에서 실제로 발생하는 타입만 표에
넣었고(`grep issue_type=` 전수 확인), 표에 없는 타입은 지어내지 않고 원본 메시지만 보여준다 -
없는 처리 방법을 그럴듯하게 만들어내지 않기 위해서다.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = _PROJECT_ROOT / "tracking" / "conversion-reports"

# issue_type -> 사람이 실제로 해야 할 일. 이 프로젝트에서 그 이슈가 왜 나는지 확인된 것만 적는다.
_GUIDANCE: dict[str, str] = {
    "UNSUPPORTED_DB_VERB": (
        "이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 "
        "MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 "
        "`<select>`가 맞는지 확인하세요."
    ),
    "BRACE_MISMATCH": (
        "중괄호 짝이 맞지 않아 컴파일되지 않습니다. 원본 BizUnit 자체에 결함이 있어 그대로 옮긴 경우가 "
        "많으니(`// FIXME(원본 버그)` 표시 확인), 원본과 대조해 의도를 확인한 뒤 고치세요."
    ),
    "PORTING_INCOMPLETE": (
        "LLM 포팅이 끝나지 않아 `UnsupportedOperationException` 스텁이 남아 있습니다. 원본 F 메서드 "
        "로직을 직접 옮기거나 파이프라인을 다시 실행하세요."
    ),
    "UNRESOLVED_SERVICE_CALL": (
        "Api가 부르는 Service 메서드가 없습니다. 원본 P→F 위임 관계를 확인해 메서드 이름을 맞추세요."
    ),
    "UNRESOLVED_STORE_CALL": (
        "Service가 부르는 Store 메서드가 없습니다. 원본 F→D 호출을 확인해 이름을 맞추세요."
    ),
    "MISSING_STATEMENT": (
        "Store가 참조하는 statement id가 Mapper.xml에 없습니다. 원본 XSQL에 해당 쿼리가 있는지, "
        "D 메서드의 `dbSelect(\"S00N\")` id와 맞는지 대조하세요."
    ),
    "DELEGATE_CALL_NOT_FOUND": (
        "P 메서드 본문에서 F 메서드 호출을 못 찾아 Api가 임시 이름으로 호출하도록 생성됐습니다. "
        "원본을 보고 실제 위임 대상으로 고치세요."
    ),
    "DTO_FIELD_EXTRACT_INCOMPLETE": (
        "요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 "
        "넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요."
    ),
    "NCTRID_MAP_EMPTY": (
        ".bizunit에서 nctRid를 못 찾아 Api 주석이 비어 있습니다. 실제 트랜잭션 ID를 확인해 채우세요."
    ),
    "NO_METHODS_FOUND": (
        "`public IDataSet 메서드(...)` 시그니처를 못 찾았습니다. 원본 파일이 깨졌거나 구조가 다를 수 "
        "있으니 원본부터 확인하세요."
    ),
    "MISSING_INPUT_FILE": "해당 계층 원본 파일이 없어 산출물을 만들지 않았습니다. 원본 확보 여부를 확인하세요.",
    "XML_PARSE_ERROR": (
        "XML이 유효하지 않습니다. 원본 XSQL의 태그 짝(예: `<isNotEqual>`이 `</isEqual>`로 닫힘)을 "
        "먼저 고쳐야 변환 결과도 유효해집니다."
    ),
    "DUPLICATE_STATEMENT_ID": "statement id가 중복이라 MyBatis 로드 시 오류가 납니다. 한쪽 id를 바꾸세요.",
    "UNCLOSED_BIND_EXPR": "`#{`/`${` 바인드 표현식이 닫히지 않았습니다. 해당 줄을 직접 고치세요.",
    "DYNAMIC_TAG_INSIDE_CDATA": (
        "CDATA 안에 동적 태그가 남아 문자 그대로 SQL에 섞여 들어갑니다. CDATA 밖으로 빼세요."
    ),
    "UNSUPPORTED_TAG": "이 변환기가 규칙을 갖고 있지 않은 iBatis 태그입니다. MyBatis 문법으로 직접 옮기세요.",
    "TAG_MISMATCH": "원본 XSQL의 태그 짝이 맞지 않습니다. 원본을 먼저 고치세요.",
    "REMAPRESULTS_DROPPED": "remapResults 속성은 MyBatis에 대응이 없어 제거했습니다. 동작 차이가 없는지 확인하세요.",
    "FETCH_SIZE_DROPPED": "fetchSize 속성을 제거했습니다. 성능이 중요하면 MyBatis 설정으로 다시 지정하세요.",
    "CDATA_SIMPLIFIED": "CDATA 처리를 단순화했습니다. SQL 의미가 바뀌지 않았는지 확인하세요.",
    "STMT_ID_MAP_MISSING": (
        "statement id를 D 메서드명으로 바꾸지 못했습니다. Store가 참조하는 id와 Mapper.xml id를 "
        "직접 맞추세요."
    ),
    "ORIGINAL_BUG": (
        "원본에 있던 결함을 고치지 않고 그대로 옮긴 지점입니다(의도된 동작). 업무 규칙을 아는 사람이 "
        "고칠지 유지할지 판단해야 합니다."
    ),
    "HARDCODED_CREDENTIAL": "비밀번호/키로 보이는 값이 하드코딩돼 있습니다. 즉시 확인해 설정/시크릿으로 옮기세요.",
    "SQL_INJECTION_RISK": (
        "`${...}`가 조건절에 쓰였습니다. 값이 외부 입력에서 오면 인젝션 위험이니 가능하면 `#{...}`로 "
        "바꿀 수 있는지 검토하세요."
    ),
    "DYNAMIC_SQL_STRING_CONCAT": "문자열 연결로 SQL을 조립합니다. 바인드 변수로 대체 가능한지 검토하세요.",
    "DEPRECATED_NEXCORE_API": "NEXCORE 프레임워크 의존이 남아 있습니다. 포팅이 불완전한지 확인하세요.",
    "DIFF_TEST_FAIL": "AS-IS와 TO-BE SQL 실행 결과가 다릅니다. 변환된 쿼리를 원본과 대조하세요.",
}


def _issue_rows(issues, source: str) -> list[dict]:
    rows = []
    for i in issues or []:
        rows.append({
            "severity": getattr(i, "severity", "INFO"),
            "issue_type": getattr(i, "issue_type", "UNKNOWN"),
            "method": getattr(i, "method_name", None),
            "line_no": getattr(i, "line_no", None),
            "message": getattr(i, "message", ""),
            "source": source,
        })
    return rows


def collect_issue_rows(entry: dict) -> list[dict]:
    """배치 entry 하나에서 모든 이슈를 한 줄씩으로 모은다(판정을 새로 하지 않고 모으기만)."""
    rows: list[dict] = []
    rows += _issue_rows(entry.get("skel_issues"), "골격 생성(skeleton_gen)")
    rows += _issue_rows(entry.get("mapper_issues"), "Mapper 변환(converters)")
    rows += _issue_rows(entry.get("dto_issues"), "DTO 생성(skeleton_gen)")
    for vr in entry.get("validation_results") or []:
        rows += _issue_rows(getattr(vr, "issues", []), f"정적 검증({getattr(vr, 'file_name', '?')})")
    for fname, findings in (entry.get("review_findings") or {}).items():
        rows += _issue_rows(findings, f"품질·취약점 스캔({fname})")
    return rows


def _fmt_issue(row: dict) -> list[str]:
    where = []
    if row.get("method"):
        where.append(f"메서드 `{row['method']}`")
    if row.get("line_no"):
        where.append(f"{row['line_no']}행")
    where_txt = f" ({', '.join(where)})" if where else ""
    lines = [f"- **{row['issue_type']}**{where_txt} — {row['message']}", f"  - 발견: {row['source']}"]
    guide = _GUIDANCE.get(row["issue_type"])
    if guide:
        lines.append(f"  - 조치: {guide}")
    return lines


def build_handoff_report(entry: dict) -> str:
    """화면 하나의 인수인계 마크다운을 만든다.

    entry는 `chatui/app.py`의 `_pipeline_state_to_batch_results()`가 만든 화면별 dict.
    """
    screen_id = entry.get("screen_id", "?")
    plan = entry.get("plan") or {}
    files = entry.get("files") or {}
    rows = collect_issue_rows(entry)
    blockers = [r for r in rows if r["severity"] == "BLOCKER"]
    warnings = [r for r in rows if r["severity"] == "WARNING"]
    infos = [r for r in rows if r["severity"] not in ("BLOCKER", "WARNING")]
    port_errors = entry.get("port_errors") or []

    out: list[str] = [
        f"# {screen_id} 변환 인수인계 (미변환 사유 + 수동 처리 가이드)",
        "",
        f"- 생성 시각: {datetime.now().isoformat(timespec='seconds')}",
        f"- TO-BE 패키지: `com.skhynix.gscm.r.{entry.get('package_p1')}.{entry.get('package_p2')}`",
        f"- 생성된 파일: {len(files)}개 ({', '.join(sorted(files)) or '없음'})",
        f"- 사람이 반드시 처리해야 할 항목: **{len(blockers) + len(port_errors)}건**, "
        f"확인 권장: {len(warnings)}건",
        "",
        "> 이 문서는 파이프라인이 이미 만든 결과(계획서·생성 이슈·정적 검증·품질 스캔)를 사람이 읽을 "
        "순서로 재구성한 것입니다. 자동 변환 결과는 **사람 리뷰 없이 커밋/배포하지 않습니다.**",
        "",
    ]

    if plan.get("unsupported_db_verbs"):
        out += [
            "## ⛔ 이 화면은 자동 변환을 신뢰하면 안 됩니다",
            "",
            "D 계층에 이 변환기가 다루지 못하는 verb가 있습니다(변환기는 `dbSelect`만 지원):",
            "",
        ]
        for method, verbs in plan["unsupported_db_verbs"].items():
            out.append(f"- `{method}`: {', '.join('db' + v for v in verbs)}")
        out += ["", f"→ {_GUIDANCE['UNSUPPORTED_DB_VERB']}", ""]

    if plan.get("track_signals", {}).get("as_is_source_broken"):
        broken = {k: v for k, v in plan["track_signals"].get("as_is_unbalanced_braces", {}).items() if v}
        out += [
            "## ⚠️ AS-IS 원본 자체가 컴파일되지 않는 상태입니다",
            "",
            f"중괄호 불일치: {broken}. 원본 결함은 고치지 않고 그대로 옮기는 게 이 프로젝트 원칙이라, "
            "변환 결과에도 같은 결함이 남아 있을 수 있습니다. CLAUDE.md는 이런 화면을 **Reimagine 트랙** "
            "(업무 규칙만 추출해 재설계) 후보로 봅니다 - 트랙 결정은 사람이 합니다.",
            "",
        ]

    if port_errors:
        out += ["## 🔴 LLM 포팅 실패 (스텁이 그대로 남음)", ""]
        for _sid, method, err in port_errors:
            out.append(f"- `{method}`: {err}")
        out += ["", "→ 파이프라인을 다시 실행하거나, 원본 F 메서드 로직을 직접 옮기세요.", ""]

    def _section(title: str, items: list[dict], empty_msg: str) -> None:
        # out += [...] 를 쓰면 파이썬이 out을 이 함수의 지역 변수로 잡아 UnboundLocalError가 난다
        # (증강 대입이라서) - 바깥 리스트를 그대로 채우려면 extend/append만 쓴다.
        out.append(f"## {title}")
        out.append("")
        if not items:
            out.extend([empty_msg, ""])
            return
        for row in items:
            out.extend(_fmt_issue(row))
        out.append("")

    _section("🔴 반드시 사람이 처리해야 할 것 (BLOCKER)", blockers, "없습니다.")
    _section("🟡 확인이 필요한 것 (WARNING)", warnings, "없습니다.")

    if infos:
        out += ["<details><summary>참고 항목 (INFO)</summary>", ""]
        for row in infos:
            out += _fmt_issue(row)
        out += ["", "</details>", ""]

    if plan.get("expected_outputs"):
        out += ["## 자동 변환된 산출물", "", "| 파일 | TO-BE 경로 | 변환 방식 |", "|---|---|---|"]
        for o in plan["expected_outputs"]:
            out.append(f"| {o['file']} | `{o['tobe_path']}` | {o['conversion_method']} |")
        out.append("")

    if plan.get("llm_porting_targets"):
        out += [
            "## LLM이 포팅한 메서드 (반드시 사람 리뷰)",
            "",
            "생성 코드 첫 줄의 `// AI 변경 요약:` 주석에 무엇을 어떻게 옮겼는지 적혀 있습니다.",
            "",
        ]
        for m in plan["llm_porting_targets"]:
            out.append(f"- `{m}`")
        out.append("")

    return "\n".join(out)


def write_reports(entries: list[dict], reports_dir: Path | None = None) -> dict[str, str]:
    """화면별 인수인계 문서를 `tracking/conversion-reports/{화면}-handoff.md`로 쓴다.

    계획서와 같은 이유로 `pilot/`이 아니라 추적용 폴더에 쓴다(pilot/은 사람이 승인해야 파일이
    생기는 곳). 반환값은 {screen_id: 경로}.
    """
    target = reports_dir or REPORTS_DIR
    target.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for entry in entries:
        if entry.get("error"):
            continue
        screen_id = entry.get("screen_id", "UNKNOWN")
        path = target / f"{screen_id}-handoff.md"
        path.write_text(build_handoff_report(entry), encoding="utf-8")
        written[screen_id] = str(path)
    return written
