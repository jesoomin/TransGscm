package com.skhynix.gscm.r.pm.pla.dto;

import lombok.Data;

// Pla047Service.pla04702()가 requestData.get("X")로 직접 읽는 필드(Java 소스에서 확인) +
// dPLA04702 select 본문의 #{}}/${} 바인드 필드를 합쳐 자동 추출. 화면에서 넘어오는 원본 요청 DTO.
// TODO: DISPLAY_QUATER는 원본 SQL(dPLA04702)에 실제로 이 철자(R 누락)로 바인딩되어 있다 -
//   다른 곳은 전부 DISPLAY_QUARTER를 쓰는 것과 다르다. 원본 오타로 보이지만 확정 전까지
//   임의로 고치지 않고 그대로 둔다(CLAUDE.md 원칙) - 사람 확인 필요.
@Data
public class Pla04702Dto {

    /** AS-IS 바인드 변수명: APP_LVL_1_CD */
    private String appLvl1Cd;

    /** AS-IS 바인드 변수명: CELL_LAYER_TYP_CD */
    private String cellLayerTypCd;

    /** AS-IS 바인드 변수명: CHG_PROD_MODE_CD */
    private String chgProdModeCd;

    /** AS-IS 바인드 변수명: CHK_SUBTOTAL */
    private String chkSubtotal;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_DIE_YN */
    private String cooProfRateDieYn;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_EQ_YN */
    private String cooProfRateEqYn;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_PROD_YN */
    private String cooProfRateProdYn;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_WF_YN */
    private String cooProfRateWfYn;

    /** AS-IS 바인드 변수명: DIM */
    private String dim;

    /** AS-IS 바인드 변수명: DISPLAY_HALF */
    private String displayHalf;

    /** AS-IS 바인드 변수명: DISPLAY_MONTH */
    private String displayMonth;

    /** AS-IS 바인드 변수명: DISPLAY_QUATER */
    private String displayQuater;

    /** AS-IS 바인드 변수명: DISPLAY_YEAR */
    private String displayYear;

    /** AS-IS 바인드 변수명: FAB_DEN_CD */
    private String fabDenCd;

    /** AS-IS 바인드 변수명: FROM_YM */
    private String fromYm;

    /** AS-IS 바인드 변수명: PKG_TYP_CD2 */
    private String pkgTypCd2;

    /** AS-IS 바인드 변수명: PLN_VER */
    private String plnVer;

    /** AS-IS 바인드 변수명: SEARCH_TYPE */
    private String searchType;

    /** AS-IS 바인드 변수명: SRCTYPE */
    private String srctype;

    /** AS-IS 바인드 변수명: TECH_CD */
    private String techCd;

    /** AS-IS 바인드 변수명: TECH_GRP_ID */
    private String techGrpId;

    /** AS-IS 바인드 변수명: TO_YM */
    private String toYm;

    /** AS-IS 바인드 변수명: YEAR */
    private String year;

}