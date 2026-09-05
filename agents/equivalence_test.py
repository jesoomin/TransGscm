"""L3 기능 동등성 측정 — AS-IS F 로직과 TO-BE Service를 **실제로 실행해서** 결과를 비교한다.

**왜 여태 못 쟀나, 그리고 무엇이 바뀌었나.**

이 프로젝트는 줄곧 "포팅된 Service를 실행할 수단이 없다(Spring Boot를 못 띄운다)"는 이유로
L3(기능 동등성)를 미측정으로 뒀다. 그런데 그 전제를 다시 따져보니 틀렸다 — 필요한 건 애플리케이션
기동이 아니라 **F 계층 메서드를 호출할 수 있는 최소 환경**이고, 그건 만들 수 있었다:

  - AS-IS가 실제로 쓰는 NEXCORE API 표면은 **10개 남짓의 닫힌 집합**이다(실측: IDataSet의
    getField/setField/getFieldMap/putFieldMap/putRecordset/getRecordSet, IRecordSet.getRecordCount,
    ProcessUnit.lookupDataUnit/dbSelect, BizRuntimeException). `harness/stub/`에 최소 재현을 뒀다.
  - TO-BE Service는 Spring 애노테이션만 떼면 평범한 클래스다. Store는 인터페이스 경계라 스텁으로
    바꿔 끼우면 된다.
  - javac/java는 이미 이 PC에 있다(SQL Developer 번들 JDK).

**핵심 설계 — D 계층을 양쪽 동일한 상수로 고정한다.**
AS-IS의 `dbSelect`와 TO-BE의 `store.dXxx()`가 **같은 캔드 데이터**를 돌려주게 만든다. 그러면 두
실행 결과의 차이는 오직 **F 계층 업무 로직의 포팅 차이**에서만 나온다. SQL 동등성은 이미
`agents/diff_test.py`(같은 DB에 AS-IS/TO-BE SQL을 실행해 비교)가 담당하는 별개 층이라, 여기서
또 다루면 무엇을 재는 실험인지가 흐려진다.

**이 측정이 말하는 것 / 말하지 않는 것**
  - 말한다: 같은 입력·같은 데이터에서 **F 로직이 같은 값을 내는가** (LLM 포팅의 정확성)
  - 말하지 않는다: SQL이 맞는가(diff_test 담당) · HTTP/직렬화 계층이 맞는가 · 실제 운영 데이터에서
    맞는가. 캔드 데이터는 우리가 만든 값이므로 **원본 데이터 분포를 대표하지 않는다.**

사용:
    python -m agents.equivalence_test <AS-IS 폴더> --screens PLA087,... [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
for _p in (str(_PROJECT_ROOT), str(_PROJECT_ROOT / "chatui")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

STUB_DIR = _PROJECT_ROOT / "harness" / "stub"
SNAPSHOT_DIR = _PROJECT_ROOT / "tracking" / "generated-snapshots"

# 캔드 데이터 행 수 - 분기 경로를 훑기 위해 여러 케이스를 돌린다. 0행은 "조회 결과 없음" 분기를,
# 1행/3행은 정상 분기를 태운다(fAuthCheck의 getRecordCount()>0 같은 판정이 여기서 갈린다).
ROW_COUNTS = [0, 1, 3]


def _find_java() -> tuple[str, str] | None:
    """javac/java 경로를 찾는다. PATH에 없으면 검증기가 쓰는 것과 같은 로컬 JDK를 쓴다."""
    from validators import _find_local_mvn_and_java_home

    exe = ".exe" if os.name == "nt" else ""
    for base in (None,):
        pass
    _mvn, java_home = _find_local_mvn_and_java_home()
    if java_home:
        jc = Path(java_home) / "bin" / f"javac{exe}"
        jv = Path(java_home) / "bin" / f"java{exe}"
        if jc.exists() and jv.exists():
            return str(jc), str(jv)
    jc, jv = shutil.which("javac"), shutil.which("java")
    return (jc, jv) if jc and jv else None


_RS_NAME_RE = re.compile(r'(?:get|put)Recordset?\s*\(\s*"(\w+)"', re.I)
_GETRS_RE = re.compile(r'getRecordSet\s*\(\s*"(\w+)"')
_PUTRS_RE = re.compile(r'putRecordset\s*\(\s*"(\w+)"')
_D_METHOD_RE = re.compile(r"public\s+IDataSet\s+(d\w+)\s*\(")
_F_METHOD_RE = re.compile(r"public\s+IDataSet\s+(f\w+)\s*\(")
_P_METHOD_RE = re.compile(r"public\s+IDataSet\s+(p\w+)\s*\(")
# `ResponseEntity<Map<String, Object>>`처럼 제네릭이 중첩되므로 `[^>]*`로는 못 잡는다
# (실제로 이것 때문에 Api 비교가 0건으로 조용히 비어 있었다).
_API_METHOD_RE = re.compile(r"public\s+ResponseEntity<.+?>\s+(\w+)\s*\(")


def _recordset_names(f_src: str) -> list[str]:
    return sorted(set(_GETRS_RE.findall(f_src)) | set(_PUTRS_RE.findall(f_src)))


def _tobe_store_stub(package: str, cls: str, signatures: list[tuple[str, str, str]],
                     rs_names: list[str], svc_pkg: str) -> str:
    """TO-BE Store를 캔드 데이터 스텁으로 대체한다 — AS-IS의 dbSelect와 같은 값을 준다.

    실제 Store의 시그니처(반환 타입·파라미터)를 그대로 복제한다. 반환 타입이 `Map`이 아니라
    `List<XxxDto>`인 메서드도 있어서(규칙 기반 위임 경로), 타입을 맞추지 않으면 Service가
    컴파일되지 않는다.
    """
    puts = "\n".join(
        f'        out.put("{n}", gscm.fwk.base.CannedData.rows());' for n in rs_names
    ) or "        // 반환할 recordset 이름이 소스에 없다"

    body = []
    for ret, name, params in signatures:
        ret = ret.strip()
        if ret.startswith("List<"):
            body.append(
                f"    public {ret} {name}({params}) {{\n"
                f"        return new java.util.ArrayList<>();\n    }}")
        else:
            body.append(
                f"    public {ret} {name}({params}) {{\n"
                f"        return canned();\n    }}")
    methods = "\n\n".join(body)
    return f"""package {package};

import java.util.*;
import {svc_pkg.rsplit('.', 1)[0]}.dto.*;

/** 하네스 전용 Store 스텁 - AS-IS dbSelect와 **동일한** 캔드 데이터를 돌려준다. */
public class {cls} {{
    private java.util.Map<String, Object> canned() {{
        java.util.Map<String, Object> out = new java.util.LinkedHashMap<String, Object>();
{puts}
        return out;
    }}

{methods}
}}
"""


def _strip_spring(src: str) -> str:
    """Spring/MyBatis 애노테이션과 임포트만 걷어낸다.

    DTO 임포트는 **남긴다** - 규칙 기반 위임 메서드가 `List<XxxDto>`를 쓰기 때문에 DTO를 같이
    컴파일해야 한다. 처음엔 스텁을 줄이려고 DTO까지 버렸는데, 그러면 그 메서드들이 컴파일되지
    않아 비교 대상에서 통째로 빠진다(측정 범위가 조용히 좁아진다).

    `ResponseEntity`는 지우지 않고 **최소 스텁으로 대체**한다(harness/stub) - Api가 무엇을
    돌려주는지 봐야 HTTP/직렬화 경계를 비교할 수 있다.
    """
    drop_prefix = ("import org.springframework.stereotype",
                   "import org.springframework.beans",
                   "import org.springframework.web",
                   "import org.mybatis")
    drop_exact = {"@Service", "@Autowired", "@Repository", "@RestController"}
    drop_start = ("@RequestMapping", "@PostMapping", "@GetMapping",
                  "@PutMapping", "@DeleteMapping")
    out = []
    for line in src.splitlines():
        s = line.strip()
        if s.startswith(drop_prefix):
            continue
        if s in drop_exact or s.startswith(drop_start):
            continue
        out.append(line.replace("@RequestBody ", ""))
    return "\n".join(out)


def _harness_main(asis_pkg: str, asis_f_cls: str, asis_d_cls: str,
                  tobe_svc_pkg: str, tobe_service: str,
                  tobe_store_pkg: str, tobe_store: str,
                  methods: list[str],
                  asis_p_cls: str = "", tobe_api_pkg: str = "", tobe_api: str = "",
                  api_methods: list[str] | None = None) -> str:
    calls = "\n".join(
        f'''        runPair("{m}", rows, out);'''
        for m in methods
    )
    api_methods = api_methods or []
    # Api 계층(HTTP/직렬화 경계) 비교 - P 메서드와 Api 메서드를 같은 입력으로 부른다.
    api_calls = "\n".join(
        f'''        runApiPair("{m}", rows, out);'''
        for m in api_methods
    )
    api_setup = ""
    api_block = ""
    if api_methods:
        api_setup = (
            f"            ProcessUnit.registerDataUnit({asis_pkg}.{asis_f_cls}.class, asisF);\n"
            f"            asisP = new {asis_pkg}.{asis_p_cls}();\n"
            f"            tobeApi = new {tobe_api_pkg}.{tobe_api}();\n"
            f"            setField(tobeApi, \"service\", tobeSvc);\n"
        )
        api_block = f"""
    static {asis_pkg}.{asis_p_cls} asisP;
    static {tobe_api_pkg}.{tobe_api} tobeApi;

    /** Api 계층 비교 - P 메서드(AS-IS 진입점) vs Api 메서드(TO-BE 엔드포인트). */
    static void runApiPair(String method, int rows, List<String> out) {{
        String asis = safeAsisP(method);
        String tobe = safeTobeApi(method);
        out.add("{{\\"layer\\":\\"API\\",\\"method\\":\\"" + method + "\\",\\"rows\\":" + rows
                + ",\\"asis\\":" + q(asis) + ",\\"tobe\\":" + q(tobe)
                + ",\\"match\\":" + asis.equals(tobe) + "}}");
    }}

    static String safeAsisP(String method) {{
        try {{
            IDataSet req = new DataSet();
            req.setField("TGT_CD", "T0");
            java.lang.reflect.Method m = asisP.getClass().getMethod(
                method, IDataSet.class, IOnlineContext.class);
            return render((IDataSet) m.invoke(asisP, req, new OnlineContext()));
        }} catch (Throwable t) {{
            return "ERROR:" + rootName(t);
        }}
    }}

    static String safeTobeApi(String method) {{
        try {{
            Map<String, Object> req = new LinkedHashMap<String, Object>();
            req.put("TGT_CD", "T0");
            java.lang.reflect.Method m = tobeApi.getClass().getMethod(method, Map.class);
            Object r = m.invoke(tobeApi, req);
            Object body = r == null ? null
                : r.getClass().getMethod("getBody").invoke(r);
            return renderMap(body);
        }} catch (Throwable t) {{
            return "ERROR:" + rootName(t);
        }}
    }}

    static void setField(Object target, String name, Object value) {{
        try {{
            java.lang.reflect.Field f = target.getClass().getDeclaredField(name);
            f.setAccessible(true);
            f.set(target, value);
        }} catch (Exception e) {{
            throw new RuntimeException("필드 주입 실패: " + name + " - " + e, e);
        }}
    }}
"""
    return f"""import java.util.*;

import nexcore.framework.core.data.*;
import gscm.fwk.base.CannedData;
import gscm.fwk.base.ProcessUnit;

/** AS-IS F와 TO-BE Service를 같은 입력으로 실행해 결과를 JSON 한 줄로 뱉는다. */
public class Harness {{
    static {asis_pkg}.{asis_f_cls} asisF;
    static {tobe_svc_pkg}.{tobe_service} tobeSvc;

    public static void main(String[] args) throws Exception {{
        List<String> out = new ArrayList<String>();
        for (int rows : new int[]{{ {", ".join(str(r) for r in ROW_COUNTS)} }}) {{
            CannedData.setRowCount(rows);
            ProcessUnit.clearRegistry();
            ProcessUnit.registerDataUnit({asis_pkg}.{asis_d_cls}.class, new {asis_pkg}.{asis_d_cls}());
            asisF = new {asis_pkg}.{asis_f_cls}();
            tobeSvc = new {tobe_svc_pkg}.{tobe_service}();
            setStore(tobeSvc, new {tobe_store_pkg}.{tobe_store}());
{api_setup}{calls}
{api_calls}
        }}
        System.out.println("[" + String.join(",", out) + "]");
    }}

{api_block}
    static void setStore(Object svc, Object store) {{
        try {{
            java.lang.reflect.Field f = svc.getClass().getDeclaredField("store");
            f.setAccessible(true);
            f.set(svc, store);
        }} catch (Exception e) {{
            throw new RuntimeException("Service에 store 필드를 꽂지 못했다: " + e, e);
        }}
    }}

    static void runPair(String method, int rows, List<String> out) {{
        String asis = safeAsis(method);
        String tobe = safeTobe(method);
        out.add("{{\\"method\\":\\"" + method + "\\",\\"rows\\":" + rows
                + ",\\"asis\\":" + q(asis) + ",\\"tobe\\":" + q(tobe)
                + ",\\"match\\":" + asis.equals(tobe) + "}}");
    }}

    static String q(String s) {{
        return "\\"" + s.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"") + "\\"";
    }}

    static String safeAsis(String method) {{
        try {{
            IDataSet req = new DataSet();
            req.setField("TGT_CD", "T0");
            java.lang.reflect.Method m = asisF.getClass().getMethod(
                method, IDataSet.class, IOnlineContext.class);
            Object r = m.invoke(asisF, req, new OnlineContext());
            return render((IDataSet) r);
        }} catch (Throwable t) {{
            return "ERROR:" + rootName(t);
        }}
    }}

    static String safeTobe(String method) {{
        try {{
            Map<String, Object> req = new LinkedHashMap<String, Object>();
            req.put("TGT_CD", "T0");
            java.lang.reflect.Method m = tobeSvc.getClass().getMethod(method, Map.class);
            Object r = m.invoke(tobeSvc, req);
            return renderMap(r);
        }} catch (Throwable t) {{
            return "ERROR:" + rootName(t);
        }}
    }}

    static String rootName(Throwable t) {{
        Throwable c = t;
        while (c.getCause() != null) {{ c = c.getCause(); }}
        return c.getClass().getSimpleName();
    }}

    /** AS-IS IDataSet -> 정규화 문자열. 필드와 recordset 행수를 이름순으로 늘어놓는다. */
    static String render(IDataSet ds) {{
        if (ds == null) return "null";
        StringBuilder sb = new StringBuilder();
        Map<String, Object> f = ds.getFieldMap();
        for (String k : new TreeSet<String>(f.keySet())) {{
            sb.append(k).append('=').append(String.valueOf(f.get(k))).append(';');
        }}
        String rc = ds.harnessResultCode();
        if (rc != null) {{ sb.append("@msg=").append(rc).append(';'); }}
        if (ds instanceof DataSet) {{
            Map<String, IRecordSet> rsm = ((DataSet) ds).harnessRecordsets();
            for (String k : new TreeSet<String>(rsm.keySet())) {{
                IRecordSet rs = rsm.get(k);
                sb.append(k).append('#').append(rs == null ? -1 : rs.getRecordCount()).append(';');
            }}
        }}
        return sb.toString();
    }}

    /** TO-BE Map -> 같은 규칙의 정규화 문자열. 리스트는 이름#행수로 맞춘다. */
    @SuppressWarnings("unchecked")
    static String renderMap(Object o) {{
        if (o == null) return "null";
        if (!(o instanceof Map)) return String.valueOf(o);
        Map<String, Object> m = (Map<String, Object>) o;
        StringBuilder sb = new StringBuilder();
        for (String k : new TreeSet<String>(m.keySet())) {{
            Object v = m.get(k);
            if (v instanceof Collection) {{
                sb.append(k).append('#').append(((Collection<?>) v).size()).append(';');
            }} else {{
                sb.append(k).append('=').append(String.valueOf(v)).append(';');
            }}
        }}
        return sb.toString();
    }}
}}
"""


def run_screen(screen_id: str, asis_dir: Path, tobe_dir: Path,
               javac: str, java: str, work: Path) -> dict:
    """화면 하나에 대해 AS-IS/TO-BE를 실행하고 비교한다."""
    f_path = asis_dir / f"F{screen_id}.java"
    d_path = asis_dir / f"D{screen_id}.java"
    p_path = asis_dir / f"P{screen_id}.java"
    prefix = screen_id[:1].upper() + screen_id[1:].lower()
    svc_path = tobe_dir / f"{prefix}Service.java"
    store_path = tobe_dir / f"{prefix}Store.java"
    for p in (f_path, d_path, svc_path, store_path):
        if not p.exists():
            return {"screen_id": screen_id, "status": "SKIPPED",
                    "reason": f"필요한 파일 없음: {p.name}"}

    f_src = f_path.read_text(encoding="utf-8", errors="replace")
    d_src = d_path.read_text(encoding="utf-8", errors="replace")
    svc_src = svc_path.read_text(encoding="utf-8", errors="replace")
    store_src = store_path.read_text(encoding="utf-8", errors="replace")

    asis_pkg = re.search(r"^package\s+([\w.]+);", f_src, re.M).group(1)
    tobe_svc_pkg = re.search(r"^package\s+([\w.]+);", svc_src, re.M).group(1)
    tobe_store_pkg = re.search(r"^package\s+([\w.]+);", store_src, re.M).group(1)

    src = work / "src"
    (src / asis_pkg.replace(".", "/")).mkdir(parents=True, exist_ok=True)
    (src / tobe_svc_pkg.replace(".", "/")).mkdir(parents=True, exist_ok=True)
    (src / tobe_store_pkg.replace(".", "/")).mkdir(parents=True, exist_ok=True)

    (src / asis_pkg.replace(".", "/") / f"F{screen_id}.java").write_text(f_src, encoding="utf-8")
    (src / asis_pkg.replace(".", "/") / f"D{screen_id}.java").write_text(d_src, encoding="utf-8")
    (src / tobe_svc_pkg.replace(".", "/") / f"{prefix}Service.java").write_text(
        _strip_spring(svc_src), encoding="utf-8")

    # DTO도 함께 컴파일한다(규칙 기반 위임 메서드가 참조한다).
    dto_path = tobe_dir / f"{prefix}Dto.java"
    if dto_path.exists():
        dto_src = dto_path.read_text(encoding="utf-8", errors="replace")
        dto_pkg = re.search(r"^package\s+([\w.]+);", dto_src, re.M).group(1)
        (src / dto_pkg.replace(".", "/")).mkdir(parents=True, exist_ok=True)
        (src / dto_pkg.replace(".", "/") / f"{prefix}Dto.java").write_text(
            _strip_spring(dto_src), encoding="utf-8")

    # Store 스텁은 **실제 생성된 Store의 시그니처를 그대로** 흉내낸다 - 반환 타입이 다르면
    # Service가 컴파일되지 않는다(규칙 기반 위임은 List<Dto>를, LLM 포팅분은 Map을 기대한다).
    real_sigs = re.findall(r"public\s+([\w<>,\s.]+?)\s+(\w+)\s*\(([^)]*)\)", store_src)
    rs_names = _recordset_names(f_src)
    (src / tobe_store_pkg.replace(".", "/") / f"{prefix}Store.java").write_text(
        _tobe_store_stub(tobe_store_pkg, f"{prefix}Store", real_sigs, rs_names, tobe_svc_pkg),
        encoding="utf-8")

    # 양쪽에 다 존재하는 메서드만 비교한다 - 한쪽에만 있으면 동등성 질문 자체가 성립하지 않는다.
    asis_methods = set(_F_METHOD_RE.findall(f_src))
    tobe_methods = set(re.findall(r"public\s+Map<String,\s*Object>\s+(\w+)\s*\(", svc_src))
    methods = sorted(asis_methods & tobe_methods)
    if not methods:
        return {"screen_id": screen_id, "status": "SKIPPED",
                "reason": "AS-IS/TO-BE 양쪽에 공통으로 있는 F 메서드가 없음"}

    # ---- Api(HTTP/직렬화) 계층 준비 -------------------------------------------
    # F 계층만 비교하면 "P 계층의 오케스트레이션(권한 게이트·빈 결과 메시지)이 옮겨졌는가"를
    # 영영 못 본다. 실제로 이 세트의 P 메서드는 F를 4~5개 호출하고 분기까지 하는데, 생성된
    # Api는 위임 1건만 배선한다 - 그 격차를 수치로 드러내려고 이 계층을 따로 비교한다.
    api_methods: list[str] = []
    asis_p_cls = tobe_api_pkg = tobe_api_cls = ""
    api_path = tobe_dir / f"{prefix}Api.java"
    if p_path.exists() and api_path.exists():
        p_src = p_path.read_text(encoding="utf-8", errors="replace")
        api_src = api_path.read_text(encoding="utf-8", errors="replace")
        tobe_api_pkg = re.search(r"^package\s+([\w.]+);", api_src, re.M).group(1)
        (src / tobe_api_pkg.replace(".", "/")).mkdir(parents=True, exist_ok=True)
        (src / asis_pkg.replace(".", "/") / f"P{screen_id}.java").write_text(
            p_src, encoding="utf-8")
        (src / tobe_api_pkg.replace(".", "/") / f"{prefix}Api.java").write_text(
            _strip_spring(api_src), encoding="utf-8")
        asis_p_cls = f"P{screen_id}"
        tobe_api_cls = f"{prefix}Api"
        api_methods = sorted(set(_P_METHOD_RE.findall(p_src))
                             & set(_API_METHOD_RE.findall(api_src)))

    (src / "Harness.java").write_text(
        _harness_main(asis_pkg, f"F{screen_id}", f"D{screen_id}",
                      tobe_svc_pkg, f"{prefix}Service",
                      tobe_store_pkg, f"{prefix}Store", methods,
                      asis_p_cls, tobe_api_pkg, tobe_api_cls, api_methods),
        encoding="utf-8")

    out = work / "classes"
    out.mkdir(exist_ok=True)
    stub_files = [str(p) for p in STUB_DIR.rglob("*.java")]

    def _compile(files: list[str]):
        return subprocess.run([javac, "-encoding", "UTF-8", "-nowarn", "-d", str(out)]
                              + files + stub_files,
                              capture_output=True, text=True, errors="replace")

    all_files = [str(p) for p in src.rglob("*.java")]
    cp = _compile(all_files)
    api_degraded = ""
    if cp.returncode != 0 and api_methods:
        # **우아한 축소**: P/Api가 컴파일되지 않아도 Service 계층 비교까지 잃지 않는다.
        # 실제로 P 원본이 깨진 화면(주입 결함)에서 Api 계층을 추가하자마자 F 계층 결과까지
        # 통째로 사라지는 커버리지 회귀가 났다 - 층을 하나 더 보려다 이미 보던 걸 잃으면 안 된다.
        api_degraded = (cp.stderr or cp.stdout).strip().splitlines()[:3]
        drop = {str(src / asis_pkg.replace(".", "/") / f"P{screen_id}.java"),
                str(src / tobe_api_pkg.replace(".", "/") / f"{prefix}Api.java")}
        for f in list(drop):
            try:
                os.remove(f)
            except OSError:
                pass
        api_methods = []
        (src / "Harness.java").write_text(
            _harness_main(asis_pkg, f"F{screen_id}", f"D{screen_id}",
                          tobe_svc_pkg, f"{prefix}Service",
                          tobe_store_pkg, f"{prefix}Store", methods),
            encoding="utf-8")
        cp = _compile([str(p) for p in src.rglob("*.java")])

    if cp.returncode != 0:
        return {"screen_id": screen_id, "status": "COMPILE_FAIL",
                "reason": (cp.stderr or cp.stdout).strip().splitlines()[:6],
                "methods": methods}

    rp = subprocess.run([java, "-cp", str(out), "Harness"],
                        capture_output=True, text=True, errors="replace", timeout=120)
    if rp.returncode != 0:
        return {"screen_id": screen_id, "status": "RUN_FAIL",
                "reason": (rp.stderr or rp.stdout).strip().splitlines()[:6]}
    try:
        results = json.loads(rp.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"screen_id": screen_id, "status": "PARSE_FAIL", "reason": rp.stdout[:400]}

    matched = sum(1 for r in results if r["match"])
    by_layer: dict[str, dict] = {}
    for r in results:
        layer = r.get("layer", "SERVICE")
        b = by_layer.setdefault(layer, {"cases": 0, "matched": 0})
        b["cases"] += 1
        b["matched"] += int(r["match"])
    for b in by_layer.values():
        b["match_rate"] = round(b["matched"] / b["cases"], 4) if b["cases"] else None
    return {"screen_id": screen_id, "status": "OK", "methods": methods,
            "api_methods": api_methods,
            "api_layer_skipped": api_degraded or None,
            "cases": len(results), "matched": matched,
            "match_rate": round(matched / len(results), 4) if results else None,
            "by_layer": by_layer, "results": results}


def run(asis_dir: Path, screens: list[str], tobe_root: Path | None = None) -> dict:
    tools = _find_java()
    if not tools:
        return {"error": "javac/java를 찾지 못했습니다 - JDK가 있어야 실행 비교가 가능합니다"}
    javac, java = tools
    tobe_root = tobe_root or SNAPSHOT_DIR

    per_screen = []
    for sid in screens:
        work = Path(tempfile.mkdtemp(prefix=f"equiv-{sid}-"))
        try:
            per_screen.append(run_screen(sid, asis_dir, tobe_root / sid, javac, java, work))
        finally:
            shutil.rmtree(work, ignore_errors=True)

    ok = [s for s in per_screen if s["status"] == "OK"]
    cases = sum(s["cases"] for s in ok)
    matched = sum(s["matched"] for s in ok)
    # 계층별로 나눠서 집계한다 - 합치면 "Service는 맞는데 Api가 전부 틀린" 상황이 평균에
    # 묻혀 버린다. 실제로 그 일이 일어나서 이렇게 바꿨다.
    layers: dict[str, dict] = {}
    for s in ok:
        for name, b in (s.get("by_layer") or {}).items():
            agg = layers.setdefault(name, {"cases": 0, "matched": 0, "screens": 0})
            agg["cases"] += b["cases"]
            agg["matched"] += b["matched"]
            agg["screens"] += 1
    for b in layers.values():
        b["match_rate"] = round(b["matched"] / b["cases"], 4) if b["cases"] else None
    return {
        "screens_total": len(screens),
        "screens_executed": len(ok),
        "cases": cases,
        "matched": matched,
        "by_layer": layers,
        # 실행하지 못한 화면을 분모에 넣지 않는다 - 못 잰 것과 틀린 것은 다르다.
        "match_rate": round(matched / cases, 4) if cases else None,
        "per_screen": per_screen,
        "scope_note": (
            "D 계층(SQL)을 양쪽 동일한 캔드 데이터로 고정하고 F 계층 로직만 비교했습니다. "
            "Api 계층은 P 메서드(AS-IS 진입점) vs Api 메서드(TO-BE 엔드포인트)를 같은 입력으로 비교합니다. "
            "SQL 정확성은 agents/diff_test.py가 담당하는 별개 층입니다. "
            "캔드 데이터는 합성값이라 실제 운영 데이터 분포를 대표하지 않습니다."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m agents.equivalence_test")
    ap.add_argument("asis_dir")
    ap.add_argument("--screens", required=True)
    ap.add_argument("--tobe-root", default="")
    ap.add_argument("--json", default="")
    args = ap.parse_args(argv)

    screens = [s.strip().upper() for s in args.screens.split(",") if s.strip()]
    res = run(Path(args.asis_dir).expanduser().resolve(), screens,
              Path(args.tobe_root) if args.tobe_root else None)
    if "error" in res:
        print(res["error"], file=sys.stderr)
        return 2

    print("=" * 78)
    print("  L3 기능 동등성 — AS-IS(F·P) vs TO-BE(Service·Api) 실제 실행 비교")
    print("=" * 78)
    for s in res["per_screen"]:
        if s["status"] != "OK":
            print(f"  {s['screen_id']:<10} {s['status']:<12} {s.get('reason')}")
            continue
        per = " · ".join(
            f"{k} {v['matched']}/{v['cases']}" for k, v in sorted((s.get("by_layer") or {}).items()))
        print(f"  {s['screen_id']:<10} 일치 {s['matched']}/{s['cases']} ({s['match_rate']:.0%})"
              f"  [{per}]")
        if s.get("api_layer_skipped"):
            print(f"      ! Api 계층 비교 생략(P/Api 컴파일 실패) — Service 계층만 측정")
        for r in s["results"]:
            if not r["match"]:
                print(f"      X {r['method']} (rows={r['rows']})")
                print(f"          AS-IS: {r['asis'][:90]}")
                print(f"          TO-BE: {r['tobe'][:90]}")
    print("-" * 78)
    label = {"SERVICE": "F 계층(업무 로직)", "API": "Api 계층(HTTP/직렬화)"}
    for name, b in sorted((res.get("by_layer") or {}).items()):
        print(f"  {label.get(name, name):<22} {b['matched']:>3}/{b['cases']:<3} "
              f"({b['match_rate']:.0%})  · 화면 {b['screens']}개")
    if res["match_rate"] is not None:
        print(f"  {'합계':<22} {res['matched']:>3}/{res['cases']:<3} ({res['match_rate']:.1%})"
              f"  · 화면 {res['screens_executed']}/{res['screens_total']} 실행")
    print(f"\n  범위: {res['scope_note']}")
    if args.json:
        Path(args.json).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON 저장: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
