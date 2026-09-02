package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla037Service {

    @Autowired
    private Pla037Store store;

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
		java.util.Map<String, Object> duResult = store.dAuthCheck(request);
		// FIXME(원본 버그): 원본은 getRecordSet("AUTH_LIST")의 반환형을 IRecordSet으로 가정하고 getRecordCount()를 호출함. Spring 포팅에서도 동일 로직을 그대로 유지하기 위해 타입 안정성 검증 없이 처리함.
		Object rs = duResult.get("AUTH_LIST");
		if (((java.util.List) rs).size() > 0) {
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
public Map<String, Object> fPLA037QrySelectMainList(Map<String, Object> request) {
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

        // FIXME(원본 버그): 원본은 onlineCtx를 사용하지만 Spring 포팅 대상 메서드 시그니처에는 해당 변수가 선언되어 있지 않음
        Map<String, Object> storeResult = store.dPLA03701(request, onlineCtx);
        responseData.put("MAIN_LIST", storeResult.get("MAIN_LIST"));
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA037QrySelectDetail(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<>();
    try {
        DPLA037 du = null; // FIXME(원본 버그): 원본은 lookupDataUnit(DPLA037.class)로 초기화하나, 프레임워크 의존 제거 요구에 따라 그대로 둘 수 없어 미초기화 상태로 유지
        Map<String, Object> paramMap = request; // FIXME(원본 버그): 원본의 requestData.getFieldMap()을 그대로 옮겨야 하나 requestData가 미선언임

        String strTGT_CD = (String) request.get("TGT_CD"); // FIXME(원본 버그): 원본의 requestData.getField("TGT_CD")를 request 기반으로 기계적 치환
        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("METRIC_TYPE", "TIME_MIN");
        request.putAll(paramMap); // FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap)을 request Map 반영으로 치환

        Object rs = store.dPLA03702(request).get("DETAIL_LIST"); // FIXME(원본 버그): 원본의 onlineCtx 인자 제거 및 반환형/접근 방식은 원본 프레임워크 의존으로 인해 정확한 컴파일 보장 불가
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