package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla039Service {

    @Autowired
    private Pla039Store store;

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
		// FIXME(원본 버그): 원본은 DPLA039 du = (DPLA039) lookupDataUnit(DPLA039.class); 로 DataUnit을 조회했으나, 프레임워크 의존 제거 요구에 따라 store 사용으로만 치환
		java.util.Map<String, Object> _result = store.dAuthCheck(request);
		// FIXME(원본 버그): 원본의 getRecordSet("AUTH_LIST") 동작을 그대로 옮기기 위해 결과 구조를 단정하고 있으나 타입/구조 보장이 없음
		java.util.List rs = (java.util.List) _result.get("AUTH_LIST");
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
public Map<String, Object> fPLA039QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<String, Object>();
	try{
		Map<String,Object> paramMap = request;

		String strTGT_CD        = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo   = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		request.putAll(paramMap);

		Map<String, Object> storeResult = store.dPLA03901(request);
		responseData.put("MAIN_LIST", storeResult.get("MAIN_LIST"));
	} catch (BizRuntimeException be){
		throw be;
	} catch (Exception e){
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA039QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "QTY");
		request.putAll(paramMap);

		// FIXME(원본 버그): 원본은 du.dPLA03902(requestData, onlineCtx).getRecordSet("DETAIL_LIST") 형태로 NEXCORE IDataSet/IOnlineContext에 의존함
		Object rs = store.dPLA03902(request).get("DETAIL_LIST");
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