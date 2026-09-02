package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla049Service {

    @Autowired
    private Pla049Store store;

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
		java.util.Map<String, Object> duResult = store.dAuthCheck(request);
		// FIXME(원본 버그): 원본은 getRecordSet("AUTH_LIST")의 반환 타입(IRecordSet)과 내부 구조에 프레임워크 의존이 있으나, 이를 그대로 포팅할 수 없어 최소한의 Map/List 접근 형태로만 치환함.
		Object authList = duResult.get("AUTH_LIST");
		if (((java.util.List<?>) authList).size() > 0) {
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
public Map<String, Object> fPLA049QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		// FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 NEXCORE IDataSet 전용 동작이며, Spring Map 포팅에서는 request 자체가 동일 객체이므로 별도 반영 로직이 없음.

		Object rs = store.dPLA04901(request).get("MAIN_LIST");
		responseData.put("MAIN_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA049QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try {
		Map<String, Object> paramMap = request;
		String strTGT_CD = (String) request.get("TGT_CD");
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "QTY");
		request.putAll(paramMap);

		// FIXME(원본 버그): 원본은 du.dPLA04902(requestData, onlineCtx).getRecordSet("DETAIL_LIST") 형태로 NEXCORE IDataSet/IRecordSet에 의존함. 동일 로직만 포팅하며 타입/반환구조는 원본 그대로 가정.
		Object rs = store.dPLA04902(request).get("DETAIL_LIST");
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