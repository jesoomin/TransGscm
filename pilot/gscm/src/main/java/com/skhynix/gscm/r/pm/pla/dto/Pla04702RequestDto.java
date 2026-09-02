package com.skhynix.gscm.r.pm.pla.dto;

import lombok.Data;

import java.util.List;

// Mapper의 dPLA04703/dPLA04704/dPLA04705 select 3개(전부 parameterType=Pla04702RequestDto)가
// 실제로 바인딩하는 #{}}/${} 및 <if test=...> 프로퍼티 전체를 합집합으로 자동 추출했다.
// Pla047Service.pla04702()가 화면 원본 요청(Pla04702Dto) + 직접 계산한 SQL 조각(DIM_OUTER,
// GROUPING_NETDIE1~5, ORDER_BY, PIVOT_STR, CUM2_COL 등)을 한데 모아 이 타입으로 매핑해 Store에
// 넘긴다 - 필드가 많은 건 원본 자체가 그렇다(PIVOT 동적 컬럼 생성용).
// TODO: 전부 String으로 잠정 지정 - 실제로는 파생 SQL 조각 문자열이라 String이 맞을 가능성이 높음.
@Data
public class Pla04702RequestDto {

    /** AS-IS 바인드 변수명: ASP_SALE_PLN */
    private String aspSalePln;

    /** AS-IS 바인드 변수명: ASP_SALE_PLN_ST */
    private String aspSalePlnSt;

    /** AS-IS 바인드 변수명: ASP_SALE_PLN_ST_O */
    private String aspSalePlnStO;

    /** AS-IS 바인드 변수명: ASP_SALE_PLN_YN */
    private String aspSalePlnYn;

    /** AS-IS 바인드 변수명: CASH_COST_DIE_COST */
    private String cashCostDieCost;

    /** AS-IS 바인드 변수명: CASH_COST_DIE_COST_ST */
    private String cashCostDieCostSt;

    /** AS-IS 바인드 변수명: CASH_COST_DIE_COST_ST_O */
    private String cashCostDieCostStO;

    /** AS-IS 바인드 변수명: CASH_COST_DIE_COST_YN */
    private String cashCostDieCostYn;

    /** AS-IS 바인드 변수명: CASH_COST_EQ_COST */
    private String cashCostEqCost;

    /** AS-IS 바인드 변수명: CASH_COST_EQ_COST_ST */
    private String cashCostEqCostSt;

    /** AS-IS 바인드 변수명: CASH_COST_EQ_COST_ST_O */
    private String cashCostEqCostStO;

    /** AS-IS 바인드 변수명: CASH_COST_EQ_COST_YN */
    private String cashCostEqCostYn;

    /** AS-IS 바인드 변수명: CASH_COST_PROD_COST */
    private String cashCostProdCost;

    /** AS-IS 바인드 변수명: CASH_COST_PROD_COST_ST */
    private String cashCostProdCostSt;

    /** AS-IS 바인드 변수명: CASH_COST_PROD_COST_ST_O */
    private String cashCostProdCostStO;

    /** AS-IS 바인드 변수명: CASH_COST_PROD_COST_YN */
    private String cashCostProdCostYn;

    /** AS-IS 바인드 변수명: CASH_COST_WF_SLS_COST */
    private String cashCostWfSlsCost;

    /** AS-IS 바인드 변수명: CASH_COST_WF_SLS_COST_ST */
    private String cashCostWfSlsCostSt;

    /** AS-IS 바인드 변수명: CASH_COST_WF_SLS_COST_ST_O */
    private String cashCostWfSlsCostStO;

    /** AS-IS 바인드 변수명: CASH_COST_WF_SLS_COST_YN */
    private String cashCostWfSlsCostYn;

    /** AS-IS 바인드 변수명: CASH_COST_YR_COST */
    private String cashCostYrCost;

    /** AS-IS 바인드 변수명: CASH_COST_YR_COST_ST */
    private String cashCostYrCostSt;

    /** AS-IS 바인드 변수명: CASH_COST_YR_COST_ST_O */
    private String cashCostYrCostStO;

    /** AS-IS 바인드 변수명: CASH_COST_YR_COST_YN */
    private String cashCostYrCostYn;

    /** AS-IS 바인드 변수명: CASH_PROF_DIE_PROF */
    private String cashProfDieProf;

    /** AS-IS 바인드 변수명: CASH_PROF_DIE_PROF_ST */
    private String cashProfDieProfSt;

    /** AS-IS 바인드 변수명: CASH_PROF_DIE_PROF_ST_O */
    private String cashProfDieProfStO;

    /** AS-IS 바인드 변수명: CASH_PROF_DIE_PROF_YN */
    private String cashProfDieProfYn;

    /** AS-IS 바인드 변수명: CASH_PROF_EQ_PROF */
    private String cashProfEqProf;

    /** AS-IS 바인드 변수명: CASH_PROF_EQ_PROF_ST */
    private String cashProfEqProfSt;

    /** AS-IS 바인드 변수명: CASH_PROF_EQ_PROF_ST_O */
    private String cashProfEqProfStO;

    /** AS-IS 바인드 변수명: CASH_PROF_EQ_PROF_YN */
    private String cashProfEqProfYn;

    /** AS-IS 바인드 변수명: CASH_PROF_PROD_PROF */
    private String cashProfProdProf;

    /** AS-IS 바인드 변수명: CASH_PROF_PROD_PROF_ST */
    private String cashProfProdProfSt;

    /** AS-IS 바인드 변수명: CASH_PROF_PROD_PROF_ST_O */
    private String cashProfProdProfStO;

    /** AS-IS 바인드 변수명: CASH_PROF_PROD_PROF_YN */
    private String cashProfProdProfYn;

    /** AS-IS 바인드 변수명: CASH_PROF_WF_SLS_PROF */
    private String cashProfWfSlsProf;

    /** AS-IS 바인드 변수명: CASH_PROF_WF_SLS_PROF_ST */
    private String cashProfWfSlsProfSt;

    /** AS-IS 바인드 변수명: CASH_PROF_WF_SLS_PROF_ST_O */
    private String cashProfWfSlsProfStO;

    /** AS-IS 바인드 변수명: CASH_PROF_WF_SLS_PROF_YN */
    private String cashProfWfSlsProfYn;

    /** AS-IS 바인드 변수명: CASH_PROF_YR_PROF */
    private String cashProfYrProf;

    /** AS-IS 바인드 변수명: CASH_PROF_YR_PROF_ST */
    private String cashProfYrProfSt;

    /** AS-IS 바인드 변수명: CASH_PROF_YR_PROF_ST_O */
    private String cashProfYrProfStO;

    /** AS-IS 바인드 변수명: CASH_PROF_YR_PROF_YN */
    private String cashProfYrProfYn;

    /** AS-IS 바인드 변수명: CHKAPPYN */
    private String chkappyn;

    /** AS-IS 바인드 변수명: CHKDASHBOARDYN */
    private String chkdashboardyn;

    /** AS-IS 바인드 변수명: CHKMODEYN */
    private String chkmodeyn;

    /** AS-IS 바인드 변수명: CHKTECHYN */
    private String chktechyn;

    /** AS-IS 바인드 변수명: CHKYN */
    private String chkyn;

    /** AS-IS 바인드 변수명: CHK_SSD_BUFFER_YN */
    private String chkSsdBufferYn;

    /** AS-IS 바인드 변수명: CNTRB_PROF_DIE_PROF */
    private String cntrbProfDieProf;

    /** AS-IS 바인드 변수명: CNTRB_PROF_DIE_PROF_ST */
    private String cntrbProfDieProfSt;

    /** AS-IS 바인드 변수명: CNTRB_PROF_DIE_PROF_ST_O */
    private String cntrbProfDieProfStO;

    /** AS-IS 바인드 변수명: CNTRB_PROF_DIE_PROF_YN */
    private String cntrbProfDieProfYn;

    /** AS-IS 바인드 변수명: CNTRB_PROF_EQ_PROF */
    private String cntrbProfEqProf;

    /** AS-IS 바인드 변수명: CNTRB_PROF_EQ_PROF_ST */
    private String cntrbProfEqProfSt;

    /** AS-IS 바인드 변수명: CNTRB_PROF_EQ_PROF_ST_O */
    private String cntrbProfEqProfStO;

    /** AS-IS 바인드 변수명: CNTRB_PROF_EQ_PROF_YN */
    private String cntrbProfEqProfYn;

    /** AS-IS 바인드 변수명: CNTRB_PROF_PROD_PROF */
    private String cntrbProfProdProf;

    /** AS-IS 바인드 변수명: CNTRB_PROF_PROD_PROF_ST */
    private String cntrbProfProdProfSt;

    /** AS-IS 바인드 변수명: CNTRB_PROF_PROD_PROF_ST_O */
    private String cntrbProfProdProfStO;

    /** AS-IS 바인드 변수명: CNTRB_PROF_PROD_PROF_YN */
    private String cntrbProfProdProfYn;

    /** AS-IS 바인드 변수명: CNTRB_PROF_WF_SLS_PROF */
    private String cntrbProfWfSlsProf;

    /** AS-IS 바인드 변수명: CNTRB_PROF_WF_SLS_PROF_ST */
    private String cntrbProfWfSlsProfSt;

    /** AS-IS 바인드 변수명: CNTRB_PROF_WF_SLS_PROF_ST_O */
    private String cntrbProfWfSlsProfStO;

    /** AS-IS 바인드 변수명: CNTRB_PROF_WF_SLS_PROF_YN */
    private String cntrbProfWfSlsProfYn;

    /** AS-IS 바인드 변수명: CNTRB_PROF_YR_PROF */
    private String cntrbProfYrProf;

    /** AS-IS 바인드 변수명: CNTRB_PROF_YR_PROF_ST */
    private String cntrbProfYrProfSt;

    /** AS-IS 바인드 변수명: CNTRB_PROF_YR_PROF_ST_O */
    private String cntrbProfYrProfStO;

    /** AS-IS 바인드 변수명: CNTRB_PROF_YR_PROF_YN */
    private String cntrbProfYrProfYn;

    /** AS-IS 바인드 변수명: COGS_COST_DIE_COST */
    private String cogsCostDieCost;

    /** AS-IS 바인드 변수명: COGS_COST_DIE_COST_ST */
    private String cogsCostDieCostSt;

    /** AS-IS 바인드 변수명: COGS_COST_DIE_COST_ST_O */
    private String cogsCostDieCostStO;

    /** AS-IS 바인드 변수명: COGS_COST_DIE_COST_YN */
    private String cogsCostDieCostYn;

    /** AS-IS 바인드 변수명: COGS_COST_EQ_COST */
    private String cogsCostEqCost;

    /** AS-IS 바인드 변수명: COGS_COST_EQ_COST_ST */
    private String cogsCostEqCostSt;

    /** AS-IS 바인드 변수명: COGS_COST_EQ_COST_ST_O */
    private String cogsCostEqCostStO;

    /** AS-IS 바인드 변수명: COGS_COST_EQ_COST_YN */
    private String cogsCostEqCostYn;

    /** AS-IS 바인드 변수명: COGS_COST_PROD_COST */
    private String cogsCostProdCost;

    /** AS-IS 바인드 변수명: COGS_COST_PROD_COST_ST */
    private String cogsCostProdCostSt;

    /** AS-IS 바인드 변수명: COGS_COST_PROD_COST_ST_O */
    private String cogsCostProdCostStO;

    /** AS-IS 바인드 변수명: COGS_COST_PROD_COST_YN */
    private String cogsCostProdCostYn;

    /** AS-IS 바인드 변수명: COGS_COST_WF_SLS_COST */
    private String cogsCostWfSlsCost;

    /** AS-IS 바인드 변수명: COGS_COST_WF_SLS_COST_ST */
    private String cogsCostWfSlsCostSt;

    /** AS-IS 바인드 변수명: COGS_COST_WF_SLS_COST_ST_O */
    private String cogsCostWfSlsCostStO;

    /** AS-IS 바인드 변수명: COGS_COST_WF_SLS_COST_YN */
    private String cogsCostWfSlsCostYn;

    /** AS-IS 바인드 변수명: COGS_COST_YR_COST */
    private String cogsCostYrCost;

    /** AS-IS 바인드 변수명: COGS_COST_YR_COST_ST */
    private String cogsCostYrCostSt;

    /** AS-IS 바인드 변수명: COGS_COST_YR_COST_ST_O */
    private String cogsCostYrCostStO;

    /** AS-IS 바인드 변수명: COGS_COST_YR_COST_YN */
    private String cogsCostYrCostYn;

    /** AS-IS 바인드 변수명: COO_COST_DIE_COST */
    private String cooCostDieCost;

    /** AS-IS 바인드 변수명: COO_COST_DIE_COST_ST */
    private String cooCostDieCostSt;

    /** AS-IS 바인드 변수명: COO_COST_DIE_COST_ST_O */
    private String cooCostDieCostStO;

    /** AS-IS 바인드 변수명: COO_COST_DIE_COST_YN */
    private String cooCostDieCostYn;

    /** AS-IS 바인드 변수명: COO_COST_EQ_COST */
    private String cooCostEqCost;

    /** AS-IS 바인드 변수명: COO_COST_EQ_COST_ST */
    private String cooCostEqCostSt;

    /** AS-IS 바인드 변수명: COO_COST_EQ_COST_ST_O */
    private String cooCostEqCostStO;

    /** AS-IS 바인드 변수명: COO_COST_EQ_COST_YN */
    private String cooCostEqCostYn;

    /** AS-IS 바인드 변수명: COO_COST_PROD_COST */
    private String cooCostProdCost;

    /** AS-IS 바인드 변수명: COO_COST_PROD_COST_ST */
    private String cooCostProdCostSt;

    /** AS-IS 바인드 변수명: COO_COST_PROD_COST_ST_O */
    private String cooCostProdCostStO;

    /** AS-IS 바인드 변수명: COO_COST_PROD_COST_YN */
    private String cooCostProdCostYn;

    /** AS-IS 바인드 변수명: COO_COST_WF_SLS_COST */
    private String cooCostWfSlsCost;

    /** AS-IS 바인드 변수명: COO_COST_WF_SLS_COST_ST */
    private String cooCostWfSlsCostSt;

    /** AS-IS 바인드 변수명: COO_COST_WF_SLS_COST_ST_O */
    private String cooCostWfSlsCostStO;

    /** AS-IS 바인드 변수명: COO_COST_WF_SLS_COST_YN */
    private String cooCostWfSlsCostYn;

    /** AS-IS 바인드 변수명: COO_COST_YR_COST */
    private String cooCostYrCost;

    /** AS-IS 바인드 변수명: COO_COST_YR_COST_ST */
    private String cooCostYrCostSt;

    /** AS-IS 바인드 변수명: COO_COST_YR_COST_ST_O */
    private String cooCostYrCostStO;

    /** AS-IS 바인드 변수명: COO_COST_YR_COST_YN */
    private String cooCostYrCostYn;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_DIE */
    private String cooProfRateDie;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_DIE_COL */
    private String cooProfRateDieCol;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_DIE_ST */
    private String cooProfRateDieSt;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_DIE_YN */
    private String cooProfRateDieYn;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_EQ */
    private String cooProfRateEq;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_EQ_COL */
    private String cooProfRateEqCol;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_EQ_ST */
    private String cooProfRateEqSt;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_EQ_YN */
    private String cooProfRateEqYn;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_PROD */
    private String cooProfRateProd;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_PROD_COL */
    private String cooProfRateProdCol;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_PROD_ST */
    private String cooProfRateProdSt;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_PROD_YN */
    private String cooProfRateProdYn;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_WF */
    private String cooProfRateWf;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_WF_COL */
    private String cooProfRateWfCol;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_WF_ST */
    private String cooProfRateWfSt;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_WF_YN */
    private String cooProfRateWfYn;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_YR */
    private String cooProfRateYr;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_YR_ST */
    private String cooProfRateYrSt;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_YR_ST_O */
    private String cooProfRateYrStO;

    /** AS-IS 바인드 변수명: COO_PROF_RATE_YR_YN */
    private String cooProfRateYrYn;

    /** AS-IS 바인드 변수명: CUM2_COL */
    private String cum2Col;

    /** AS-IS 바인드 변수명: CUM2_YLD_MASTER_DATA */
    private String cum2YldMasterData;

    /** AS-IS 바인드 변수명: CUM2_YLD_MASTER_DATA_ST */
    private String cum2YldMasterDataSt;

    /** AS-IS 바인드 변수명: CUM2_YLD_MASTER_DATA_YN */
    private String cum2YldMasterDataYn;

    /** AS-IS 바인드 변수명: DIM */
    private String dim;

    /** AS-IS 바인드 변수명: DIMORG */
    private String dimorg;

    /** AS-IS 바인드 변수명: DIM_GROUP */
    private String dimGroup;

    /** AS-IS 바인드 변수명: DIM_OUTER */
    private String dimOuter;

    /** AS-IS 바인드 변수명: DIM_OUTER_SEQ */
    private String dimOuterSeq;

    /** AS-IS 바인드 변수명: DIM_OUTER_SUB_TOTAL */
    private String dimOuterSubTotal;

    /** AS-IS 바인드 변수명: DISPLAY_HALF */
    private String displayHalf;

    /** AS-IS 바인드 변수명: DISPLAY_MONTH */
    private String displayMonth;

    /** AS-IS 바인드 변수명: DISPLAY_QUARTER */
    private String displayQuarter;

    /** AS-IS 바인드 변수명: DISPLAY_YEAR */
    private String displayYear;

    /** AS-IS 바인드 변수명: DISPLAY_YRAR */
    private String displayYrar;

    /** AS-IS 바인드 변수명: FROM_YM */
    private String fromYm;

    /** AS-IS 바인드 변수명: GOOD_DIE_COL */
    private String goodDieCol;

    /** AS-IS 바인드 변수명: GOOD_DIE_MASTER_DATA */
    private String goodDieMasterData;

    /** AS-IS 바인드 변수명: GOOD_DIE_MASTER_DATA_ST */
    private String goodDieMasterDataSt;

    /** AS-IS 바인드 변수명: GOOD_DIE_MASTER_DATA_YN */
    private String goodDieMasterDataYn;

    /** AS-IS 바인드 변수명: GRAVYN */
    private String gravyn;

    /** AS-IS 바인드 변수명: GROUPING_NETDIE1 */
    private String groupingNetdie1;

    /** AS-IS 바인드 변수명: GROUPING_NETDIE2 */
    private String groupingNetdie2;

    /** AS-IS 바인드 변수명: GROUPING_NETDIE3 */
    private String groupingNetdie3;

    /** AS-IS 바인드 변수명: GROUPING_NETDIE4 */
    private String groupingNetdie4;

    /** AS-IS 바인드 변수명: GROUPING_NETDIE5 */
    private String groupingNetdie5;

    /** AS-IS 바인드 변수명: GROUPING_WHERE */
    private String groupingWhere;

    /** AS-IS 바인드 변수명: NETDIE_WHERE */
    private String netdieWhere;

    /** AS-IS 바인드 변수명: NET_DIE_YN */
    private String netDieYn;

    /** AS-IS 바인드 변수명: ODD_CUM2_YLD_MASTER_DATA */
    private String oddCum2YldMasterData;

    /** AS-IS 바인드 변수명: ODD_CUM2_YLD_MASTER_DATA_ST */
    private String oddCum2YldMasterDataSt;

    /** AS-IS 바인드 변수명: ODD_GOOD_DIE_MASTER_DATA */
    private String oddGoodDieMasterData;

    /** AS-IS 바인드 변수명: ODD_GOOD_DIE_MASTER_DATA_ST */
    private String oddGoodDieMasterDataSt;

    /** AS-IS 바인드 변수명: ORDER_BY */
    private String orderBy;

    /** AS-IS 바인드 변수명: ORG_QTY_SALE_PLN */
    private String orgQtySalePln;

    /** AS-IS 바인드 변수명: ORG_QTY_SALE_PLN_ST */
    private String orgQtySalePlnSt;

    /** AS-IS 바인드 변수명: ORG_QTY_SALE_PLN_ST_O */
    private String orgQtySalePlnStO;

    /** AS-IS 바인드 변수명: ORG_QTY_SALE_PLN_YN */
    private String orgQtySalePlnYn;

    /** AS-IS 바인드 변수명: PIVOT_STR */
    private String pivotStr;

    /** AS-IS 바인드 변수명: PLN_VER */
    private String plnVer;

    /** AS-IS 바인드 변수명: QTY_GRAV_SALE_PLN */
    private String qtyGravSalePln;

    /** AS-IS 바인드 변수명: QTY_GRAV_SALE_PLN_ST */
    private String qtyGravSalePlnSt;

    /** AS-IS 바인드 변수명: QTY_GRAV_SALE_PLN_ST_O */
    private String qtyGravSalePlnStO;

    /** AS-IS 바인드 변수명: QTY_GRAV_SALE_PLN_YN */
    private String qtyGravSalePlnYn;

    /** AS-IS 바인드 변수명: SALES_PROF_DIE_PROF */
    private String salesProfDieProf;

    /** AS-IS 바인드 변수명: SALES_PROF_DIE_PROF_ST */
    private String salesProfDieProfSt;

    /** AS-IS 바인드 변수명: SALES_PROF_DIE_PROF_ST_O */
    private String salesProfDieProfStO;

    /** AS-IS 바인드 변수명: SALES_PROF_DIE_PROF_YN */
    private String salesProfDieProfYn;

    /** AS-IS 바인드 변수명: SALES_PROF_EQ_PROF */
    private String salesProfEqProf;

    /** AS-IS 바인드 변수명: SALES_PROF_EQ_PROF_ST */
    private String salesProfEqProfSt;

    /** AS-IS 바인드 변수명: SALES_PROF_EQ_PROF_ST_O */
    private String salesProfEqProfStO;

    /** AS-IS 바인드 변수명: SALES_PROF_EQ_PROF_YN */
    private String salesProfEqProfYn;

    /** AS-IS 바인드 변수명: SALES_PROF_GRAV */
    private String salesProfGrav;

    /** AS-IS 바인드 변수명: SALES_PROF_GRAV_ST */
    private String salesProfGravSt;

    /** AS-IS 바인드 변수명: SALES_PROF_GRAV_ST_O */
    private String salesProfGravStO;

    /** AS-IS 바인드 변수명: SALES_PROF_GRAV_YN */
    private String salesProfGravYn;

    /** AS-IS 바인드 변수명: SALES_PROF_PROD_PROF */
    private String salesProfProdProf;

    /** AS-IS 바인드 변수명: SALES_PROF_PROD_PROF_ST */
    private String salesProfProdProfSt;

    /** AS-IS 바인드 변수명: SALES_PROF_PROD_PROF_ST_O */
    private String salesProfProdProfStO;

    /** AS-IS 바인드 변수명: SALES_PROF_PROD_PROF_YN */
    private String salesProfProdProfYn;

    /** AS-IS 바인드 변수명: SALES_PROF_WF_SLS_PROF */
    private String salesProfWfSlsProf;

    /** AS-IS 바인드 변수명: SALES_PROF_WF_SLS_PROF_ST */
    private String salesProfWfSlsProfSt;

    /** AS-IS 바인드 변수명: SALES_PROF_WF_SLS_PROF_ST_O */
    private String salesProfWfSlsProfStO;

    /** AS-IS 바인드 변수명: SALES_PROF_WF_SLS_PROF_YN */
    private String salesProfWfSlsProfYn;

    /** AS-IS 바인드 변수명: SALES_PROF_YR_PROF */
    private String salesProfYrProf;

    /** AS-IS 바인드 변수명: SALES_PROF_YR_PROF_ST */
    private String salesProfYrProfSt;

    /** AS-IS 바인드 변수명: SALES_PROF_YR_PROF_ST_O */
    private String salesProfYrProfStO;

    /** AS-IS 바인드 변수명: SALES_PROF_YR_PROF_YN */
    private String salesProfYrProfYn;

    /** AS-IS 바인드 변수명: SALE_AMT_SALE_PLN */
    private String saleAmtSalePln;

    /** AS-IS 바인드 변수명: SALE_AMT_SALE_PLN_ST */
    private String saleAmtSalePlnSt;

    /** AS-IS 바인드 변수명: SALE_AMT_SALE_PLN_ST_O */
    private String saleAmtSalePlnStO;

    /** AS-IS 바인드 변수명: SALE_AMT_SALE_PLN_YN */
    private String saleAmtSalePlnYn;

    /** AS-IS 바인드 변수명: SALE_DIE_PROF */
    private String saleDieProf;

    /** AS-IS 바인드 변수명: SALE_DIE_PROF_ST */
    private String saleDieProfSt;

    /** AS-IS 바인드 변수명: SALE_DIE_PROF_ST_O */
    private String saleDieProfStO;

    /** AS-IS 바인드 변수명: SALE_DIE_PROF_YN */
    private String saleDieProfYn;

    /** AS-IS 바인드 변수명: SALE_EQ_PROF */
    private String saleEqProf;

    /** AS-IS 바인드 변수명: SALE_EQ_PROF_ST */
    private String saleEqProfSt;

    /** AS-IS 바인드 변수명: SALE_EQ_PROF_ST_O */
    private String saleEqProfStO;

    /** AS-IS 바인드 변수명: SALE_EQ_PROF_YN */
    private String saleEqProfYn;

    /** AS-IS 바인드 변수명: SALE_GRAV_SALE_PLN */
    private String saleGravSalePln;

    /** AS-IS 바인드 변수명: SALE_GRAV_SALE_PLN_ST */
    private String saleGravSalePlnSt;

    /** AS-IS 바인드 변수명: SALE_GRAV_SALE_PLN_ST_O */
    private String saleGravSalePlnStO;

    /** AS-IS 바인드 변수명: SALE_GRAV_SALE_PLN_YN */
    private String saleGravSalePlnYn;

    /** AS-IS 바인드 변수명: SALE_PROD_PROF */
    private String saleProdProf;

    /** AS-IS 바인드 변수명: SALE_PROD_PROF_ST */
    private String saleProdProfSt;

    /** AS-IS 바인드 변수명: SALE_PROD_PROF_YN */
    private String saleProdProfYn;

    /** AS-IS 바인드 변수명: SALE_PROF_DIE_PROF */
    private String saleProfDieProf;

    /** AS-IS 바인드 변수명: SALE_PROF_DIE_PROF_ST */
    private String saleProfDieProfSt;

    /** AS-IS 바인드 변수명: SALE_PROF_DIE_PROF_ST_O */
    private String saleProfDieProfStO;

    /** AS-IS 바인드 변수명: SALE_PROF_DIE_PROF_YN */
    private String saleProfDieProfYn;

    /** AS-IS 바인드 변수명: SALE_PROF_EQ_PROF */
    private String saleProfEqProf;

    /** AS-IS 바인드 변수명: SALE_PROF_EQ_PROF_ST */
    private String saleProfEqProfSt;

    /** AS-IS 바인드 변수명: SALE_PROF_EQ_PROF_ST_O */
    private String saleProfEqProfStO;

    /** AS-IS 바인드 변수명: SALE_PROF_EQ_PROF_YN */
    private String saleProfEqProfYn;

    /** AS-IS 바인드 변수명: SALE_PROF_PROD_PROF */
    private String saleProfProdProf;

    /** AS-IS 바인드 변수명: SALE_PROF_PROD_PROF_ST */
    private String saleProfProdProfSt;

    /** AS-IS 바인드 변수명: SALE_PROF_PROD_PROF_ST_O */
    private String saleProfProdProfStO;

    /** AS-IS 바인드 변수명: SALE_PROF_PROD_PROF_YN */
    private String saleProfProdProfYn;

    /** AS-IS 바인드 변수명: SALE_PROF_WF_SLS_PROF */
    private String saleProfWfSlsProf;

    /** AS-IS 바인드 변수명: SALE_PROF_WF_SLS_PROF_ST */
    private String saleProfWfSlsProfSt;

    /** AS-IS 바인드 변수명: SALE_PROF_WF_SLS_PROF_ST_O */
    private String saleProfWfSlsProfStO;

    /** AS-IS 바인드 변수명: SALE_PROF_WF_SLS_PROF_YN */
    private String saleProfWfSlsProfYn;

    /** AS-IS 바인드 변수명: SALE_PROF_YR_PROF */
    private String saleProfYrProf;

    /** AS-IS 바인드 변수명: SALE_PROF_YR_PROFV */
    private String saleProfYrProfv;

    /** AS-IS 바인드 변수명: SALE_PROF_YR_PROF_ST */
    private String saleProfYrProfSt;

    /** AS-IS 바인드 변수명: SALE_PROF_YR_PROF_YN */
    private String saleProfYrProfYn;

    /** AS-IS 바인드 변수명: SALE_WF_SLS_PROF */
    private String saleWfSlsProf;

    /** AS-IS 바인드 변수명: SALE_WF_SLS_PROF_ST */
    private String saleWfSlsProfSt;

    /** AS-IS 바인드 변수명: SALE_WF_SLS_PROF_ST_O */
    private String saleWfSlsProfStO;

    /** AS-IS 바인드 변수명: SALE_WF_SLS_PROF_YN */
    private String saleWfSlsProfYn;

    /** AS-IS 바인드 변수명: SALE_YR_PROF */
    private String saleYrProf;

    /** AS-IS 바인드 변수명: SALE_YR_PROF_ST */
    private String saleYrProfSt;

    /** AS-IS 바인드 변수명: SALE_YR_PROF_ST_O */
    private String saleYrProfStO;

    /** AS-IS 바인드 변수명: SALE_YR_PROF_YN */
    private String saleYrProfYn;

    /** AS-IS 바인드 변수명: SOM_DIE_QTY_SALE_PLN */
    private String somDieQtySalePln;

    /** AS-IS 바인드 변수명: SOM_DIE_QTY_SALE_PLN_ST */
    private String somDieQtySalePlnSt;

    /** AS-IS 바인드 변수명: SOM_DIE_QTY_SALE_PLN_ST_O */
    private String somDieQtySalePlnStO;

    /** AS-IS 바인드 변수명: SOM_DIE_QTY_SALE_PLN_YN */
    private String somDieQtySalePlnYn;

    /** AS-IS 바인드 변수명: SOM_EQ_QTY_SALE_PLN */
    private String somEqQtySalePln;

    /** AS-IS 바인드 변수명: SOM_EQ_QTY_SALE_PLN_ST */
    private String somEqQtySalePlnSt;

    /** AS-IS 바인드 변수명: SOM_EQ_QTY_SALE_PLN_ST_O */
    private String somEqQtySalePlnStO;

    /** AS-IS 바인드 변수명: SOM_EQ_QTY_SALE_PLN_YN */
    private String somEqQtySalePlnYn;

    /** AS-IS 바인드 변수명: SRCTYPE */
    private String srctype;

    /** AS-IS 바인드 변수명: TECH_GRP_ID */
    private String techGrpId;

    /** AS-IS 바인드 변수명: TO_YM */
    private String toYm;

    /** AS-IS 바인드 변수명: TYPE */
    private String type;

    /** AS-IS 바인드 변수명: VAR_COST_DIE_COST */
    private String varCostDieCost;

    /** AS-IS 바인드 변수명: VAR_COST_DIE_COST_ST */
    private String varCostDieCostSt;

    /** AS-IS 바인드 변수명: VAR_COST_DIE_COST_ST_O */
    private String varCostDieCostStO;

    /** AS-IS 바인드 변수명: VAR_COST_DIE_COST_YN */
    private String varCostDieCostYn;

    /** AS-IS 바인드 변수명: VAR_COST_EQ_COST */
    private String varCostEqCost;

    /** AS-IS 바인드 변수명: VAR_COST_EQ_COST_ST */
    private String varCostEqCostSt;

    /** AS-IS 바인드 변수명: VAR_COST_EQ_COST_ST_O */
    private String varCostEqCostStO;

    /** AS-IS 바인드 변수명: VAR_COST_EQ_COST_YN */
    private String varCostEqCostYn;

    /** AS-IS 바인드 변수명: VAR_COST_PROD_COST */
    private String varCostProdCost;

    /** AS-IS 바인드 변수명: VAR_COST_PROD_COST_ST */
    private String varCostProdCostSt;

    /** AS-IS 바인드 변수명: VAR_COST_PROD_COST_ST_O */
    private String varCostProdCostStO;

    /** AS-IS 바인드 변수명: VAR_COST_PROD_COST_YN */
    private String varCostProdCostYn;

    /** AS-IS 바인드 변수명: VAR_COST_WF_SLS_COST */
    private String varCostWfSlsCost;

    /** AS-IS 바인드 변수명: VAR_COST_WF_SLS_COST_ST */
    private String varCostWfSlsCostSt;

    /** AS-IS 바인드 변수명: VAR_COST_WF_SLS_COST_ST_O */
    private String varCostWfSlsCostStO;

    /** AS-IS 바인드 변수명: VAR_COST_WF_SLS_COST_YN */
    private String varCostWfSlsCostYn;

    /** AS-IS 바인드 변수명: VAR_COST_YR_COST */
    private String varCostYrCost;

    /** AS-IS 바인드 변수명: VAR_COST_YR_COST_ST */
    private String varCostYrCostSt;

    /** AS-IS 바인드 변수명: VAR_COST_YR_COST_ST_O */
    private String varCostYrCostStO;

    /** AS-IS 바인드 변수명: VAR_COST_YR_COST_YN */
    private String varCostYrCostYn;

    /** AS-IS 바인드 변수명: WF_CONV_QTY_SALE_PLN */
    private String wfConvQtySalePln;

    /** AS-IS 바인드 변수명: WF_CONV_QTY_SALE_PLN_ST */
    private String wfConvQtySalePlnSt;

    /** AS-IS 바인드 변수명: WF_CONV_QTY_SALE_PLN_ST_O */
    private String wfConvQtySalePlnStO;

    /** AS-IS 바인드 변수명: WF_CONV_QTY_SALE_PLN_YN */
    private String wfConvQtySalePlnYn;

    /** AS-IS 바인드 변수명: YEAR */
    private String year;

    /** AS-IS foreach collection명: ARR_APP_LVL_1_CD (List<String>) */
    private List<String> arrAppLvl1Cd;

    /** AS-IS foreach collection명: ARR_CELL_LAYER_TYP_CD (List<String>) */
    private List<String> arrCellLayerTypCd;

    /** AS-IS foreach collection명: ARR_CHG_PROD_MODE_CD (List<String>) */
    private List<String> arrChgProdModeCd;

    /** AS-IS foreach collection명: ARR_FAB_DEN_CD (List<String>) */
    private List<String> arrFabDenCd;

    /** AS-IS foreach collection명: ARR_PKG_TYP_CD2 (List<String>) */
    private List<String> arrPkgTypCd2;

    /** AS-IS foreach collection명: ARR_TECH_CD (List<String>) */
    private List<String> arrTechCd;

}