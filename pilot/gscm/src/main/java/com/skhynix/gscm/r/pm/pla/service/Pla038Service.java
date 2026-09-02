package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla038Service {

    @Autowired
    private Pla038Store store;

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
        IRecordSet rs = store.dAuthCheck(request).getRecordSet("AUTH_LIST");
        if (rs.getRecordCount() > 0) {
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
public Map<String, Object> fPLA038QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		// FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 request/requestData가 동일 객체로 보이며 실질적으로 불필요하나, 프레임워크 의존 제거로 인해 그대로 호출할 수 없음

		Map<String, Object> storeResult = store.dPLA03801(request);
		responseData.put("MAIN_LIST", storeResult.get("MAIN_LIST"));
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA038QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<String, Object>();
	try {
		Map<String, Object> paramMap = request;
		// FIXME(원본 버그): 원본은 requestData.getFieldMap()을 사용하나 requestData가 미선언 상태임. 원본 그대로 포팅 불가하여 request를 사용.
		String strTGT_CD = (String) request.get("TGT_CD");
		// FIXME(원본 버그): 원본은 requestData.getField("TGT_CD")를 사용하나 requestData가 미선언 상태임. 원본 그대로 포팅 불가하여 request에서 조회.
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "REMARK_CD");
		request.putAll(paramMap);
		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap)을 사용하나 requestData가 미선언 상태임. 원본 그대로 포팅 불가하여 request.putAll(paramMap)로만 치환.
		Object rs = store.dPLA03802(request).get("DETAIL_LIST");
		responseData.put("DETAIL_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

}