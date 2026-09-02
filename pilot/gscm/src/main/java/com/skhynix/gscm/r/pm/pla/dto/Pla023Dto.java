package com.skhynix.gscm.r.pm.pla.dto;

import java.util.List;
import java.util.Map;

// .BIZUNIT의 <fields/>가 비어있어 AS-IS 코드의 getField/putRecordset 실사용값에서
// 역추출했다(CLAUDE.md AS-IS->TO-BE 매핑표 참고). 필드 타입은 전부 String/List<Map<>>로
// 잠정 지정했다 - 원본에 실제 타입이 선언돼 있지 않아 사람 확인이 필요하다.
public class Pla023Dto {

    // ===== (nctRid 미확인) (pPLA02301) =====
    public static class Ppla02301Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla02301Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== (nctRid 미확인) (pPLA02302) =====
    public static class Ppla02302Request {
        private String tgtCd; // AS-IS: TGT_CD

        public String getTgtCd() { return tgtCd; }
        public void setTgtCd(String tgtCd) { this.tgtCd = tgtCd; }
    }

    public static class Ppla02302Response {
        private List<Map<String, Object>> detailList; // AS-IS recordset: DETAIL_LIST

        public List<Map<String, Object>> getDetailList() { return detailList; }
        public void setDetailList(List<Map<String, Object>> detailList) { this.detailList = detailList; }
    }

    // ===== (nctRid 미확인) (pPLA02303) =====
    public static class Ppla02303Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla02303Response {
        private List<Map<String, Object>> histList; // AS-IS recordset: HIST_LIST

        public List<Map<String, Object>> getHistList() { return histList; }
        public void setHistList(List<Map<String, Object>> histList) { this.histList = histList; }
    }

    // ===== (nctRid 미확인) (pPLA02304) =====
    public static class Ppla02304Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla02304Response {
        private List<Map<String, Object>> excelList; // AS-IS recordset: EXCEL_LIST

        public List<Map<String, Object>> getExcelList() { return excelList; }
        public void setExcelList(List<Map<String, Object>> excelList) { this.excelList = excelList; }
    }

}