package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla011Service {

    @Autowired
    private Pla011Store store;

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
		Object du = store; // FIXME(원본 버그): 원본은 DPLA011 du = (DPLA011) lookupDataUnit(DPLA011.class); 이나 프레임워크 의존 제거로 직접 치환 불가
		Object result = store.dAuthCheck(request); // FIXME(원본 버그): 원본은 du.dAuthCheck(requestData, onlineCtx) 호출이며 requestData, onlineCtx가 미선언 상태였음
		Object rs = null;
		if (result instanceof java.util.Map) {
			rs = ((java.util.Map<?, ?>) result).get("AUTH_LIST");
		} // FIXME(원본 버그): 원본은 getRecordSet("AUTH_LIST") 사용, 반환 타입/구조가 불명확하여 그대로 대응 불가

		int recordCount;
		if (rs instanceof java.util.Collection) {
			recordCount = ((java.util.Collection<?>) rs).size();
		} else if (rs != null && rs.getClass().isArray()) {
			recordCount = java.lang.reflect.Array.getLength(rs);
		} else {
			recordCount = 0; // FIXME(원본 버그): 원본은 IRecordSet#getRecordCount() 호출
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
public Map<String, Object> fPLA011QrySelectMainList(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<>();
    try {
        Map<String, Object> paramMap = request;

        String strTGT_CD = (String) request.get("TGT_CD");
        String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
        String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
        paramMap.put("SEARCH_DT_TO", strSearchDtTo);
        // FIXME(원본 버그): requestData.putFieldMap(paramMap); 원본의 requestData가 본문에 선언되어 있지 않음. 원본 로직 그대로 유지 불가.

        Map<String, Object> storeResult = store.dPLA01101(request);
        responseData.put("MAIN_LIST", storeResult.get("MAIN_LIST"));
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA011QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try {
		Map<String, Object> paramMap = request;
		// FIXME(원본 버그): 원본은 requestData.getFieldMap()을 사용하나 requestData는 미선언 상태였음. 원본 그대로 의도만 유지하여 request를 사용.
		String strTGT_CD = (String) request.get("TGT_CD");
		// FIXME(원본 버그): 원본은 requestData.getField("TGT_CD")를 사용하나 requestData는 미선언 상태였음.
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "QTY");
		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap)를 호출하나 requestData는 미선언 상태였음. request(Map) 자체에 반영된 것으로 유지.
		Map<String, Object> storeResponse = store.dPLA01102(request);
		Object rs = storeResponse.get("DETAIL_LIST");
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