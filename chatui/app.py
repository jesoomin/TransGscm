"""업로드 -> TO-BE 변환 챗UI (v0, 로컬 전용).

docs/07-tobe-structure.xlsx AS_IS 시트 기준, 화면 하나의 P/F/D BizUnit(.java/.bizunit) +
XSQL 파일을 업로드하면 결정론적 규칙으로 Api/Service/Store 골격 + MyBatis Mapper를 생성한다.
CLAUDE.md 핵심 원칙에 따라:
  - 결정론적으로 되는 부분(골격, iBatis->MyBatis 문법)은 규칙 기반으로만 처리한다.
  - Service 메서드 "본문"(업무 로직 포팅)만 선택적으로 LLM Gateway를 쓴다 - 기본은 꺼져있다.
  - 변환기(converters.py/skeleton_gen.py)와 검증기(validators.py)를 분리한다. 골격 생성/포팅
    직후 자동으로 validators.py의 정적 검증(중괄호 균형, 계층 간 실제 호출 대상 존재 여부,
    Mapper.xml well-formed 여부)을 돌려 "실행 가능성에 가까운지"를 보여준다 - 진짜 Maven/Spring
    빌드가 아직 없어 실제 컴파일/기동 검증은 아니다(그 결과가 PASS/FAIL로 CONV_FILE.BUILD_CHECK에
    저장된다).
  - 아무것도 자동으로 커밋하지 않는다. 로컬 pilot/{screen}/ 폴더에 "저장" 버튼을 눌러야만
    파일이 생기며, docs/07-tobe-structure.xlsx 기준 실제 TO-BE 폴더 구조
    (gscm/src/main/java/com/skhynix/gscm/r/{p1}/{p2}/Controller|dto|service|store/,
    gscm/src/main/resources/mapper/r/{p1}/{p2}/)로 저장한다.
  - 발견한 이슈(문법 오류, 정적 검증 실패 등)는 체크박스(기본 켜짐)를 켜면 agents/db.py로
    CONV_FILE/CONV_ISSUE 테이블(로컬 Oracle)에도 기록한다.

실행: (프로젝트 루트에서) streamlit run chatui/app.py
converters.py/skeleton_gen.py/validators.py/db.py는 실제 PLA047 소스 + 실제 로컬 Oracle DB로 검증했다.
app.py(Streamlit 화면) 자체는 이 환경에 브라우저가 없어 직접 렌더링 확인은 못 했다.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from converters import convert_xsql_fragment, finalize_mapper_document  # noqa: E402
from skeleton_gen import (  # noqa: E402
    extract_dto_fields,
    extract_method_bodies,
    extract_methods,
    generate_dto,
    generate_skeletons,
    splice_ported_method,
    strip_code_fence,
    to_prefix,
    tobe_relpath,
)
from validators import validate_screen  # noqa: E402
from quality_scanner import run_review, llm_review  # noqa: E402
from react_variant import recommend_react_variant  # noqa: E402
from agents.source_scan import (  # noqa: E402
    FILENAME_RE,
    scan_folder as _scan_folder,
    guess_package as _guess_package,
)

# TO-BE AS_IS_LAYER 값(agents/db_schema.sql의 CONV_FILE.AS_IS_LAYER) - 생성 파일 접미사 -> 계층 매핑.
# DB 저장 시 이 순서대로 화면당 CONV_FILE 행을 만든다.
_LAYER_BY_SUFFIX = [
    ("Api.java", "P(JAVA)"),
    ("Service.java", "F(JAVA)"),
    ("Store.java", "D(JAVA)"),
    ("Mapper.xml", "XSQL"),
    ("Dto.java", "DERIVED"),
]

def _persist_methods_and_calls(
    db, methods: list[dict], method_calls: list[dict], file_id_by_layer: dict[str, int]
) -> dict[str, dict[str, int]]:
    """SkeletonResult.methods/method_calls(generate_skeletons가 함께 뽑은 함수 단위 레지스트리+콜그래프)를
    CONV_METHOD/CONV_METHOD_CALL에 적재한다.

    CONV_FILE이 "화면의 파일 단위" 추적이라면 이건 "그 파일 안의 함수 단위" 추적이다 - 화면 간
    중복 로직 탐지(agents.db.find_duplicate_methods), 콜그래프 기반 영향도 분석(이 D 메서드/XSQL
    statement를 바꾸면 어떤 F 메서드까지 영향받는지)이 여기서 가능해진다.

    file_id_by_layer는 {"P": file_id, "F": file_id, "D": file_id} - P/F/D BizUnit Java 파일 각각의
    CONV_FILE.FILE_ID. 반환값은 {"P": {method_name: method_id}, "F": {...}, "D": {...}} - 같은 파일의
    CONV_ISSUE를 메서드에 연결할 때(db.record_issues의 method_id_by_name) 그대로 넘기면 된다.
    """
    method_ids: dict[str, dict[str, int]] = {"P": {}, "F": {}, "D": {}}
    for m in methods:
        file_id = file_id_by_layer.get(m["layer"])
        if not file_id:
            continue
        method_id = db.upsert_conv_method(
            file_id=file_id, method_name=m["method_name"],
            method_name_tobe=m.get("method_name_tobe"), body_hash=m.get("body_hash"),
            conversion_method=m.get("conversion_method"), mapper_stmt_id=m.get("mapper_stmt_id"),
            nctrid=m.get("nctrid"),
        )
        method_ids[m["layer"]][m["method_name"]] = method_id
    for call in method_calls:
        caller_id = method_ids.get(call["caller_layer"], {}).get(call["caller_method"])
        if not caller_id:
            continue
        callee_id = method_ids.get(call["callee_layer"], {}).get(call["callee_method"])
        db.link_method_call(
            caller_method_id=caller_id, callee_method_id=callee_id,
            callee_name_raw=None if callee_id else call["callee_method"],
        )
    return method_ids


def _copy_button(label: str, text: str, key: str) -> None:
    """클립보드 복사 버튼. json.dumps로 JS 문자열 이스케이프를 안전하게 처리한다.

    브라우저가 iframe 안에서 clipboard 권한을 막는 경우를 대비해 execCommand로 폴백한다.
    (참고: st.code() 블록 자체도 Streamlit 1.29+ 부터 우측 상단에 기본 복사 아이콘을 제공한다 -
    이 버튼이 동작하지 않는 환경이면 그 아이콘을 대신 쓰면 된다.)
    """
    safe_key = re.sub(r"[^A-Za-z0-9_]", "_", key)
    payload = json.dumps(text)
    html = f"""
    <div style="font-family:sans-serif;">
      <button id="copy_{safe_key}" style="padding:4px 12px;font-size:0.8rem;cursor:pointer;
        border:1px solid #999;border-radius:4px;background:#f0f2f6;">{label}</button>
      <span id="copied_{safe_key}" style="margin-left:8px;color:#0a0;font-size:0.8rem;display:none;">복사됨 ✓</span>
    </div>
    <script>
      (function() {{
        const btn = document.getElementById("copy_{safe_key}");
        const msg = document.getElementById("copied_{safe_key}");
        btn.addEventListener("click", async () => {{
          const text = {payload};
          try {{
            await navigator.clipboard.writeText(text);
          }} catch (e) {{
            const ta = document.createElement("textarea");
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            document.body.removeChild(ta);
          }}
          msg.style.display = "inline";
          setTimeout(() => {{ msg.style.display = "none"; }}, 1500);
        }});
      }})();
    </script>
    """
    components.html(html, height=36)


def _scroll_to(anchor_id: str) -> None:
    """부모 Streamlit 페이지에서 anchor_id 엘리먼트로 부드럽게 스크롤한다.

    components.html은 iframe 안에서 실행되지만 Streamlit은 보통 동일 출처라 window.parent.document로
    부모 DOM에 접근할 수 있다. 렌더링이 아직 안 끝났을 수 있어 짧게 지연 후 시도한다.
    """
    components.html(
        f"""
        <script>
          setTimeout(function() {{
            var el = window.parent.document.getElementById("{anchor_id}");
            if (el) {{ el.scrollIntoView({{behavior: "smooth", block: "start"}}); }}
          }}, 300);
        </script>
        """,
        height=0,
    )


st.set_page_config(page_title="G-SCM AS-IS → TO-BE 변환", layout="wide")

_JAVAC_ERR_RE = re.compile(r"^\[ERROR\]\s+(.+?\.java):\[(\d+),(\d+)\]\s+(.*)$")


def _parse_javac_errors(error_lines: list[str]) -> tuple[dict[str, list[tuple[int, int, str]]], list[str]]:
    """`mvn compile` 실패 메시지(줄 목록)를 파일별로 묶는다.

    javac 에러는 `[ERROR] /긴/경로/File.java:[57,41] 'else' without 'if'` 형태로 나온다 - 화면
    하나가 아니라 여러 화면이 동시에 실패하면 파일별로 접어서 보여줘야 어느 파일이 문제인지 바로
    보인다(2026-08-28 피드백: "결과를 보기 너무 어렵다"). 이 패턴에 안 맞는 줄(예: "Failed to
    execute goal..." 요약 줄)은 ungrouped로 따로 둔다 - 억지로 파일에 갖다 붙이지 않는다.
    """
    grouped: dict[str, list[tuple[int, int, str]]] = {}
    ungrouped: list[str] = []
    for ln in error_lines:
        m = _JAVAC_ERR_RE.match(ln)
        if not m:
            ungrouped.append(ln)
            continue
        path, line_no, col, msg = m.groups()
        fname = path.replace("\\", "/").rsplit("/", 1)[-1]
        grouped.setdefault(fname, []).append((int(line_no), int(col), msg))
    return grouped, ungrouped


def _render_maven_errors(grouped: dict[str, list[tuple[int, int, str]]], ungrouped: list[str]) -> None:
    """_parse_javac_errors() 결과를 파일별 expander로 렌더링한다(사이드바/팝업 공용)."""
    for fname, errs in grouped.items():
        with st.expander(f"📄 {fname} ({len(errs)}건)"):
            for line_no, col, msg in errs:
                st.code(f"L{line_no}:{col}  {msg}", language=None)
    if ungrouped:
        with st.expander(f"기타 메시지 ({len(ungrouped)}줄)"):
            st.code("\n".join(ungrouped), language=None)


@st.dialog("🔨 Maven 컴파일 결과", width="large")
def _show_maven_dialog(header: str, grouped: dict[str, list[tuple[int, int, str]]], ungrouped: list[str]) -> None:
    st.error(header)
    _render_maven_errors(grouped, ungrouped)


@st.dialog("🎯 영향도 질의 (콜그래프 역추적)", width="large")
def _show_impact_dialog() -> None:
    """"이 메서드를 고치면 뭐가 영향받나"를 팝업에서 바로 조회한다.

    LLM을 쓰지 않는다 - 콜그래프(CONV_METHOD_CALL) 역방향 추적이라 답이 결정론적이고 근거를 그대로
    보여줄 수 있다(CLAUDE.md "결정론적으로 가능한 건 LLM에 맡기지 않는다"). 조회 전용이라 변환
    파이프라인의 결정성에도 영향이 없다.
    """
    st.caption(
        "**DB에 적재된(저장했거나 `agents/nctrid_graph.py`를 돌린) 화면 기준**으로, 지정한 메서드를 "
        "호출하는 쪽을 거슬러 올라가 영향받는 화면·nctRid를 찾습니다."
    )
    with st.form("impact_query_form"):
        c1, c2 = st.columns([2, 1])
        method_name = c1.text_input("메서드명", placeholder="예: dPLA04702 / fPLA047QrySelectMainList")
        screen_filter = c2.text_input("화면 ID(선택)", placeholder="예: PLA047")
        submitted = st.form_submit_button("조회", type="primary")

    if not submitted:
        return
    if not method_name.strip():
        st.warning("메서드명을 입력하세요.")
        return

    from agents.impact_analysis import find_impact_of_method

    try:
        result = find_impact_of_method(method_name.strip(), screen_filter.strip() or None)
    except Exception as e:  # noqa: BLE001 - DB 미접속 등도 그대로 사용자에게 보여준다
        st.error(f"조회 실패: {e}")
        return

    if not result["targets"]:
        for note in result["notes"]:
            st.warning(note)
        return

    m1, m2, m3 = st.columns(3)
    m1.metric("찾은 대상 메서드", len(result["targets"]))
    m2.metric("영향받는 화면", len(result["affected_screens"]))
    m3.metric("영향받는 nctRid", len(result["affected_nctrids"]))

    if result["affected_nctrids"]:
        st.success("영향받는 nctRid: " + ", ".join(result["affected_nctrids"]))

    st.markdown("**대상 메서드**")
    st.dataframe(
        [
            {"화면": t["screen_id"], "계층": t["layer"], "메서드": t["method_name"],
             "Mapper statement": t.get("mapper_stmt_id") or ""}
            for t in result["targets"]
        ],
        hide_index=True,
    )

    st.markdown("**이 메서드를 (간접적으로라도) 호출하는 쪽 — 고치면 같이 확인해야 할 범위**")
    if result["callers"]:
        st.dataframe(
            [
                {"깊이": c["depth"], "화면": c["screen_id"], "계층": c["layer"],
                 "메서드": c["method_name"], "nctRid": c.get("nctrid") or "",
                 "nctRid 출처": c.get("nctrid_source", "CONV_METHOD" if c.get("nctrid") else "")}
                for c in result["callers"]
            ],
            hide_index=True,
        )
    else:
        st.info("호출자를 찾지 못했습니다.")

    for note in result["notes"]:
        st.caption(f"※ {note}")


def _categorize(files) -> tuple[dict[str, dict[str, str]], list[str]]:
    """업로드된 파일들을 계층(P/F/D)별, 종류(java/bizunit/xsql)별로 분류한다."""
    buckets: dict[str, dict[str, str]] = {"P": {}, "F": {}, "D": {}}
    ids_seen: dict[str, int] = {}
    problems: list[str] = []

    for f in files:
        m = FILENAME_RE.match(f.name)
        if not m:
            problems.append(f"'{f.name}' - 예상 파일명 패턴(P/F/D + 화면ID + .java/.bizunit/.xsql)이 아니라 건너뜀")
            continue
        layer, screen_id, kind = m.group(1).upper(), m.group(2), m.group(3).lower()
        ids_seen[screen_id] = ids_seen.get(screen_id, 0) + 1
        content = f.getvalue().decode("utf-8", errors="replace")
        buckets[layer][kind] = content

    if len(ids_seen) > 1:
        problems.append(f"화면ID가 여러 개 감지됨({list(ids_seen.keys())}) - 한 번에 한 화면씩 올려주세요. 가장 많이 등장한 걸 사용합니다.")
    screen_id = max(ids_seen, key=ids_seen.get) if ids_seen else ""
    return buckets, problems, screen_id


_PORT_PROMPT_TMPL = (
    "다음은 NEXCORE(BizUnit) F(Function) 계층 Java 메서드 {method}의 본문이다. "
    "이 로직(계산/분기/문자열 처리 등)을 하나도 빠짐없이 그대로 유지하면서, "
    "IDataSet/IOnlineContext/lookupDataUnit/lookupFunctionUnit 같은 NEXCORE 프레임워크 "
    "의존만 제거하고 Spring 서비스 메서드로 옮겨라. "
    "D BizUnit 호출(du.dXXXX(...))은 store.dXXXX(...) 형태로 바꿔라 (Service에 이미 "
    "`store` 필드가 있다). SQL이나 업무 규칙을 새로 설계하지 말고 원본 그대로 포팅만 해라. "
    "원본에 컴파일 에러나 미선언 변수가 있어도 그 부분을 고치지 말고 원본 그대로 옮긴 뒤 "
    "`// FIXME(원본 버그): ...` 로 표시해라. "
    "`public Map<String, Object> {method}(Map<String, Object> request) {{ ... }}` 형태의 "
    "완성된 메서드 코드 하나만 출력하고, 코드 펜스나 다른 설명은 붙이지 마라.\n\n"
    "원본 메서드 본문:\n```\n{body}\n```"
)


def _run_batch_save(batch_results: list[dict], save_to_db: bool, progress_cb=None) -> list[dict]:
    """agents/workflow_graph.run_pipeline_part_a()의 결과(_pipeline_state_to_batch_results()로
    모양을 맞춘 것)를 실제로 pilot/에 저장하고(옵션에 따라 DB에도 반영)한다.

    사람이 화면별 상세보기(_render_batch_screen_detail)로 결과를 먼저 검토한 뒤, 이 함수를 명시적으로
    호출해야만 실제 파일이 생기고 DB에 반영된다 - "생성됐다"와 "저장됐다"를 UI에서도 분리했다
    (2026-08-28 피드백: 전체 자동 진행이 생성과 저장을 한 번에 해버려서 개별 파일 승인 없이 밀어붙여지는
    문제가 있었다). 에러가 났거나 골격 생성 자체가 실패한 화면(files가 빈 항목)은 건너뛴다.
    """
    targets = [e for e in batch_results if not e["error"] and e["files"]]
    total = len(targets)

    for idx, entry in enumerate(targets):
        if progress_cb:
            progress_cb(idx, total, entry["screen_id"])
        screen_id = entry["screen_id"]
        package_p1, package_p2 = entry["package_p1"], entry["package_p2"]
        prefix = to_prefix(screen_id)
        files = entry["files"]
        buckets = entry["buckets"]
        as_is_paths = entry["as_is_paths"]
        validation_results = entry["validation_results"]
        review_findings = entry["review_findings"]

        out_dir = PROJECT_ROOT / "pilot"
        saved_paths: dict[str, Path] = {}
        for fname, content in files.items():
            rel = tobe_relpath(fname, package_p1, package_p2)
            full_path = out_dir / rel
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            saved_paths[fname] = full_path
        entry["saved_files"] = len(saved_paths)
        entry["saved"] = True

        if save_to_db:
            from agents import db

            db.ensure_schema()
            by_file = {r.file_name: r for r in validation_results}
            layer_meta = {
                "P(JAVA)": (f"P{screen_id}.java", as_is_paths.get("P.java"),
                            entry["skel_issues"], "chatui/skeleton_gen.py", buckets["P"].get("java")),
                "F(JAVA)": (f"F{screen_id}.java", as_is_paths.get("F.java"), [], None, buckets["F"].get("java")),
                "D(JAVA)": (f"D{screen_id}.java", as_is_paths.get("D.java"), [], None, buckets["D"].get("java")),
                "XSQL": (f"D{screen_id}.xsql", as_is_paths.get("D.xsql"), entry["mapper_issues"],
                          "chatui/converters.py", buckets["D"].get("xsql")),
                "DERIVED": (f"{screen_id}-dto-derived", None, entry["dto_issues"], "chatui/skeleton_gen.py", None),
            }
            file_ids: dict[str, int] = {}
            file_id_by_layer: dict[str, int] = {}
            for suffix, layer in _LAYER_BY_SUFFIX:
                fname = f"{prefix}{suffix}"
                if fname not in files:
                    continue
                as_is_filename, as_is_path, gen_issues, gen_detected_by, as_is_content = layer_meta[layer]
                vr = by_file.get(fname)
                build_check = "PASS" if vr and vr.passed else ("FAIL" if vr else "NOT_RUN")
                content_hash = db.content_hash(as_is_content) if as_is_content else None
                file_id = db.upsert_conv_file(
                    screen_id=screen_id, as_is_layer=layer,
                    as_is_filename=as_is_filename, as_is_path=as_is_path,
                    tobe_filename=fname, tobe_path=str(saved_paths[fname].parent),
                    conversion_method="RULE_BASED", conversion_status="IN_PROGRESS",
                    build_check=build_check, as_is_content_hash=content_hash,
                )
                file_ids[fname] = file_id
                if layer in ("P(JAVA)", "F(JAVA)", "D(JAVA)"):
                    file_id_by_layer[layer[0]] = file_id
            # 함수 단위 레지스트리/콜그래프를 먼저 적재해서 method_id를 얻어야, 아래에서
            # 이슈를 메서드에 연결할 수 있다(그래서 이슈 기록을 파일 upsert 루프와 분리했다).
            method_ids = _persist_methods_and_calls(
                db, entry["skel_methods"], entry["skel_method_calls"], file_id_by_layer
            )
            for suffix, layer in _LAYER_BY_SUFFIX:
                fname = f"{prefix}{suffix}"
                if fname not in file_ids:
                    continue
                file_id = file_ids[fname]
                as_is_filename, as_is_path, gen_issues, gen_detected_by, as_is_content = layer_meta[layer]
                vr = by_file.get(fname)
                m_ids = method_ids.get(layer[0]) if layer in ("P(JAVA)", "F(JAVA)", "D(JAVA)") else None
                if gen_issues and gen_detected_by:
                    db.record_issues(file_id, gen_issues, gen_detected_by, method_id_by_name=m_ids)
                if vr and vr.issues:
                    db.record_issues(file_id, vr.issues, "chatui/validators.py", method_id_by_name=m_ids)
                if review_findings.get(fname):
                    db.record_issues(
                        file_id, review_findings[fname], "chatui/quality_scanner.py",
                        method_id_by_name=m_ids,
                    )
            cross_vr = next((r for r in validation_results if r.check == "CROSS_LAYER_REF"), None)
            if cross_vr:
                cross_file_id = db.upsert_conv_file(
                    screen_id=screen_id, as_is_layer="DERIVED",
                    as_is_filename=f"{screen_id}-cross-layer-check", as_is_path=None,
                    tobe_filename=None, tobe_path=str(out_dir),
                    conversion_method=None, conversion_status="NOT_STARTED",
                    build_check="PASS" if cross_vr.passed else "FAIL",
                )
                if cross_vr.issues:
                    # UNRESOLVED_SERVICE_CALL/UNRESOLVED_STORE_CALL/MISSING_STATEMENT는 각각
                    # Api(P)/Service(F)/Store(D) 메서드 이름에 귀속된다(validators.py가 세
                    # 계층을 한 issues 리스트에 섞어 돌려준다) - 그래서 P/F/D method_ids를 하나로
                    # 합쳐서 넘긴다(이름이 계층 간에 우연히 겹칠 일은 거의 없다, AS-IS 명명 규칙상
                    # p/f/d 접두어가 이미 다르다).
                    combined_method_ids = {
                        **method_ids.get("P", {}), **method_ids.get("F", {}), **method_ids.get("D", {}),
                    }
                    db.record_issues(
                        cross_file_id, cross_vr.issues, "chatui/validators.py",
                        method_id_by_name=combined_method_ids,
                    )

    if progress_cb:
        progress_cb(total, total, None)
    return batch_results


def _write_batch_files_to_dir(batch_results: list[dict], pilot_root: Path) -> None:
    """batch_results의 화면별 파일을 pilot_root 아래 실제 저장 경로와 동일한 상대경로로 쓴다.

    `_run_batch_save()`가 실제 `pilot/`에 쓸 때 쓰는 것과 똑같은 `tobe_relpath()` 규칙이다 -
    다만 여기서는 사람이 승인하기 전에 6~7단계를 미리 돌려보기 위한 임시 사본(pilot_root)에
    쓰는 것뿐이라, 이 함수는 실제 `pilot/` 폴더에는 손대지 않는다.
    """
    for entry in batch_results:
        if entry["error"] or not entry["files"]:
            continue
        package_p1, package_p2 = entry["package_p1"], entry["package_p2"]
        for fname, content in entry["files"].items():
            rel = tobe_relpath(fname, package_p1, package_p2)
            full_path = pilot_root / rel
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")


def _run_stage_6_7_preview(batch_results: list[dict]) -> dict:
    """승인·저장 전(1~5단계가 끝난 직후)에 6단계(교차분석+영향도분석)·7단계(Maven 빌드)를 미리
    실행한다 - 사용자가 "6~7단계까지 파이프라인에 포함하고, 그 다음에 사람이 승인·저장한다"는
    순서를 요청해서(2026-09-02) 원래 저장 이후(Part B)에 있던 이 두 단계를 저장 이전으로 옮겼다.

    `cross_analysis.analyze_pilot_folder()`/`validators.check_maven_build()` 둘 다 디스크의
    `pilot/` 트리를 직접 읽는 함수라(로직은 안 바꿈), 아직 저장하지 않은 이번 배치를 대상으로
    미리 실행하려면 격리된 사본이 필요하다 - 실제 `pilot/` 전체를 임시 폴더로 복사하고 이번
    배치 파일을 그 위에 겹쳐 쓴 뒤(진짜 `pilot/`은 전혀 건드리지 않음) 그 임시 사본을 대상으로
    두 함수를 그대로 돌린다. 결과를 돌려준 뒤 임시 폴더는 항상 지운다(`agents/dummy_data.py`의
    "만들고 확인하고 항상 지운다" 패턴과 동일 - CLAUDE.md "사람 리뷰 없는 자동 저장 금지" 원칙을
    지키면서도 저장 전에 미리보기가 가능한 이유가 이 격리 덕분이다).

    **알려진 한계**: DB 기반 조회(`db.find_duplicate_methods`/`impact_analysis.build_impact_dashboard`)는
    이번 배치가 아직 DB에 반영되지 않은 상태에서 도는 거라 **이미 저장된 과거 화면 기준**으로만
    정확하다 - 이번 배치 자신의 메서드는 DB에 없어서 이 조회 결과에는 안 잡힌다(저장하기 전이라
    어쩔 수 없는 한계, 호출부에서 라벨로 명시한다). 디스크 기반 `analyze_pilot_folder`/Maven
    빌드는 이번 배치를 포함해서 정확하다.
    """
    import shutil
    import tempfile

    from cross_analysis import analyze_pilot_folder
    from validators import check_maven_build
    from agents import db as _db
    from agents.impact_analysis import build_impact_dashboard

    real_pilot = PROJECT_ROOT / "pilot"
    tmp_dir = Path(tempfile.mkdtemp(prefix="gscm_pipeline_preview_"))
    try:
        tmp_pilot = tmp_dir / "pilot"
        if real_pilot.exists():
            shutil.copytree(real_pilot, tmp_pilot)
        else:
            tmp_pilot.mkdir(parents=True, exist_ok=True)
        _write_batch_files_to_dir(batch_results, tmp_pilot)

        cross_result = analyze_pilot_folder(tmp_pilot)
        try:
            dup_methods = _db.find_duplicate_methods(min_group_size=2)
        except Exception as e:
            dup_methods = []
            cross_result.notes.append(f"(DB 기반 중복 함수 조회 실패 - {e})")
        try:
            dashboard_rows = build_impact_dashboard()
        except Exception as e:
            dashboard_rows = []
            cross_result.notes.append(f"(영향도 분석 대시보드 조회 실패 - {e})")
        maven_result = check_maven_build(tmp_pilot / "gscm" / "pom.xml")
        return {
            "cross_result": cross_result, "dup_methods": dup_methods,
            "dashboard_rows": dashboard_rows, "maven_result": maven_result,
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _pipeline_state_to_batch_results(
    final_state: dict, screens: dict, all_paths: dict, package_map: dict[str, tuple[str, str]],
) -> list[dict]:
    """agents/workflow_graph.run_pipeline_part_a() 결과(화면ID를 키로 쓰는 dict 모음)를
    _run_batch_save()/_render_batch_screen_detail()가 기대하는 "화면별 entry 리스트" 모양으로
    바꾼다 - 그 두 함수의 파일쓰기/DB반영/렌더링 로직은 그대로 재사용하고 입력 모양만 맞춘다
    (2026-09-02, 7단계 LangGraph 파이프라인 재구성 - 로직 재구현 없음, 어댑터만 새로 만듦).
    """
    ai_by_screen: dict[str, dict] = {}
    for screen_id, p_method, variant in final_state.get("ai_recommend_results", []):
        ai_by_screen.setdefault(screen_id, {})[p_method] = variant

    results = []
    for screen_id in screens:
        files = final_state.get("files", {}).get(screen_id, {})
        package_p1, package_p2 = package_map.get(screen_id, ("TODO", "TODO"))
        results.append({
            "screen_id": screen_id, "package_p1": package_p1, "package_p2": package_p2,
            "error": None if files else "골격 생성 결과 없음",
            "files": files,
            "buckets": screens[screen_id],
            "as_is_paths": all_paths.get(screen_id, {}),
            "validation_results": final_state.get("validation_results", {}).get(screen_id, []),
            "review_findings": final_state.get("review_findings", {}).get(screen_id, {}),
            "validation_total": len(final_state.get("validation_results", {}).get(screen_id, [])),
            "validation_pass": sum(1 for r in final_state.get("validation_results", {}).get(screen_id, []) if r.passed),
            "review_count": sum(len(v) for v in final_state.get("review_findings", {}).get(screen_id, {}).values()),
            "skel_issues": final_state.get("skel_issues", {}).get(screen_id, []),
            "mapper_issues": final_state.get("mapper_issues", {}).get(screen_id, []),
            "dto_issues": final_state.get("dto_issues", {}).get(screen_id, []),
            "skel_methods": final_state.get("skel_methods", {}).get(screen_id, []),
            "skel_method_calls": final_state.get("skel_method_calls", {}).get(screen_id, []),
            "saved_files": 0, "saved": False,
            "ai_recommendations": ai_by_screen.get(screen_id, {}),
            "plan": final_state.get("plans", {}).get(screen_id),
            "plan_path": final_state.get("plan_paths", {}).get(screen_id),
            # LLM 호출이 끝내 실패해 스텁이 남은 메서드 - 인수인계 문서가 "사람이 직접 옮겨야 할
            # 메서드"로 표시한다(agents/handoff_report.py).
            "port_errors": [e for e in final_state.get("port_errors", []) if e[0] == screen_id],
        })
    return results


def _render_ai_recommendation(screen_id: str, prefix: str, files: dict, buckets: dict | None) -> None:
    """AI 추천 - nctRid별로 Api/Service/Store/Mapper/Dto 5개 파일 단위 대안을 기존과 나란히
    보여준다. 단일 화면 흐름과 배치 상세보기 양쪽에서 공유해서 쓴다(두 곳에서 따로 구현하면
    한쪽만 고치고 잊어버리는 문제가 생긴다 - 실제로 한 번 그랬다).
    """
    if not buckets or not buckets.get("P", {}).get("java"):
        st.info("P(Java) 파일이 없어 추천할 필드가 없습니다.")
        return

    dto_entries = extract_dto_fields(
        buckets["P"]["java"], buckets["F"].get("java"), buckets["P"].get("bizunit"),
    )
    file_suffixes = [
        ("Dto.java", "dto_java", "java"),
        ("Api.java", "api_java", "java"),
        ("Service.java", "service_java", "java"),
        ("Store.java", "store_java", "java"),
        ("Mapper.xml", "mapper_xml", "xml"),
    ]
    for entry in dto_entries:
        p_method, nctrid = entry["p_method"], entry["nctrid"]
        st.markdown(f"**{nctrid or p_method}** (`{p_method}`)")
        variant_key = f"react_variant_{screen_id}_{p_method}"
        if st.button(f"AI 추천받기 — {p_method}", key=f"ai_reco_btn_{screen_id}_{p_method}"):
            with st.spinner("AI 추천을 받는 중..."):
                st.session_state[variant_key] = recommend_react_variant(
                    screen_id=screen_id, p_method=p_method, nctrid=nctrid,
                    request_fields=entry["request_fields"], response_fields=entry["response_fields"],
                    api_java=files.get(f"{prefix}Api.java"),
                )
        variant = st.session_state.get(variant_key)
        if variant:
            for issue in variant.issues:
                text = f"[{issue.severity}/{issue.issue_type}] {issue.message}"
                if issue.severity == "BLOCKER":
                    st.error(text)
                elif issue.severity == "WARNING":
                    st.warning(text)
                else:
                    st.info(text)
            if variant.dto_java:
                file_tabs = st.tabs([suffix for suffix, _, _ in file_suffixes])
                for file_tab, (suffix, attr, lang) in zip(file_tabs, file_suffixes):
                    with file_tab:
                        existing = files.get(f"{prefix}{suffix}", "(생성된 파일 없음)")
                        recommended = getattr(variant, attr) or "(이 파일 종류는 추천 내용 없음)"
                        cmp_cols = st.columns(2)
                        with cmp_cols[0]:
                            st.caption(f"기존 {suffix} (규칙 기반, AI 개입 없음)")
                            with st.container(height=300):
                                st.code(existing, language=lang, line_numbers=True)
                        with cmp_cols[1]:
                            st.caption("AI 추천")
                            with st.container(height=300):
                                st.code(recommended, language=lang, line_numbers=True)
                if variant.rationale:
                    st.markdown(f"**추천 이유**: {variant.rationale}")
        st.divider()


def _render_diff_test(screen_id: str, buckets: dict | None, package_p1: str, package_p2: str) -> None:
    """더미 데이터를 자동 생성해서 AS-IS XSQL과 TO-BE Mapper SQL이 실제로 같은 값을 내는지
    로컬 Oracle에서 비교한다(2026-09-01 멘토 피드백: "전환이 실제로 됐는지, AS-IS/TO-BE 결과가
    같은지 확인할 방법이 없다"). agents/diff_test.py의 run_dummy_diff_test()를 그대로 쓴다 -
    더미 행은 WHERE 조건에 맞춰 자동으로 만들고 비교 직후 항상 지운다. 단일 화면 흐름과 배치
    상세보기 양쪽에서 공유한다(AI 추천과 같은 이유 - 한쪽만 고치고 잊어버리는 문제 방지).
    """
    if not buckets or not buckets.get("D", {}).get("xsql") or not buckets.get("D", {}).get("java"):
        st.info("D(Java)/XSQL 파일이 없어 차등 테스트를 할 수 없습니다.")
        return

    st.caption(
        "AS-IS XSQL과 TO-BE MyBatis SQL을 로컬 Oracle DB에 실제로 실행해서 결과가 같은지 "
        "비교합니다. WHERE 절 조건을 만족하는 더미 데이터를 자동으로 만들어 넣고, 비교가 끝나면 "
        "즉시 삭제합니다(태그: `ZZDIFFTEST_*`). 정적 바인드 SELECT만 지원 - 동적 태그가 있거나 "
        "여러 테이블을 조인하는 statement는 SKIPPED로 표시됩니다(추측으로 더미 데이터를 넣지 않음)."
    )
    result_key = f"diff_test_{screen_id}"
    if st.button("🧪 더미 데이터로 차등 테스트 실행", key=f"diff_test_btn_{screen_id}"):
        with st.spinner("더미 데이터 생성 → AS-IS/TO-BE 실행 → 비교 → 삭제 중..."):
            try:
                from agents import diff_test
                st.session_state[result_key] = diff_test.run_dummy_diff_test(
                    screen_id=screen_id, package_p1=package_p1, package_p2=package_p2,
                    d_java_text=buckets["D"]["java"], d_xsql_text=buckets["D"]["xsql"],
                )
            except Exception as e:
                st.error(f"차등 테스트 실행 실패: {e}")

    results = st.session_state.get(result_key)
    if results:
        icon_map = {"PASS": "✅", "FAIL": "❌", "SKIPPED": "⏭️", "ERROR": "⚠️"}
        pass_n = sum(1 for r in results if r.status == "PASS")
        st.write(f"결과: {pass_n}/{len(results)}건 PASS")
        for r in results:
            icon = icon_map.get(r.status, "❓")
            rows_note = f" ({r.legacy_row_count} vs {r.new_row_count}행)" if r.status in ("PASS", "FAIL") else ""
            st.markdown(f"{icon} **{r.stmt_id}** — {r.status}{rows_note}")
            if r.message:
                st.caption(r.message)


def _estimate_pipeline_outputs(screens: dict, target_ids: list[str]) -> dict:
    """선택된 화면의 AS-IS 원본 파일이 몇 개 있는지만 보고 TO-BE 파일 개수를 미리 가늠한다.

    추측이 아니라 실제 생성 조건을 그대로 반복한 것 - `chatui/skeleton_gen.py`의
    `generate_skeletons()`/`generate_dto()`, `agents/workflow_graph.py`의 `_convert_screen()`을
    보면 Api.java/Dto.java는 P java가 있어야, Service.java는 F java가 있어야, Store.java는
    D java가 있어야, Mapper.xml은 D xsql이 있어야 만들어진다. 실제 실행 전에 "화면 몇 개 중 몇 개
    파일이 나올지" 가늠할 수 있게 화면을 실제로 변환하지 않고 버킷 존재 여부만 센다.
    """
    as_is = {"p_java": 0, "f_java": 0, "d_java": 0, "d_xsql": 0}
    to_be = {"Api.java": 0, "Dto.java": 0, "Service.java": 0, "Store.java": 0, "Mapper.xml": 0}
    for sid in target_ids:
        buckets = screens.get(sid, {})
        has_p = bool(buckets.get("P", {}).get("java"))
        has_f = bool(buckets.get("F", {}).get("java"))
        has_d = bool(buckets.get("D", {}).get("java"))
        has_x = bool(buckets.get("D", {}).get("xsql"))
        as_is["p_java"] += has_p
        as_is["f_java"] += has_f
        as_is["d_java"] += has_d
        as_is["d_xsql"] += has_x
        if has_p:
            to_be["Api.java"] += 1
            to_be["Dto.java"] += 1
        if has_f:
            to_be["Service.java"] += 1
        if has_d:
            to_be["Store.java"] += 1
        if has_x:
            to_be["Mapper.xml"] += 1
    return {"as_is": as_is, "to_be": to_be}


# TO-BE 파일 접미사 -> AS-IS 원본 버킷 위치. 정적 검증에 실패한 파일을 원본과 나란히 비교해서
# 보여줄 때 쓴다(_render_source_comparison) - 어느 원본이 이 변환 결과의 "재료"였는지는
# CLAUDE.md AS-IS->TO-BE 매핑표 그대로다. Dto.java는 P java/F java/.bizunit 여러 개에서
# 역추출되는 산출물이라 1:1 원본이 없어 이 표에 없다(원본 비교 없이 변환 결과만 보여준다).
_ASIS_SOURCE_MAP: dict[str, tuple[str, str, str]] = {
    "Api.java": ("P", "java", "P BizUnit 원본 (P{화면}.java)"),
    "Service.java": ("F", "java", "F BizUnit 원본 (F{화면}.java)"),
    "Store.java": ("D", "java", "D BizUnit 원본 (D{화면}.java)"),
    "Mapper.xml": ("D", "xsql", "XSQL 원본 (D{화면}.xsql)"),
}


def _render_marked_code(content: str, lang: str, highlight_lines: list[int], key: str, context: int = 12) -> None:
    """문제로 지목된 줄을 '>>>' 표시로 눈에 띄게 하고, 파일이 길면 그 줄 앞뒤만 보여준다.

    st.code(line_numbers=True)는 항상 1행부터 번호를 매겨서 일부만 잘라 보여주면 실제 행 번호와
    어긋난다 - 그래서 잘라낸 구간에도 원본 파일 기준 행 번호를 직접 접두어로 붙인다. 하이라이트할
    줄이 없으면(원본 비교 대상 파일이 아니거나 line_no를 모르는 이슈면) 그냥 보통 코드 블록을 쓴다.
    """
    lines = content.split("\n")
    total = len(lines)
    valid = sorted({n for n in highlight_lines if n and 1 <= n <= total})
    if not valid:
        st.code(content, language=lang, line_numbers=True)
        return

    start = max(1, min(valid) - context)
    end = min(total, max(valid) + context)
    show_full = (end - start + 1) >= total or st.checkbox(f"전체 보기 (총 {total}행)", key=f"{key}_full")

    if show_full:
        width = len(str(total))
        rng = range(1, total + 1)
    else:
        width = len(str(end))
        rng = range(start, end + 1)
        st.caption(
            f"{start}~{end}행만 표시했습니다({total}행 중, 문제 줄 '>>>' 기준 앞뒤 {context}행) - "
            "위 체크박스로 전체를 볼 수 있습니다."
        )
    numbered = [
        f"{'>>>' if ln in valid else '   '} {str(ln).rjust(width)} | {lines[ln - 1]}"
        for ln in rng
    ]
    st.code("\n".join(numbered), language=lang)


def _render_source_comparison(
    fname: str, converted_content: str, buckets: dict | None, highlight_lines: list[int], key: str,
) -> None:
    """정적 검증에 실패한 파일 하나를 원본(AS-IS)과 변환 결과(TO-BE) 나란히 비교해서 보여준다.

    AS-IS 쪽은 어느 줄이 문제인지 알 방법이 없어(포팅/골격 생성 과정에서 줄 번호가 그대로 안
    옮겨진다 - LLM 포팅은 포맷을 바꾸고, 골격 생성은 클래스/메서드 틀을 새로 씌운다) 하이라이트하지
    않고 원본 그대로 보여주기만 한다. 문제 줄이 정확히 몇 행인지는 검증기(validators.py)가 TO-BE
    코드 기준으로 이미 알고 있으므로 TO-BE 쪽만 강조한다.
    """
    lang = "xml" if fname.endswith(".xml") else "java"
    as_is_content, as_is_label = None, None
    if buckets:
        for suffix, (layer, field, label) in _ASIS_SOURCE_MAP.items():
            if fname.endswith(suffix):
                as_is_content = buckets.get(layer, {}).get(field)
                as_is_label = label
                break

    col_asis, col_tobe = st.columns(2)
    with col_asis:
        st.markdown(f"**🗂 기존 원본 (AS-IS){' — ' + as_is_label if as_is_label else ''}**")
        if not as_is_content:
            st.info(
                "이 파일은 원본과 1:1로 대응하지 않습니다(여러 원본에서 규칙 기반으로 역추출된 "
                "산출물) - 비교할 단일 원본이 없어 변환 결과만 표시합니다."
            )
        else:
            lines_list = as_is_content.split("\n")
            total_lines = len(lines_list)
            preview_n = 40
            show_full = (
                st.checkbox(f"전체 보기 (총 {total_lines}행)", key=f"{key}_asis_full")
                if total_lines > preview_n else True
            )
            if show_full:
                st.code(as_is_content, language=lang, line_numbers=True)
            else:
                st.code("\n".join(lines_list[:preview_n]), language=lang, line_numbers=True)
                st.caption(f"총 {total_lines}행 중 {preview_n}행만 표시했습니다 - 위 체크박스로 전체를 보세요.")
    with col_tobe:
        st.markdown(f"**🆕 변환 결과 (TO-BE) — `{fname}`**")
        if highlight_lines:
            lines_txt = ", ".join(f"{n}행" for n in sorted(set(highlight_lines)))
            st.error(f"🔴 문법 오류로 지목된 줄: {lines_txt} — 아래 '>>>' 표시를 확인하세요.")
        _render_marked_code(converted_content, lang, highlight_lines, key=f"{key}_tobe")


def _render_validation_issue_list(
    validation_results: list, files: dict, buckets: dict | None, key_prefix: str,
) -> None:
    """정적 검증 결과 목록 + (실패한 파일은) 원본과 비교해서 보기를 렌더링한다.

    전에는 배치/파이프라인 상세 보기와 단일 화면 업로드 흐름 두 곳에 이 목록 렌더링이 따로
    구현돼 있었다(한쪽만 고치고 잊어버리는 문제 - AI 추천 때 실제로 한 번 겪었다). 이제 이 함수
    하나로 합쳐서 두 곳이 항상 같은 방식으로 동작하게 한다.
    """
    if not validation_results:
        st.write("검증 결과가 없습니다.")
        return
    for idx, r in enumerate(validation_results):
        icon = "✅" if r.passed else "❌"
        st.markdown(f"{icon} **{r.file_name}** ({r.check})")
        for issue in r.issues:
            label = f"[{issue.severity}/{issue.issue_type}]"
            if issue.line_no:
                label += f" (L{issue.line_no})"
            text = f"{label} {issue.message}"
            if issue.severity == "BLOCKER":
                st.error(text)
            elif issue.severity == "WARNING":
                st.warning(text)
            else:
                st.info(text)

        if not r.passed and r.check in ("JAVA_STATIC", "MAPPER_XML") and r.file_name in files:
            blocker_lines = sorted({
                i.line_no for i in r.issues if i.severity == "BLOCKER" and i.line_no
            })
            with st.expander(f"🔍 {r.file_name} — 원본과 비교해서 보기", expanded=False):
                _render_source_comparison(
                    r.file_name, files[r.file_name], buckets, blocker_lines,
                    key=f"{key_prefix}_{idx}_{r.file_name}",
                )


def _render_conversion_plan(plan: dict | None, plan_path: str | None) -> None:
    """변환 전에 고정된 계획서(agents/conversion_plan.py)를 사람이 검토할 수 있게 보여준다.

    계획서 자체는 파이프라인이 코드 생성 전에 이미 파일로 써둔 것이고(tracking/conversion-plans/),
    여기서는 그 내용을 읽기 좋게 펼쳐 보여주기만 한다 - 값을 여기서 다시 계산하지 않는다.
    """
    if not plan:
        st.info(
            "이 화면의 변환 계획이 없습니다 - 파이프라인을 다시 실행하면 0단계에서 생성됩니다"
            "(예전 실행 결과를 보고 있는 경우일 수 있습니다)."
        )
        return

    if plan_path:
        st.caption(f"계획 파일: `{plan_path}` (변환 **전에** 기록됨 - CLAUDE.md \"계획 없이 코드 생성 금지\")")

    signals = plan.get("track_signals", {})
    est = plan.get("estimated_llm_calls", {})
    cols = st.columns(4)
    cols[0].metric("트랙", plan.get("track", "UNDECIDED"))
    cols[1].metric("nctRid", signals.get("nctrid_count", 0))
    cols[2].metric("LLM 포팅 대상", len(plan.get("llm_porting_targets", [])))
    cols[3].metric("예상 산출 파일", len(plan.get("expected_outputs", [])))

    if plan.get("unsupported_db_verbs"):
        st.error(
            "이 화면의 D 계층에 **이 변환기가 다루지 못하는 verb**가 있습니다: "
            + ", ".join(f"{m}({', '.join('db' + v for v in vs)})"
                        for m, vs in plan["unsupported_db_verbs"].items())
            + " — 변환기는 dbSelect만 지원해서 Store 코드가 selectOne으로 생성됩니다(맞지 않음). "
            "지금까지 확보한 원본이 전부 조회 전용이라 이 경로는 검증된 적이 없습니다 - "
            "자동 변환 결과를 믿지 말고 사람이 직접 확인하세요."
        )

    if signals.get("as_is_source_broken"):
        broken = {k: v for k, v in signals.get("as_is_unbalanced_braces", {}).items() if v}
        st.warning(
            f"AS-IS 원본의 중괄호가 맞지 않습니다({broken}) - 원본이 그대로는 컴파일되지 않는 "
            "상태라는 뜻입니다. CLAUDE.md가 이런 화면을 Reimagine 트랙 후보로 들었습니다 - "
            "트랙 결정은 사람 몫이라 자동으로 정하지 않았습니다."
        )

    st.markdown("**예상 산출 파일**")
    st.dataframe(
        [
            {"파일": o["file"], "TO-BE 경로": o["tobe_path"], "변환 방식": o["conversion_method"]}
            for o in plan.get("expected_outputs", [])
        ],
        hide_index=True,
    )

    st.markdown("**LLM 호출 예상**")
    st.caption(
        f"2단계 포팅 {est.get('porting', 0)}건 - 단순 위임 {est.get('porting_skipped_rule_based', 0)}건은 "
        "규칙 기반으로 생성돼 LLM을 부르지 않습니다. AI 추천은 nctRid당 1회로 "
        f"{est.get('ai_recommend', 0)}건 예상(5단계를 켠 경우)."
    )
    if plan.get("rule_based_delegations"):
        st.caption("단순 위임(규칙 기반 생성): " + ", ".join(
            f"{k} → {v}" for k, v in plan["rule_based_delegations"].items()
        ))

    with st.expander("원본 fragment 목록 / 계획서 원문(JSON)", expanded=False):
        st.dataframe(
            [
                {"fragment": name, "존재": info.get("present"), "줄수": info.get("lines"),
                 "AS-IS 경로": info.get("as_is_path")}
                for name, info in plan.get("fragments", {}).items()
            ],
            hide_index=True,
        )
        st.code(json.dumps(plan, ensure_ascii=False, indent=2), language="json")


def _render_batch_screen_detail(
    screen_id: str, files: dict, validation_results: list, review_findings: dict,
    buckets: dict | None = None, package_p1: str = "TODO", package_p2: str = "TODO",
    plan: dict | None = None, plan_path: str | None = None,
    entry: dict | None = None, handoff_path: str | None = None,
) -> None:
    """전체 자동 진행 결과 목록에서 화면 하나를 클릭했을 때, 그 화면의 포팅된 소스/정적 검증/
    품질·취약점 스캔/AI 추천 상세를 탭으로 보여준다. 단일 화면 흐름(tab_result)의 렌더링 스타일을
    그대로 따르되, 배치 결과는 이미 끝난 실행 결과를 다시 보여주는 것뿐이라 포팅 실행 버튼 등 상태를
    변경하는 조작은 넣지 않는다(읽기 전용 상세 보기, AI 추천 버튼은 예외 - opt-in 조회라 상태를
    바꾸지 않는다).

    buckets는 _pipeline_state_to_batch_results()가 entry["buckets"]에 넣어둔 그 화면의 원본
    P/F/D 텍스트다 - AI 추천 탭이 extract_dto_fields()로 요청/응답 필드를 다시 뽑는 데 필요하다
    (단일 화면 흐름과 동일한 방식, 파이프라인 모드라고 다르게 만들지 않는다).
    """
    if not files:
        st.warning("이 화면은 골격 생성 단계에서 실패해서 볼 수 있는 산출물이 없습니다 - 위 오류 메시지를 확인하세요.")
        return

    blocker_n = sum(1 for r in validation_results if not r.passed)
    review_n = sum(len(v) for v in review_findings.values())
    tab_plan, tab_handoff, tab_files, tab_validation, tab_review, tab_ai, tab_diff = st.tabs([
        "📋 변환 계획",
        "📝 인수인계",
        f"📄 소스 ({len(files)}개 파일)",
        f"🔍 정적 검증 ({len(validation_results) - blocker_n}/{len(validation_results)} 통과)",
        f"🛡️ 품질/취약점 스캔 ({review_n}건)",
        "🎨 AI 추천",
        "🧪 차등 테스트",
    ])

    with tab_plan:
        _render_conversion_plan(plan, plan_path)

    with tab_handoff:
        if entry is None:
            st.info("인수인계 문서를 만들 결과가 없습니다 - 파이프라인을 다시 실행하세요.")
        else:
            from agents.handoff_report import build_handoff_report

            report_md = build_handoff_report(entry)
            if handoff_path:
                st.caption(f"파일: `{handoff_path}` (그대로 메일/zip으로 전달할 수 있습니다)")
            _copy_button("📋 인수인계 문서 복사", report_md, key=f"handoff_copy_{screen_id}")
            with st.container(height=520):
                st.markdown(report_md)

    with tab_files:
        source_tabs = st.tabs(list(files.keys()))
        PREVIEW_LINES = 40
        for source_tab, (fname, content) in zip(source_tabs, files.items()):
            with source_tab:
                lines_list = content.split("\n")
                total_lines = len(lines_list)
                fc1, fc2 = st.columns([4, 1])
                with fc1:
                    _copy_button(f"📋 {fname} 복사", content, key=f"batch_copy_{screen_id}_{fname}")
                with fc2:
                    expand_key = f"batch_expand_{screen_id}_{fname}"
                    show_full = (
                        st.checkbox("펼치기 (전체 보기)", key=expand_key)
                        if total_lines > PREVIEW_LINES else True
                    )
                lang = "xml" if fname.endswith(".xml") else "java"
                if show_full or total_lines <= PREVIEW_LINES:
                    with st.container(height=450):
                        st.code(content, language=lang, line_numbers=True)
                else:
                    st.code("\n".join(lines_list[:PREVIEW_LINES]), language=lang, line_numbers=True)
                    st.caption(f"총 {total_lines}줄 중 {PREVIEW_LINES}줄만 표시했습니다 - 필요하면 '펼치기'를 누르세요.")

    with tab_validation:
        _render_validation_issue_list(validation_results, files, buckets, key_prefix=f"pipeline_{screen_id}")

    with tab_review:
        st.caption(
            "정규식 기반 규칙 스캔입니다(LLM 아님) - 확정된 취약점이 아니라 '검토가 필요한 후보'를 표시합니다."
        )
        if not review_findings:
            st.write("발견된 항목이 없습니다.")
        for fname, findings in review_findings.items():
            by_type: dict[str, list] = {}
            for f in findings:
                by_type.setdefault(f.issue_type, []).append(f)
            st.markdown(f"**{fname}** — {len(findings)}건")
            for issue_type, items in by_type.items():
                _rank = {"BLOCKER": 2, "WARNING": 1, "INFO": 0}
                group_severity = max((it.severity for it in items), key=lambda s: _rank.get(s, 0))
                show_key = f"batch_review_expand_{screen_id}_{fname}_{issue_type}"
                show_all = (
                    st.checkbox(f"[{group_severity}/{issue_type}] {len(items)}건 전체 보기", key=show_key)
                    if len(items) > 5 else True
                )
                if not show_all:
                    st.write(f"[{group_severity}/{issue_type}] {len(items)}건 (아래 예시 5건, 체크박스로 전체 보기)")
                sample = items if show_all else items[:5]
                for it in sample:
                    text = f"L{it.line_no}: {it.message}" if it.line_no else it.message
                    if it.severity == "BLOCKER":
                        st.error(text)
                    elif it.severity == "WARNING":
                        st.warning(text)
                    else:
                        st.info(text)

    with tab_ai:
        _render_ai_recommendation(screen_id, to_prefix(screen_id), files, buckets)

    with tab_diff:
        _render_diff_test(screen_id, buckets, package_p1, package_p2)


st.title("G-SCM AS-IS → TO-BE 변환 (v0)")
st.caption(
    "P/F/D BizUnit(.java/.bizunit) + XSQL을 화면 1개 단위로 업로드하세요. "
    "결정론적 규칙으로 먼저 변환하고, LLM은 선택했을 때만 Service 로직 포팅에 씁니다."
)

input_mode = st.radio(
    "입력 방식", ["폴더 경로 지정", "파일 직접 업로드"], horizontal=True,
    help="로컬 전용 앱이라 폴더 경로를 직접 읽을 수 있습니다. 폴더 안에 화면이 여러 개 섞여 있어도 "
         "한 번에 전부 변환하지 않고 화면을 골라서 하나씩 처리합니다(CLAUDE.md 원칙).",
)

buckets: dict[str, dict[str, str]] = {"P": {}, "F": {}, "D": {}}
screen_id = ""
as_is_paths: dict[str, str] = {}
package_p1, package_p2 = "TODO", "TODO"

if input_mode == "폴더 경로 지정":
    st.caption(
        "폴더를 지정하면 1~7단계가 전부 자동으로 이어서 진행됩니다(진행 상태가 실시간으로 "
        "표시됩니다) - 6단계(교차분석+영향도분석)·7단계(Maven 빌드)는 아직 저장하지 않은 이번 "
        "배치를 임시 사본(pilot/ 전체 복사본 + 이번 배치 파일)에 미리 반영해서 확인합니다. "
        "실제 pilot/ 폴더와 DB에는 사람이 결과를 검토하고 '승인하고 저장'을 눌러야만 반영됩니다 "
        "(CLAUDE.md \"사람 리뷰 없는 자동 저장 금지\" 원칙)."
    )
    folder_str = st.text_input(
        "AS-IS 폴더 경로",
        value=r"C:\project\gscm\workspace\dev-rp-online\src\java\gscm",
        placeholder=r"예: C:\Users\10982\project\TransGscm\legacy 또는 ...\r\pm\pla\plab",
        help="하위 폴더까지 재귀적으로 뒤집니다 - biz/와 db/가 나뉘어 있어도 됩니다. 필요하면 직접 수정하세요.",
    )
    if folder_str:
        screens, all_paths, problems = _scan_folder(Path(folder_str))
        for p in problems:
            st.warning(p)

        if screens:
            screen_ids = sorted(screens.keys())
            st.info(f"폴더에서 화면 {len(screen_ids)}개 발견: {', '.join(screen_ids)}")

            # 영향도 질의는 이번 실행 결과가 아니라 **DB에 이미 적재된 콜그래프**를 보므로
            # 파이프라인을 돌리지 않아도 쓸 수 있다 - 그래서 실행 버튼보다 앞에 둔다.
            if st.button("🎯 영향도 질의 (메서드 → 영향받는 화면·nctRid)", key="impact_query_btn"):
                _show_impact_dialog()

            pipeline_target_ids = st.multiselect(
                "파이프라인 대상 화면", screen_ids, default=screen_ids, key="pipeline_target_ids",
                help="화면이 많을수록 2단계(LLM 포팅)·5단계(AI 추천) LLM 호출이 늘어납니다 - "
                     "파일럿 단계에서는 몇 개만 골라 돌려보는 걸 권장합니다.",
            )
            if pipeline_target_ids:
                _est = _estimate_pipeline_outputs(screens, pipeline_target_ids)
                _as_is_total = sum(_est["as_is"].values())
                _to_be_total = sum(_est["to_be"].values())
                st.caption(
                    f"📊 변환 예상: 선택한 {len(pipeline_target_ids)}개 화면의 AS-IS 원본 {_as_is_total}개"
                    f"(P java {_est['as_is']['p_java']}·F java {_est['as_is']['f_java']}·"
                    f"D java {_est['as_is']['d_java']}·D xsql {_est['as_is']['d_xsql']}) 기준으로 "
                    f"TO-BE 파일 약 {_to_be_total}개가 생성될 것으로 예상됩니다(Api {_est['to_be']['Api.java']}·"
                    f"Service {_est['to_be']['Service.java']}·Store {_est['to_be']['Store.java']}·"
                    f"Dto {_est['to_be']['Dto.java']}·Mapper {_est['to_be']['Mapper.xml']}) - 화면마다 "
                    "P/F/D 원본이 실제로 있는지에 따라 달라지는 추정치이며, 실제 결과는 1단계 실행 후 확정됩니다."
                )
            opt_cols = st.columns([2, 1, 1])
            with opt_cols[0]:
                pipeline_include_ai = st.checkbox(
                    "5단계(AI 추천) 포함", value=True, key="pipeline_include_ai",
                    help="끄면 5단계를 건너뛰고 바로 승인 대기로 넘어갑니다 - nctRid 개수만큼 LLM "
                         "Gateway 호출이 추가되니(약 4초/건) 화면이 많을 때는 꺼도 됩니다.",
                )
            with opt_cols[1]:
                pipeline_max_retries = st.number_input(
                    "호출 실패 재시도", min_value=0, max_value=5, value=2,
                    key="pipeline_max_retries",
                    help="2단계에서 LLM Gateway 호출 자체가 실패한(타임아웃/네트워크) 메서드를 "
                         "다시 시도하는 라운드 수입니다.",
                )
            with opt_cols[2]:
                pipeline_max_repair = st.number_input(
                    "오류 수리 라운드", min_value=0, max_value=5, value=2,
                    key="pipeline_max_repair",
                    help="3단계 정적 검증에서 BLOCKER가 난 'LLM이 포팅한' 메서드를 오류 메시지와 "
                         "함께 다시 LLM에 보내 고치게 하는 라운드 수입니다(0이면 수리 안 함). "
                         "라운드마다 수리 대상 메서드 수만큼 LLM 호출이 추가됩니다.",
                )

            package_map: dict[str, tuple[str, str]] = {}
            for sid in pipeline_target_ids:
                guess = _guess_package(all_paths.get(sid, {}))
                package_map[sid] = guess if guess else ("TODO", "TODO")
            if any(v == ("TODO", "TODO") for v in package_map.values()):
                st.warning(
                    "일부 화면은 경로에서 패키지 p1/p2를 자동 인식하지 못했습니다 "
                    "(.../r/{p1}/{p2}/{p2}b/... 패턴이 아닌 경로) - 해당 화면은 TO-BE 패키지가 "
                    "com.skhynix.gscm.r.TODO.TODO로 생성됩니다."
                )

            _STAGE_LABELS = {
                # 0단계는 사용자가 정의한 7단계 밖이지만, CLAUDE.md "계획 없이 바로 코드를
                # 생성하지 않는다" 원칙에 따라 변환 전에 반드시 먼저 도는 준비 단계라 같이 보여준다.
                0: "변환 계획 수립 (tracking/conversion-plans/)",
                1: "1단계 규칙기반 변환 (LLM 미사용)",
                2: "2단계 LLM 포팅",
                3: "정적 검증 (규칙기반)",
                4: "품질·취약점 스캔 (규칙기반)",
                5: "AI 추천 변환 소스",
                6: "전체 화면 교차 분석 + 영향도 분석 (임시 사본)",
                7: "Maven 빌드 검증 (임시 사본)",
            }

            def _render_stage_line(placeholder, num: int, icon: str, extra: str = "") -> None:
                placeholder.markdown(f"{icon} **{num}. {_STAGE_LABELS[num]}**{extra}")

            if st.button(
                f"▶️ 파이프라인 시작 (계획 수립 + 1~7단계, {len(pipeline_target_ids)}개 화면)",
                disabled=not pipeline_target_ids, key="pipeline_start_btn",
            ):
                from agents.workflow_graph import run_pipeline_part_a

                pipeline_screens = {sid: screens[sid] for sid in pipeline_target_ids}
                stage_placeholders = {n: st.empty() for n in range(0, 8)}
                for n in range(0, 8):
                    _render_stage_line(stage_placeholders[n], n, "⏳", " — 대기")
                if not pipeline_include_ai:
                    _render_stage_line(stage_placeholders[5], 5, "⏭️", " — 건너뜀(선택 해제됨)")

                total_screens = len(pipeline_target_ids)

                # 5단계(AI 추천) 대상 건수는 화면의 P/F 원본 텍스트만으로 미리 셀 수 있다(포팅 결과와
                # 무관 - extract_dto_fields는 원본 P/F/.bizunit 텍스트에서 nctRid별 필드를 뽑는
                # 결정론적 함수다, chatui/react_variant.py·agents/workflow_graph.py와 동일 호출).
                # 파이프라인을 시작하기 전에 "총 N건 중 몇 건 남았는지"를 보여주려면 이 총량을
                # 먼저 알아야 한다 - 재추출이 아니라 진행률 표시용으로 같은 함수를 한 번 더 부르는 것뿐.
                total_ai = 0
                if pipeline_include_ai:
                    for sid in pipeline_target_ids:
                        buckets = pipeline_screens[sid]
                        p_java = buckets.get("P", {}).get("java")
                        if not p_java:
                            continue
                        total_ai += len(extract_dto_fields(
                            p_java, buckets.get("F", {}).get("java"), buckets.get("P", {}).get("bizunit"),
                        ))

                # 2단계(LLM 포팅) 대상 건수는 1단계(convert_all)가 끝나야 알 수 있다 - 화면마다
                # Service.java가 실제로 생성됐고 F 메서드가 있어야 포팅 대상이 되기 때문(_convert_screen
                # 참고). convert_all 노드가 끝나는 순간 partial["pending_methods"]로 정확한 총량을 받는다.
                _counts = {"port": 0, "total_port": None, "ai": 0}

                def _pipeline_progress_cb(node_name: str, partial: dict) -> None:
                    if node_name == "plan_all":
                        _written = partial.get("plan_paths", {}) or {}
                        _ok = [k for k in _written if not k.startswith("_")]
                        _render_stage_line(
                            stage_placeholders[0], 0, "✅",
                            f" — 완료 ({len(_ok)}개 화면 계획 기록)"
                            + (f" · {_written.get('_error')}" if "_error" in _written else ""),
                        )
                        _render_stage_line(stage_placeholders[1], 1, "🔄", " — 진행 중")
                    elif node_name == "convert_all":
                        pending = partial.get("pending_methods", {}) or {}
                        _counts["total_port"] = sum(len(v) for v in pending.values())
                        _render_stage_line(stage_placeholders[1], 1, "✅", f" — 완료 (전체 {total_screens}개 화면)")
                        if _counts["total_port"]:
                            _render_stage_line(
                                stage_placeholders[2], 2, "🔄",
                                f" — 0/{_counts['total_port']}건 진행 중 (남음 {_counts['total_port']}건)",
                            )
                        else:
                            _render_stage_line(stage_placeholders[2], 2, "🔄", " — 포팅 대상 없음")
                    elif node_name == "port_one_screen_method":
                        _counts["port"] += 1
                        total = _counts["total_port"] or _counts["port"]
                        remaining = max(total - _counts["port"], 0)
                        _render_stage_line(
                            stage_placeholders[2], 2, "🔄",
                            f" — {_counts['port']}/{total}건 진행 중 (남음 {remaining}건)",
                        )
                    elif node_name == "validate_all":
                        total = _counts["total_port"] or 0
                        if total:
                            extra = f" — 완료 ({min(_counts['port'], total)}/{total}건)"
                        else:
                            extra = " — 완료 (포팅 대상 없음)"
                        _render_stage_line(stage_placeholders[2], 2, "✅", extra)
                        _render_stage_line(stage_placeholders[3], 3, "✅", f" — 완료 (전체 {total_screens}개 화면)")
                        _render_stage_line(stage_placeholders[4], 4, "🔄", " — 진행 중")
                    elif node_name == "scan_all":
                        _render_stage_line(stage_placeholders[4], 4, "✅", f" — 완료 (전체 {total_screens}개 화면)")
                        if pipeline_include_ai:
                            if total_ai:
                                _render_stage_line(
                                    stage_placeholders[5], 5, "🔄", f" — 0/{total_ai}건 진행 중 (남음 {total_ai}건)",
                                )
                            else:
                                _render_stage_line(stage_placeholders[5], 5, "🔄", " — 대상 nctRid 없음")
                    elif node_name == "ai_recommend_one":
                        _counts["ai"] += 1
                        total = total_ai or _counts["ai"]
                        remaining = max(total - _counts["ai"], 0)
                        _render_stage_line(
                            stage_placeholders[5], 5, "🔄",
                            f" — {_counts['ai']}/{total}건 진행 중 (남음 {remaining}건)",
                        )

                final_state = run_pipeline_part_a(
                    pipeline_screens, package_map,
                    include_ai_recommend=pipeline_include_ai, max_retries=pipeline_max_retries,
                    max_repair_retries=pipeline_max_repair, all_paths=all_paths,
                    progress_cb=_pipeline_progress_cb,
                )
                if pipeline_include_ai:
                    if total_ai:
                        extra = f" — 완료 ({min(_counts['ai'], total_ai)}/{total_ai}건)"
                    else:
                        extra = " — 완료 (대상 nctRid 없음)"
                    _render_stage_line(stage_placeholders[5], 5, "✅", extra)

                # 3단계에서 BLOCKER가 나서 LLM에게 다시 고치게 한 라운드가 있었으면 그 사실을
                # 남긴다(수리 자체는 repair_gate 노드가 그래프 안에서 처리 - 여기선 표시만).
                _repair_rounds = final_state.get("repair_round", 0)
                if _repair_rounds:
                    _render_stage_line(
                        stage_placeholders[3], 3, "✅",
                        f" — 완료 (BLOCKER 수리 {_repair_rounds}라운드 수행 후 재검증)",
                    )

                pipeline_batch_results = _pipeline_state_to_batch_results(
                    final_state, pipeline_screens, all_paths, package_map,
                )

                # 화면별 "미변환 사유 + 수동 처리 가이드"를 파일로 남긴다(멘토 코멘트 §A) - 새로
                # 계산하는 값 없이 위 결과를 사람이 읽을 순서로 재구성만 한다.
                from agents.handoff_report import write_reports

                try:
                    handoff_paths = write_reports(pipeline_batch_results)
                except OSError as e:
                    handoff_paths = {}
                    st.warning(f"인수인계 문서 기록 실패(변환 결과에는 영향 없음): {e}")

                _render_stage_line(stage_placeholders[6], 6, "🔄", " — 진행 중 (임시 사본 준비 중)")
                _render_stage_line(stage_placeholders[7], 7, "⏳", " — 대기")
                stage67_preview = _run_stage_6_7_preview(pipeline_batch_results)
                _render_stage_line(
                    stage_placeholders[6], 6, "✅",
                    f" — 완료 (중복 후보 {len(stage67_preview['cross_result'].duplicate_groups)}건, "
                    f"DB 기준 중복 함수 {len(stage67_preview['dup_methods'])}건, "
                    f"영향도 대시보드 {len(stage67_preview['dashboard_rows'])}건)",
                )
                maven_ok = stage67_preview["maven_result"].passed
                _render_stage_line(stage_placeholders[7], 7, "✅" if maven_ok else "❌", " — 완료")

                st.session_state["pipeline_final_state"] = final_state
                st.session_state["pipeline_screens"] = pipeline_screens
                st.session_state["pipeline_all_paths"] = all_paths
                st.session_state["pipeline_package_map"] = package_map
                st.session_state["pipeline_batch_results"] = pipeline_batch_results
                st.session_state["pipeline_stage67_preview"] = stage67_preview
                st.session_state["pipeline_handoff_paths"] = handoff_paths
                st.session_state["pipeline_saved"] = False
                st.rerun()

            pipeline_batch_results = st.session_state.get("pipeline_batch_results")
            if pipeline_batch_results:
                st.divider()
                ok_n = sum(
                    1 for r in pipeline_batch_results
                    if not r["error"] and r["validation_total"] == r["validation_pass"]
                )
                st.write(
                    f"1~5단계 완료(화면별): {len(pipeline_batch_results)}개 화면 중 정적 검증 전부 통과 {ok_n}개 "
                    "— 6~7단계 결과는 아래 참고"
                )
                st.caption("화면 ID를 누르면 바로 아래에 소스/검증/스캔/AI추천 상세가 나타납니다.")
                for r in pipeline_batch_results:
                    if r["error"]:
                        st.error(f"❌ {r['screen_id']}: {r['error']}")
                        continue
                    icon = "✅" if r["validation_total"] == r["validation_pass"] else "⚠️"
                    row_cols = st.columns([1, 5])
                    with row_cols[0]:
                        if st.button(r["screen_id"], key=f"pipeline_detail_btn_{r['screen_id']}"):
                            st.session_state["pipeline_detail_screen"] = r["screen_id"]
                    with row_cols[1]:
                        saved_label = "저장됨" if r["saved"] else "미저장"
                        st.write(
                            f"{icon} `{r['package_p1']}.{r['package_p2']}` - "
                            f"정적 검증 {r['validation_pass']}/{r['validation_total']} 통과, "
                            f"품질/취약점 스캔 {r['review_count']}건, AI 추천 {len(r['ai_recommendations'])}건 "
                            f"({saved_label})"
                        )

                selected_pipeline_screen = st.session_state.get("pipeline_detail_screen")
                if selected_pipeline_screen:
                    match = next((r for r in pipeline_batch_results if r["screen_id"] == selected_pipeline_screen), None)
                    if match and not match["error"]:
                        st.divider()
                        st.subheader(f"📂 {selected_pipeline_screen} 상세 결과")
                        for p_method, variant in match["ai_recommendations"].items():
                            st.session_state[f"react_variant_{selected_pipeline_screen}_{p_method}"] = variant
                        _render_batch_screen_detail(
                            selected_pipeline_screen, match["files"], match["validation_results"],
                            match["review_findings"], match.get("buckets"),
                            match.get("package_p1", "TODO"), match.get("package_p2", "TODO"),
                            plan=match.get("plan"), plan_path=match.get("plan_path"),
                            entry=match,
                            handoff_path=(st.session_state.get("pipeline_handoff_paths") or {}).get(
                                selected_pipeline_screen
                            ),
                        )

                stage67_preview = st.session_state.get("pipeline_stage67_preview")
                if stage67_preview:
                    st.divider()
                    st.markdown("### 6~7단계 결과 (승인 전 미리보기)")
                    st.caption(
                        "실제 pilot/ 폴더는 아직 그대로입니다 - 이번 배치 파일을 pilot/ 임시 사본에 "
                        "겹쳐 써서 미리 확인한 결과입니다. 아래 DB 기준 중복/미사용 함수는 이미 저장된 "
                        "과거 화면 기준이며(이번 배치는 저장 전이라 DB에 없음), 교차 분석 노트·Maven "
                        "빌드 결과는 이번 배치를 포함한 값입니다."
                    )
                    for note in stage67_preview["cross_result"].notes:
                        st.info(note)
                    for g in stage67_preview["cross_result"].duplicate_groups:
                        st.warning(f"[{g.kind}] {len(g.locations)}곳 중복: " + " / ".join(g.locations))
                    if stage67_preview["dup_methods"]:
                        with st.expander(
                            f"🧬 DB 기준 중복 함수(BODY_HASH 동일, 기존 저장 화면) — "
                            f"{len(stage67_preview['dup_methods'])}건", expanded=False,
                        ):
                            for grp in stage67_preview["dup_methods"]:
                                members = ", ".join(f"{m['screen_id']}:{m['method_name']}" for m in grp["members"])
                                st.write(f"- {members}")

                    st.markdown("#### 🎯 영향도 분석 대시보드 (기존 저장 화면 기준)")
                    st.caption(
                        "미사용 함수(콜그래프에서 한 번도 안 불림)와 오류 함수(BLOCKER 이슈·원본 버그 "
                        "보존)를 한 표로 합쳐 위험도 순으로 정렬했습니다 - 위험도 = BLOCKER건수*3 + "
                        "WARNING건수*1 + (미사용이면 +2) + (원본 버그 보존이면 +1). 확정 판정이 아니라 "
                        "검토 우선순위 신호이며, 삭제/수정은 사람이 원본을 보고 직접 판단하세요(자동 "
                        "삭제 없음). 이번 배치 자신의 메서드는 아직 저장 전이라 이 표에 없습니다."
                    )
                    dashboard_rows = stage67_preview["dashboard_rows"]
                    if not dashboard_rows:
                        st.info("검토가 필요한 항목이 없습니다(기존 저장 화면 기준).")
                    else:
                        _dash_table = [
                            {
                                "위험도": r["risk_score"],
                                "화면": r["screen_id"],
                                "계층": r["layer"],
                                "메서드": r["method_name"],
                                "TO-BE명": r.get("method_name_tobe") or "",
                                "케이스": ", ".join(r["cases"]) if r["cases"] else "-",
                                "BLOCKER": r["blocker_count"],
                                "WARNING": r["warning_count"],
                            }
                            for r in dashboard_rows
                        ]
                        st.dataframe(_dash_table, hide_index=True)
                        with st.expander(f"📋 항목별 상세 메시지 보기 ({len(dashboard_rows)}건)", expanded=False):
                            for r in dashboard_rows:
                                st.markdown(f"**{r['screen_id']}:{r['method_name']}** (위험도 {r['risk_score']}) — {', '.join(r['cases'])}")
                                for msg in r["sample_messages"]:
                                    st.caption(msg)

                    maven_result = stage67_preview["maven_result"]
                    if maven_result.passed:
                        st.success("✅ Maven 빌드 검증 통과 (임시 사본 기준)")
                    else:
                        st.error("❌ Maven 빌드 검증 실패 (임시 사본 기준) - 저장해도 실제 pilot/이 컴파일되지 않습니다.")
                    for issue in maven_result.issues:
                        if issue.severity != "BLOCKER":
                            st.info(f"[{issue.severity}/{issue.issue_type}] {issue.message}")
                            continue
                        lines = issue.message.split("\n")
                        header, error_lines = lines[0], lines[1:]
                        st.caption(f"[{issue.severity}/{issue.issue_type}] {header}")
                        grouped, ungrouped = _parse_javac_errors(error_lines)
                        if st.button("🔍 팝업으로 크게 보기", key=f"pipeline_maven_dialog_btn_{issue.issue_type}"):
                            _show_maven_dialog(header, grouped, ungrouped)
                        _render_maven_errors(grouped, ungrouped)

                st.divider()
                st.markdown("### 승인 후 저장")
                pipeline_save_to_db = st.checkbox("DB에도 기록", value=True, key="pipeline_save_to_db")
                if st.button("✅ 승인하고 저장", key="pipeline_approve_save_btn"):
                    saved_results = _run_batch_save(pipeline_batch_results, pipeline_save_to_db)
                    st.session_state["pipeline_batch_results"] = saved_results
                    st.session_state["pipeline_saved"] = True
                    st.session_state["pipeline_just_saved"] = True
                    st.rerun()

                # st.rerun() 직후라 버튼 콜백 안에서 띄운 st.success()는 화면에 그려지기도 전에
                # 사라진다 - 플래그를 세션에 남겨뒀다가 재실행된 다음 화면에서 한 번만 보여주고
                # 지운다(이 파일의 scroll_to_validation/_trigger_save와 같은 패턴).
                if st.session_state.pop("pipeline_just_saved", False):
                    st.success("✅ 저장 완료 - 실제 pilot/ 폴더와 DB에 반영되었습니다.")
else:
    uploaded = st.file_uploader(
        "AS-IS 파일 업로드 (여러 개 선택 가능)",
        type=["java", "bizunit", "xsql"],
        accept_multiple_files=True,
    )
    if uploaded:
        buckets, problems, screen_id = _categorize(uploaded)
        for p in problems:
            st.warning(p)
        if screen_id:
            st.warning(
                "파일 직접 업로드 모드는 원본 경로 정보가 없어 패키지 p1/p2를 자동 인식할 수 없습니다 "
                "(TO-BE 패키지가 com.skhynix.gscm.r.TODO.TODO로 생성됩니다) - 정확한 패키지가 필요하면 "
                "'폴더 경로 지정' 모드를 쓰세요."
            )

if screen_id:
    if not any(buckets[layer] for layer in buckets):
        st.error("화면ID를 인식하지 못했습니다. 파일명이 P/F/D + 화면ID + 확장자 형태인지 확인하세요 (예: PPLA047.java).")
        st.stop()

    # 작업 상태 요약 - 아래로 스크롤해서 2/3단계를 보는 동안에도 핵심 진행 상황을 다시 위로
    # 올라오지 않고 확인할 수 있게, position: sticky로 상단에 고정한다. st.container(key=...)가
    # 만드는 "st-key-{key}" 클래스를 CSS로 targeting하는 방식 - Streamlit 내부 DOM 구조를 추측해서
    # 짜맞춘 선택자보다 안정적이다(공식 지원되는 key 기능 기반). 다만 이 개발 환경엔 브라우저가
    # 없어 실제 렌더링/스크롤 동작은 직접 확인하지 못했다 - 사용해보고 어긋나면 알려달라.
    st.markdown(
        """
        <style>
        div.st-key-status_bar {
            position: sticky;
            top: 2.875rem;
            z-index: 999;
            background-color: var(--background-color, inherit);
            padding: 0.5rem 0;
            border-bottom: 1px solid rgba(128, 128, 128, 0.3);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="status_bar"):
        status_cols = st.columns(5)
        status_cols[0].metric("화면ID", screen_id)

        has_skeleton = "skeleton_files" in st.session_state
        service_fname_quick = f"{to_prefix(screen_id)}Service.java"

        with status_cols[1]:
            val_results = st.session_state.get("validation_results", [])
            if val_results:
                passed_n = sum(1 for r in val_results if r.passed)
                st.metric("정적 검증", f"{passed_n}/{len(val_results)} 통과")
            else:
                st.metric("정적 검증", "미실행")
            if has_skeleton and st.button("🔍 재검증", key=f"quick_revalidate_{screen_id}"):
                st.session_state["validation_results"] = validate_screen(
                    st.session_state["skeleton_files"], to_prefix(screen_id)
                )
                st.rerun()

        with status_cols[2]:
            f_java_present = bool(buckets["F"].get("java"))
            total_f = len(extract_methods(buckets["F"]["java"])) if f_java_present else 0
            ported_n = 0
            if f_java_present:
                ported_n = len(st.session_state.get(f"ported_methods_{screen_id}", set()))
                st.metric("F 포팅 진행", f"{ported_n}/{total_f}")
            else:
                st.metric("F 포팅 진행", "N/A")
            if has_skeleton and total_f > 0 and service_fname_quick in st.session_state["skeleton_files"]:
                if st.button("▶️ 전체 포팅 실행", key=f"quick_port_all_{screen_id}"):
                    st.session_state["_trigger_bulk_porting"] = True
                    st.rerun()

        with status_cols[3]:
            if "review_findings" in st.session_state:
                review_n = sum(len(v) for v in st.session_state["review_findings"].values())
                st.metric("품질/취약점 스캔", f"{review_n}건")
            else:
                st.metric("품질/취약점 스캔", "미실행")
            if has_skeleton and st.button("🛡️ 재스캔", key=f"quick_rescan_{screen_id}"):
                st.session_state["review_findings"] = run_review(
                    st.session_state["skeleton_files"], to_prefix(screen_id)
                )
                st.rerun()

        with status_cols[4]:
            # 포팅이 끝나야 저장 가능(스텁 상태 저장 방지, tab_save와 동일한 게이트) - F가 없는
            # 화면은 포팅 자체가 필요 없어 바로 준비된 것으로 본다.
            porting_ready = (not f_java_present) or total_f == 0 or ported_n >= total_f
            if has_skeleton:
                st.metric("3단계 저장", "준비됨" if porting_ready else "포팅 필요")
            else:
                st.metric("3단계 저장", "미실행")
            if has_skeleton and porting_ready:
                if st.button("💾 저장", key=f"quick_save_{screen_id}"):
                    st.session_state["_trigger_save"] = True
                    st.rerun()

    def _run_conversion() -> None:
        """규칙 기반 골격/Mapper/Dto 생성 + 정적 검증까지 한 번에 실행한다.

        "1단계" 최초 실행과 "변환 재수행"(예: 원본 XSQL 태그 정정 후 다시 돌릴 때) 둘 다
        이 함수를 쓴다 - 두 버튼이 서로 다른 로직으로 갈라지지 않게 하기 위함.
        """
        progress = st.progress(0, text="변환 시작...")

        progress.progress(15, text="1/4 골격(Api/Service/Store) 생성 중...")
        skel = generate_skeletons(
            screen_id=screen_id,
            package_p1=package_p1,
            package_p2=package_p2,
            p_java_text=buckets["P"].get("java"),
            f_java_text=buckets["F"].get("java"),
            d_java_text=buckets["D"].get("java"),
            p_bizunit_text=buckets["P"].get("bizunit"),
        )

        progress.progress(40, text="2/4 XSQL → MyBatis Mapper 변환 중...")
        mapper_result = None
        if buckets["D"].get("xsql"):
            mapper_result = convert_xsql_fragment(buckets["D"]["xsql"])
            # 문서 뼈대(DOCTYPE/root/namespace/select id·parameterType·resultType)는 화면ID/패키지/
            # D 메서드명 컨텍스트가 있어야 알 수 있어 별도 단계로 분리했다 - skel(1단계 결과)의
            # stmt_id_to_method(D의 dbSelect("S00N",...) 호출에서 뽑음)를 그대로 재사용한다.
            doc_result = finalize_mapper_document(
                mapper_result.mybatis_xml,
                screen_id=screen_id,
                package_p1=package_p1,
                package_p2=package_p2,
                stmt_id_to_method=skel.stmt_id_to_method,
            )
            mapper_result.mybatis_xml = doc_result.mybatis_xml
            mapper_result.issues.extend(doc_result.issues)

        progress.progress(65, text="3/4 Dto(요청/응답 필드) 생성 중...")
        dto = None
        if buckets["P"].get("java"):
            dto = generate_dto(
                screen_id=screen_id,
                package_p1=package_p1,
                package_p2=package_p2,
                p_java_text=buckets["P"].get("java"),
                f_java_text=buckets["F"].get("java"),
                p_bizunit_text=buckets["P"].get("bizunit"),
            )

        st.session_state["skeleton_files"] = skel.files
        st.session_state["skeleton_issues"] = list(skel.issues)
        st.session_state["skeleton_methods"] = list(skel.methods)
        st.session_state["skeleton_method_calls"] = list(skel.method_calls)
        st.session_state["mapper_issues"] = list(mapper_result.issues) if mapper_result else []
        st.session_state["dto_issues"] = list(dto.issues) if dto else []
        if mapper_result:
            st.session_state["skeleton_files"][f"{to_prefix(screen_id)}Mapper.xml"] = mapper_result.mybatis_xml
        if dto:
            st.session_state["skeleton_files"].update(dto.files)
        st.session_state["screen_id"] = screen_id
        # 포팅 진행 상태(ported_methods_{screen})는 일부러 지우지 않는다 - 재수행이 골격/Mapper/Dto만
        # 다시 만들고 이미 포팅된 Service 스텁을 덮어쓰긴 하지만, 사용자가 재수행 의도를 명확히 알 수
        # 있도록 아래 캡션에 경고를 남긴다.
        st.session_state[f"ported_methods_{screen_id}"] = set()

        progress.progress(90, text="4/4 실행 가능성 정적 검증 + 코드 품질/취약점 스캔 중...")
        st.session_state["validation_results"] = validate_screen(
            st.session_state["skeleton_files"], to_prefix(screen_id)
        )
        st.session_state["review_findings"] = run_review(
            st.session_state["skeleton_files"], to_prefix(screen_id)
        )
        progress.progress(100, text="완료")

    c1, c2 = st.columns([3, 2])
    with c1:
        if st.button("1단계: 규칙 기반 변환 실행 (골격 + MyBatis Mapper + Dto)", type="primary"):
            _run_conversion()
            st.rerun()
    with c2:
        if "skeleton_files" in st.session_state:
            if st.button("🔄 변환 재수행 (원본 다시 읽어서 처음부터 재생성)"):
                _run_conversion()
                st.rerun()
    if "skeleton_files" in st.session_state:
        st.caption(
            "⚠️ 재수행하면 골격/Mapper/Dto를 처음부터 다시 만들고, LLM으로 포팅한 Service 로직도 "
            "스텁으로 초기화됩니다(2단계에서 다시 포팅해야 함). 원본 파일(폴더 경로 모드)이나 "
            "패키지 p1/p2 입력을 고친 뒤 다시 반영할 때 쓰세요."
        )

    st.divider()
    if st.button(
        "⚡ LangGraph 오케스트레이션으로 한번에 실행 (규칙변환 + F메서드 병렬 포팅 + 검증 + 스캔)",
        help=(
            "1단계~2단계를 agents/workflow_graph.py의 LangGraph 그래프 하나로 실행합니다. F 메서드를 "
            "순차 호출(기존 '전체 포팅')이 아니라 LangGraph의 Send로 동시에 LLM Gateway에 보내고, "
            "호출 자체가 실패한 메서드만 최대 2회 재시도합니다(정적 검증 실패를 자동으로 고치는 "
            "수리 루프는 아직 범위 밖 - Phase 5). 결과는 기존 탭(변환 결과/2단계 포팅/3단계 저장)에 "
            "그대로 반영되고, 저장은 여전히 사람이 검토 후 눌러야 합니다."
        ),
    ):
        f_java_present = bool(buckets["F"].get("java"))
        spinner_text = (
            "LangGraph 그래프 실행 중... (F 메서드를 병렬로 LLM Gateway에 보내는 중이라 시간이 걸릴 수 있습니다)"
            if f_java_present else "LangGraph 그래프 실행 중... (규칙 기반 변환만 - F 원본이 없어 포팅 단계는 건너뜁니다)"
        )
        with st.spinner(spinner_text):
            from agents.workflow_graph import run_screen_conversion

            result = run_screen_conversion(
                screen_id=screen_id,
                package_p1=package_p1,
                package_p2=package_p2,
                p_java=buckets["P"].get("java"),
                f_java=buckets["F"].get("java"),
                d_java=buckets["D"].get("java"),
                p_bizunit=buckets["P"].get("bizunit"),
                d_xsql=buckets["D"].get("xsql"),
            )
        st.session_state["skeleton_files"] = result["files"]
        st.session_state["skeleton_issues"] = result.get("generation_issues", [])
        # LangGraph 경로(agents/workflow_graph.py)는 아직 함수 단위 레지스트리를 안 돌려준다 -
        # 이 경로로 저장하면 CONV_METHOD/CONV_METHOD_CALL 적재는 빈 채로 남는다(파일 단위 CONV_FILE/
        # CONV_ISSUE 기록은 그대로 동작함, 알려진 한계로 남겨둔다).
        st.session_state["skeleton_methods"] = result.get("skeleton_methods", [])
        st.session_state["skeleton_method_calls"] = result.get("skeleton_method_calls", [])
        st.session_state["mapper_issues"] = []
        st.session_state["dto_issues"] = []
        st.session_state["validation_results"] = result.get("validation_results", [])
        st.session_state["review_findings"] = result.get("review_findings", {})
        st.session_state["screen_id"] = screen_id
        st.session_state[f"ported_methods_{screen_id}"] = set(result.get("ported_methods", []))
        st.rerun()

    if "skeleton_files" in st.session_state:
        files = st.session_state["skeleton_files"]

        all_issues = (
            st.session_state.get("skeleton_issues", [])
            + st.session_state.get("mapper_issues", [])
            + st.session_state.get("dto_issues", [])
        )
        validation_results = st.session_state.get("validation_results", [])
        blocker_files = [r for r in validation_results if not r.passed]
        review_findings: dict[str, list] = st.session_state.get("review_findings", {})
        total_review = sum(len(v) for v in review_findings.values())

        f_java = buckets["F"].get("java")
        service_fname = f"{to_prefix(screen_id)}Service.java"
        f_methods: list[str] = []
        f_bodies: dict[str, str] = {}
        ported: set[str] = set()
        if f_java and service_fname in files:
            f_methods = extract_methods(f_java)
            f_bodies = extract_method_bodies(f_java)
            ported = st.session_state.setdefault(f"ported_methods_{screen_id}", set())
        porting_complete = not f_methods or len(ported) >= len(f_methods)

        def _port_method(method: str) -> None:
            from agents.llm_gateway import chat

            body = f_bodies.get(method, "")
            prompt = (
                f"다음은 NEXCORE(BizUnit) F(Function) 계층 Java 메서드 {method}의 본문이다. "
                "이 로직(계산/분기/문자열 처리 등)을 하나도 빠짐없이 그대로 유지하면서, "
                "IDataSet/IOnlineContext/lookupDataUnit/lookupFunctionUnit 같은 NEXCORE 프레임워크 "
                "의존만 제거하고 Spring 서비스 메서드로 옮겨라. "
                "D BizUnit 호출(du.dXXXX(...))은 store.dXXXX(...) 형태로 바꿔라 (Service에 이미 "
                "`store` 필드가 있다). SQL이나 업무 규칙을 새로 설계하지 말고 원본 그대로 포팅만 해라. "
                "원본에 컴파일 에러나 미선언 변수가 있어도 그 부분을 고치지 말고 원본 그대로 옮긴 뒤 "
                "`// FIXME(원본 버그): ...` 로 표시해라. "
                f"`public Map<String, Object> {method}(Map<String, Object> request) {{ ... }}` 형태의 "
                "완성된 메서드 코드 하나만 출력하고, 코드 펜스나 다른 설명은 붙이지 마라.\n\n"
                f"원본 메서드 본문:\n```\n{body}\n```"
            )
            ported_code = chat(messages=[{"role": "user", "content": prompt}])
            ported_code = strip_code_fence(ported_code)
            st.session_state["skeleton_files"][service_fname] = splice_ported_method(
                st.session_state["skeleton_files"][service_fname], method, ported_code
            )
            ported.add(method)
            # 포팅할 때마다 정적 검증 + 취약점 스캔을 다시 돌린다 - "함수별로 실행에 문제 없는지" 바로 확인하기 위함.
            st.session_state["validation_results"] = validate_screen(
                st.session_state["skeleton_files"], to_prefix(screen_id)
            )
            st.session_state["review_findings"] = run_review(
                st.session_state["skeleton_files"], to_prefix(screen_id)
            )

        def _run_bulk_porting() -> None:
            progress = st.progress(0.0, text=f"0/{len(f_methods)} (0%)")
            for i, method in enumerate(f_methods):
                try:
                    with st.spinner(f"{method} 포팅 중... ({i + 1}/{len(f_methods)})"):
                        _port_method(method)
                except Exception as e:
                    st.error(f"{method} 포팅 실패: {e}")
                pct = int((i + 1) / len(f_methods) * 100)
                progress.progress(
                    (i + 1) / len(f_methods), text=f"{i + 1}/{len(f_methods)} ({pct}%) - 마지막: {method}"
                )
            final_results = st.session_state.get("validation_results", [])
            if any(not r.passed for r in final_results):
                st.session_state["scroll_to_validation"] = True

        # 상단 상태바의 "▶️ 전체 포팅 실행" 버튼은 탭 안이 아니라 여기(탭보다 앞, 항상 화면에 보이는
        # 위치)에서 실행한다 - 예전에는 이 실행 로직이 "🔧 2단계 포팅" 탭 안에만 있어서, 사용자가
        # 다른 탭을 보고 있는 상태에서 상단 버튼을 누르면 진행률이 안 보이는 화면 뒤에서만 갱신되고
        # 있었다(포팅은 실제로 진행되지만 사용자 눈에는 아무것도 안 보임). 여기서 실행하면 어느
        # 탭을 보고 있었든 진행률 바가 바로 이 자리에 나타난다.
        if f_java and service_fname in files and st.session_state.pop("_trigger_bulk_porting", False):
            st.info("▶️ 상단 버튼으로 전체 포팅을 시작합니다...")
            _run_bulk_porting()
            st.rerun()

        def _save_reviewed_files(save_to_db: bool) -> None:
            """검토 완료 저장 - pilot/에 TO-BE 트리로 쓰고, 선택 시 DB에도 기록한다.

            저장하기 직전에 정적 검증과 품질/취약점 스캔을 session_state에 남아있던 값이 아니라
            지금 st.session_state["skeleton_files"](=포팅 결과가 반영된 최신 코드) 기준으로 다시
            돌린다 - "화면 로드 시" 스텁 코드로 한 번 스캔한 결과가 포팅 후에도 그대로 DB에 남는
            일을 막기 위함이다. 저장되는 코드와 DB에 기록되는 스캔 결과가 항상 같은 시점 기준이어야
            한다.
            """
            current_files = st.session_state["skeleton_files"]
            fresh_validation = validate_screen(current_files, to_prefix(screen_id))
            fresh_review = run_review(current_files, to_prefix(screen_id))
            st.session_state["validation_results"] = fresh_validation
            st.session_state["review_findings"] = fresh_review

            # pilot/ 바로 아래에 실제 TO-BE 트리(gscm/src/main/...)를 만든다 - 화면별 하위 폴더를
            # 두지 않는다. 파일명 자체가 이미 화면 접두어(Pla047Api.java 등)로 구분되고, 이렇게 해야
            # 나중에 여러 화면이 쌓였을 때 실제 프로젝트에 그대로 병합할 수 있는 구조가 된다.
            out_dir = PROJECT_ROOT / "pilot"
            p1, p2 = package_p1, package_p2
            saved_paths: dict[str, Path] = {}
            for fname, content in current_files.items():
                rel = tobe_relpath(fname, p1, p2)
                full_path = out_dir / rel
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                saved_paths[fname] = full_path
            tree = "\n".join(f"- `{saved_paths[f].relative_to(out_dir)}`" for f in current_files)
            st.success(f"저장됨: {out_dir} ({len(current_files)}개 파일)\n\n{tree}\n\ngit add/commit은 별도로 직접 하세요.")

            if not save_to_db:
                return
            try:
                from agents import db

                db.ensure_schema()
                sid = st.session_state["screen_id"]
                prefix = to_prefix(sid)
                by_file = {r.file_name: r for r in fresh_validation}

                # 생성 단계 이슈(문법/골격 관련)는 계층별로 정확히 나뉘지 않는 부분이 남아있다 -
                # skeleton_issues는 Api/Service/Store 골격 생성 전체에서 나온 걸 P(JAVA)에 대표로
                # 붙인다(v0 한계, tracking/conversion-verification.csv에도 명시). 반면 정적 검증
                # 결과(fresh_validation)는 파일 단위로 정확히 나오므로 계층마다 정확히 귀속시킨다.
                layer_meta = {
                    "P(JAVA)": (f"P{sid}.java", as_is_paths.get("P.java"),
                                st.session_state.get("skeleton_issues", []), "chatui/skeleton_gen.py",
                                buckets["P"].get("java")),
                    "F(JAVA)": (f"F{sid}.java", as_is_paths.get("F.java"), [], None,
                                buckets["F"].get("java")),
                    "D(JAVA)": (f"D{sid}.java", as_is_paths.get("D.java"), [], None,
                                buckets["D"].get("java")),
                    "XSQL": (f"D{sid}.xsql", as_is_paths.get("D.xsql"),
                             st.session_state.get("mapper_issues", []), "chatui/converters.py",
                             buckets["D"].get("xsql")),
                    "DERIVED": (f"{sid}-dto-derived", None,
                                st.session_state.get("dto_issues", []), "chatui/skeleton_gen.py", None),
                }

                file_ids: dict[str, int] = {}
                file_id_by_layer: dict[str, int] = {}
                for suffix, layer in _LAYER_BY_SUFFIX:
                    fname = f"{prefix}{suffix}"
                    if fname not in current_files:
                        continue
                    as_is_filename, as_is_path, gen_issues, gen_detected_by, as_is_content = layer_meta[layer]
                    vr = by_file.get(fname)
                    build_check = "PASS" if vr and vr.passed else ("FAIL" if vr else "NOT_RUN")
                    content_hash = db.content_hash(as_is_content) if as_is_content else None

                    file_id = db.upsert_conv_file(
                        screen_id=sid, as_is_layer=layer,
                        as_is_filename=as_is_filename, as_is_path=as_is_path,
                        tobe_filename=fname, tobe_path=str(saved_paths[fname].parent),
                        conversion_method="RULE_BASED", conversion_status="IN_PROGRESS",
                        build_check=build_check, as_is_content_hash=content_hash,
                    )
                    file_ids[fname] = file_id
                    if layer in ("P(JAVA)", "F(JAVA)", "D(JAVA)"):
                        file_id_by_layer[layer[0]] = file_id
                # 함수 단위 레지스트리/콜그래프를 먼저 적재해서 method_id를 얻어야, 아래에서
                # 이슈를 메서드에 연결할 수 있다(그래서 이슈 기록을 파일 upsert 루프와 분리했다).
                method_ids = _persist_methods_and_calls(
                    db,
                    st.session_state.get("skeleton_methods", []),
                    st.session_state.get("skeleton_method_calls", []),
                    file_id_by_layer,
                )
                for suffix, layer in _LAYER_BY_SUFFIX:
                    fname = f"{prefix}{suffix}"
                    if fname not in file_ids:
                        continue
                    file_id = file_ids[fname]
                    as_is_filename, as_is_path, gen_issues, gen_detected_by, as_is_content = layer_meta[layer]
                    vr = by_file.get(fname)
                    m_ids = method_ids.get(layer[0]) if layer in ("P(JAVA)", "F(JAVA)", "D(JAVA)") else None
                    if gen_issues and gen_detected_by:
                        db.record_issues(file_id, gen_issues, gen_detected_by, method_id_by_name=m_ids)
                    if vr and vr.issues:
                        db.record_issues(file_id, vr.issues, "chatui/validators.py", method_id_by_name=m_ids)
                    if fresh_review.get(fname):
                        db.record_issues(
                            file_id, fresh_review[fname], "chatui/quality_scanner.py",
                            method_id_by_name=m_ids,
                        )

                # 계층 간 참조(Api->Service->Store->Mapper) 검증은 파일 하나에 속하지 않아
                # 별도 DERIVED 행으로 기록한다(AS_IS_FILENAME을 고유하게 둬서 위 Dto 파생 행과
                # 안 겹치게 한다 - CONV_FILE UNIQUE 제약이 NULL을 다 같은 값처럼 취급하지 않게 함).
                cross_vr = next((r for r in fresh_validation if r.check == "CROSS_LAYER_REF"), None)
                if cross_vr:
                    cross_file_id = db.upsert_conv_file(
                        screen_id=sid, as_is_layer="DERIVED",
                        as_is_filename=f"{sid}-cross-layer-check", as_is_path=None,
                        tobe_filename=None, tobe_path=str(out_dir),
                        conversion_method=None, conversion_status="NOT_STARTED",
                        build_check="PASS" if cross_vr.passed else "FAIL",
                    )
                    if cross_vr.issues:
                        db.record_issues(cross_file_id, cross_vr.issues, "chatui/validators.py")

                st.success("DB에 기록했습니다 (CONV_FILE.BUILD_CHECK 포함, CONV_ISSUE).")
            except Exception as e:
                st.error(f"DB 기록 실패: {e}")

        # 상단 상태바의 "💾 저장" 버튼도 탭(3단계 저장) 안이 아니라 여기서 처리한다 - 같은 이유로
        # 탭을 안 보고 있어도 저장 결과(성공/실패 메시지)가 바로 이 자리에 나타나게 하기 위함.
        if st.session_state.pop("_trigger_save", False):
            if porting_complete:
                with st.spinner("저장 중..."):
                    _save_reviewed_files(st.session_state.get(f"save_to_db_{screen_id}", True))
                st.rerun()
            else:
                st.warning("⏳ 2단계 포팅이 끝나지 않아 저장할 수 없습니다 - 먼저 F 메서드를 전부 포팅하세요.")

        # 단계별로 탭을 나눠서, 소스 보기 -> 포팅 -> 저장으로 넘어갈 때마다 페이지 전체를
        # 스크롤하지 않고 탭만 클릭하면 되게 한다. 탭 라벨에 진행 개수를 넣어서 굳이 안을
        # 열어보지 않아도 상태를 알 수 있다.
        result_label = "📄 변환 결과"
        if validation_results:
            result_label += f" ({len(validation_results) - len(blocker_files)}/{len(validation_results)} 통과)"
        porting_label = "🔧 2단계 포팅"
        if f_methods:
            porting_label += f" ({len(ported)}/{len(f_methods)})"
        save_label = "💾 3단계 저장" + (" (준비됨)" if porting_complete else " (포팅 필요)")

        tab_result, tab_porting, tab_save = st.tabs([result_label, porting_label, save_label])

        with tab_result:
            if all_issues:
                with st.expander(f"⚠️ 주의/미변환 항목 {len(all_issues)}건 - 반드시 확인", expanded=True):
                    for issue in all_issues:
                        label = f"[{issue.severity}/{issue.issue_type}]"
                        if issue.line_no:
                            label += f" (원본 {issue.line_no}행)"
                        text = f"{label} {issue.message}"
                        if issue.severity == "BLOCKER":
                            st.error(text)
                        else:
                            st.warning(text)

            st.markdown('<div id="validation-anchor"></div>', unsafe_allow_html=True)
            if st.session_state.pop("scroll_to_validation", False):
                _scroll_to("validation-anchor")
            with st.expander(
                f"🔍 실행 가능성 정적 검증 결과 - {len(validation_results) - len(blocker_files)}/{len(validation_results)} 통과"
                + (f", {len(blocker_files)}건 실패" if blocker_files else ""),
                expanded=bool(blocker_files),
            ):
                st.caption(
                    "실제 Maven/Spring 빌드 환경이 아직 없어 진짜 컴파일은 못 합니다 - 대신 중괄호 균형, "
                    "LLM 포팅 미완료 스텁, 계층 간 실제 호출 대상 존재 여부(Api→Service→Store→Mapper), "
                    "Mapper.xml well-formed 여부를 정적으로 확인합니다. PASS는 \"돌아간다\"가 아니라 "
                    "\"이 정적 검사를 통과했다\"는 뜻입니다."
                )
                _render_validation_issue_list(validation_results, files, buckets, key_prefix=f"single_{screen_id}")

            with st.expander(f"🛡️ 코드 품질/취약점 스캔 (규칙 기반) - {total_review}건", expanded=False):
                st.caption(
                    "정규식 기반 규칙 스캔입니다(LLM 아님) - 확정된 취약점이 아니라 '검토가 필요한 후보'를 "
                    "표시합니다: ${...}(MyBatis 텍스트 치환, 값에 따라 SQL 인젝션 가능), 문자열 연결로 "
                    "조립되는 SQL, 하드코딩된 비밀번호/키로 보이는 값, 남아있는 NEXCORE 의존, 포팅 시 "
                    "보존된 원본 버그(FIXME) 집계."
                )
                if not review_findings:
                    st.write("발견된 항목이 없습니다.")
                for fname, findings in review_findings.items():
                    by_type: dict[str, list] = {}
                    for f in findings:
                        by_type.setdefault(f.issue_type, []).append(f)
                    st.markdown(f"**{fname}** — {len(findings)}건")
                    for issue_type, items in by_type.items():
                        # 같은 issue_type이라도 항목별 severity가 다를 수 있다(예: SQL_INJECTION_RISK는
                        # 조건절 문맥 여부로 WARNING/INFO가 갈림) - 그룹 라벨은 그 중 가장 심각한
                        # severity로 보여주되, 실제 색상은 항목별 severity(it.severity)를 따른다.
                        _rank = {"BLOCKER": 2, "WARNING": 1, "INFO": 0}
                        group_severity = max((it.severity for it in items), key=lambda s: _rank.get(s, 0))
                        show_key = f"review_expand_{screen_id}_{fname}_{issue_type}"
                        show_all = (
                            st.checkbox(f"[{group_severity}/{issue_type}] {len(items)}건 전체 보기", key=show_key)
                            if len(items) > 5 else True
                        )
                        if not show_all:
                            st.write(f"[{group_severity}/{issue_type}] {len(items)}건 (아래 예시 5건, 체크박스로 전체 보기)")
                        sample = items if show_all else items[:5]
                        for it in sample:
                            text = f"L{it.line_no}: {it.message}" if it.line_no else it.message
                            if it.severity == "BLOCKER":
                                st.error(text)
                            elif it.severity == "WARNING":
                                st.warning(text)
                            else:
                                st.info(text)

                service_fname_for_review = f"{to_prefix(screen_id)}Service.java"
                if service_fname_for_review in files:
                    st.divider()
                    llm_review_key = f"llm_review_{screen_id}"
                    if st.button("🤖 LLM 코드 리뷰 (선택, 실험적 - 코드는 수정하지 않음)", key=f"llmreview_btn_{screen_id}"):
                        with st.spinner("LLM이 Service 코드를 리뷰하는 중..."):
                            try:
                                st.session_state[llm_review_key] = llm_review(files[service_fname_for_review])
                            except Exception as e:
                                st.error(f"LLM 리뷰 실패: {e}")
                    if llm_review_key in st.session_state:
                        st.markdown("**LLM 리뷰 결과 (참고용 - 코드에는 반영되지 않았습니다):**")
                        st.markdown(st.session_state[llm_review_key])

            source_tabs = st.tabs(list(files.keys()))
            PREVIEW_LINES = 40
            for source_tab, (fname, content) in zip(source_tabs, files.items()):
                with source_tab:
                    lines_list = content.split("\n")
                    total_lines = len(lines_list)
                    fc1, fc2 = st.columns([4, 1])
                    with fc1:
                        _copy_button(f"📋 {fname} 복사", content, key=f"copy_{screen_id}_{fname}")
                    with fc2:
                        expand_key = f"expand_{screen_id}_{fname}"
                        show_full = (
                            st.checkbox("펼치기 (전체 보기)", key=expand_key)
                            if total_lines > PREVIEW_LINES else True
                        )
                    lang = "xml" if fname.endswith(".xml") else "java"
                    # line_numbers=True로 왼쪽에 줄번호를 붙인다 - 위 검증 결과의 "L123" 같은 표시를
                    # 실제 소스에서 바로 찾을 수 있게 하기 위함.
                    if show_full or total_lines <= PREVIEW_LINES:
                        # 전체 보기일 때는 높이 고정 스크롤 박스 안에 넣는다 - 5000줄짜리 Mapper.xml도
                        # 페이지 전체를 끝없이 스크롤하지 않고 이 박스 안에서만 스크롤하면 되게 하기 위함.
                        with st.container(height=450):
                            st.code(content, language=lang, line_numbers=True)
                    else:
                        st.code("\n".join(lines_list[:PREVIEW_LINES]), language=lang, line_numbers=True)
                        st.caption(
                            f"총 {total_lines}줄 중 {PREVIEW_LINES}줄만 표시했습니다(줄번호는 원본 기준 그대로) - "
                            "소스가 길어 변환 결과를 한눈에 보기 어려우니 필요할 때만 위 '펼치기'를 누르세요."
                        )

            with st.expander("🎨 AI 추천 (opt-in, 비교용)", expanded=False):
                _render_ai_recommendation(screen_id, to_prefix(screen_id), files, buckets)

            with st.expander("🧪 차등 테스트 (더미 데이터 자동 생성)", expanded=False):
                _render_diff_test(screen_id, buckets, package_p1, package_p2)

        with tab_porting:
            st.caption(
                "F BizUnit의 실제 계산/분기 로직을 메서드 단위로 LLM Gateway에 보내, Service 파일의 스텁 "
                "(`throw new UnsupportedOperationException`)을 실제 포팅된 코드로 바로 교체합니다. "
                "메서드가 크면(예: 500줄 넘는 로직) 한 번에 정확히 옮겨진다는 보장이 없으니, "
                "포팅 후 반드시 원본과 줄 단위로 대조해서 검토하세요 - 이 앱은 자동으로 완료 처리하지 않습니다."
            )
            if f_java and service_fname in files:
                # _port_method/_run_bulk_porting은 이 탭 밖(위쪽, "🔧 2단계 포팅" 탭보다 앞)에서
                # 이미 정의됐다 - 상단 상태바의 "▶️ 전체 포팅 실행" 버튼이 이 탭을 보고 있지 않을 때도
                # 진행률을 보여줄 수 있어야 해서, 실행 로직을 이 탭에 가두지 않고 공유한다.
                if st.button(f"전체 포팅 ({len(f_methods)}개 메서드, LLM {len(f_methods)}회 호출)"):
                    _run_bulk_porting()
                    st.rerun()

                for method in f_methods:
                    status = "✅ 포팅됨 (검토 필요)" if method in ported else "⏳ 스텁"
                    pc1, pc2 = st.columns([5, 1])
                    pc1.write(f"`{method}` — {status} ({len(f_bodies.get(method, ''))}자)")
                    if pc2.button("포팅", key=f"port_{screen_id}_{method}"):
                        try:
                            with st.spinner(f"{method} 포팅 중..."):
                                _port_method(method)
                            st.rerun()
                        except Exception as e:
                            st.error(f"{method} 포팅 실패: {e}")
            elif not f_java:
                st.info("F(Java) 원본이 없어 포팅할 대상이 없습니다.")

        with tab_save:
            if not porting_complete:
                st.warning(
                    f"⏳ 2단계 포팅이 아직 끝나지 않았습니다({len(ported)}/{len(f_methods)}개 메서드 완료) - "
                    "F 메서드를 전부 포팅해야 저장 버튼이 활성화됩니다. 원본 F 로직 없이 스텁 상태로 저장하면 "
                    "포팅했다는 착각을 줄 수 있어서 막아뒀습니다."
                )
            save_to_db = st.checkbox(
                "DB에도 기록 (agents/db_schema.sql의 CONV_FILE/CONV_ISSUE, 로컬 Oracle - 정적 검증 결과 BUILD_CHECK 포함)",
                value=True,
                key=f"save_to_db_{screen_id}",
            )
            if st.button(
                "검토 완료 - pilot/ 에 TO-BE 폴더 구조로 저장",
                type="primary",
                disabled=not porting_complete,
            ):
                # 실제 저장/DB 기록 로직은 _save_reviewed_files() 하나로 공유한다(상단 상태바의
                # "💾 저장" 버튼도 같은 함수를 쓴다) - 저장 직전 재스캔까지 포함해 두 진입점이
                # 서로 다른 결과를 남기지 않게 하기 위함.
                _save_reviewed_files(save_to_db)
