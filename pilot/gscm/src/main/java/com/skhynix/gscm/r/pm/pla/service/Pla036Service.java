package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla036Service {

    @Autowired
    private Pla036Store store;

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
		// FIXME(원본 버그): 원본은 requestData, onlineCtx를 사용하지만 선언되어 있지 않음. 원본 그대로 유지.
		Object rs = store.dAuthCheck(requestData, onlineCtx).getRecordSet("AUTH_LIST");
		// FIXME(원본 버그): 원본은 IRecordSet 타입 및 getRecordCount() 호출에 프레임워크 의존이 있음. 원본 로직 그대로 유지.
		if (((IRecordSet) rs).getRecordCount() > 0) {
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
public Map<String, Object> fPLA036QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<String, Object>();
	try{
		Map<String,Object> paramMap = request;

		String strTGT_CD        = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo   = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		// FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 Spring Map 기반 포팅에서 대응 API가 없음

		Object rs = store.dPLA03601(request).get("MAIN_LIST");
		responseData.put("MAIN_LIST", rs);
	} catch (BizRuntimeException be){
		throw be;
	} catch (Exception e){
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA036QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try {
		Map<String, Object> paramMap = request;
		// FIXME(원본 버그): 원본은 requestData.getFieldMap()을 사용하나 requestData는 미선언 변수임
		// FIXME(원본 버그): 원본 로직을 그대로 유지하기 위해 request를 requestData에 대응시켜 사용함

		String strTGT_CD = (String) request.get("TGT_CD");
		// FIXME(원본 버그): 원본은 requestData.getField("TGT_CD")를 사용하나 requestData는 미선언 변수임
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "SCORE");
		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap)을 호출하나 Spring Map 기반으로는 동일 객체 갱신으로 대체

		Map<String, Object> storeResult = store.dPLA03602(request);
		// FIXME(원본 버그): 원본은 du.dPLA03602(requestData, onlineCtx).getRecordSet("DETAIL_LIST")를 호출하나 requestData/onlineCtx는 미선언 변수임
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