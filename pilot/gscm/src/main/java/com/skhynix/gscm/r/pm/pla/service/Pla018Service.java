package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla018Service {

    @Autowired
    private Pla018Store store;

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
		// FIXME(원본 버그): 원본은 DPLA018 du = (DPLA018) lookupDataUnit(DPLA018.class); 를 사용했으나 프레임워크 의존 제거 요구에 따라 store 필드 사용으로 치환
		Object authResult = store.dAuthCheck(request);
		// FIXME(원본 버그): 원본은 du.dAuthCheck(requestData, onlineCtx).getRecordSet("AUTH_LIST") 를 호출하나 requestData, onlineCtx가 본문 내 미선언 상태였음. 요구사항에 따라 원본 로직은 유지하되 프레임워크 의존만 제거하여 request 사용으로 포팅
		Object rs = ((Map<String, Object>) authResult).get("AUTH_LIST");
		if (((com.nexcore.framework.core.data.IRecordSet) rs).getRecordCount() > 0) {
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
public Map<String, Object> fPLA018QrySelectMainList(Map<String, Object> request) {
    Map<String, Object> responseData = new HashMap<>();
    try {
        Map<String, Object> paramMap = request;

        String strTGT_CD = (String) request.get("TGT_CD");
        String strSearchDtFrom = (String) request.get("SEARCH_DT_FROM");
        String strSearchDtTo = (String) request.get("SEARCH_DT_TO");

        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
        paramMap.put("SEARCH_DT_TO", strSearchDtTo);
        request.putAll(paramMap);

        // FIXME(원본 버그): 원본은 du.dPLA01801(requestData, onlineCtx).getRecordSet("MAIN_LIST") 호출 구조에 의존하며 반환 타입/구조가 명확하지 않음. 원본 로직 그대로 유지하기 위해 동일한 체이닝을 store 호출로만 치환.
        Object rs = store.dPLA01801(request).get("MAIN_LIST");
        responseData.put("MAIN_LIST", rs);
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA018QrySelectDetail(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<>();
    try {
        Map<String, Object> paramMap = request;

        String strTGT_CD = (String) request.get("TGT_CD");
        paramMap.put("TGT_CD", strTGT_CD);
        paramMap.put("METRIC_TYPE", "REMARK_CD");
        // FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 Spring Map 기반 포팅에서는 대응 메서드가 없어 그대로 반영 불가

        Object rs = store.dPLA01802(request).get("DETAIL_LIST");
        responseData.put("DETAIL_LIST", rs);
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

}