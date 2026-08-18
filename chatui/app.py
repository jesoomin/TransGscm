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

from converters import convert_xsql_fragment  # noqa: E402
from skeleton_gen import (  # noqa: E402
    extract_method_bodies,
    extract_methods,
    generate_dto,
    generate_skeletons,
    splice_ported_method,
    to_prefix,
    tobe_relpath,
)
from validators import validate_screen  # noqa: E402
from reviewer import run_review, llm_review  # noqa: E402
from cross_analysis import analyze_pilot_folder  # noqa: E402

# TO-BE AS_IS_LAYER 값(agents/db_schema.sql의 CONV_FILE.AS_IS_LAYER) - 생성 파일 접미사 -> 계층 매핑.
# DB 저장 시 이 순서대로 화면당 CONV_FILE 행을 만든다.
_LAYER_BY_SUFFIX = [
    ("Api.java", "P(JAVA)"),
    ("Service.java", "F(JAVA)"),
    ("Store.java", "D(JAVA)"),
    ("Mapper.xml", "XSQL"),
    ("Dto.java", "DERIVED"),
]

# buckets[layer][kind] -> (AS_IS_LAYER, AS-IS 파일명 패턴). 스킵 캐싱 조회 키를 만드는 데 쓴다 -
# 저장 시 DB에 기록하는 as_is_layer/as_is_filename 규칙과 동일해야 캐시가 실제로 맞아떨어진다.
_AS_IS_KEY_MAP = {
    ("P", "java"): "P(JAVA)",
    ("F", "java"): "F(JAVA)",
    ("D", "java"): "D(JAVA)",
    ("D", "xsql"): "XSQL",
}


def _strip_code_fence(text: str) -> str:
    """LLM이 하지 말라고 해도 ```java ... ``` 로 감싸서 줄 때가 있어 방어적으로 벗겨낸다."""
    text = text.strip()
    m = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", text, re.DOTALL)
    return m.group(1) if m else text


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

FILENAME_RE = re.compile(r"^([PFD])([A-Za-z0-9]+)\.(java|bizunit|xsql)$", re.IGNORECASE)
# AS-IS 경로 gscm/r/{p1}/{p2}/{p2}b/... 에서 p1/p2를 최선 추정으로 뽑아본다(확정 아님).
PACKAGE_HINT_RE = re.compile(r"[\\/]r[\\/]([a-z0-9]+)[\\/]([a-z0-9]+)[\\/]\2b(?:[\\/]|$)", re.IGNORECASE)


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


def _scan_folder(folder: Path) -> tuple[dict[str, dict[str, dict[str, str]]], dict[str, dict[str, str]], list[str]]:
    """폴더(하위 폴더 포함)를 뒤져서 화면ID별로 P/F/D 파일을 묶는다.

    실제 AS-IS 저장소는 `.../plab/biz/`(java, bizunit)와 `.../plab/db/`(xsql)가 나뉘어 있어서
    (CLAUDE.md "레거시 소스 정리" 참고) 한 화면이라도 폴더 하나로 안 끝날 수 있다 - 그래서
    지정한 폴더 아래를 재귀적으로 훑는다. 여러 화면이 섞여 있어도 여기서 자동으로 다 변환하지
    않는다 - CLAUDE.md 원칙("화면 단위로 검토, 일괄 처리 금지")대로 화면을 고르는 건 사람이 한다.
    """
    screens: dict[str, dict[str, dict[str, str]]] = {}
    paths: dict[str, dict[str, str]] = {}
    problems: list[str] = []

    if not folder.exists():
        problems.append(f"경로가 존재하지 않습니다: {folder}")
        return screens, paths, problems
    if not folder.is_dir():
        problems.append(f"폴더가 아닙니다: {folder}")
        return screens, paths, problems

    matched = 0
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        m = FILENAME_RE.match(path.name)
        if not m:
            continue
        matched += 1
        layer, screen_id, kind = m.group(1).upper(), m.group(2), m.group(3).lower()
        screens.setdefault(screen_id, {"P": {}, "F": {}, "D": {}})
        screens[screen_id][layer][kind] = path.read_text(encoding="utf-8", errors="replace")
        paths.setdefault(screen_id, {})[f"{layer}.{kind}"] = str(path)

    if matched == 0:
        problems.append(
            "폴더(하위 폴더 포함)에서 P/F/D + 화면ID + .java/.bizunit/.xsql 패턴 파일을 하나도 못 찾았습니다."
        )
    return screens, paths, problems


def _guess_package(paths_for_screen: dict[str, str]) -> tuple[str, str] | None:
    for p in paths_for_screen.values():
        m = PACKAGE_HINT_RE.search(p)
        if m:
            return m.group(1).lower(), m.group(2).lower()
    return None


st.title("G-SCM AS-IS → TO-BE 변환 (v0)")
st.caption(
    "P/F/D BizUnit(.java/.bizunit) + XSQL을 화면 1개 단위로 업로드하세요. "
    "결정론적 규칙으로 먼저 변환하고, LLM은 선택했을 때만 Service 로직 포팅에 씁니다."
)

with st.sidebar:
    st.subheader("LLM Gateway 상태")
    try:
        from agents.llm_gateway import DEFAULT_CHAT_MODEL
        import os
        from dotenv import load_dotenv

        load_dotenv()
        key_present = bool(os.getenv("LLM_GATEWAY_API_KEY"))
        st.write(f"기본 모델: `{DEFAULT_CHAT_MODEL}`")
        st.write("API 키: " + ("✅ .env에서 감지됨" if key_present else "❌ 없음 (.env 확인)"))
    except Exception as e:  # pragma: no cover - 진단용
        st.error(f"agents.llm_gateway 로드 실패: {e}")

    st.divider()
    st.subheader("🔗 전체 화면 교차 분석")
    st.caption(
        "pilot/{화면}/ 아래 쌓인 화면들끼리 Service/Store 메서드나 Mapper SQL이 겹치는지 비교합니다. "
        "화면이 1개뿐이면 비교 대상이 없어 그 사실만 보고합니다 - nctRid 매핑 그래프(멘토 코멘트 §1) "
        "전까지는 정식 영향도 분석이 아니라 화면이 쌓일 때 바로 쓸 인프라 단계입니다."
    )
    if st.button("교차 분석 실행"):
        cross_result = analyze_pilot_folder(PROJECT_ROOT / "pilot")
        st.session_state["cross_analysis_result"] = cross_result
    cross_result = st.session_state.get("cross_analysis_result")
    if cross_result:
        st.write(f"분석 대상 화면: {', '.join(cross_result.screens_analyzed) or '없음'}")
        for note in cross_result.notes:
            st.info(note)
        for g in cross_result.duplicate_groups:
            st.warning(f"[{g.kind}] {len(g.locations)}곳 중복: " + " / ".join(g.locations))

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
            if len(screen_ids) > 1:
                st.info(f"폴더에서 화면 {len(screen_ids)}개 발견: {', '.join(screen_ids)} — 한 번에 하나씩 처리합니다.")

            # 스킵 캐싱: 화면이 많을 때(업무 폴더 하나에 PU/FU/DU/XSQL 세트가 50개+ 섞여 있는 경우)
            # 이전에 이미 정적 검증을 통과했고 원본 내용도 그대로인 화면을 목록에서 미리 표시해준다.
            # 자동으로 건너뛰지는 않는다 - 변환기 자체가 바뀌었을 수 있어 최종 판단은 사람 몫이다.
            cache_rows: dict[tuple[str, str, str], dict] = {}
            try:
                from agents import db as _db_for_cache
                cache_rows = _db_for_cache.get_cached_status_bulk(screen_ids)
            except Exception:
                pass  # DB 연결 안 될 수 있음 - 캐싱 표시는 그냥 생략하고 정상 진행

            def _screen_label(sid: str) -> str:
                if not cache_rows:
                    return sid
                fragments_found = False
                all_pass_unchanged = True
                for (layer, kind), as_is_layer in _AS_IS_KEY_MAP.items():
                    content = screens[sid].get(layer, {}).get(kind)
                    if not content:
                        continue
                    fragments_found = True
                    as_is_filename = f"{layer}{sid}.{kind}"
                    cached = cache_rows.get((sid, as_is_layer, as_is_filename))
                    if not cached or cached["build_check"] != "PASS" or cached["content_hash"] != _db_for_cache.content_hash(content):
                        all_pass_unchanged = False
                        break
                if fragments_found and all_pass_unchanged:
                    return f"✅ {sid} (이전 변환 PASS, 원본 변경 없음)"
                return sid

            screen_id = st.selectbox("변환할 화면 선택", screen_ids, format_func=_screen_label)
            if cache_rows and _screen_label(screen_id).startswith("✅"):
                st.info(
                    "이 화면은 이전에 정적 검증을 통과했고 원본 내용도 그대로입니다 - 다시 돌릴 필요가 "
                    "없을 수 있습니다. 그래도 재변환하려면 아래 '1단계'를 그대로 누르면 됩니다."
                )
            buckets = screens[screen_id]
            as_is_paths = all_paths.get(screen_id, {})

            # 패키지 p1/p2는 AS-IS 경로 .../r/{p1}/{p2}/{p2}b/...에서 자동으로 뽑는다(docs/07-tobe-structure.xlsx
            # AS_IS 시트의 폴더8=p1, 폴더9=p2로 실제 확인된 규칙) - 입력받지 않는다.
            guess = _guess_package(as_is_paths)
            if guess:
                package_p1, package_p2 = guess
                st.caption(f"경로에서 패키지 자동 인식: p1=`{package_p1}`, p2=`{package_p2}`")
            else:
                st.warning(
                    "경로에서 패키지 p1/p2를 자동으로 인식하지 못했습니다 "
                    "(.../r/{p1}/{p2}/{p2}b/... 패턴이 아닌 경로) - TO-BE 패키지가 com.skhynix.gscm.r.TODO.TODO로 생성됩니다."
                )
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

    st.success(f"화면ID: **{screen_id}** (TO-BE 접두어: `{to_prefix(screen_id)}`)")

    detected = []
    for layer in ("P", "F", "D"):
        kinds = ", ".join(sorted(buckets[layer].keys())) or "없음"
        detected.append(f"- **{layer}**: {kinds}")
    st.markdown("\n".join(detected))

    # 작업 상태 요약 - 아래로 스크롤해서 2/3단계를 보는 동안에도 핵심 진행 상황을 다시 위로
    # 올라오지 않고 확인할 수 있게, 화면 선택 직후(스크롤 맨 위 근처)에 고정적으로 보여준다.
    status_cols = st.columns(4)
    status_cols[0].metric("화면ID", screen_id)
    val_results = st.session_state.get("validation_results", [])
    if val_results:
        passed_n = sum(1 for r in val_results if r.passed)
        status_cols[1].metric("정적 검증", f"{passed_n}/{len(val_results)} 통과")
    else:
        status_cols[1].metric("정적 검증", "미실행")
    f_java_present = bool(buckets["F"].get("java"))
    if f_java_present:
        total_f = len(extract_methods(buckets["F"]["java"]))
        ported_n = len(st.session_state.get(f"ported_methods_{screen_id}", set()))
        status_cols[2].metric("F 포팅 진행", f"{ported_n}/{total_f}")
    else:
        status_cols[2].metric("F 포팅 진행", "N/A")
    if "review_findings" in st.session_state:
        review_n = sum(len(v) for v in st.session_state["review_findings"].values())
        status_cols[3].metric("품질/취약점 스캔", f"{review_n}건")
    else:
        status_cols[3].metric("품질/취약점 스캔", "미실행")

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

    if "skeleton_files" in st.session_state:
        st.divider()
        st.subheader("변환 결과 (검토 전 - 아직 저장 안 됨)")

        all_issues = (
            st.session_state.get("skeleton_issues", [])
            + st.session_state.get("mapper_issues", [])
            + st.session_state.get("dto_issues", [])
        )
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

        files = st.session_state["skeleton_files"]

        validation_results = st.session_state.get("validation_results", [])
        blocker_files = [r for r in validation_results if not r.passed]
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
            for r in validation_results:
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

        review_findings: dict[str, list] = st.session_state.get("review_findings", {})
        total_review = sum(len(v) for v in review_findings.values())
        with st.expander(f"🛡️ 코드 품질/취약점 스캔 (규칙 기반) - {total_review}건", expanded=False):
            st.caption(
                "정규식 기반 규칙 스캔입니다(LLM 아님) - 확정된 취약점이 아니라 '검토가 필요한 후보'를 "
                "표시합니다: ${...}(MyBatis 텍스트 치환, 값에 따라 SQL 인젝션 가능), 문자열 연결로 "
                "조립되는 SQL, 포팅 시 보존된 원본 버그(FIXME) 집계."
            )
            if not review_findings:
                st.write("발견된 항목이 없습니다.")
            for fname, findings in review_findings.items():
                by_type: dict[str, list] = {}
                for f in findings:
                    by_type.setdefault(f.issue_type, []).append(f)
                st.markdown(f"**{fname}** — {len(findings)}건")
                for issue_type, items in by_type.items():
                    severity = items[0].severity
                    show_key = f"review_expand_{screen_id}_{fname}_{issue_type}"
                    show_all = (
                        st.checkbox(f"[{severity}/{issue_type}] {len(items)}건 전체 보기", key=show_key)
                        if len(items) > 5 else True
                    )
                    if not show_all:
                        st.write(f"[{severity}/{issue_type}] {len(items)}건 (아래 예시 5건, 체크박스로 전체 보기)")
                    sample = items if show_all else items[:5]
                    for it in sample:
                        text = f"L{it.line_no}: {it.message}" if it.line_no else it.message
                        if severity == "BLOCKER":
                            st.error(text)
                        elif severity == "WARNING":
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

        tabs = st.tabs(list(files.keys()))
        PREVIEW_LINES = 40
        for tab, (fname, content) in zip(tabs, files.items()):
            with tab:
                lines_list = content.split("\n")
                total_lines = len(lines_list)
                c1, c2 = st.columns([4, 1])
                with c1:
                    _copy_button(f"📋 {fname} 복사", content, key=f"copy_{screen_id}_{fname}")
                with c2:
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

        st.divider()
        st.subheader("2단계 (선택, 실험적): LLM으로 Service 로직 포팅")
        st.caption(
            "F BizUnit의 실제 계산/분기 로직을 메서드 단위로 LLM Gateway에 보내, Service 파일의 스텁 "
            "(`throw new UnsupportedOperationException`)을 실제 포팅된 코드로 바로 교체합니다. "
            "메서드가 크면(예: 500줄 넘는 로직) 한 번에 정확히 옮겨진다는 보장이 없으니, "
            "포팅 후 반드시 원본과 줄 단위로 대조해서 검토하세요 - 이 앱은 자동으로 완료 처리하지 않습니다."
        )
        f_java = buckets["F"].get("java")
        service_fname = f"{to_prefix(screen_id)}Service.java"
        f_methods: list[str] = []
        ported: set[str] = set()
        if f_java and service_fname in files:
            f_methods = extract_methods(f_java)
            f_bodies = extract_method_bodies(f_java)
            ported_key = f"ported_methods_{screen_id}"
            ported = st.session_state.setdefault(ported_key, set())

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
                ported_code = _strip_code_fence(ported_code)
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

            if st.button(f"전체 포팅 ({len(f_methods)}개 메서드, LLM {len(f_methods)}회 호출)"):
                progress = st.progress(0.0, text=f"0/{len(f_methods)} (0%)")
                for i, method in enumerate(f_methods):
                    try:
                        with st.spinner(f"{method} 포팅 중... ({i + 1}/{len(f_methods)})"):
                            _port_method(method)
                    except Exception as e:
                        st.error(f"{method} 포팅 실패: {e}")
                    pct = int((i + 1) / len(f_methods) * 100)
                    progress.progress((i + 1) / len(f_methods), text=f"{i + 1}/{len(f_methods)} ({pct}%) - 마지막: {method}")
                # 전체 포팅이 끝난 뒤 BLOCKER가 남아있으면 정적 검증 결과 쪽으로 바로 포커스시킨다.
                final_results = st.session_state.get("validation_results", [])
                if any(not r.passed for r in final_results):
                    st.session_state["scroll_to_validation"] = True
                st.rerun()

            for method in f_methods:
                status = "✅ 포팅됨 (검토 필요)" if method in ported else "⏳ 스텁"
                c1, c2 = st.columns([5, 1])
                c1.write(f"`{method}` — {status} ({len(f_bodies.get(method, ''))}자)")
                if c2.button("포팅", key=f"port_{screen_id}_{method}"):
                    try:
                        with st.spinner(f"{method} 포팅 중..."):
                            _port_method(method)
                        st.rerun()
                    except Exception as e:
                        st.error(f"{method} 포팅 실패: {e}")
        elif not f_java:
            st.info("F(Java) 원본이 없어 포팅할 대상이 없습니다.")

        st.divider()
        porting_complete = not f_methods or len(ported) >= len(f_methods)
        if not porting_complete:
            st.warning(
                f"⏳ 2단계 포팅이 아직 끝나지 않았습니다({len(ported)}/{len(f_methods)}개 메서드 완료) - "
                "F 메서드를 전부 포팅해야 저장 버튼이 활성화됩니다. 원본 F 로직 없이 스텁 상태로 저장하면 "
                "포팅했다는 착각을 줄 수 있어서 막아뒀습니다."
            )
        save_to_db = st.checkbox(
            "DB에도 기록 (agents/db_schema.sql의 CONV_FILE/CONV_ISSUE, 로컬 Oracle - 정적 검증 결과 BUILD_CHECK 포함)",
            value=True,
        )
        if st.button(
            "검토 완료 - pilot/ 에 TO-BE 폴더 구조로 저장",
            type="primary",
            disabled=not porting_complete,
        ):
            # pilot/ 바로 아래에 실제 TO-BE 트리(gscm/src/main/...)를 만든다 - 화면별 하위 폴더를
            # 두지 않는다. 파일명 자체가 이미 화면 접두어(Pla047Api.java 등)로 구분되고, 이렇게 해야
            # 나중에 여러 화면이 쌓였을 때 실제 프로젝트에 그대로 병합할 수 있는 구조가 된다.
            out_dir = PROJECT_ROOT / "pilot"
            p1, p2 = package_p1, package_p2
            saved_paths: dict[str, Path] = {}
            for fname, content in files.items():
                rel = tobe_relpath(fname, p1, p2)
                full_path = out_dir / rel
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
                saved_paths[fname] = full_path
            tree = "\n".join(f"- `{saved_paths[f].relative_to(out_dir)}`" for f in files)
            st.success(f"저장됨: {out_dir} ({len(files)}개 파일)\n\n{tree}\n\ngit add/commit은 별도로 직접 하세요.")

            if save_to_db:
                try:
                    from agents import db

                    db.ensure_schema()
                    sid = st.session_state["screen_id"]
                    prefix = to_prefix(sid)
                    validation_results = st.session_state.get("validation_results", [])
                    by_file = {r.file_name: r for r in validation_results}
                    review_findings = st.session_state.get("review_findings", {})

                    # 생성 단계 이슈(문법/골격 관련)는 계층별로 정확히 나뉘지 않는 부분이 남아있다 -
                    # skeleton_issues는 Api/Service/Store 골격 생성 전체에서 나온 걸 P(JAVA)에 대표로
                    # 붙인다(v0 한계, tracking/conversion-verification.csv에도 명시). 반면 정적 검증
                    # 결과(validation_results)는 파일 단위로 정확히 나오므로 계층마다 정확히 귀속시킨다.
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

                    for suffix, layer in _LAYER_BY_SUFFIX:
                        fname = f"{prefix}{suffix}"
                        if fname not in files:
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
                        if gen_issues and gen_detected_by:
                            db.record_issues(file_id, gen_issues, gen_detected_by)
                        if vr and vr.issues:
                            db.record_issues(file_id, vr.issues, "chatui/validators.py")
                        if review_findings.get(fname):
                            db.record_issues(file_id, review_findings[fname], "chatui/reviewer.py")

                    # 계층 간 참조(Api->Service->Store->Mapper) 검증은 파일 하나에 속하지 않아
                    # 별도 DERIVED 행으로 기록한다(AS_IS_FILENAME을 고유하게 둬서 위 Dto 파생 행과
                    # 안 겹치게 한다 - CONV_FILE UNIQUE 제약이 NULL을 다 같은 값처럼 취급하지 않게 함).
                    cross_vr = next((r for r in validation_results if r.check == "CROSS_LAYER_REF"), None)
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
else:
    st.info("폴더 경로를 입력하거나 화면 1개 분량의 P/F/D .java, .bizunit, XSQL 파일을 올려주세요.")
