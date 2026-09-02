package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla016Service {

    @Autowired
    private Pla016Store store;

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
		Map<String, Object> duResult = store.dAuthCheck(request);
		// FIXME(원본 버그): 원본은 getRecordSet("AUTH_LIST") 및 IRecordSet.getRecordCount()에 의존하나, 프레임워크 제거 지시에 따라 그대로 포팅하면서 해당 구조/타입은 보정하지 않음
		Object rs = duResult.get("AUTH_LIST");
		if (((com.ntels.ncf.core.dataset.IRecordSet) rs).getRecordCount() > 0) {
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
public Map<String, Object> fPLA016QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		// FIXME(원본 버그): requestData.putFieldMap(paramMap); 원본의 requestData 미선언 상태를 그대로 유지할 수 없어 request 맵 갱신으로 대체

		Map<String, Object> storeResult = store.dPLA01601(request);
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
public Map<String, Object> fPLA016QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<>();
	try {
		Map<String, Object> paramMap = request; // FIXME(원본 버그): 원본은 requestData.getFieldMap()을 사용하나 requestData가 미선언 상태임
		String strTGT_CD = (String) request.get("TGT_CD"); // FIXME(원본 버그): 원본은 requestData.getField("TGT_CD")를 사용하나 requestData가 미선언 상태임
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "SCORE");
		// FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 requestData 미선언으로 인해 그대로 이식 불가
		Object rs = store.dPLA01602(request).get("DETAIL_LIST"); // FIXME(원본 버그): 원본은 du.dPLA01602(requestData, onlineCtx).getRecordSet("DETAIL_LIST")를 호출하나 requestData/onlineCtx가 미선언 상태임
		responseData.put("DETAIL_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

}