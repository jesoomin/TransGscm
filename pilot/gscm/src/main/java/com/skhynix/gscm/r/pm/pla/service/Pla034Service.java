package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla034Service {

    @Autowired
    private Pla034Store store;

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
		// FIXME(원본 버그): 원본은 DPLA034 du = (DPLA034) lookupDataUnit(DPLA034.class); 를 사용했으나 프레임워크 의존 제거 요구에 따라 store 호출로 포팅
		Object result = store.dAuthCheck(request);
		// FIXME(원본 버그): 원본의 getRecordSet("AUTH_LIST")/IRecordSet 의존을 그대로 유지할 수 없어 최소 치환만 수행
		java.util.List<?> rs = null;
		if (result instanceof java.util.Map) {
			Object authList = ((java.util.Map<?, ?>) result).get("AUTH_LIST");
			if (authList instanceof java.util.List) {
				rs = (java.util.List<?>) authList;
			}
		}
		if (rs != null && rs.size() > 0) {
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
public Map<String, Object> fPLA034QrySelectMainList(Map<String, Object> request) {
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

        // FIXME(원본 버그): 원본은 store.dPLA03401(requestData, onlineCtx).getRecordSet("MAIN_LIST") 형태로 NEXCORE IDataSet/IOnlineContext 및 getRecordSet에 의존함
        Object rs = store.dPLA03401(request);
        responseData.put("MAIN_LIST", rs);
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA034QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<>();
	try {
		// FIXME(원본 버그): 원본은 requestData.getFieldMap() / getField() / putFieldMap()을 사용하나 requestData 변수가 선언되어 있지 않음
		Map<String, Object> paramMap = requestData.getFieldMap();

		// FIXME(원본 버그): 원본은 requestData 변수가 미선언 상태임
		String strTGT_CD = requestData.getField("TGT_CD");
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "CNT");

		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap)을 호출하나 requestData 변수가 선언되어 있지 않음
		requestData.putFieldMap(paramMap);

		// FIXME(원본 버그): 원본은 onlineCtx 변수를 사용하나 선언되어 있지 않음
		Object rs = store.dPLA03402(requestData, onlineCtx).getRecordSet("DETAIL_LIST");
		responseData.put("DETAIL_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

}