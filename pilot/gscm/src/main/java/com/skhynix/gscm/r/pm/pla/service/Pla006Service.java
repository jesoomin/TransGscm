package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla006Service {

    @Autowired
    private Pla006Store store;

    // 원본 fCommonCodeQry가 dCommonCodeQry 하나만 호출하고 recordset을 그대로 돌려주는 단순
    // 위임이라(계산/분기 없음) LLM 포팅 없이 규칙 기반으로 바로 옮겼다 - 원본과
    // 다르게 동작한다고 판단되면 사람이 확인할 것.
    public List<CommoncodeqryDto> commoncodeqry(CommoncodeqryDto dto) {
        return store.dCommonCodeQry(dto);
    }

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fAuthCheck(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<>();
    try {
        Object du = store;
        // FIXME(원본 버그): 원본은 DPLA006 du = (DPLA006) lookupDataUnit(DPLA006.class); 를 사용하나, 프레임워크 의존 제거 요구에 따라 store 사용으로 치환하면서 타입/선언이 원본과 정확히 일치하지 않음
        java.util.Map<String, Object> result = store.dAuthCheck(request);
        java.util.List<?> rs = (java.util.List<?>) result.get("AUTH_LIST");
        if (rs.size() > 0) {
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
public Map<String, Object> fPLA006QrySelectMainList(Map<String, Object> request) {
    Map<String, Object> responseData = new HashMap<>();
    try {
        Map<String, Object> paramMap = request;

        String strTGT_CD = (String) request.get("TGT_CD");
        String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
        String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
        paramMap.put("SEARCH_DT_TO", strSearchDtTo);
        request.putAll(paramMap);

        // FIXME(원본 버그): 원본은 onlineCtx 미선언 상태로 du.dPLA00601(requestData, onlineCtx)를 호출함. 프레임워크 의존 제거에 따라 그대로 옮길 수 없어 request만 전달.
        Map<String, Object> storeResult = store.dPLA00601(request);
        responseData.put("MAIN_LIST", storeResult.get("MAIN_LIST"));
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA006QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<String, Object>();
	try {
		Map<String, Object> paramMap = request;
		// FIXME(원본 버그): 원본은 requestData.getFieldMap()를 사용하나 requestData가 미선언 상태임. 원본 그대로 포팅 불가하여 request를 사용함.
		String strTGT_CD = (String) request.get("TGT_CD");
		// FIXME(원본 버그): 원본은 requestData.getField("TGT_CD")를 사용하나 requestData가 미선언 상태임. 원본 그대로 포팅 불가하여 request에서 직접 조회함.
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "SCORE");
		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap)를 호출하나 requestData가 미선언 상태임. 원본 그대로 포팅 불가하여 request에 반영된 상태로 간주함.

		Map<String, Object> result = store.dPLA00602(request);
		// FIXME(원본 버그): 원본은 du.dPLA00602(requestData, onlineCtx).getRecordSet("DETAIL_LIST")를 사용하나 requestData/onlineCtx가 미선언 상태임. 원본 그대로 포팅 불가하여 store.dPLA00602(request) 결과에서 DETAIL_LIST를 조회함.
		Object rs = result.get("DETAIL_LIST");
		responseData.put("DETAIL_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

}