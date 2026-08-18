"""화면(파일럿) 여러 개가 쌓였을 때, 화면 하나짜리 세트를 넘어서는 중복/영향도를 분석한다.

CLAUDE.md 멘토 코멘트(§1, §J)의 "nctRid 매핑 그래프(화면↔nctRid↔BizUnit↔XSQL)"가 이런 전체
분석의 진짜 전제다 - 아직 그 그래프가 없고 파일럿 화면도 적어서, 이 모듈은 지금 당장 완전한
영향도 분석을 하는 게 아니라 "화면이 늘어날 때 바로 쓸 수 있는 비교 인프라"를 먼저 만든다.
화면이 1개뿐이면 비교 대상이 없다는 사실을 그대로 보고한다 - 추측으로 채우지 않는다.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

# TO-BE Service/Store 메서드 시그니처: `public Map<String, Object> method(...) {`
# (AS-IS의 `public IDataSet method(...)`와 달라서 skeleton_gen._METHOD_SIG_RE를 그대로 못 쓴다)
_TOBE_METHOD_SIG_RE = re.compile(r"public\s+[\w<>\[\],\s]+?\s(\w+)\s*\([^)]*\)\s*\{")
_MAPPER_STMT_RE = re.compile(
    r'<(?:select|insert|update|delete)\s+id="([^"]+)"[^>]*>(.*?)</(?:select|insert|update|delete)>',
    re.DOTALL,
)


@dataclass
class DuplicateGroup:
    kind: str  # "SERVICE_METHOD_BODY" | "MAPPER_STATEMENT_SQL"
    preview: str  # 정규화된 내용의 앞부분 미리보기
    locations: list[str] = field(default_factory=list)  # "화면ID:파일명:식별자"


@dataclass
class CrossAnalysisResult:
    screens_analyzed: list[str]
    duplicate_groups: list[DuplicateGroup] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _normalize(text: str) -> str:
    """공백/줄바꿈 차이를 무시하고 비교하기 위한 정규화. 변수명 차이는 못 잡는다(정확 일치 기준)."""
    return re.sub(r"\s+", " ", text).strip()


def _extract_tobe_methods(java_text: str) -> dict[str, str]:
    """TO-BE Service/Store 파일에서 메서드 이름->본문을 뽑는다(다음 시그니처 전까지를 본문으로 근사)."""
    matches = list(_TOBE_METHOD_SIG_RE.finditer(java_text))
    methods: dict[str, str] = {}
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(java_text)
        methods[m.group(1)] = java_text[start:end]
    return methods


def _extract_mapper_statements(mapper_xml: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for m in _MAPPER_STMT_RE.finditer(mapper_xml)}


# pilot/ 아래에는 화면별 하위 폴더가 없다(실제 TO-BE 프로젝트 구조를 그대로 병합할 수 있게
# gscm/src/main/... 트리를 공유한다) - 그래서 화면 구분은 폴더가 아니라 파일명 접두어
# (Pla047Api.java -> "Pla047")로 한다.
_SCREEN_FROM_FILENAME_RE = re.compile(r"^(.+?)(?:Api|Service|Store|Dto|Mapper)\.(?:java|xml)$")


def _screen_prefix(filename: str) -> str:
    m = _SCREEN_FROM_FILENAME_RE.match(filename)
    return m.group(1) if m else filename


_MIN_MEANINGFUL_LEN = 80  # 너무 짧은 본문/SQL은 우연히 같아도 의미가 없어 비교에서 뺀다


def analyze_pilot_folder(pilot_root: Path) -> CrossAnalysisResult:
    """pilot/ 아래(화면별 폴더 없이 gscm/src/main/... 공유 트리)의 TO-BE 산출물을 전부 훑어
    화면 간 중복 로직/SQL을 찾는다.

    같은 화면 안에서의 중복은 다루지 않는다(그건 그 화면 자체의 설계 문제) - 여기서는 서로 다른
    화면 사이의 중복만 본다. 실제로 여러 화면이 쌓이기 전까지는 항상 "비교 불가" 노트만 나온다.
    """
    if not pilot_root.exists():
        return CrossAnalysisResult(screens_analyzed=[], notes=["pilot/ 폴더가 아직 없습니다."])

    service_like_paths = list(pilot_root.rglob("*Service.java")) + list(pilot_root.rglob("*Store.java"))
    mapper_paths = list(pilot_root.rglob("*Mapper.xml"))
    screens = sorted({_screen_prefix(p.name) for p in service_like_paths + mapper_paths})
    result = CrossAnalysisResult(screens_analyzed=screens)

    if len(screens) < 2:
        result.notes.append(
            f"파일럿 화면이 {len(screens)}개뿐이라 화면 간 중복/영향도 비교를 할 수 없습니다"
            "(비교하려면 최소 2개 화면 필요) - 화면이 더 쌓이면 다음 실행부터 자동으로 비교됩니다."
        )
        return result

    body_index: dict[str, list[str]] = {}
    stmt_index: dict[str, list[str]] = {}

    for service_path in service_like_paths:
        screen = _screen_prefix(service_path.name)
        text = service_path.read_text(encoding="utf-8", errors="replace")
        for name, body in _extract_tobe_methods(text).items():
            norm = _normalize(body)
            if len(norm) < _MIN_MEANINGFUL_LEN:
                continue
            key = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            body_index.setdefault(key, []).append(f"{screen}:{service_path.name}:{name}")

    for mapper_path in mapper_paths:
        screen = _screen_prefix(mapper_path.name)
        xml_text = mapper_path.read_text(encoding="utf-8", errors="replace")
        for stmt_id, sql in _extract_mapper_statements(xml_text).items():
            norm = _normalize(sql)
            if len(norm) < _MIN_MEANINGFUL_LEN:
                continue
            key = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            stmt_index.setdefault(key, []).append(f"{screen}:{mapper_path.name}:{stmt_id}")

    for key, locations in body_index.items():
        distinct_screens = {loc.split(":", 1)[0] for loc in locations}
        if len(distinct_screens) > 1:
            result.duplicate_groups.append(DuplicateGroup(
                kind="SERVICE_METHOD_BODY",
                preview=locations[0],
                locations=locations,
            ))

    for key, locations in stmt_index.items():
        distinct_screens = {loc.split(":", 1)[0] for loc in locations}
        if len(distinct_screens) > 1:
            result.duplicate_groups.append(DuplicateGroup(
                kind="MAPPER_STATEMENT_SQL",
                preview=locations[0],
                locations=locations,
            ))

    if not result.duplicate_groups:
        result.notes.append(f"{len(screens)}개 화면({', '.join(screens)})을 비교했지만 화면 간 중복(동일 로직/SQL)은 발견되지 않았습니다.")

    return result
