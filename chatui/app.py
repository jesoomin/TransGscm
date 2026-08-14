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

# TO-BE AS_IS_LAYER 값(agents/db_schema.sql의 CONV_FILE.AS_IS_LAYER) - 생성 파일 접미사 -> 계층 매핑.
# DB 저장 시 이 순서대로 화면당 CONV_FILE 행을 만든다.
_LAYER_BY_SUFFIX = [
    ("Api.java", "P(JAVA)"),
    ("Service.java", "F(JAVA)"),
    ("Store.java", "D(JAVA)"),
    ("Mapper.xml", "XSQL"),
    ("Dto.java", "DERIVED"),
]


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
    package_p1 = st.text_input("패키지 p1 (예: pm)", value="")
    package_p2 = st.text_input("패키지 p2 (예: pla)", value="")
    st.caption("AS-IS 경로 gscm/r/{p1}/{p2}/{p2}b/... 기준. 파일 내용만으로는 알 수 없어 직접 입력해야 합니다.")

input_mode = st.radio(
    "입력 방식", ["폴더 경로 지정", "파일 직접 업로드"], horizontal=True,
    help="로컬 전용 앱이라 폴더 경로를 직접 읽을 수 있습니다. 폴더 안에 화면이 여러 개 섞여 있어도 "
         "한 번에 전부 변환하지 않고 화면을 골라서 하나씩 처리합니다(CLAUDE.md 원칙).",
)

buckets: dict[str, dict[str, str]] = {"P": {}, "F": {}, "D": {}}
screen_id = ""
as_is_paths: dict[str, str] = {}

if input_mode == "폴더 경로 지정":
    folder_str = st.text_input(
        "AS-IS 폴더 경로",
        placeholder=r"예: C:\Users\10982\project\TransGscm\legacy 또는 ...\r\pm\pla\plab",
        help="하위 폴더까지 재귀적으로 뒤집니다 - biz/와 db/가 나뉘어 있어도 됩니다.",
    )
    if folder_str:
        screens, all_paths, problems = _scan_folder(Path(folder_str))
        for p in problems:
            st.warning(p)

        if screens:
            screen_ids = sorted(screens.keys())
            if len(screen_ids) > 1:
                st.info(f"폴더에서 화면 {len(screen_ids)}개 발견: {', '.join(screen_ids)} — 한 번에 하나씩 처리합니다.")
            screen_id = st.selectbox("변환할 화면 선택", screen_ids)
            buckets = screens[screen_id]
            as_is_paths = all_paths.get(screen_id, {})

            guess = _guess_package(as_is_paths)
            if guess:
                st.caption(f"경로에서 패키지 추정: p1=`{guess[0]}`, p2=`{guess[1]}` — 사이드바에 그대로 입력하거나 필요하면 수정하세요.")
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
    if not any(buckets[layer] for layer in buckets):
        st.error("화면ID를 인식하지 못했습니다. 파일명이 P/F/D + 화면ID + 확장자 형태인지 확인하세요 (예: PPLA047.java).")
        st.stop()

    st.success(f"화면ID: **{screen_id}** (TO-BE 접두어: `{to_prefix(screen_id)}`)")

    detected = []
    for layer in ("P", "F", "D"):
        kinds = ", ".join(sorted(buckets[layer].keys())) or "없음"
        detected.append(f"- **{layer}**: {kinds}")
    st.markdown("\n".join(detected))

    def _run_conversion() -> None:
        """규칙 기반 골격/Mapper/Dto 생성 + 정적 검증까지 한 번에 실행한다.

        "1단계" 최초 실행과 "변환 재수행"(예: 원본 XSQL 태그 정정 후 다시 돌릴 때) 둘 다
        이 함수를 쓴다 - 두 버튼이 서로 다른 로직으로 갈라지지 않게 하기 위함.
        """
        skel = generate_skeletons(
            screen_id=screen_id,
            package_p1=package_p1 or "TODO",
            package_p2=package_p2 or "TODO",
            p_java_text=buckets["P"].get("java"),
            f_java_text=buckets["F"].get("java"),
            d_java_text=buckets["D"].get("java"),
            p_bizunit_text=buckets["P"].get("bizunit"),
        )

        mapper_result = None
        if buckets["D"].get("xsql"):
            mapper_result = convert_xsql_fragment(buckets["D"]["xsql"])

        dto = None
        if buckets["P"].get("java"):
            dto = generate_dto(
                screen_id=screen_id,
                package_p1=package_p1 or "TODO",
                package_p2=package_p2 or "TODO",
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
        st.session_state["validation_results"] = validate_screen(
            st.session_state["skeleton_files"], to_prefix(screen_id)
        )

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

        validation_results = st.session_state.get("validation_results", [])
        blocker_files = [r for r in validation_results if not r.passed]
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

        files = st.session_state["skeleton_files"]
        tabs = st.tabs(list(files.keys()))
        for tab, (fname, content) in zip(tabs, files.items()):
            with tab:
                _copy_button(f"📋 {fname} 복사", content, key=f"copy_{screen_id}_{fname}")
                lang = "xml" if fname.endswith(".xml") else "java"
                st.code(content, language=lang)

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
        if f_java and service_fname in files:
            f_methods = extract_methods(f_java)
            f_bodies = extract_method_bodies(f_java)
            ported_key = f"ported_methods_{screen_id}"
            ported: set[str] = st.session_state.setdefault(ported_key, set())

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
                # 포팅할 때마다 정적 검증을 다시 돌린다 - "함수별로 실행에 문제 없는지" 바로 확인하기 위함.
                st.session_state["validation_results"] = validate_screen(
                    st.session_state["skeleton_files"], to_prefix(screen_id)
                )

            if st.button(f"전체 포팅 ({len(f_methods)}개 메서드, LLM {len(f_methods)}회 호출)"):
                progress = st.progress(0.0)
                for i, method in enumerate(f_methods):
                    try:
                        with st.spinner(f"{method} 포팅 중... ({i + 1}/{len(f_methods)})"):
                            _port_method(method)
                    except Exception as e:
                        st.error(f"{method} 포팅 실패: {e}")
                    progress.progress((i + 1) / len(f_methods))
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
        save_to_db = st.checkbox(
            "DB에도 기록 (agents/db_schema.sql의 CONV_FILE/CONV_ISSUE, 로컬 Oracle - 정적 검증 결과 BUILD_CHECK 포함)",
            value=True,
        )
        if st.button("검토 완료 - pilot/{screen}/ 에 TO-BE 폴더 구조로 저장", type="primary"):
            out_dir = PROJECT_ROOT / "pilot" / st.session_state["screen_id"]
            p1 = package_p1 or "TODO"
            p2 = package_p2 or "TODO"
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

                    # 생성 단계 이슈(문법/골격 관련)는 계층별로 정확히 나뉘지 않는 부분이 남아있다 -
                    # skeleton_issues는 Api/Service/Store 골격 생성 전체에서 나온 걸 P(JAVA)에 대표로
                    # 붙인다(v0 한계, tracking/conversion-verification.csv에도 명시). 반면 정적 검증
                    # 결과(validation_results)는 파일 단위로 정확히 나오므로 계층마다 정확히 귀속시킨다.
                    layer_meta = {
                        "P(JAVA)": (f"P{sid}.java", as_is_paths.get("P.java"),
                                    st.session_state.get("skeleton_issues", []), "chatui/skeleton_gen.py"),
                        "F(JAVA)": (f"F{sid}.java", as_is_paths.get("F.java"), [], None),
                        "D(JAVA)": (f"D{sid}.java", as_is_paths.get("D.java"), [], None),
                        "XSQL": (f"D{sid}.xsql", as_is_paths.get("D.xsql"),
                                 st.session_state.get("mapper_issues", []), "chatui/converters.py"),
                        "DERIVED": (f"{sid}-dto-derived", None,
                                    st.session_state.get("dto_issues", []), "chatui/skeleton_gen.py"),
                    }

                    for suffix, layer in _LAYER_BY_SUFFIX:
                        fname = f"{prefix}{suffix}"
                        if fname not in files:
                            continue
                        as_is_filename, as_is_path, gen_issues, gen_detected_by = layer_meta[layer]
                        vr = by_file.get(fname)
                        build_check = "PASS" if vr and vr.passed else ("FAIL" if vr else "NOT_RUN")

                        file_id = db.upsert_conv_file(
                            screen_id=sid, as_is_layer=layer,
                            as_is_filename=as_is_filename, as_is_path=as_is_path,
                            tobe_filename=fname, tobe_path=str(saved_paths[fname].parent),
                            conversion_method="RULE_BASED", conversion_status="IN_PROGRESS",
                            build_check=build_check,
                        )
                        if gen_issues and gen_detected_by:
                            db.record_issues(file_id, gen_issues, gen_detected_by)
                        if vr and vr.issues:
                            db.record_issues(file_id, vr.issues, "chatui/validators.py")

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
