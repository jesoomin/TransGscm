"""규칙 기반 위임 메서드가 원본 이름을 그대로 유지하는지 지킨다.

예전에는 D 메서드명 기준으로 개명했다(`fHistoryQry` -> `historyqry`). 그 개명의 이유였던
DTO 타입명 파생이 사라진 뒤에도 규칙만 남아, LLM이 포팅한 Api가 원본 이름으로 부르는
`service.fHistoryQry(...)`를 Service가 갖고 있지 않아 화면마다 UNRESOLVED_SERVICE_CALL이
났다(평가 세트 5화면에서 8건). 이름 규칙이 다시 갈라지면 여기서 먼저 걸린다.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "chatui"))

from chatui import skeleton_gen  # noqa: E402


P_SRC = """
public class PZZT001 extends BaseBizUnit {
    public IDataSet pZZT00101(IDataSet requestData, IOnlineContext onlineCtx){
        FZZT001 fu = (FZZT001) lookupFunctionUnit(FZZT001.class);
        return fu.fHistoryQry(requestData, onlineCtx);
    }
}
"""

# detect_simple_delegation_spec가 인식하는 정확한 모양이어야 RULE_BASED_DELEGATION 경로를 탄다
# (배관 패턴으로 새면 개명이 일어나지 않아 이 테스트가 아무것도 지키지 못한다).
F_SRC = """
public class FZZT001 extends BaseBizUnit {
    public IDataSet fHistoryQry(IDataSet requestData, IOnlineContext onlineCtx){
        IDataSet responseData = new DataSet();
        try{
            DZZT001 du = (DZZT001) lookupDataUnit(DZZT001.class);
            IRecordSet rs = du.dHistoryQry(requestData, onlineCtx).getRecordSet("HIST_LIST");
            responseData.putRecordset("HIST_LIST", rs);
        }catch(BizException be){ throw be; }
        catch(Exception e){ throw new BizException("E0052", e); }
        return responseData;
    }
}
"""

D_SRC = """
public class DZZT001 extends BaseBizUnit {
    public IDataSet dHistoryQry(IDataSet requestData, IOnlineContext onlineCtx){
        return dbSelect("S001", requestData.getFieldMap(), onlineCtx);
    }
}
"""

XSQL_SRC = """<sqlMap namespace="DZZT001">
  <select id="S001" parameterClass="map" resultClass="java.util.HashMap">
    SELECT 1 FROM DUAL
  </select>
</sqlMap>
"""


def _generate():
    return skeleton_gen.generate_skeletons(
        "ZZT001", "pm", "pla", P_SRC, F_SRC, D_SRC, None, None, XSQL_SRC
    )


def _service_methods(result) -> set[str]:
    for name, content in result.files.items():
        if "Service" in name:
            return set(re.findall(r"public\s+[\w<>,\s\[\]]+?\s+(\w+)\s*\(", content))
    raise AssertionError("Service 파일이 생성되지 않았다")


def test_rule_based_delegation_keeps_the_original_method_name() -> None:
    methods = _service_methods(_generate())
    assert "fHistoryQry" in methods, f"원본 이름이 사라졌다: {sorted(methods)}"
    assert "historyqry" not in methods, "옛 개명 규칙이 되살아났다"


def test_api_calls_the_name_the_service_actually_defines() -> None:
    """생성된 Api의 service.* 호출이 Service에 실재하는 이름이어야 한다."""
    result = _generate()
    defined = _service_methods(result)
    called = set()
    for name, content in result.files.items():
        if "Api" in name:
            called |= set(re.findall(r"service\.(\w+)\s*\(", content))
    missing = called - defined
    assert not missing, f"Service에 없는 메서드를 Api가 호출한다: {sorted(missing)}"


def test_registry_tobe_name_matches_the_generated_code() -> None:
    """추적 DB에 남는 TO-BE 이름이 실제 생성 코드와 같아야 한다(영향도 조회가 이걸 쓴다)."""
    result = _generate()
    defined = _service_methods(result)
    for m in result.methods:
        if m.get("layer") == "F" and m.get("method_name_tobe"):
            assert m["method_name_tobe"] in defined, (
                f"레지스트리의 TO-BE명 {m['method_name_tobe']}가 생성 코드에 없다"
            )
