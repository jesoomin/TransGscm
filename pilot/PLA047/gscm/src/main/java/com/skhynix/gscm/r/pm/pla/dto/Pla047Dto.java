package com.skhynix.gscm.r.pm.pla.dto;

import java.util.List;
import java.util.Map;

// .BIZUNIT의 <fields/>가 비어있어 AS-IS 코드의 getField/putRecordset 실사용값에서
// 역추출했다(CLAUDE.md AS-IS->TO-BE 매핑표 참고). 필드 타입은 전부 String/List<Map<>>로
// 잠정 지정했다 - 원본에 실제 타입이 선언돼 있지 않아 사람 확인이 필요하다.
public class Pla047Dto {

    // ===== RPLA04701 (pPLA04701) =====
    public static class Rpla04701Request {
        private String appLvl1Cd; // AS-IS: APP_LVL_1_CD
        private String cellLayerTypCd; // AS-IS: CELL_LAYER_TYP_CD
        private String chgProdModeCd; // AS-IS: CHG_PROD_MODE_CD
        private String chkSubtotal; // AS-IS: CHK_SUBTOTAL
        private String cooProfRateDieYn; // AS-IS: COO_PROF_RATE_DIE_YN
        private String cooProfRateProdYn; // AS-IS: COO_PROF_RATE_PROD_YN
        private String cooProfRateWfYn; // AS-IS: COO_PROF_RATE_WF_YN
        private String dim; // AS-IS: DIM
        private String fabDenCd; // AS-IS: FAB_DEN_CD
        private String pkgTypCd2; // AS-IS: PKG_TYP_CD2
        private String searchType; // AS-IS: SEARCH_TYPE
        private String srctype; // AS-IS: SRCTYPE
        private String techCd; // AS-IS: TECH_CD
        private String techGrpId; // AS-IS: TECH_GRP_ID
        private String year; // AS-IS: YEAR

        public String getAppLvl1Cd() { return appLvl1Cd; }
        public void setAppLvl1Cd(String appLvl1Cd) { this.appLvl1Cd = appLvl1Cd; }
        public String getCellLayerTypCd() { return cellLayerTypCd; }
        public void setCellLayerTypCd(String cellLayerTypCd) { this.cellLayerTypCd = cellLayerTypCd; }
        public String getChgProdModeCd() { return chgProdModeCd; }
        public void setChgProdModeCd(String chgProdModeCd) { this.chgProdModeCd = chgProdModeCd; }
        public String getChkSubtotal() { return chkSubtotal; }
        public void setChkSubtotal(String chkSubtotal) { this.chkSubtotal = chkSubtotal; }
        public String getCooProfRateDieYn() { return cooProfRateDieYn; }
        public void setCooProfRateDieYn(String cooProfRateDieYn) { this.cooProfRateDieYn = cooProfRateDieYn; }
        public String getCooProfRateProdYn() { return cooProfRateProdYn; }
        public void setCooProfRateProdYn(String cooProfRateProdYn) { this.cooProfRateProdYn = cooProfRateProdYn; }
        public String getCooProfRateWfYn() { return cooProfRateWfYn; }
        public void setCooProfRateWfYn(String cooProfRateWfYn) { this.cooProfRateWfYn = cooProfRateWfYn; }
        public String getDim() { return dim; }
        public void setDim(String dim) { this.dim = dim; }
        public String getFabDenCd() { return fabDenCd; }
        public void setFabDenCd(String fabDenCd) { this.fabDenCd = fabDenCd; }
        public String getPkgTypCd2() { return pkgTypCd2; }
        public void setPkgTypCd2(String pkgTypCd2) { this.pkgTypCd2 = pkgTypCd2; }
        public String getSearchType() { return searchType; }
        public void setSearchType(String searchType) { this.searchType = searchType; }
        public String getSrctype() { return srctype; }
        public void setSrctype(String srctype) { this.srctype = srctype; }
        public String getTechCd() { return techCd; }
        public void setTechCd(String techCd) { this.techCd = techCd; }
        public String getTechGrpId() { return techGrpId; }
        public void setTechGrpId(String techGrpId) { this.techGrpId = techGrpId; }
        public String getYear() { return year; }
        public void setYear(String year) { this.year = year; }
    }

    public static class Rpla04701Response {
        private List<Map<String, Object>> datetimeMap; // AS-IS recordset: DATETIME_MAP
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getDatetimeMap() { return datetimeMap; }
        public void setDatetimeMap(List<Map<String, Object>> datetimeMap) { this.datetimeMap = datetimeMap; }
        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

    // ===== RPLA04702 (pPLA04702) =====
    public static class Rpla04702Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Rpla04702Response {
        private List<Map<String, Object>> revList; // AS-IS recordset: REV_LIST

        public List<Map<String, Object>> getRevList() { return revList; }
        public void setRevList(List<Map<String, Object>> revList) { this.revList = revList; }
    }

    // ===== RPLA04703 (pPLA04703) =====
    public static class Rpla04703Request {
        // TODO: 요청 필드 자동 추출 실패 - 원본 대조해서 수동으로 채울 것
    }

    public static class Rpla04703Response {
        private List<Map<String, Object>> mainList; // AS-IS recordset: MAIN_LIST

        public List<Map<String, Object>> getMainList() { return mainList; }
        public void setMainList(List<Map<String, Object>> mainList) { this.mainList = mainList; }
    }

}