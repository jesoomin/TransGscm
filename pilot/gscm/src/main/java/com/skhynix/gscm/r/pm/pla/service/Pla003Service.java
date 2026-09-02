package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla003Service {

    @Autowired
    private Pla003Store store;

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
		// FIXME(원본 버그): 원본은 DPLA003 du = (DPLA003) lookupDataUnit(DPLA003.class); 를 사용했으나 Spring 포팅 요구에 따라 framework 의존 제거 및 store 호출로 변경
		java.util.Map<String, Object> result = store.dAuthCheck(request);
		// FIXME(원본 버그): 원본의 getRecordSet("AUTH_LIST") 구조를 그대로 포팅해야 하나 반환 타입 정보가 없어 컴파일 보장을 할 수 없음
		Object rs = result.get("AUTH_LIST");
		// FIXME(원본 버그): 원본은 IRecordSet rs 및 rs.getRecordCount()를 사용하나 해당 타입/메서드는 framework 의존이므로 그대로 재현 불가
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
public Map<String, Object> fPLA003QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<String, Object>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		// FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap); 호출은 Spring Map 기반 포팅에서 별도 의미가 없어 그대로 반영 불가

		Object rs = store.dPLA00301(request).get("MAIN_LIST");
		responseData.put("MAIN_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA003QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<String, Object>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "RATE");
		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap) 호출로 requestData 전체를 갱신하나, 포팅에서는 request 자체를 직접 수정하는 형태로만 유지됨.

		// FIXME(원본 버그): 원본은 store.dPLA00302(...) 반환값에서 getRecordSet("DETAIL_LIST")를 호출하나, Spring 포팅에서는 프레임워크 의존 제거 지시에 따라 해당 구조를 그대로 표현할 수 없음.
		Object rs = store.dPLA00302(request).get("DETAIL_LIST");
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