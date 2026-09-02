package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla017Service {

    @Autowired
    private Pla017Store store;

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
		// FIXME(원본 버그): 원본은 getRecordSet("AUTH_LIST") 및 IRecordSet#getRecordCount()에 의존하나, 포팅 대상 타입/구조가 원본에 선언되어 있지 않음.
		Object rs = duResult.get("AUTH_LIST");
		if (((com.ntels.ncf.core.dataset.IRecordSet) rs).getRecordCount() > 0) {
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
public Map<String, Object> fPLA017QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<>();
	try {
		// FIXME(원본 버그): 원본은 requestData 변수를 사용하지만 선언되어 있지 않음
		Map<String, Object> paramMap = requestData.getFieldMap();

		// FIXME(원본 버그): 원본은 requestData.getField(...) 를 사용하지만 requestData 선언이 없음
		String strTGT_CD = requestData.getField("TGT_CD");
		String strSearchDtFrom = requestData.getField("SEARCH_DT_FROM");
		String strSearchDtTo = requestData.getField("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		requestData.putFieldMap(paramMap);

		// FIXME(원본 버그): 원본은 onlineCtx 변수를 사용하지만 선언되어 있지 않음
		Object rs = store.dPLA01701(requestData, onlineCtx).getRecordSet("MAIN_LIST");
		responseData.put("MAIN_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA017QrySelectDetail(Map<String, Object> request) {
    Map<String, Object> responseData = new HashMap<>();
    try {
        Map<String, Object> paramMap = request;

        String strTGT_CD = (String) request.get("TGT_CD");
        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("METRIC_TYPE", "TIME_MIN");
        request.putAll(paramMap);

        // FIXME(원본 버그): 원본은 onlineCtx 미선언 상태로 du.dPLA01702(requestData, onlineCtx)를 호출함
        Object rs = store.dPLA01702(request).get("DETAIL_LIST");
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