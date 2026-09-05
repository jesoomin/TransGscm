"""화면마다 복제된 공통 메서드를 한 곳으로 모은다.

**무엇이 문제인가**: 이 코퍼스의 화면 30개는 각자 `fAuthCheck`/`fCommonCodeQry`/`fHistoryQry`
(+절반은 `fExcelDownQry`)와 그에 대응하는 D 메서드, 그리고 `S901`~`S903` SQL을 **똑같이** 갖고
있다. 그대로 변환하면 30벌의 사본이 그대로 30벌의 TO-BE 사본이 된다 - 멘토가 §2에서 경고한
"1,416개 화면에 1,416가지 변형"이 시작되는 지점이고, 지금의 '개발자별 이원화' 문제가 그대로
이식된다.

**판단은 하지 않고 세기만 한다.** 어떤 메서드가 공통인지는 추측이 아니라 측정으로 정한다 -
`agents/dup_detect.normalized_at()`의 정규화 단계를 그대로 재사용해서, 화면들 사이에서 본문이
**어느 단계에서 하나로 수렴하는지**를 본다.

    EXACT   글자 그대로 같다            → 화면 정보가 본문에 아예 없다(D 계층 4종이 여기)
    SCREEN  화면 ID만 치환하면 같다      → 자기 화면의 D 클래스명만 다르다(F 계층 3종)
    수렴 안 함                          → 진짜로 다르다. **공통화 대상이 아니다**

**수렴하지 않는 화면은 버리지 않고 이름을 부른다.** 실제로 `fCommonCodeQry`는 29화면이 한
덩어리인데 PLA107 하나만 갈라졌다 - 그 화면이 `lookupDataUnit` 대신 `lookupFunctionUnit`을
부르고 있어서다(컴파일은 통과하고 런타임에 실패하는 결함). 즉 **"공통화하려다 걸리는 화면"이
곧 결함 후보**다. 이건 결함 탐지기가 아니라 공통화 분석이 찾아낸 것이라, 두 관점이 서로를
교차 검증한다.

사용:
    python -m agents.common_methods <AS-IS 폴더>
    python -m agents.common_methods <폴더> --emit pilot/gscm/src/main/java   # 공통 클래스 생성
    python -m agents.common_methods <폴더> --json tracking/common-methods.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_PROJECT_ROOT), str(_PROJECT_ROOT / "chatui")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from java_ast import extract_method_bodies, extract_methods  # noqa: E402

from agents.dup_detect import NORM_STEPS, normalized_at  # noqa: E402

# 공통화를 인정하는 최소 수렴 단계. LITERAL/LOCAL_VAR까지 가서야 같아지는 건 "리터럴이 다른
# 서로 다른 로직"일 수 있어서 자동 공통화 대상으로 삼지 않는다 - 재현율보다 안전을 택한다.
_ACCEPTED_STEPS = ("EXACT", "SCREEN")

# 이 비율 이상의 화면이 같은 본문을 가져야 공통으로 본다. 2~3화면이 우연히 같은 걸 공통 모듈로
# 올리면 나중에 갈라질 때 더 비싸다.
_MIN_SHARE = 0.8
_MIN_SCREENS = 5

CONFIG_PATH = _PROJECT_ROOT / "config" / "common-methods.json"

_SCREEN_RE = re.compile(r"PLA\d+", re.IGNORECASE)
_STMT_RE = re.compile(r'<select\s+id="([^"]+)"(.*?)</select>', re.DOTALL | re.IGNORECASE)


@dataclass
class CommonMethod:
    layer: str            # "F" | "D"
    method: str
    step: str             # 수렴한 정규화 단계
    screens: list[str] = field(default_factory=list)
    outliers: dict[str, str] = field(default_factory=dict)  # {화면: 갈라진 본문 미리보기}

    @property
    def share(self) -> float:
        total = len(self.screens) + len(self.outliers)
        return len(self.screens) / total if total else 0.0


def _collect_bodies(src: Path, layer: str) -> dict[str, dict[str, str]]:
    """{메서드명: {화면: 본문}} - 해당 계층의 모든 화면을 훑는다."""
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for path in sorted(src.glob(f"{layer}PLA*.java")):
        m = _SCREEN_RE.search(path.name)
        if not m:
            continue
        screen = m.group(0).upper()
        text = path.read_text(encoding="utf-8", errors="replace")
        bodies = extract_method_bodies(text)
        for name in extract_methods(text):
            out[name][screen] = bodies.get(name, "")
    return out


def _converge(per_screen: dict[str, str]) -> tuple[str | None, list[str], dict[str, str]]:
    """가장 이른 수렴 단계와, 그 단계에서 다수를 이루는 화면/갈라진 화면을 돌려준다."""
    for step, _desc in NORM_STEPS:
        groups: dict[str, list[str]] = defaultdict(list)
        for screen, body in per_screen.items():
            groups[normalized_at(body, screen, step)].append(screen)
        biggest = max(groups.values(), key=len)
        if len(biggest) == len(per_screen):
            return step, sorted(biggest), {}
        if len(biggest) / len(per_screen) >= _MIN_SHARE and step in _ACCEPTED_STEPS:
            # 다수는 같고 소수만 갈라진 경우 - 그 소수가 곧 검토 대상이다(결함일 수 있다).
            odd = {s: " ".join(per_screen[s].split())[:120]
                   for s in per_screen if s not in biggest}
            return step, sorted(biggest), dict(sorted(odd.items()))
    return None, [], {}


def find_common_methods(src: Path) -> list[CommonMethod]:
    """AS-IS 폴더 전체에서 공통화 후보를 찾는다(LLM 미사용, 전부 정적 비교)."""
    found: list[CommonMethod] = []
    for layer in ("F", "D"):
        for method, per_screen in sorted(_collect_bodies(src, layer).items()):
            if len(per_screen) < _MIN_SCREENS:
                continue
            step, screens, outliers = _converge(per_screen)
            if step not in _ACCEPTED_STEPS:
                continue
            found.append(CommonMethod(layer=layer, method=method, step=step,
                                      screens=screens, outliers=outliers))
    return found


def find_common_statements(src: Path) -> list[CommonMethod]:
    """Mapper(XSQL) statement도 같은 방식으로 본다.

    SQL 본문에는 `/* Biz: ...DPLA096.S902 ... */` 같은 추적 주석이 들어 있어 화면마다 글자가
    다르다 - 그래서 EXACT로는 절대 안 잡히고 SCREEN 단계에서야 하나가 된다. 그걸 모르고
    "SQL은 화면마다 다르다"고 결론 내리면 30벌 복제를 그대로 옮기게 된다.
    """
    per_stmt: dict[str, dict[str, str]] = defaultdict(dict)
    for path in sorted(src.glob("DPLA*.xsql")):
        m = _SCREEN_RE.search(path.name)
        if not m:
            continue
        screen = m.group(0).upper()
        text = path.read_text(encoding="utf-8", errors="replace")
        for stmt_id, body in _STMT_RE.findall(text):
            per_stmt[stmt_id][screen] = body
    out: list[CommonMethod] = []
    for stmt_id, per_screen in sorted(per_stmt.items()):
        if len(per_screen) < _MIN_SCREENS:
            continue
        step, screens, outliers = _converge(per_screen)
        if step not in _ACCEPTED_STEPS:
            continue
        out.append(CommonMethod(layer="XSQL", method=stmt_id, step=step,
                                screens=screens, outliers=outliers))
    return out


def analyze(src: Path) -> dict:
    methods = find_common_methods(src)
    statements = find_common_statements(src)
    screens = sorted({s for m in methods + statements for s in m.screens})
    return {
        "source": str(src),
        "screens_scanned": len(screens),
        "methods": [
            {"layer": m.layer, "name": m.method, "converged_at": m.step,
             "screens": len(m.screens), "share": round(m.share, 4),
             "outliers": m.outliers}
            for m in methods
        ],
        "statements": [
            {"layer": m.layer, "name": m.method, "converged_at": m.step,
             "screens": len(m.screens), "share": round(m.share, 4),
             "outliers": m.outliers}
            for m in statements
        ],
        "note": (
            "수렴 단계가 EXACT/SCREEN인 항목만 담았습니다. 리터럴·지역변수까지 지워야 같아지는 "
            "것은 서로 다른 로직일 수 있어 자동 공통화 대상에서 제외했습니다. "
            "outliers는 다수와 갈라진 화면이며, 공통화 전에 반드시 원인을 확인해야 합니다 - "
            "실제로 이 목록에서 원본 결함이 나왔습니다."
        ),
    }


# ---------------------------------------------------------------------------
# 확정 레지스트리 - 무엇을 실제로 공통화할지는 사람이 정한다
# ---------------------------------------------------------------------------

def load_registry(path: Path | None = None) -> dict:
    """확정된 공통 메서드 목록. 없거나 CONFIRMED가 아니면 **적용하지 않는다**.

    CLAUDE.md가 "공통 모듈은 사람이 먼저 확정한다"고 못 박고 있어, 분석 결과를 생성기가 바로
    집어삼키지 않게 파일 하나를 사이에 둔다 - 사람이 이 파일에서 항목을 빼면 그 메서드는
    화면별로 그대로 생성된다.
    """
    p = path or CONFIG_PATH
    if not p.is_file():
        return {"status": "ABSENT", "service": [], "store": [], "statements": []}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"status": "ABSENT", "service": [], "store": [], "statements": []}
    if data.get("status") != "CONFIRMED":
        return {"status": data.get("status", "PROPOSED"),
                "service": [], "store": [], "statements": []}
    return data


def common_service_methods(registry: dict | None = None) -> set[str]:
    return set((registry or load_registry()).get("service", []))


def common_store_methods(registry: dict | None = None) -> set[str]:
    return set((registry or load_registry()).get("store", []))


def common_statements(registry: dict | None = None) -> set[str]:
    return set((registry or load_registry()).get("statements", []))


# ---------------------------------------------------------------------------
# 공통 클래스 생성 - 화면마다가 아니라 **한 번만** 만든다
# ---------------------------------------------------------------------------

COMMON_PKG = "com.skhynix.gscm.common"
COMMON_SERVICE_CLASS = "GscmCommonService"
COMMON_STORE_CLASS = "GscmCommonStore"

_HEADER = """// 화면 간 공통 로직 - 자동 생성(python -m agents.common_methods --emit).
// 무엇을 여기에 둘지는 config/common-methods.json(사람 확정)이 정한다. 화면별 Service/Store는
// 같은 이름의 메서드를 그대로 노출하되 본문만 이 클래스로 위임하므로, 호출부는 바뀌지 않는다."""


def render_common_service(methods: list[str], specs: dict) -> str:
    lines = [
        f"package {COMMON_PKG}.service;",
        "",
        "import org.springframework.beans.factory.annotation.Autowired;",
        "import org.springframework.stereotype.Service;",
        "",
        f"import {COMMON_PKG}.store.{COMMON_STORE_CLASS};",
        "",
        "import java.util.HashMap;",
        "import java.util.Map;",
        "",
        _HEADER,
        "@Service",
        f"public class {COMMON_SERVICE_CLASS} {{",
        "",
        "    @Autowired",
        f"    private {COMMON_STORE_CLASS} store;",
        "",
    ]
    for m in methods:
        spec = specs.get(m)
        d_method = spec.d_method if spec else ("d" + m[1:] if m.startswith("f") else m)
        lines.append(f"    public Map<String, Object> {m}(Map<String, Object> request) {{")
        if spec and spec.recordset:
            # 원본이 `du.dXXX(...).getRecordSet("NAME")` 한 줄로 꺼내 그대로 담는 패턴이면
            # 그 키를 그대로 옮긴다 - 결과 Map을 통째로 넘기면 원본이 반환하지 않던 데이터가
            # 새어 나간다(Api 계층에서 실제로 겪은 결함과 같은 종류다).
            lines += [
                f"        Map<String, Object> result = store.{d_method}(request);",
                f"        Map<String, Object> response = new HashMap<>();",
                f'        response.put("{spec.recordset}", '
                f'result == null ? null : result.get("{spec.recordset}"));',
                f"        return response;",
            ]
        else:
            # 분기·계산이 있는 메서드는 여기서 규칙으로 만들지 않는다. 스텁으로 남겨 사람이
            # 한 번만 포팅하게 한다 - 30벌을 각각 포팅하던 것을 1벌로 줄이는 게 목적이지,
            # 로직을 여기서 새로 설계하는 게 아니다.
            lines += [
                f"        // PORT_ONCE:{m} — 원본 F 메서드에 분기/계산이 있어 규칙으로 옮기지 않았다.",
                f"        //   화면 30벌이 같은 본문이므로 **한 번만** 포팅하면 된다.",
                f'        throw new UnsupportedOperationException("TODO: {m} 공통 포팅 필요");',
            ]
        lines += [f"    }}", ""]
    lines.append("}")
    return "\n".join(lines) + "\n"


@dataclass
class _ServiceSpec:
    d_method: str
    recordset: str | None


_PASSTHROUGH_RE = re.compile(
    r"(?:IRecordSet|var)\s+\w+\s*=\s*\w+\.(\w+)\([^)]*\)\.getRecordSet\(\s*\"([^\"]+)\"\s*\)\s*;"
    r"\s*\w+\.putRecordset\(\s*\"\2\"",
    re.DOTALL,
)
_D_CALL_RE = re.compile(r"\w+\.(d\w+)\s*\(")


def service_specs(src: Path, methods: list[str]) -> dict:
    """공통 Service 메서드마다 (호출하는 D 메서드, 그대로 옮길 레코드셋 키)를 원본에서 읽는다.

    30화면이 같은 본문이라는 걸 이미 확인했으므로 대표 1건에서 읽으면 된다. 키를 지어내지
    않고 실제 `getRecordSet("...")` 인자를 그대로 쓴다.
    """
    out: dict = {}
    for path in sorted(src.glob("FPLA*.java")):
        bodies = extract_method_bodies(path.read_text(encoding="utf-8", errors="replace"))
        for m in methods:
            if m in out or m not in bodies:
                continue
            body = bodies[m]
            d_call = _D_CALL_RE.search(body)
            pt = _PASSTHROUGH_RE.search(body)
            out[m] = _ServiceSpec(
                d_method=(d_call.group(1) if d_call else ""),
                recordset=(pt.group(2) if pt else None),
            )
        if len(out) == len(methods):
            break
    return out


def render_common_store(methods: list[str], stmt_by_method: dict[str, str]) -> str:
    lines = [
        f"package {COMMON_PKG}.store;",
        "",
        "import org.mybatis.spring.SqlSessionTemplate;",
        "import org.springframework.beans.factory.annotation.Autowired;",
        "import org.springframework.stereotype.Repository;",
        "",
        "import java.util.Map;",
        "",
        _HEADER,
        "@Repository",
        f"public class {COMMON_STORE_CLASS} {{",
        "",
        f'    private static final String NS = "{COMMON_PKG}.store.{COMMON_STORE_CLASS}.";',
        "",
        "    @Autowired",
        "    private SqlSessionTemplate sqlSession;",
        "",
    ]
    for m in methods:
        lines += [
            f"    public Map<String, Object> {m}(Map<String, Object> params) {{",
            f'        return sqlSession.selectOne(NS + "{m}", params);',
            f"    }}",
            "",
        ]
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_common_mapper(sql_by_method: dict[str, str]) -> str:
    body = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE sqlMap PUBLIC "-//mybatid.org//DTD Mapper 3.0//EN" '
        '"http://mybatid.org/dtd/mybatis-3-mapper.dtd">',
        f'<mapper namespace="{COMMON_PKG}.store.{COMMON_STORE_CLASS}">',
        "",
    ]
    for method, sql in sql_by_method.items():
        body.append(f'\t<select id="{method}" parameterType="map" resultType="map">')
        body.append(sql.rstrip())
        body.append("\t</select>")
        body.append("")
    body.append("</mapper>")
    return "\n".join(body) + "\n"


def _d_method_statements(src: Path) -> dict[str, str]:
    """{D 메서드명: dbSelect가 참조하는 statement id} - 대표 화면 하나면 충분하다."""
    out: dict[str, str] = {}
    for path in sorted(src.glob("DPLA*.java")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(
                r"public\s+IDataSet\s+(\w+)\s*\(.*?dbSelect\(\s*\"([^\"]+)\"",
                text, re.DOTALL):
            out.setdefault(m.group(1), m.group(2))
        if out:
            break
    return out


def _common_sql(src: Path, registry: dict) -> dict[str, str]:
    """공통 statement의 SQL 본문을 대표 화면 하나에서 가져온다.

    30벌이 (추적 주석을 빼면) 같다는 걸 이미 확인했으므로 아무거나 하나면 된다 - 다만 그
    "같다"는 판정을 여기서 다시 하지는 않는다(analyze()가 이미 한 일이다).
    """
    d_to_stmt: dict[str, str] = {}
    common_store_names = set(registry.get("store", []))
    stmt_ids = set(registry.get("statements", []))
    for path in sorted(src.glob("DPLA*.java")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"public\s+IDataSet\s+(\w+)\s*\(.*?dbSelect\(\s*\"([^\"]+)\"",
                             text, re.DOTALL):
            method, sid = m.group(1), m.group(2)
            if method in common_store_names and sid in stmt_ids:
                d_to_stmt.setdefault(method, sid)
        if len(d_to_stmt) == len(common_store_names & set(d_to_stmt) | d_to_stmt.keys()):
            pass
    out: dict[str, str] = {}
    for path in sorted(src.glob("DPLA*.xsql")):
        text = path.read_text(encoding="utf-8", errors="replace")
        found = dict(_STMT_RE.findall(text))
        for method, sid in d_to_stmt.items():
            if method in out or sid not in found:
                continue
            inner = found[sid]
            m = re.search(r"<!\[CDATA\[(.*?)\]\]>", inner, re.DOTALL)
            sql = m.group(1) if m else inner
            # 추적 주석에는 화면별 클래스명이 박혀 있어 공통 SQL에 그대로 두면 거짓말이 된다.
            sql = re.sub(r"/\*\s*Biz:.*?\*/", "/* Biz: 공통 (GscmCommonStore) */", sql,
                         flags=re.DOTALL)
            sql = re.sub(r"#(\w+)#", r"#{\1}", sql)
            out[method] = f"\t\t<![CDATA[{sql}]]>"
    return out


def check_registry(src: Path, registry: dict) -> list[str]:
    """확정 목록 자체가 앞뒤 안 맞는 곳을 짚는다.

    **Store 메서드는 그 SQL까지 공통이어야 공통화할 수 있다.** 본문이 화면마다 똑같아도
    (`dbSelect("S903")` 한 줄이면 당연히 똑같다) 그 S903의 SQL이 도메인마다 다르면, 메서드만
    공통 클래스로 올리는 순간 5개 도메인이 하나의 SQL을 공유하게 된다 - 조용히 동작이 바뀐다.
    실제로 dHistoryQry가 정확히 그 경우였고(본문 EXACT 동일, S903은 DOMAIN_CD 리터럴이 도메인별로
    다름) 첫 적용에서 그대로 통과했다.
    """
    problems: list[str] = []
    common_stmts = set(registry.get("statements", []))
    d_to_stmt = _d_method_statements(src)
    for method in sorted(registry.get("store", [])):
        sid = d_to_stmt.get(method)
        if sid is None:
            problems.append(f"{method}: 대응하는 dbSelect statement를 찾지 못했습니다.")
        elif sid not in common_stmts:
            problems.append(
                f"{method}: 본문은 화면 간 동일하지만 그 SQL({sid})은 공통이 아닙니다 - "
                f"메서드만 공통화하면 화면마다 다른 쿼리가 하나로 합쳐집니다. "
                f"statements에 {sid}이 없으면 store에서도 빼세요.")
    return problems


def emit_common_sources(src: Path, out_root: Path, registry: dict) -> list[Path]:
    """공통 Service/Store/Mapper를 파일로 쓴다. 화면 수와 무관하게 각 1개다."""
    problems = check_registry(src, registry)
    if problems:
        raise ValueError("확정 목록이 앞뒤가 맞지 않습니다:\n  - " + "\n  - ".join(problems))
    service_methods = sorted(registry.get("service", []))
    store_methods = sorted(registry.get("store", []))
    sql_by_method = _common_sql(src, registry)

    written: list[Path] = []
    java_root = out_root / "src" / "main" / "java" / COMMON_PKG.replace(".", "/")
    res_root = out_root / "src" / "main" / "resources" / "mapper" / "common"
    if service_methods:
        p = java_root / "service" / f"{COMMON_SERVICE_CLASS}.java"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            render_common_service(service_methods, service_specs(src, service_methods)),
            encoding="utf-8")
        written.append(p)
    if store_methods:
        p = java_root / "store" / f"{COMMON_STORE_CLASS}.java"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_common_store(store_methods, sql_by_method), encoding="utf-8")
        written.append(p)
    if sql_by_method:
        p = res_root / "GscmCommonMapper.xml"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(render_common_mapper(sql_by_method), encoding="utf-8")
        written.append(p)
    return written


def render(result: dict) -> str:
    out = ["=" * 78, "  화면 간 공통 메서드/SQL 분석", "=" * 78]
    for title, key in (("F/D 메서드", "methods"), ("Mapper statement", "statements")):
        rows = result[key]
        out.append(f"\n[{title}]")
        if not rows:
            out.append("  공통화할 만한 항목이 없습니다.")
            continue
        for r in rows:
            out.append(f"  {r['layer']:<4} {r['name']:<20} {r['screens']:>3}화면 "
                       f"({r['share']:.0%}) · 수렴 단계 {r['converged_at']}")
            for screen, preview in r["outliers"].items():
                out.append(f"        ! {screen} 만 다름 — {preview[:90]}")
    dup_lines = sum(r["screens"] for r in result["methods"] + result["statements"])
    out.append("-" * 78)
    out.append(f"  화면 {result['screens_scanned']}개 기준, 같은 내용이 총 {dup_lines}벌 복제돼 "
               f"있습니다 ({len(result['methods']) + len(result['statements'])}종).")
    out.append("\n  " + result["note"].replace(". ", ".\n  "))
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agents.common_methods")
    ap.add_argument("folder", help="AS-IS 소스 폴더")
    ap.add_argument("--json", default="", help="분석 결과를 JSON으로 저장")
    ap.add_argument("--propose", default="", help="확정 레지스트리 초안을 이 경로에 쓴다")
    ap.add_argument("--emit", default="",
                    help="확정된 공통 Service/Store/Mapper를 이 프로젝트 루트에 생성(예: pilot/gscm)")
    args = ap.parse_args(argv)

    src = Path(args.folder).expanduser().resolve()
    if not src.is_dir():
        print(f"폴더가 없습니다: {src}", file=sys.stderr)
        return 2
    result = analyze(src)
    print(render(result))

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                   encoding="utf-8")
        print(f"\nJSON 저장: {args.json}")

    if args.propose:
        # outliers가 있는 항목은 초안에서 뺀다 - 원인을 모르는 채로 공통화하면 그 화면의
        # 동작을 조용히 바꾸게 된다. 사람이 원인을 확인하고 직접 넣어야 한다.
        clean = [r for r in result["methods"] if not r["outliers"]]
        _clean_stmt_ids = {r["name"] for r in result["statements"] if not r["outliers"]}
        draft = {
            "status": "PROPOSED",
            "generated_from": str(src),
            "service": sorted(r["name"] for r in clean if r["layer"] == "F"),
            # SQL이 공통이 아닌 Store 메서드는 초안에서 뺀다(check_registry와 같은 규칙).
            "store": sorted(
                r["name"] for r in clean if r["layer"] == "D"
                and _d_method_statements(src).get(r["name"]) in _clean_stmt_ids),
            "statements": sorted(_clean_stmt_ids),
            "excluded_due_to_outliers": {
                r["name"]: r["outliers"] for r in result["methods"] + result["statements"]
                if r["outliers"]
            },
            "how_to_apply": (
                "내용을 확인한 뒤 status를 CONFIRMED로 바꾸면 생성기가 이 목록의 메서드를 "
                "화면마다 복제하지 않고 공통 클래스로 위임합니다. 항목을 빼면 그 메서드는 "
                "지금처럼 화면별로 생성됩니다."
            ),
        }
        Path(args.propose).parent.mkdir(parents=True, exist_ok=True)
        Path(args.propose).write_text(json.dumps(draft, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
        print(f"확정 레지스트리 초안: {args.propose} (status=PROPOSED — 사람이 CONFIRMED로 바꿔야 적용)")

    if args.emit:
        registry = load_registry()
        if registry.get("status") != "CONFIRMED":
            print(f"\n공통 클래스를 생성하지 않았습니다 — {CONFIG_PATH}의 status가 "
                  f"'{registry.get('status')}'입니다. 사람이 CONFIRMED로 바꿔야 적용됩니다.",
                  file=sys.stderr)
            return 1
        written = emit_common_sources(src, Path(args.emit).expanduser().resolve(), registry)
        print("\n공통 클래스 생성(화면 수와 무관하게 각 1개):")
        for p in written:
            print(f"  {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
