"""업로드 -> TO-BE 변환 챗UI (v0, 로컬 전용).

docs/07-tobe-structure.xlsx AS_IS 시트 기준, 화면 하나의 P/F/D BizUnit(.java/.bizunit) +
XSQL 파일을 업로드하면 결정론적 규칙으로 Api/Service/Store 골격 + MyBatis Mapper를 생성한다.
CLAUDE.md 핵심 원칙에 따라:
  - 결정론적으로 되는 부분(골격, iBatis->MyBatis 문법)은 규칙 기반으로만 처리한다.
  - Service 메서드 "본문"(업무 로직 포팅)만 선택적으로 LLM Gateway를 쓴다 - 기본은 꺼져있다.
  - 아무것도 자동으로 커밋하지 않는다. 로컬 pilot/ 폴더에 "저장" 버튼을 눌러야만 파일이 생긴다.
  - 발견한 이슈(문법 오류 등)는 체크박스를 켜면 agents/db.py로 CONV_FILE/CONV_ISSUE 테이블(로컬
    Oracle)에도 기록한다 - 이 두 테이블과 insert 로직은 실제 DB로 검증 완료.

실행: (프로젝트 루트에서) streamlit run chatui/app.py
converters.py/skeleton_gen.py/db.py는 실제 PLA047 소스 + 실제 로컬 Oracle DB로 검증했다.
app.py(Streamlit 화면) 자체는 이 환경에 브라우저가 없어 직접 렌더링 확인은 못 했다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from converters import convert_xsql_fragment  # noqa: E402
from skeleton_gen import generate_skeletons, to_prefix  # noqa: E402

st.set_page_config(page_title="G-SCM AS-IS → TO-BE 변환", layout="wide")

FILENAME_RE = re.compile(r"^([PFD])([A-Za-z0-9]+)\.(java|bizunit|xsql)$", re.IGNORECASE)


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

uploaded = st.file_uploader(
    "AS-IS 파일 업로드 (여러 개 선택 가능)",
    type=["java", "bizunit", "xsql"],
    accept_multiple_files=True,
)

if uploaded:
    buckets, problems, screen_id = _categorize(uploaded)

    for p in problems:
        st.warning(p)

    if not screen_id:
        st.error("화면ID를 인식하지 못했습니다. 파일명이 P/F/D + 화면ID + 확장자 형태인지 확인하세요 (예: PPLA047.java).")
        st.stop()

    st.success(f"화면ID: **{screen_id}** (TO-BE 접두어: `{to_prefix(screen_id)}`)")

    detected = []
    for layer in ("P", "F", "D"):
        kinds = ", ".join(sorted(buckets[layer].keys())) or "없음"
        detected.append(f"- **{layer}**: {kinds}")
    st.markdown("\n".join(detected))

    if st.button("1단계: 규칙 기반 변환 실행 (골격 + MyBatis Mapper)", type="primary"):
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

        st.session_state["skeleton_files"] = skel.files
        st.session_state["skeleton_issues"] = list(skel.issues)
        st.session_state["mapper_issues"] = list(mapper_result.issues) if mapper_result else []
        if mapper_result:
            st.session_state["skeleton_files"][f"{to_prefix(screen_id)}Mapper.xml"] = mapper_result.mybatis_xml
        st.session_state["screen_id"] = screen_id

    if "skeleton_files" in st.session_state:
        st.divider()
        st.subheader("변환 결과 (검토 전 - 아직 저장 안 됨)")

        all_issues = st.session_state.get("skeleton_issues", []) + st.session_state.get("mapper_issues", [])
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
        tabs = st.tabs(list(files.keys()))
        for tab, (fname, content) in zip(tabs, files.items()):
            with tab:
                lang = "xml" if fname.endswith(".xml") else "java"
                st.code(content, language=lang)

        st.divider()
        st.subheader("2단계 (선택, 실험적): LLM으로 Service 로직 초안 작성")
        st.caption(
            "F BizUnit의 실제 계산/분기 로직을 Service 메서드 본문으로 포팅하는 초안을 LLM Gateway로 생성합니다. "
            "결과는 반드시 사람이 검토해야 하며, 이 앱이 자동으로 신뢰하지 않습니다."
        )
        if st.button("Service 로직 초안 생성 (LLM 호출)"):
            f_java = buckets["F"].get("java")
            if not f_java:
                st.error("F(Java) 원본이 없어 포팅할 대상이 없습니다.")
            else:
                try:
                    from agents.llm_gateway import chat

                    prompt = (
                        "다음은 NEXCORE(BizUnit) 프레임워크로 작성된 Java 업무 로직이다. "
                        "이 로직의 계산/분기를 그대로 유지하면서, IDataSet/IOnlineContext/lookupDataUnit 같은 "
                        "NEXCORE 프레임워크 의존만 제거하고 Spring 서비스 클래스 메서드로 옮겨라. "
                        "SQL이나 업무 규칙을 새로 설계하지 말고 원본 그대로 포팅만 해라. "
                        "원본에 컴파일 에러가 있다면 그 부분은 고치지 말고 // FIXME 주석과 함께 표시해라.\n\n"
                        f"```java\n{f_java}\n```"
                    )
                    with st.spinner("LLM 호출 중..."):
                        draft = chat(messages=[{"role": "user", "content": prompt}])
                    st.code(draft, language="java")
                    st.info("이 초안은 그대로 저장되지 않습니다. 검토 후 Service 파일에 직접 반영하세요.")
                except Exception as e:
                    st.error(f"LLM 호출 실패: {e}")

        st.divider()
        save_to_db = st.checkbox(
            "DB에도 기록 (agents/db_schema.sql의 CONV_FILE/CONV_ISSUE, 로컬 Oracle)",
            value=False,
        )
        if st.button("검토 완료 - pilot/{screen}/ 에 저장", type="primary"):
            out_dir = PROJECT_ROOT / "pilot" / st.session_state["screen_id"]
            out_dir.mkdir(parents=True, exist_ok=True)
            for fname, content in files.items():
                (out_dir / fname).write_text(content, encoding="utf-8")
            st.success(f"저장됨: {out_dir} ({len(files)}개 파일). git add/commit은 별도로 직접 하세요.")

            if save_to_db:
                try:
                    from agents import db

                    db.ensure_schema()
                    sid = st.session_state["screen_id"]

                    # 골격(P/F/D) 관련 이슈는 화면 단위로만 구분 가능해서 P(JAVA) 파일에 대표로 붙인다 -
                    # 정확한 파일별 귀속은 v0 범위 밖(추후 개선 지점).
                    if buckets["P"].get("java"):
                        p_file_id = db.upsert_conv_file(
                            screen_id=sid, as_is_layer="P(JAVA)",
                            as_is_filename=f"P{sid}.java", as_is_path=None,
                            tobe_filename=f"{to_prefix(sid)}Api.java", tobe_path=str(out_dir),
                            conversion_method="RULE_BASED", conversion_status="IN_PROGRESS",
                        )
                        db.record_issues(p_file_id, st.session_state.get("skeleton_issues", []), "chatui/skeleton_gen.py")

                    if buckets["D"].get("xsql"):
                        d_file_id = db.upsert_conv_file(
                            screen_id=sid, as_is_layer="XSQL",
                            as_is_filename=f"D{sid}.xsql", as_is_path=None,
                            tobe_filename=f"{to_prefix(sid)}Mapper.xml", tobe_path=str(out_dir),
                            conversion_method="RULE_BASED", conversion_status="IN_PROGRESS",
                        )
                        db.record_issues(d_file_id, st.session_state.get("mapper_issues", []), "chatui/converters.py")

                    st.success("DB에 기록했습니다 (CONV_FILE/CONV_ISSUE).")
                except Exception as e:
                    st.error(f"DB 기록 실패: {e}")
else:
    st.info("화면 1개 분량의 P/F/D .java, .bizunit, XSQL 파일을 올려주세요.")
