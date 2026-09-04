"""BizUnit Java 소스에서 `public IDataSet 메서드(...)` 시그니처/본문을 뽑는 파서.

CLAUDE.md 기술 스택 표는 "Java(BizUnit)는 javalang 또는 tree-sitter"라고만 정해뒀다 - 이번에
tree-sitter를 골랐다. 이유:

  - javalang은 엄격한(strict) 파서라 파일 어딘가에 문법 오류가 있으면 그 시점부터 전체 파싱이
    실패한다. 그런데 이 프로젝트의 AS-IS 원본은 실제로 컴파일이 안 되는 경우가 드물지 않다
    (FPLA047.java: 중괄호 누락/미선언 변수 다수, PPLA047.java: 파라미터 누락 - Phase 0에서
    실측 확인됨). "원본이 깨졌다고 통째로 포기"는 이 프로젝트에서 못 쓴다.
  - tree-sitter는 편집기 실시간 파싱용으로 설계된 오류 복구(error-recovering) 파서라, 문제가
    있는 구간은 ERROR 노드로 남기고 나머지는 최대한 정상 파싱한다. `node.has_error`로 "이
    메서드 서브트리는 신뢰할 수 있는가"까지 판단할 수 있어, 이전 정규식 방식보다 정확도를
    올리면서도 실패를 침묵하지 않고 신호로 남길 수 있다.

파일 전체가 구문 오류 없이 깨끗하게 파싱되면(`tree.root_node.has_error == False`) tree-sitter
결과를 전적으로 신뢰한다 - 실제로 테스트해보니 정규식은 문자열 리터럴/주석 안에 "public
IDataSet fakeMethod(x)" 같은 텍스트가 있어도 진짜 메서드로 오탐하는 반면, tree-sitter는
string_literal 토큰 안이라는 걸 구조적으로 알기 때문에 오탐하지 않는다(직접 재현/확인함) - 이
경우엔 tree-sitter가 정규식보다 항상 더 정확하다.

파일에 실제 구문 오류가 있으면(중괄호 누락 등, FPLA047.java류) 얘기가 달라진다 - tree-sitter의
오류 복구 과정에서 뒤 메서드가 앞 메서드의 깨진 블록 안에 먹혀버려 아예 안 잡힐 수 있다(이것도
직접 재현/확인함). 이때는 tree-sitter 결과와 정규식 결과의 합집합을 취한다 - 메서드를 놓치는
쪽(포팅 대상에서 통째로 빠짐)이 정규식의 오탐(사람이 리뷰 중 걸러낼 수 있음)보다 더 위험한
실패이기 때문이다. 본문 경계는 이 경우 메서드별 `node.has_error`를 따로 봐서, 깨끗한 서브트리는
tree-sitter 경계를, 나머지는 정규식 근사치를 쓴다.

tree-sitter/tree-sitter-java가 설치돼 있지 않은 환경(예: 아직 requirements.txt를 새로
설치하지 않은 로컬)에서도 이 모듈은 임포트 자체는 항상 성공하고, 정규식 전용으로 동작한다.
"""
from __future__ import annotations

import re

_METHOD_SIG_RE = re.compile(
    r"public\s+IDataSet\s+(\w+)\s*\(([^)]*)\)", re.DOTALL
)

try:
    import tree_sitter_java as _tsjava
    from tree_sitter import Language, Node, Parser

    _JAVA_LANGUAGE = Language(_tsjava.language())
    _parser = Parser(_JAVA_LANGUAGE)
    TREE_SITTER_AVAILABLE = True
except Exception:  # pragma: no cover - 의존성 미설치 환경 대비, 조용히 정규식 전용으로 내려간다
    TREE_SITTER_AVAILABLE = False


def _regex_extract_methods(java_text: str) -> list[str]:
    return [m.group(1) for m in _METHOD_SIG_RE.finditer(java_text)]


def _regex_extract_method_bodies(java_text: str) -> dict[str, str]:
    matches = list(_METHOD_SIG_RE.finditer(java_text))
    bodies: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(java_text)
        bodies[m.group(1)] = java_text[start:end]
    return bodies


def _parse(source: bytes):
    """소스를 파싱해 (tree, [(이름, 본문시작, 본문끝, 메서드별 has_error), ...])를 반환한다.

    파싱 자체가 예외를 던지면(설치는 됐지만 이 버전 그래머가 안 맞는 등) None을 반환해 호출부가
    정규식으로 폴백하게 한다.
    """
    try:
        tree = _parser.parse(source)
    except Exception:
        return None

    results: list[tuple[str, int, int, bool]] = []

    def walk(node: "Node") -> None:
        if node.type == "method_declaration":
            name_node = node.child_by_field_name("name")
            type_node = node.child_by_field_name("type")
            body_node = node.child_by_field_name("body")
            # tree-sitter-java 이 버전에서는 "modifiers"가 child_by_field_name으로는 안 잡혀서
            # (필드로 선언 안 돼있음, 실제 테스트로 확인함) 위치 기반으로 직접 찾는다.
            mod_node = next((c for c in node.children if c.type == "modifiers"), None)
            is_public = mod_node is not None and b"public" in source[mod_node.start_byte:mod_node.end_byte]
            return_type = source[type_node.start_byte:type_node.end_byte] if type_node else b""
            if is_public and return_type == b"IDataSet" and name_node is not None and body_node is not None:
                name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", "replace")
                results.append((name, body_node.start_byte, body_node.end_byte, node.has_error))
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return tree, results


def extract_methods(java_text: str) -> list[str]:
    """P/F/D java 소스에서 `public IDataSet xxx(...)` 형태의 메서드 이름을 뽑는다.

    파일이 구문 오류 없이 깨끗하게 파싱되면 tree-sitter 결과를 그대로 신뢰한다(문자열/주석 안의
    가짜 시그니처에 흔들리지 않아 정규식보다 정확함 - 실측 확인). 실제 구문 오류가 있는 파일은
    tree-sitter가 오류 복구 중 뒤 메서드를 앞 블록에 먹어버릴 수 있어(실측 재현) 정규식 결과와
    합집합을 취한다 - 메서드를 놓치는 게 오탐보다 더 위험한 실패이기 때문이다.
    """
    regex_names = _regex_extract_methods(java_text)
    if not TREE_SITTER_AVAILABLE:
        return regex_names
    parsed = _parse(java_text.encode("utf-8"))
    if parsed is None:
        return regex_names
    tree, found = parsed
    ts_names = [name for name, _, _, _ in found]
    if not tree.root_node.has_error:
        return ts_names
    return list(dict.fromkeys(ts_names + regex_names))


_TOBE_METHOD_SIG_RE = re.compile(r"public\s+[\w<>\[\],\s]+?\s(\w+)\s*\(")


def extract_tobe_method_bodies(java_text: str) -> dict[str, str]:
    """**생성된 TO-BE** Java(Api/Service/Store)의 메서드 본문을 뽑는다.

    이 모듈의 다른 함수들은 전부 AS-IS 전용이다 - 정규식도 tree-sitter 조건도 `public IDataSet`
    으로 고정돼 있어서, TO-BE 산출물(`public Map<String, Object> fXxx(Map<String, Object> req)`)에
    쓰면 **아무것도 못 찾고 조용히 빈 dict를 돌려준다.**

    이걸 모르고 `extract_method_bodies`(AS-IS용)를 수리 루프에서 TO-BE Service에 썼었다. 그래서
    수리 프롬프트의 "현재 코드"가 계속 빈 문자열로 나갔고, LLM은 고칠 코드를 보지도 못한 채 오류
    메시지만 받아 메서드 이름을 지어냈다(실측: `dPLA08710` → `fPLA087QrySelectMainList` →
    `fPLA087QrySelectMain`으로 라운드마다 악화). 목(mock) 테스트는 프롬프트와 무관하게 고정 코드를
    돌려줘서 이 결함을 못 잡았고, 실 LLM 실행에서는 수리 루프가 발동한 적이 없어 드러나지 않았다.

    AS-IS 파서를 넓히지 않고 함수를 따로 둔다 - AS-IS 쪽 동작(문자열/주석 안 가짜 시그니처 회피
    등 실측으로 맞춰둔 것)을 건드리지 않기 위해서다.
    """
    matches = list(_TOBE_METHOD_SIG_RE.finditer(java_text))
    bodies: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(java_text)
        bodies[m.group(1)] = java_text[start:end].rstrip()
    return bodies


def extract_method_bodies(java_text: str) -> dict[str, str]:
    """각 메서드의 본문을 뽑는다.

    파일 전체가 깨끗하게 파싱되면 모든 메서드에 대해 tree-sitter의 실제 `{ ... }` 블록 경계를
    쓴다(정규식의 "다음 시그니처까지" 근사치보다 정확 - 중첩 클래스/주석 안 가짜 시그니처에
    안 흔들림). 구문 오류가 있는 파일은 메서드별 `has_error`로 따로 판단해서, 깨끗한 서브트리만
    tree-sitter 경계를 쓰고 나머지는 정규식 근사치를 그대로 둔다(추측으로 경계를 만들지 않는다).
    """
    bodies = _regex_extract_method_bodies(java_text)
    if not TREE_SITTER_AVAILABLE:
        return bodies
    source_bytes = java_text.encode("utf-8")
    parsed = _parse(source_bytes)
    if parsed is None:
        return bodies
    tree, found = parsed
    file_is_clean = not tree.root_node.has_error
    for name, start, end, node_has_error in found:
        if file_is_clean or not node_has_error:
            bodies[name] = source_bytes[start:end].decode("utf-8", "replace")
    return bodies
