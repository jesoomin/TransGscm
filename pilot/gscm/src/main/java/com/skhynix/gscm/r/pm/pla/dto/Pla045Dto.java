package com.skhynix.gscm.r.pm.pla.dto;

import java.util.List;
import java.util.Map;

// .BIZUNIT의 <fields/>가 비어있어 AS-IS 코드의 getField/putRecordset 실사용값에서
// 역추출했다(CLAUDE.md AS-IS->TO-BE 매핑표 참고). 필드 타입은 전부 String/List<Map<>>로
// 잠정 지정했다 - 원본에 실제 타입이 선언돼 있지 않아 사람 확인이 필요하다.
public class Pla045Dto {

    // ===== (nctRid 미확인) (pPLA04501) =====
    public static class Ppla04501Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04501Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== (nctRid 미확인) (PPLA04502) =====
    public static class Ppla04502Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04502Response {
        private List<Map<String, Object>> headerList; // AS-IS recordset: HEADER_LIST
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getHeaderList() { return headerList; }
        public void setHeaderList(List<Map<String, Object>> headerList) { this.headerList = headerList; }
        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== (nctRid 미확인) (PPLA04503) =====
    public static class Ppla04503Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04503Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== (nctRid 미확인) (PPLA04504) =====
    public static class Ppla04504Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Ppla04504Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

}