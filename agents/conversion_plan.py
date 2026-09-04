"""화면별 변환 계획(`conversion-plan.json`) 생성 - 코드를 만들기 **전에** 무엇을 어떻게 바꿀지
파일로 고정한다 (2026-09-04 추가).

CLAUDE.md 핵심 원칙: "화면마다 변환 전에 계획을 파일로 고정한다(`conversion-plan.json` 등).
계획 없이 바로 코드를 생성하지 않는다 - 계획이 있어야 리뷰·재현·재실행이 가능하다."
docs/03-kickoff-plan.md Phase 2에도 같은 항목이 있는데 그동안 비어 있었다 - 파이프라인이 계획
없이 곧장 코드를 생성하고 있었다는 뜻이라, 프로젝트가 스스로 세운 원칙을 어기고 있던 구멍이다.
ReCodeAgent(arXiv:2604.07341)의 Planner가 "계획을 파일로 못 박아 리뷰·재현 가능하게 한다"는
것과 같은 자리다.

**이 모듈은 LLM을 쓰지 않는다.** 계획 내용은 전부 정적 분석으로 결정된다(파일 존재 여부,
메서드 시그니처, nctRid 매핑, TO-BE 경로 규칙) - CLAUDE.md "결정론적으로 가능한 건 LLM에
맡기지 않는다" 그대로다. 그래서 계획 수립은 변환 결과에 의존하지 않고 **변환 전에** 돌 수 있다.

**트랙(Refactor/Reimagine)은 자동으로 정하지 않는다.** CLAUDE.md/Phase 3이 "사람이 결정"이라고
못 박았기 때문에 항상 `UNDECIDED`로 두고, 사람이 판단할 근거가 되는 신호(`track_signals`)만
사실대로 채운다 - 특히 AS-IS 원본의 중괄호가 안 맞는지(= 원본이 애초에 컴파일 안 되는 상태인지)는
CLAUDE.md가 Reimagine 후보의 예로 직접 든 기준이다.

**저장 위치는 `tracking/conversion-plans/`다 - `pilot/`이 아니다.** `pilot/`은 사람이 "승인하고
저장"을 눌러야만 파일이 생기는 곳이고(그 보장을 깨면 안 된다), 계획은 정의상 그 승인 *이전에*
있어야 하는 산출물이라 추적용 폴더에 따로 쓴다.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CHATUI_DIR = _PROJECT_ROOT / "chatui"
for _p in (str(_PROJECT_ROOT), str(_CHATUI_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from skeleton_gen import (  # noqa: E402
    detect_simple_delegation,
    extract_method_bodies,
    extract_methods,
    extract_nctrid_map,
    to_prefix,
    tobe_relpath,
    unsupported_db_verbs,
)
from validators import count_unbalanced_braces  # noqa: E402

PLAN_VERSION = 1
PLANS_DIR = _PROJECT_ROOT / "tracking" / "conversion-plans"

# (버킷 계층, 버킷 키) -> 계획서에 쓸 fragment 이름. CLAUDE.md가 "화면 하나를 통째로 넣지 말고
# 5개 fragment로 나눠 처리한다"고 정한 그 5개다.
_FRAGMENTS = [
    ("P", "java", "P.java"),
    ("P", "bizunit", "P.bizunit"),
    ("F", "java", "F.java"),
    ("D", "java", "D.java"),
    ("D", "xsql", "D.xsql"),
]


def plan_path(screen_id: str) -> Path:
    return PLANS_DIR / f"{screen_id}-conversion-plan.json"


def _fragment_entry(content: str | None, path: str | None) -> dict:
    if not content:
        return {"present": False, "as_is_path": path}
    return {
        "present": True,
        "as_is_path": path,
        "lines": content.count("\n") + 1,
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
    }


def _expected_outputs(buckets: dict, screen_id: str, package_p1: str, package_p2: str) -> list[dict]:
    """실제 생성 조건(skeleton_gen.generate_skeletons/generate_dto, workflow_graph._convert_screen)을
    그대로 반복해서 "이 화면에서 어떤 TO-BE 파일이 나올 예정인지"를 미리 적는다 - 추측이 아니라
    같은 조건식이다(P java 있으면 Api+Dto, F java 있으면 Service, D java 있으면 Store, D xsql
    있으면 Mapper.xml).
    """
    prefix = to_prefix(screen_id)
    has = {
        "p_java": bool(buckets.get("P", {}).get("java")),
        "f_java": bool(buckets.get("F", {}).get("java")),
        "d_java": bool(buckets.get("D", {}).get("java")),
        "d_xsql": bool(buckets.get("D", {}).get("xsql")),
    }
    planned: list[tuple[str, str, str]] = []
    if has["p_java"]:
        planned.append((f"{prefix}Api.java", "RULE_BASED", "P BizUnit 메서드 시그니처 -> REST 엔드포인트"))
        planned.append((f"{prefix}Dto.java", "RULE_BASED", ".BIZUNIT/실사용 getField·putRecordset에서 역추출"))
    if has["f_java"]:
        planned.append((
            f"{prefix}Service.java", "RULE_BASED_SKELETON + LLM_PORTING",
            "골격은 규칙 기반, 단순 위임이 아닌 메서드 본문만 LLM이 포팅",
        ))
    if has["d_java"]:
        planned.append((f"{prefix}Store.java", "RULE_BASED", "D 메서드 -> MyBatis statement 참조"))
    if has["d_xsql"]:
        planned.append((f"{prefix}Mapper.xml", "RULE_BASED", "iBatis -> MyBatis 문법 변환만"))
    return [
        {
            "file": fname,
            "tobe_path": tobe_relpath(fname, package_p1, package_p2),
            "conversion_method": method,
            "note": note,
        }
        for fname, method, note in planned
    ]


def build_screen_plan(
    screen_id: str,
    buckets: dict,
    package_p1: str,
    package_p2: str,
    as_is_paths: dict | None = None,
) -> dict:
    """화면 하나의 변환 계획을 만든다(파일로 쓰지는 않는다 - write_plans가 한다).

    buckets는 agents/source_scan.scan_folder()가 준 {"P": {"java":..., "bizunit":...}, ...} 형태.
    """
    as_is_paths = as_is_paths or {}
    p_java = buckets.get("P", {}).get("java")
    f_java = buckets.get("F", {}).get("java")
    p_bizunit = buckets.get("P", {}).get("bizunit")

    fragments = {
        name: _fragment_entry(buckets.get(layer, {}).get(key), as_is_paths.get(name))
        for layer, key, name in _FRAGMENTS
    }

    nctrid_map = extract_nctrid_map(p_bizunit) if p_bizunit else {}
    f_methods = extract_methods(f_java) if f_java else []
    f_bodies = extract_method_bodies(f_java) if f_java else {}

    # F 메서드를 "단순 위임(규칙 기반으로 바로 생성)"과 "LLM 포팅 필요"로 나눈다.
    simple_delegations: dict[str, str] = {}
    llm_targets: list[str] = []
    for m in f_methods:
        delegate = detect_simple_delegation(f_bodies.get(m, ""))
        if delegate:
            simple_delegations[m] = delegate
        else:
            llm_targets.append(m)

    unbalanced = {
        name: count_unbalanced_braces(buckets.get(layer, {}).get(key) or "")
        for layer, key, name in _FRAGMENTS
        if key == "java" and buckets.get(layer, {}).get(key)
    }
    # 이 변환기가 못 다루는 D 계층 verb(dbInsert/dbUpdate 등)를 **변환 전에** 드러낸다 - 지금까지
    # 확보한 원본이 전부 조회 전용이라 검증된 적 없는 경로라서, 계획서에서 미리 경고해야 사람이
    # "이 화면은 자동 변환을 믿으면 안 된다"를 착수 전에 알 수 있다.
    unsupported_verbs = unsupported_db_verbs(buckets.get("D", {}).get("java"))

    return {
        "plan_version": PLAN_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "screen_id": screen_id,
        "ui_id": f"U-P{screen_id}",  # agents/nctrid_graph.ui_id_for_screen과 같은 규칙
        "package": {"p1": package_p1, "p2": package_p2},
        "fragments": fragments,
        "nctrids": sorted(set(nctrid_map.values())),
        "expected_outputs": _expected_outputs(buckets, screen_id, package_p1, package_p2),
        "llm_porting_targets": llm_targets,
        "rule_based_delegations": simple_delegations,
        "estimated_llm_calls": {
            # 단순 위임 메서드는 규칙 기반으로 생성되므로 LLM을 아예 안 부른다(2026-09-04 수정).
            # 그 전에는 파이프라인이 F 메서드 전부를 보내놓고 단순 위임분 결과는 splice에서
            # 버렸고, 버려지니 재시도 라운드마다 또 불러서 PLA047 기준 유효 1건에 호출 5건이
            # 나갔다 - _convert_screen이 LLM_PENDING 메서드만 pending에 담도록 고쳐서 없앴다.
            "porting": len(llm_targets),
            "porting_skipped_rule_based": len(simple_delegations),
            "ai_recommend": len(nctrid_map) if p_java else 0,
        },
        # 트랙은 사람이 정한다 - 여기서 추측해 채우지 않는다(CLAUDE.md/Phase 3).
        "track": "UNDECIDED",
        "unsupported_db_verbs": unsupported_verbs,
        "track_signals": {
            "as_is_unbalanced_braces": unbalanced,
            "as_is_source_broken": any(v != 0 for v in unbalanced.values()),
            "f_method_count": len(f_methods),
            "nctrid_count": len(nctrid_map),
            "has_xsql": bool(buckets.get("D", {}).get("xsql")),
            # dbSelect 외 verb를 쓰면 이 변환기로는 D 계층을 자동 변환할 수 없다 - Reimagine 트랙
            # 또는 수작업 대상 판단에 직접 쓰이는 신호다(트랙 결정은 사람 몫이라 여기선 표시만).
            "has_unsupported_db_verbs": bool(unsupported_verbs),
        },
    }


def write_plans(plans: dict[str, dict], plans_dir: Path | None = None) -> dict[str, str]:
    """화면별 계획을 `tracking/conversion-plans/{화면}-conversion-plan.json`으로 쓴다.

    `pilot/`이 아니라 추적용 폴더에 쓴다 - "승인 전까지 pilot/엔 아무 파일도 안 생긴다"는 보장을
    깨지 않으면서, 계획은 변환 *이전에* 파일로 고정돼야 하기 때문. 재실행하면 같은 경로를 덮어쓴다
    (generated_at으로 언제 세운 계획인지 구분).
    반환값은 {screen_id: 쓴 파일 경로 문자열}.
    """
    target_dir = plans_dir or PLANS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}
    for screen_id, plan in plans.items():
        path = target_dir / f"{screen_id}-conversion-plan.json"
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        written[screen_id] = str(path)
    return written


def build_plans(
    screens: dict[str, dict],
    package_map: dict[str, tuple[str, str]],
    all_paths: dict | None = None,
) -> dict[str, dict]:
    """대상 화면 전체의 계획을 만든다(파일 쓰기는 write_plans가 따로)."""
    all_paths = all_paths or {}
    plans: dict[str, dict] = {}
    for screen_id, buckets in screens.items():
        p1, p2 = package_map.get(screen_id, ("TODO", "TODO"))
        plans[screen_id] = build_screen_plan(
            screen_id, buckets, p1, p2, as_is_paths=all_paths.get(screen_id, {}),
        )
    return plans
