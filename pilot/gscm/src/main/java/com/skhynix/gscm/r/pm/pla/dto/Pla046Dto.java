package com.skhynix.gscm.r.pm.pla.dto;

import java.util.List;
import java.util.Map;

// .BIZUNIT의 <fields/>가 비어있어 AS-IS 코드의 getField/putRecordset 실사용값에서
// 역추출했다(CLAUDE.md AS-IS->TO-BE 매핑표 참고). 필드 타입은 전부 String/List<Map<>>로
// 잠정 지정했다 - 원본에 실제 타입이 선언돼 있지 않아 사람 확인이 필요하다.
public class Pla046Dto {

    // ===== (nctRid 미확인) (pPLA04601) =====
    public static class Ppla04601Request {
        private String searchDtFrom; // AS-IS: SEARCH_DT_FROM
        private String searchDtTo; // AS-IS: SEARCH_DT_TO
        private String tgtCd; // AS-IS: TGT_CD

        public String getSearchDtFrom() { return searchDtFrom; }
        public void setSearchDtFrom(String searchDtFrom) { this.searchDtFrom = searchDtFrom; }
        public String getSearchDtTo() { return searchDtTo; }
        public void setSearchDtTo(String searchDtTo) { this.searchDtTo = searchDtTo; }
        public String getTgtCd() { return tgtCd; }
        public void setTgtCd(String tgtCd) { this.tgtCd = tgtCd; }
    }

    public static class Ppla04601Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== (nctRid 미확인) (pPLA04602) =====
    public static class Ppla04602Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04602Response {
        private List<Map<String, Object>> exrList; // AS-IS recordset: EXR_LIST

        public List<Map<String, Object>> getExrList() { return exrList; }
        public void setExrList(List<Map<String, Object>> exrList) { this.exrList = exrList; }
    }

    // ===== (nctRid 미확인) (pPLA04603) =====
    public static class Ppla04603Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04603Response {
        private List<Map<String, Object>> yldPlnList; // AS-IS recordset: YLD_PLN_LIST

        public List<Map<String, Object>> getYldPlnList() { return yldPlnList; }
        public void setYldPlnList(List<Map<String, Object>> yldPlnList) { this.yldPlnList = yldPlnList; }
    }

    // ===== (nctRid 미확인) (pPLA04604) =====
    public static class Ppla04604Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04604Response {
        private List<Map<String, Object>> revList; // AS-IS recordset: REV_LIST

        public List<Map<String, Object>> getRevList() { return revList; }
        public void setRevList(List<Map<String, Object>> revList) { this.revList = revList; }
    }

    // ===== (nctRid 미확인) (pPLA04605) =====
    public static class Ppla04605Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04605Response {
        private List<Map<String, Object>> revList; // AS-IS recordset: REV_LIST
        private List<Map<String, Object>> revListA; // AS-IS recordset: REV_LIST_A
        private List<Map<String, Object>> revListB; // AS-IS recordset: REV_LIST_B

        public List<Map<String, Object>> getRevList() { return revList; }
        public void setRevList(List<Map<String, Object>> revList) { this.revList = revList; }
        public List<Map<String, Object>> getRevListA() { return revListA; }
        public void setRevListA(List<Map<String, Object>> revListA) { this.revListA = revListA; }
        public List<Map<String, Object>> getRevListB() { return revListB; }
        public void setRevListB(List<Map<String, Object>> revListB) { this.revListB = revListB; }
    }

    // ===== (nctRid 미확인) (pPLA04606) =====
    public static class Ppla04606Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04606Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== (nctRid 미확인) (pPLA04607) =====
    public static class Ppla04607Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04607Response {
        private List<Map<String, Object>> memoInfo; // AS-IS recordset: MEMO_INFO

        public List<Map<String, Object>> getMemoInfo() { return memoInfo; }
        public void setMemoInfo(List<Map<String, Object>> memoInfo) { this.memoInfo = memoInfo; }
    }

    // ===== (nctRid 미확인) (pPLA04608) =====
    public static class Ppla04608Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04608Response {
        // TODO: 응답 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    // ===== (nctRid 미확인) (pPLA04609) =====
    public static class Ppla04609Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04609Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== (nctRid 미확인) (pPLA04610) =====
    public static class Ppla04610Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04610Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== (nctRid 미확인) (pPLA04611) =====
    public static class Ppla04611Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04611Response {
        // TODO: 응답 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    // ===== (nctRid 미확인) (pPLA04612) =====
    public static class Ppla04612Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04612Response {
        private List<Map<String, Object>> plnRevList; // AS-IS recordset: PLN_REV_LIST

        public List<Map<String, Object>> getPlnRevList() { return plnRevList; }
        public void setPlnRevList(List<Map<String, Object>> plnRevList) { this.plnRevList = plnRevList; }
    }

    // ===== (nctRid 미확인) (pPLA04613) =====
    public static class Ppla04613Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04613Response {
        // TODO: 응답 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    // ===== (nctRid 미확인) (pPLA04614) =====
    public static class Ppla04614Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04614Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== (nctRid 미확인) (pPLA04615) =====
    public static class Ppla04615Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04615Response {
        // TODO: 응답 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    // ===== (nctRid 미확인) (pPLA04616) =====
    public static class Ppla04616Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04616Response {
        private List<Map<String, Object>> maxWeek; // AS-IS recordset: MAX_WEEK

        public List<Map<String, Object>> getMaxWeek() { return maxWeek; }
        public void setMaxWeek(List<Map<String, Object>> maxWeek) { this.maxWeek = maxWeek; }
    }

    // ===== (nctRid 미확인) (pPLA04617) =====
    public static class Ppla04617Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04617Response {
        // TODO: 응답 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

}