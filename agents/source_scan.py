"""AS-IS 소스 폴더에서 화면ID별로 P/F/D(.java/.bizunit)/XSQL 파일을 찾아 묶는 순수 함수 모음.

chatui/app.py(Streamlit)의 _scan_folder/_guess_package를 그대로 옮겼다 - 원래 app.py 안에
있었는데, agents/nctrid_graph.py(Streamlit 없이 CLI로 도는 nctRid 매핑 그래프 빌더)도 똑같은
스캔 로직이 필요해서 공유 모듈로 뺐다. app.py는 최상위에서 st.set_page_config()를 실행하기
때문에(Streamlit 스크립트 실행 컨텍스트 밖에서 import하면 깨짐) app.py를 직접 import할 수
없어 이렇게 분리했다. 로직 자체는 바꾸지 않았다(순수 이동).
"""
from __future__ import annotations

import re
from pathlib import Path

FILENAME_RE = re.compile(r"^([PFD])([A-Za-z0-9]+)\.(java|bizunit|xsql)$", re.IGNORECASE)
# AS-IS 경로 gscm/r/{p1}/{p2}/{p2}b/... 에서 p1/p2를 최선 추정으로 뽑아본다(확정 아님).
PACKAGE_HINT_RE = re.compile(r"[\\/]r[\\/]([a-z0-9]+)[\\/]([a-z0-9]+)[\\/]\2b(?:[\\/]|$)", re.IGNORECASE)


def scan_folder(folder: Path) -> tuple[dict[str, dict[str, dict[str, str]]], dict[str, dict[str, str]], list[str]]:
    """폴더(하위 폴더 포함)를 뒤져서 화면ID별로 P/F/D 파일을 묶는다.

    실제 AS-IS 저장소는 `.../plab/biz/`(java, bizunit)와 `.../plab/db/`(xsql)가 나뉘어 있어서
    (CLAUDE.md "레거시 소스 정리" 참고) 한 화면이라도 폴더 하나로 안 끝날 수 있다 - 그래서
    지정한 폴더 아래를 재귀적으로 훑는다.
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


def guess_package(paths_for_screen: dict[str, str]) -> tuple[str, str] | None:
    for p in paths_for_screen.values():
        m = PACKAGE_HINT_RE.search(p)
        if m:
            return m.group(1).lower(), m.group(2).lower()
    return None
