package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla032Service {

    @Autowired
    private Pla032Store store;

    // 원본 fCommonCodeQry가 dCommonCodeQry 하나만 호출하고 recordset을 그대로 돌려주는 단순
    // 위임이라(계산/분기 없음) LLM 포팅 없이 규칙 기반으로 바로 옮겼다 - 원본과
    // 다르게 동작한다고 판단되면 사람이 확인할 것.
    public List<CommoncodeqryDto> commoncodeqry(CommoncodeqryDto dto) {
        return store.dCommonCodeQry(dto);
    }

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fAuthCheck(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<String, Object>();
    try {
        java.util.Map<String, Object> authCheckResult = store.dAuthCheck(request);
        // FIXME(원본 버그): 원본은 getRecordSet("AUTH_LIST") 및 IRecordSet/getRecordCount()에 의존하므로, 프레임워크 제거 후에도 동일 로직을 그대로 유지하기 어렵다.
        Object rs = authCheckResult.get("AUTH_LIST");
        // FIXME(원본 버그): 원본의 IRecordSet rs.getRecordCount() 호출을 그대로 옮길 수 없어 컴파일 가능한 형태로만 치환했다.
        if (((java.util.List<?>) rs).size() > 0) {
            responseData.put("AUTH_YN", "Y");
        } else {
            responseData.put("AUTH_YN", "N");
        }
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

    // 원본 fHistoryQry가 dHistoryQry 하나만 호출하고 recordset을 그대로 돌려주는 단순
    // 위임이라(계산/분기 없음) LLM 포팅 없이 규칙 기반으로 바로 옮겼다 - 원본과
    // 다르게 동작한다고 판단되면 사람이 확인할 것.
    public List<HistoryqryDto> historyqry(HistoryqryDto dto) {
        return store.dHistoryQry(dto);
    }

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA032QrySelectMainList(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<>();
    try {
        Map<String, Object> paramMap = request;

        String strTGT_CD = (String) request.get("TGT_CD");
        String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
        String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
        paramMap.put("SEARCH_DT_TO", strSearchDtTo);
        // FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 NEXCORE IDataSet 전용 동작이며, request는 이미 Map이므로 그대로 반영만 유지

        // FIXME(원본 버그): 원본의 onlineCtx는 미이식 상태이며 Spring 포팅 요구에 따라 제거됨
        Map<String, Object> storeResult = store.dPLA03201(request);
        Object rs = storeResult.get("MAIN_LIST");
        responseData.put("MAIN_LIST", rs);
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA032QrySelectDetail(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<>();
    try {
        Map<String, Object> paramMap = request;

        String strTGT_CD = (String) request.get("TGT_CD");
        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("METRIC_TYPE", "AMT");
        // FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 동작을 그대로 유지할 프레임워크 객체가 없음

        Object rs = store.dPLA03202(request).get("DETAIL_LIST");
        responseData.put("DETAIL_LIST", rs);
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

}