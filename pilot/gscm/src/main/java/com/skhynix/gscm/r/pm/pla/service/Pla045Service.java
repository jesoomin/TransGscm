package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla045Service {

    @Autowired
    private Pla045Store store;

    // 원본 fCommonCodeQry가 dCommonCodeQry 하나만 호출하고 recordset을 그대로 돌려주는 단순
    // 위임이라(계산/분기 없음) LLM 포팅 없이 규칙 기반으로 바로 옮겼다 - 원본과
    // 다르게 동작한다고 판단되면 사람이 확인할 것.
    public List<CommoncodeqryDto> commoncodeqry(CommoncodeqryDto dto) {
        return store.dCommonCodeQry(dto);
    }

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fAuthCheck(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try{
		Object du = store; // FIXME(원본 포팅): 원본의 DPLA045 du = (DPLA045) lookupDataUnit(DPLA045.class); 프레임워크 의존 제거
		java.util.List rs = (java.util.List) ((java.util.Map) store.dAuthCheck(request)).get("AUTH_LIST");
		if(rs.size() > 0){
			responseData.put("AUTH_YN", "Y");
		}else{
			responseData.put("AUTH_YN", "N");
		}
	} catch (BizRuntimeException be){
		throw be;
	} catch (Exception e){
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
public Map<String, Object> fPLA045QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		request.putAll(paramMap);

		// FIXME(원본 버그): 원본은 getRecordSet("MAIN_LIST")를 호출하지만 Spring Map 기반 포팅에서는 반환 타입/구조가 명확하지 않음. 원본 로직을 그대로 유지하기 위해 동일 키 접근만 이식.
		responseData.put("MAIN_LIST", ((Map<String, Object>) store.dPLA04501(request)).get("MAIN_LIST"));
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA045QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<String, Object>();
	try {
		Map<String, Object> paramMap = request;
		// FIXME(원본 버그): 원본은 requestData.getFieldMap()을 사용하나 requestData가 미선언 상태임. 원본 의도를 유지하여 request를 직접 사용.
		String strTGT_CD = (String) request.get("TGT_CD");
		// FIXME(원본 버그): 원본은 requestData.getField("TGT_CD")를 사용하나 requestData가 미선언 상태임. 원본 의도를 유지하여 request에서 조회.
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "WGT");
		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap)을 호출하나 requestData가 미선언 상태임. Spring Map request 자체에 반영된 상태로 유지.
		Map<String, Object> result = store.dPLA04502(request);
		Object rs = result.get("DETAIL_LIST");
		responseData.put("DETAIL_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // 원본 fExcelDownQry가 dExcelDownQry 하나만 호출하고 recordset을 그대로 돌려주는 단순
    // 위임이라(계산/분기 없음) LLM 포팅 없이 규칙 기반으로 바로 옮겼다 - 원본과
    // 다르게 동작한다고 판단되면 사람이 확인할 것.
    public List<ExceldownqryDto> exceldownqry(ExceldownqryDto dto) {
        return store.dExcelDownQry(dto);
    }

}