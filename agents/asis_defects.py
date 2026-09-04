"""AS-IS 원본 자체의 결함을 찾는 탐지기 모음 (변환 결과가 아니라 **입력**을 검사한다).

`chatui/validators.py`는 TO-BE 산출물을 검사하고, 이 모듈은 **AS-IS 원본**을 검사한다. 둘을
같은 모듈에 두지 않는 이유는 CLAUDE.md의 "변환기/검증기 분리"와 같다 - 검사 대상이 다르면
수명도 다르다. 변환 **전** 계획 단계와 벤치마크 채점이 이 모듈을 공유한다.

**왜 필요한가**: 확보한 실제 소스에 컴파일 불가 코드·XML 태그 불일치·SQL 문법 오류가 섞여
있었다. 전환 도구가 "정상 원본"을 전제하면 첫 화면에서 멈춘다. 원본 결함을 정상 입력의
일부로 취급하고, **변환 전에** 이름 붙여 드러내야 한다.

**탐지기를 고른 방식 — 정답키에 맞춰 규칙을 짜지 않았다.**
후보를 먼저 만들고 정답키가 있는 세트에서 **변별력을 측정**해서, 적중은 있고 오탐이 없는
것만 남겼다. 실제로 버린 것도 있다:
  - `미해결 타입 참조`(대문자 식별자를 전부 훑는 방식): 적중 7 / **오탐 54** → 폐기.
    같은 의도를 `계층 클래스 참조 미존재`와 `import 누락`으로 좁혀서 다시 만들었다.
  - `REMAPRESULTS_DROPPED`: XSQL 30개 **전부**에 균일하게 떠서 결함 신호가 못 된다 → 제외.
모든 파일에 똑같이 뜨는 신호는 정의상 결함을 구분해주지 못한다.
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_PROJECT_ROOT), str(_PROJECT_ROOT / "chatui")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_IMPORT_RE = re.compile(r"import\s+([\w.]+);")
_WILDCARD_IMPORT_RE = re.compile(r"import\s+[\w.]+\.\*;")
_LAYER_CLASS_RE = re.compile(r"\b([PFD][A-Z]{2,}\d+\w*)\b")
_METHOD_SIG_RE = re.compile(r"public\s+\w[\w<>\[\]]*\s+\w+\s*\(([^)]*)\)")
_LOOKUP_RE = re.compile(r"lookup(Function|Data)Unit\s*\(\s*\"?(\w+)")
_LOOKUP_CAST_RE = re.compile(r"\(\s*([A-Z]\w*)\s*\)\s*[\w.]*lookup(Function|Data)Unit")

# 코퍼스의 몇 %가 import하면 "이 프레임워크의 표준 타입"으로 볼 것인가.
# 0.5는 튜닝값이다 - 낮추면 오탐이, 높이면 미탐이 는다. 정답키 세트에서 0.5로 오탐 0건을
# 확인했으나 다른 코퍼스에서는 재확인이 필요하다(이 값이 임의값이라는 사실을 숨기지 않는다).
_COMMON_IMPORT_RATIO = 0.5


def detect_syntax_error(java_text: str) -> str | None:
    """원본이 그대로는 파싱되지 않는가 (tree-sitter 오류 복구 파서 기준).

    가장 일반적인 탐지기다 - 특정 오류 유형에 맞춘 규칙이 아니라 "이 파일이 유효한 Java인가"를
    묻는다. 세미콜론 누락·파라미터명 누락·중괄호 누락처럼 서로 다른 원인을 한 번에 잡는다.
    """
    try:
        import java_ast
    except ImportError:
        return None
    if not getattr(java_ast, "TREE_SITTER_AVAILABLE", False):
        return None
    parsed = java_ast._parse(java_text.encode("utf-8"))
    if parsed is None:
        return None
    tree, _ = parsed
    if not tree.root_node.has_error:
        return None
    return "원본이 그대로는 파싱되지 않습니다(구문 오류) — 컴파일 불가 상태"


def detect_missing_param_name(java_text: str) -> str | None:
    """메서드 시그니처의 파라미터에 타입만 있고 이름이 없는 경우."""
    for m in _METHOD_SIG_RE.finditer(java_text):
        params = m.group(1).strip()
        if not params:
            continue
        for prm in params.split(","):
            prm = prm.strip()
            if prm and len(prm.split()) == 1 and not prm.startswith("//"):
                return f"파라미터에 이름이 없습니다: `({params})`"
    return None


def detect_unresolved_layer_class(java_text: str, self_class: str,
                                  existing_classes: set[str]) -> str | None:
    """참조하는 P/F/D 계층 클래스가 실제 파일로 존재하지 않는 경우 (클래스명 오타 등).

    추측이 아니라 **실제 파일 목록**을 정답으로 쓴다. 그래서 이 코퍼스 안에서만 판정 가능하고,
    폴더 밖 클래스를 참조하는 경우는 알 수 없다(그 경우는 조용히 넘긴다 - 없는 사실을 만들지 않음).
    """
    for ref in sorted(set(_LAYER_CLASS_RE.findall(java_text))):
        if ref != self_class and ref not in existing_classes:
            return f"참조하는 클래스 `{ref}`가 이 소스 세트에 존재하지 않습니다(오타 의심)"
    return None


def detect_missing_import(java_text: str, common_types: set[str]) -> str | None:
    """코퍼스 대부분이 import하는 표준 타입을, 이 파일은 쓰면서 import하지 않은 경우.

    타입 목록을 하드코딩하지 않고 **코퍼스에서 스스로 뽑는다**(자가 보정) - 프레임워크가 달라도
    같은 방식이 성립한다. 와일드카드 import가 있으면 판정하지 않는다(그 경우 없는 것이 아니다).
    """
    if _WILDCARD_IMPORT_RE.search(java_text):
        return None
    mine = {i.rsplit(".", 1)[-1] for i in _IMPORT_RE.findall(java_text)}
    for ty in sorted(common_types - mine):
        if re.search(rf"\b{re.escape(ty)}\b", java_text):
            return f"`{ty}`를 사용하지만 import 구문이 없습니다"
    return None


def detect_layer_lookup_mismatch(java_text: str) -> str | None:
    """D 계층 클래스를 lookupFunctionUnit으로(또는 그 반대로) 가져오는 경우.

    P/F/D 계층 구분은 이 프로젝트의 확정된 컨벤션(CLAUDE.md, docs/04-glossary.md)이므로 추측이
    아니다. 컴파일은 통과하지만 런타임에 조회가 실패하는 유형이라 정적 검사로만 잡을 수 있다.
    """
    for kind, target in _LOOKUP_RE.findall(java_text):
        if target.startswith("D") and kind == "Function":
            return f"`{target}`(D 계층)를 lookupFunctionUnit으로 조회합니다 — lookupDataUnit이어야 합니다"
        if target.startswith("F") and kind == "Data":
            return f"`{target}`(F 계층)를 lookupDataUnit으로 조회합니다 — lookupFunctionUnit이어야 합니다"
    for m in _LOOKUP_CAST_RE.finditer(java_text):
        cls, kind = m.group(1), m.group(2)
        if cls.startswith("D") and kind == "Function":
            return f"`{cls}`(D 계층)를 lookupFunctionUnit으로 조회합니다 — lookupDataUnit이어야 합니다"
        if cls.startswith("F") and kind == "Data":
            return f"`{cls}`(F 계층)를 lookupDataUnit으로 조회합니다 — lookupFunctionUnit이어야 합니다"
    return None


def common_import_types(java_texts: dict[str, str]) -> set[str]:
    """코퍼스의 절반 이상이 import하는 타입 집합 — `detect_missing_import`의 기준이 된다."""
    if not java_texts:
        return set()
    counter: Counter[str] = Counter()
    for text in java_texts.values():
        for i in set(_IMPORT_RE.findall(text)):
            counter[i.rsplit(".", 1)[-1]] += 1
    threshold = len(java_texts) * _COMMON_IMPORT_RATIO
    return {k for k, v in counter.items() if v >= threshold}


def scan_java_corpus(java_texts: dict[str, str]) -> dict[str, list[dict]]:
    """Java 파일 묶음을 한 번에 검사한다. 코퍼스 기반 탐지기가 있어 파일 단위가 아니라
    묶음 단위 API로 둔다. 반환: {파일명: [{issue_type, message}, ...]}"""
    existing = {name[:-5] for name in java_texts if name.lower().endswith(".java")}
    common = common_import_types(java_texts)
    out: dict[str, list[dict]] = {}
    for name, text in java_texts.items():
        found = []
        for issue_type, msg in (
            ("ASIS_SYNTAX_ERROR", detect_syntax_error(text)),
            ("ASIS_MISSING_PARAM_NAME", detect_missing_param_name(text)),
            ("ASIS_UNRESOLVED_CLASS",
             detect_unresolved_layer_class(text, name[:-5], existing)),
            ("ASIS_MISSING_IMPORT", detect_missing_import(text, common)),
            ("ASIS_LAYER_LOOKUP_MISMATCH", detect_layer_lookup_mismatch(text)),
        ):
            if msg:
                found.append({"issue_type": issue_type, "message": msg})
        if found:
            out[name] = found
    return out
