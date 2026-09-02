package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

@Service
public class Pla042Service {

    @Autowired
    private Pla042Store store;

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
        Object rs = store.dAuthCheck(request).get("AUTH_LIST");
        // FIXME(원본 버그): 원본은 IRecordSet rs 선언 및 rs.getRecordCount() 호출에 프레임워크 타입 의존이 있음. 그대로 포팅 불가.
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
public Map<String, Object> fPLA042QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<>();
	try {
		// FIXME(원본 버그): 원본은 requestData.getFieldMap()을 사용하나 requestData가 선언되어 있지 않음
		Map<String, Object> paramMap = requestData.getFieldMap();

		// FIXME(원본 버그): 원본은 requestData.getField(...)를 사용하나 requestData가 선언되어 있지 않음
		String strTGT_CD = requestData.getField("TGT_CD");
		String strSearchDtFrom = requestData.getField("SEARCH_DT_FROM");
		String strSearchDtTo = requestData.getField("SEARCH_DT_TO");

		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("SEARCH_DT_FROM", strSearchDtFrom);
		paramMap.put("SEARCH_DT_TO", strSearchDtTo);
		// FIXME(원본 버그): 원본은 requestData.putFieldMap(paramMap)을 사용하나 requestData가 선언되어 있지 않음
		requestData.putFieldMap(paramMap);

		// FIXME(원본 버그): 원본은 onlineCtx를 사용하나 선언되어 있지 않음
		Object rs = store.dPLA04201(requestData, onlineCtx).getRecordSet("MAIN_LIST");
		responseData.put("MAIN_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA042QrySelectDetail(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<String, Object>();
	try {
		Map<String, Object> paramMap = request;

		String strTGT_CD = (String) request.get("TGT_CD");
		paramMap.put("TGT_CD", strTGT_CD);
		paramMap.put("METRIC_TYPE", "AMT");
		// FIXME(원본 버그): 원본의 requestData.putFieldMap(paramMap) 호출은 requestData 미선언 상태였으나 그대로 포팅하지 않음

		Object rs = store.dPLA04202(request).get("DETAIL_LIST");
		responseData.put("DETAIL_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

}