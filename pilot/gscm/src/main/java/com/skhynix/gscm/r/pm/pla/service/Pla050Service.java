package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla050Service {

    @Autowired
    private Pla050Store store;

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
		@SuppressWarnings("unchecked")
		Map<String, Object> duResult = (Map<String, Object>) store.dAuthCheck(request);
		// FIXME(원본 버그): 원본은 getRecordSet("AUTH_LIST")와 getRecordCount()에 의존하므로, 프레임워크 제거 후에도 동일 로직을 유지하기 위해 AUTH_LIST를 RecordSet/Collection 형태로 간주한다.
		Object rs = duResult.get("AUTH_LIST");
		int recordCount;
		if (rs instanceof java.util.Collection) {
			recordCount = ((java.util.Collection<?>) rs).size();
		} else if (rs instanceof java.util.Map) {
			recordCount = ((java.util.Map<?, ?>) rs).size();
		} else if (rs != null && rs.getClass().isArray()) {
			recordCount = java.lang.reflect.Array.getLength(rs);
		} else {
			recordCount = 0;
		}

		if (recordCount > 0) {
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
public Map<String, Object> fPLA050QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		// FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 NEXCORE 의존으로 제거되었으나, request와 paramMap이 동일 객체라 그대로 유지된 것으로 간주함.

		// FIXME(원본 버그): 원본의 onlineCtx 미선언/프레임워크 의존. 그대로 보정하지 말라는 요구에 따라 제거함.
		Map<String, Object> duResult = store.dPLA05001(request);
		responseData.put("MAIN_LIST", duResult.get("MAIN_LIST"));
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA050QrySelectDetail(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<>();
    try {
        Map<String, Object> paramMap = request;

        String strTGT_CD = (String) request.get("TGT_CD");
        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("METRIC_TYPE", "AMT");
        // FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 NEXCORE IDataSet 의존 로직이며, 여기서는 request 자체를 paramMap으로 사용하므로 별도 반영 코드가 없음.

        Map<String, Object> storeResult = store.dPLA05002(request);
        Object rs = storeResult.get("DETAIL_LIST");
        responseData.put("DETAIL_LIST", rs);
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

}