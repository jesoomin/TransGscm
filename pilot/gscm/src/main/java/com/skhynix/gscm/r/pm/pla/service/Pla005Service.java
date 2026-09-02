package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla005Service {

    @Autowired
    private Pla005Store store;

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
		// FIXME(원본 버그): 원본은 getRecordSet("AUTH_LIST")의 반환형을 IRecordSet으로 가정하는 NEXCORE 의존 코드였음. 프레임워크 제거 후에도 구조를 확정할 수 없어 그대로 의미만 이식.
		Object rs = duResult.get("AUTH_LIST");
		// FIXME(원본 버그): 원본은 rs.getRecordCount() > 0 로 판단했으나, rs의 구체 타입이 원본 프레임워크 타입(IRecordSet)에 의존하여 여기서는 동일 컴파일 형태로 유지 불가.
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
public Map<String, Object> fPLA005QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<String, Object>();
	try{
		Map<String,Object> paramMap = request;

		String strTGT_CD        = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo   = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap); 를 호출하지만 Spring Map 요청 객체로는 동일 API가 없음. 원본 로직 유지 차원에서 request Map 자체를 직접 수정한 상태로 둠.

		Map<String, Object> storeResult = store.dPLA00501(request);
		Object rs = storeResult.get("MAIN_LIST");
		responseData.put("MAIN_LIST", rs);
	} catch (BizRuntimeException be){
		throw be;
	} catch (Exception e){
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA005QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "WGT");
		// FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 동작을 그대로 유지해야 하나, NEXCORE 의존 제거 조건에 따라 request Map 자체를 사용함

		Object rs = store.dPLA00502(request).get("DETAIL_LIST");
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