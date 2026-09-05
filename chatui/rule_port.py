"""F BizUnit 메서드 중 **분기·계산이 전혀 없는 배관 패턴**을 규칙 기반으로 포팅한다.

`detect_simple_delegation`(skeleton_gen.py)은 "D 하나를 부르고 recordset을 그대로 반환"하는
가장 좁은 모양만 잡는다. 실제 소스를 보면 그보다 조금 넓지만 여전히 **기계적인** 모양이 자주 있다:

    IDataSet responseData = new DataSet();
    try{
        DXXX du = (DXXX) lookupDataUnit(DXXX.class);
        Map<String,Object> paramMap = requestData.getFieldMap();
        String strTGT_CD = requestData.getField("TGT_CD");   // 0..n
        paramMap.put("TGT_CD", strTGT_CD);                    // 같은 키 재삽입 = no-op
        paramMap.put("METRIC_TYPE", "QTY");                   // 리터럴 기본값
        requestData.putFieldMap(paramMap);
        IRecordSet rs = du.dXXX(requestData, onlineCtx).getRecordSet("DETAIL_LIST");
        responseData.putRecordset("DETAIL_LIST", rs);
    } catch (BizRuntimeException be){ throw be; }
      catch (Exception e){ throw new BizRuntimeException("E0052", e); }
    return responseData;

이건 **파라미터 전달 + 단일 조회 + 레코드셋 반환**뿐이라 LLM이 필요 없다. `getField` 후 같은
키로 `put`하는 건 `paramMap`이 이미 `getFieldMap()` 결과라서 값이 그대로 들어 있으므로 no-op이고,
의미가 있는 건 **리터럴 기본값 put**뿐이다.

**의도적으로 잡지 않는 것 — 여기가 이 모듈의 안전선이다.**
분기(`if`/`switch`)·반복(`for`/`while`)·산술 연산이 하나라도 있으면 **잡지 않는다.** 예를 들어
`fAuthCheck`는 `rs.getRecordCount() > 0`으로 갈라지는데, 이건 배관이 아니라 업무 규칙이므로
LLM 포팅 대상으로 남긴다. 규칙 기반 처리 비중을 올리려고 업무 로직까지 규칙으로 밀어내면
"결정론적으로 가능한 것만 규칙으로"라는 원칙이 뒤집힌다 - 비중은 결과지 목표가 아니다.

키 이름이 바뀌는 `getField("A")` → `put("B", ...)`도 잡지 않는다(값 재배치는 의미 변경일 수 있음).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# 본문에 이게 하나라도 있으면 배관이 아니다 - 업무 로직으로 보고 LLM에 넘긴다.
_CONTROL_FLOW_RE = re.compile(r"\b(if|else|for|while|switch|case|do)\s*[({:]")
_ARITHMETIC_RE = re.compile(r"[^=!<>+\-*/]\s[+\-*/%]\s[^=]")

_LOOKUP_RE = re.compile(r"\(\s*(D\w+)\s*\)\s*lookupDataUnit\s*\(")
_D_CALL_RE = re.compile(
    r"\b\w+\s*\.\s*(?P<dmethod>d\w+)\s*\([^)]*\)\s*\.\s*getRecordSet\s*\(\s*\"(?P<rsin>\w+)\"\s*\)"
)
_PUT_RS_RE = re.compile(r"putRecordset\s*\(\s*\"(?P<rsout>\w+)\"\s*,")
_GETFIELD_RE = re.compile(r"(\w+)\s*=\s*\w+\s*\.\s*getField\s*\(\s*\"(?P<key>\w+)\"\s*\)")
_PUT_VAR_RE = re.compile(r"paramMap\s*\.\s*put\s*\(\s*\"(?P<key>\w+)\"\s*,\s*(?P<var>\w+)\s*\)")
_PUT_LIT_RE = re.compile(r"paramMap\s*\.\s*put\s*\(\s*\"(?P<key>\w+)\"\s*,\s*\"(?P<val>[^\"]*)\"\s*\)")


@dataclass
class PassthroughSpec:
    """규칙 기반 포팅이 가능한 배관 메서드의 명세."""
    d_method: str
    recordset: str
    literal_params: list[tuple[str, str]] = field(default_factory=list)


def detect_passthrough_query(f_body: str,
                             known_d_methods: set[str] | None = None) -> PassthroughSpec | None:
    """배관 패턴이면 명세를, 아니면 None을 돌려준다. 조금이라도 애매하면 None이다.

    `known_d_methods`를 주면 **호출 대상이 실재할 때만** 규칙을 적용한다. 규칙 기반 생성은
    `store.dXXX(param)`을 그대로 찍어내는데, 원본이 없는 메서드를 부르고 있으면(원본 오타 등)
    규칙은 유효한 코드를 만들 수 없다 - 전제가 깨진 것이므로 규칙이 그 메서드를 맡으면 안 된다.
    이때는 None을 돌려 LLM 포팅 경로로 넘긴다. LLM 경로에는 실재하는 Store 메서드 목록이
    주입되고 검증-수리 루프도 걸려 있어서 고칠 여지가 있다(실측: 주입 결함 dPLA08710이
    규칙 경로로 새면 수리 없이 BLOCKER로 남았고, LLM 경로로 보내면 1라운드에 해소됐다).
    """
    body = f_body.strip()
    if not body:
        return None

    # 1) 분기·반복·산술이 있으면 업무 로직 - 잡지 않는다.
    if _CONTROL_FLOW_RE.search(body) or _ARITHMETIC_RE.search(body):
        return None

    # 2) D 계층 조회가 정확히 1건이어야 한다(여러 개면 조합 로직일 수 있다).
    d_calls = list(_D_CALL_RE.finditer(body))
    if len(d_calls) != 1:
        return None
    d_method = d_calls[0].group("dmethod")
    rs_in = d_calls[0].group("rsin")

    # 다른 형태의 D 호출이 더 있으면(getRecordSet 없이 부르는 등) 안전하게 포기한다.
    if len(re.findall(r"\bdu\s*\.\s*d\w+\s*\(", body)) != 1:
        return None

    # 3) 반환 레코드셋 이름이 입력과 같아야 한다(이름이 바뀌면 의미 변경 가능).
    puts = list(_PUT_RS_RE.finditer(body))
    if len(puts) != 1 or puts[0].group("rsout") != rs_in:
        return None

    # 4) lookupDataUnit이 하나(= D 계층 하나만 씀)여야 한다.
    if len(_LOOKUP_RE.findall(body)) > 1:
        return None

    # 5) 변수 경유 put은 "같은 키를 그대로 다시 넣는" 경우만 허용(no-op).
    var_to_key = {m.group(1): m.group("key") for m in _GETFIELD_RE.finditer(body)}
    for m in _PUT_VAR_RE.finditer(body):
        if var_to_key.get(m.group("var")) != m.group("key"):
            return None  # 키가 바뀌는 재배치 - 사람/LLM이 봐야 한다

    # 6) 규칙의 전제: 호출 대상이 실제로 존재해야 한다.
    if known_d_methods is not None and d_method not in known_d_methods:
        return None

    literals = [(m.group("key"), m.group("val")) for m in _PUT_LIT_RE.finditer(body)]
    return PassthroughSpec(d_method=d_method, recordset=rs_in, literal_params=literals)


def render_passthrough_method(method: str, spec: PassthroughSpec) -> list[str]:
    """배관 메서드의 TO-BE 코드를 생성한다(LLM 미사용).

    `detect_simple_delegation` 경로가 DTO 타입을 쓰는 것과 달리 여기서는 `Map<String,Object>`를
    쓴다 - 리터럴 기본값을 넣어야 해서 맵 조작이 필요하고, LLM 포팅 결과와 시그니처가 같아야
    나중에 둘을 바꿔 껴도 계층 간 참조 검증이 그대로 통과하기 때문이다.
    """
    out = [
        f"    // 규칙 기반 생성(LLM 미사용): 원본 {method}는 파라미터 전달 + {spec.d_method} 단일 조회 +",
        f"    // recordset('{spec.recordset}') 반환뿐이고 분기/계산이 없어 기계적으로 옮겼다.",
        f"    public Map<String, Object> {method}(Map<String, Object> request) {{",
        "        Map<String, Object> param = new HashMap<>(request);",
    ]
    for key, val in spec.literal_params:
        out.append(f"        param.put(\"{key}\", \"{val}\");  // 원본의 고정값")
    out += [
        "        Map<String, Object> result = store." + spec.d_method + "(param);",
        "        Map<String, Object> response = new HashMap<>();",
        # 원본은 `du.dXxx(...).getRecordSet("NAME")`으로 **레코드셋을 꺼내서** 담는다. 여기서
        # Store 반환값을 통째로 담으면 한 겹 더 감싸져 원본과 다른 모양이 된다 - 실행 하네스
        # (agents/equivalence_test.py)가 AS-IS와 대조하면서 잡아낸 실제 불일치다.
        f"        response.put(\"{spec.recordset}\", result == null ? null "
        f": result.get(\"{spec.recordset}\"));",
        "        return response;",
        "    }",
        "",
    ]
    return out
