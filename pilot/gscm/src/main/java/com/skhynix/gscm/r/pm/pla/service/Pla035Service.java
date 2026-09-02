package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla035Service {

    @Autowired
    private Pla035Store store;

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
		// FIXME(원본 버그): 원본은 DPLA035 du = (DPLA035) lookupDataUnit(DPLA035.class); 를 사용했으나 프레임워크 의존 제거 요구에 따라 store 호출로만 포팅
		// FIXME(원본 버그): 원본은 requestData, onlineCtx 변수를 사용하나 메서드 본문 내 미선언 상태임. 요청사항에 따라 의미만 유지하여 request로 치환
		Object result = store.dAuthCheck(request);
		// FIXME(원본 버그): 원본의 IDataSet/IRecordSet 의존을 제거하면서 getRecordSet("AUTH_LIST"), getRecordCount() 로직을 그대로 유지하기 어려움
		// FIXME(원본 버그): 아래는 store 반환값이 Map이며 "AUTH_LIST" 키에 java.util.Collection 또는 배열이 들어있다고 가정한 최소 포팅
		Object authList = ((Map<String, Object>) result).get("AUTH_LIST");
		int recordCount = 0;
		if (authList instanceof java.util.Collection) {
			recordCount = ((java.util.Collection<?>) authList).size();
		} else if (authList != null && authList.getClass().isArray()) {
			recordCount = java.lang.reflect.Array.getLength(authList);
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
public Map<String, Object> fPLA035QrySelectMainList(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<String, Object>();
    try {
        Map<String, Object> paramMap = request;

        String strTGT_CD = (String) request.get("TGT_CD");
        String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
        String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
        paramMap.put("SEARCH_DT_TO", strSearchDtTo);
        request.putAll(paramMap);

        // FIXME(원본 버그): 원본은 du.dPLA03501(requestData, onlineCtx).getRecordSet("MAIN_LIST") 형태이며, onlineCtx/requestData 기반 반환 타입 및 getRecordSet 호출 구조가 Spring Map 기반 포팅과 직접 호환되지 않을 수 있음.
        Object rs = store.dPLA03501(request).get("MAIN_LIST");
        responseData.put("MAIN_LIST", rs);
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA035QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try{
		Map<String,Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "WGT");
		// FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 NEXCORE IDataSet 의존 로직이며, 현재는 request 자체를 그대로 사용하므로 별도 반영 코드 없음.

		Object rs = store.dPLA03502(request).get("DETAIL_LIST");
		responseData.put("DETAIL_LIST", rs);
	} catch (BizRuntimeException be){
		throw be;
	} catch (Exception e){
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