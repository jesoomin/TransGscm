package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla020Service {

    @Autowired
    private Pla020Store store;

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
		// FIXME(원본 버그): 원본은 IDataSet#getRecordSet("AUTH_LIST") 반환형인 IRecordSet에 의존한다. 프레임워크 의존 제거만 수행해야 하므로 구체 타입/구조는 원본 그대로 확정할 수 없다.
		Object rs = duResult.get("AUTH_LIST");
		// FIXME(원본 버그): 원본의 rs.getRecordCount() 호출은 IRecordSet 전제이며, 현재 rs의 타입이 미확정이라 그대로 컴파일되지 않을 수 있다.
		if (((IRecordSet) rs).getRecordCount() > 0) {
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
public Map<String, Object> fPLA020QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<>();
	try{
		Map<String,Object> paramMap = request;

		String strTGT_CD        = (String) request.get("TGT_CD");
		String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
		String strSearchDtTo   = (String) request.get("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		request.putAll(paramMap);

		// FIXME(원본 버그): 원본은 du.dPLA02001(requestData, onlineCtx).getRecordSet("MAIN_LIST") 호출에 requestData/onlineCtx 및 getRecordSet 의존이 있음. 프레임워크 의존 제거 요청에 따라 그대로 포팅 불가한 부분만 store 호출 형태로 치환.
		Object rs = store.dPLA02001(request).get("MAIN_LIST");
		responseData.put("MAIN_LIST", rs);
	} catch (BizRuntimeException be){
		throw be;
	} catch (Exception e){
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA020QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<String, Object>();
	try {
		Map<String, Object> paramMap = request;
		// FIXME(원본 버그): 원본은 requestData.getFieldMap()을 사용하지만 requestData가 미선언이다. 원본 의도를 유지해 request를 직접 사용한다.

		String strTGT_CD = (String) request.get("TGT_CD");
		// FIXME(원본 버그): 원본은 requestData.getField("TGT_CD")를 사용하지만 requestData가 미선언이다. 원본 의도를 유지해 request에서 조회한다.

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "AMT");
		request.putAll(paramMap);
		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap)을 호출하지만 requestData가 미선언이다. 원본 의도를 유지해 request에 반영한다.

		Map<String, Object> storeResult = store.dPLA02002(request);
		// FIXME(원본 버그): 원본은 du.dPLA02002(requestData, onlineCtx)를 호출하지만 requestData, onlineCtx가 미선언이다. 프레임워크 의존 제거에 따라 store.dPLA02002(request)로 포팅.

		Object rs = storeResult.get("DETAIL_LIST");
		// FIXME(원본 버그): 원본은 getRecordSet("DETAIL_LIST")를 사용하지만 반환 타입 정보가 없다. 원본 구조를 유지해 Map에서 그대로 조회한다.

		responseData.put("DETAIL_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

}