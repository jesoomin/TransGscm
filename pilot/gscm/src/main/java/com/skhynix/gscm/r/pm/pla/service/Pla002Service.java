package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla002Service {

    @Autowired
    private Pla002Store store;

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
		// FIXME(원본 버그): 원본은 DPLA002 du = (DPLA002) lookupDataUnit(DPLA002.class); 를 사용했으나 프레임워크 의존 제거 요구에 따라 store 필드 호출로 치환
		Object du = store;
		// FIXME(원본 버그): 원본의 requestData, onlineCtx 는 미선언 변수이지만 원본 그대로 유지해야 함
		Object authResult = store.dAuthCheck(requestData, onlineCtx);
		// FIXME(원본 버그): 원본은 IDataSet#getRecordSet("AUTH_LIST") 의존 로직이며, 프레임워크 제거 요구에 따라 동일 의미로만 이식
		Object rs = ((Map<String, Object>) authResult).get("AUTH_LIST");
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
public Map<String, Object> fPLA002QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try{
		Map<String,Object> paramMap = request;

		String strTGT_CD        = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo   = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		// FIXME(원본 버그): requestData.putFieldMap(paramMap); 원본의 requestData는 Spring 포팅 대상에서 미존재하며, 실질적으로 request(paramMap) 자체를 사용함

		Map<String, Object> storeResponse = store.dPLA00201(request);
		Object rs = storeResponse.get("MAIN_LIST");
		responseData.put("MAIN_LIST", rs);
	} catch (BizRuntimeException be){
		throw be;
	} catch (Exception e){
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA002QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<String, Object>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "AMT");
		request.putAll(paramMap);

		// FIXME(원본 버그): 원본은 getRecordSet("DETAIL_LIST")를 호출하나, 포팅 대상 타입/반환형이 명확하지 않음
		Object rs = store.dPLA00202(request).get("DETAIL_LIST");
		responseData.put("DETAIL_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

}