package gscm.r.pm.plab.biz;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import nexcore.framework.core.data.DataSet;
import nexcore.framework.core.data.IDataSet;
import nexcore.framework.core.data.IOnlineContext;
import nexcore.framework.core.data.IRecordSet;
import nexcore.framework.core.exception.BizRuntimeException;

/**
 * <ul>
 * <li>업무 그룹명 : GSCM/경영관리/제품MIX/계획분석</li> 
 * <li>단위업무명 : [FU] 제품별 장당 수익</li> 
 * <li>설   명 : <pre>제품별 장당 수익</pre></li> 
*/
public class FPLA039 extends gscm.fwk.base.ProcessUnit{
	public FPLA039(){
		super();
	}
	
	/**
	 * <pre> 장당 수익성분석 조회 </pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet fPLA039QrySelectMainList(IDataSet requestData, IOnlineContext onlineCtx){
		IDataSet responseData = new DataSet();
		
		try{
			DPLA039 fu = (DPLA039) lookupFunctionUnit(DPLA039.class);
			Map<String,Object> paramMap = requestData.getFieldMap();
			
			String strDim = requestData.getField("DIM");
			String sOrderBy = "";
			String strTechCd		= requestData.getField("TECH_CD");
			String strFabDenCd		= requestData.getField("FAB_DEN_CD");
			String strChgProdModCd	= requestData.getField("CHG_PROD_MODE_CD");
			String strAppLvl1Cd		= requestData.getField("APP_LVL_1_CD");
			String strPkgtypCd2		= requestData.getField("PKG_TYP_CD2");
			String strCellTypCd		= requestData.getField("CELL_LAYER_TYP_CD");
			String strSRCTYPE		= requestData.getField("SRCTYPE");
			String strChkSubTotal	= requestData.getField("CHK_SUBTOTAL");
			
			String[] arrDim = strDim.split(",");
			String strDimOuter = "";
			String strDimOuterSubTotal = "";
			String strDimOuterSeq = "";
			String strDimGroup = "";
			String sGroupinNetDim = "";
			String sGroupingNetWhere = "";
			String sNetDie = "";
			
			if("BASE".equals(strSRCTYPE)){
				for(int i=0; i< arrDim.length; i++){
					if("APP_LVL_1_CD".equals(arrDim[i])){
						strDimOuter += ", T1.APP_LVL_1_CD";
						strDimGroup += " + GROUPING(T1.APP_LVL_1_CD)";
						sGroupinNetDim += ", NVL(APP_LVL_1_CD, ' ') AS APP_LVL_1_CD";
						sGroupingNetWhere += " AND A.APP_LVL_1_CD = B.APP_LVL_1_CD ";
						sNetDie += " AND A.APP_LVL_1_CD = NVL(T1.APP_LVL_1_CD, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.APP_LVL_1_CD END AS APP_LVL_1_CD";
						else{
							strDimOuterSubTotal += ", T1.APP_LVL_1_CD";		
						}		
						
						strDimOuterSeq += ", (SELECT APP_LVL_1_SEQ FROM RPI_APP_LVL_1_CD_VW WHERE APP_LVL_1_CD = T1.APP_LVL_1_CD||'00') AS APP_LVL_1_CD_SEQ";
						sOrderBy += ", TO_NUMBER(APP_LVL_1_CD_SEQ), NVL(APP_LVL_1_CD, '') ";
						} else if("TECH_CD".equals(arrDim[i])){
						strDimOuter += ", T1.TECH_CD";
						strDimGroup += " + GROUPING(T1.TECH_CD)";
						sGroupinNetDim += ", NVL(TECH_CD, ' ') AS TECH_CD";
						sGroupingNetWhere += " AND A.TECH_CD = B.TECH_CD ";
						sNetDie += " AND A.TECH_CD = NVL(T1.TECH_CD, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.TECH_CD END AS TECH_CD";
						else{
							strDimOuterSubTotal += ", T1.TECH_CD";		
						}		
						
						strDimOuterSeq += ", (SELECT TECH_SEQ FROM RPI_TECH_CD_VW WHERE TECH_CD = T1.TECH_CD) AS TECH_CD_SEQ";
						sOrderBy += ", TO_NUMBER(TECH_CD_SEQ), NVL(TECH_CD, '') ";
						} else if("FAB_DEN_CD".equals(arrDim[i])){
						strDimOuter += ", T1.FAB_DEN_CD";
						strDimGroup += " + GROUPING(T1.FAB_DEN_CD)";
						sGroupinNetDim += ", NVL(FAB_DEN_CD, ' ') AS FAB_DEN_CD";
						sGroupingNetWhere += " AND A.FAB_DEN_CD = B.FAB_DEN_CD ";
						sNetDie += " AND A.FAB_DEN_CD = NVL(T1.FAB_DEN_CD, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.FAB_DEN_CD END AS FAB_DEN_CD";
						else{
							strDimOuterSubTotal += ", T1.FAB_DEN_CD";		
						}		
						
						strDimOuterSeq += ", (SELECT FAB_DEN_SEQ FROM RPI_FAB_DEN_CD_VW WHERE FAB_DEN_CD = T1.FAB_DEN_CD) AS FAB_DEN_CD_SEQ";
						sOrderBy += ", TO_NUMBER(FAB_DEN_CD_SEQ), NVL(FAB_DEN_CD, '') ";
						} else if("CHG_PROD_MODE_CD".equals(arrDim[i])){
						strDimOuter += ", T1.CHG_PROD_MODE_CD";
						strDimGroup += " + GROUPING(T1.CHG_PROD_MODE_CD)";
						sGroupinNetDim += ", NVL(CHG_PROD_MODE_CD, ' ') AS CHG_PROD_MODE_CD";
						sGroupingNetWhere += " AND A.CHG_PROD_MODE_CD = B.CHG_PROD_MODE_CD ";
						sNetDie += " AND A.CHG_PROD_MODE_CD = NVL(T1.CHG_PROD_MODE_CD, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.CHG_PROD_MODE_CD END AS CHG_PROD_MODE_CD";
						else{
							strDimOuterSubTotal += ", T1.CHG_PROD_MODE_CD";		
						}		
						
						strDimOuterSeq += ", (SELECT SORT_SEQ FROM RPI_PROD_MODE_CD_VW WHERE SCM_FAMILY_CD = T1.SCM_FAMILY_CD AND CHG_PROD_MODE_CD = T1.CHG_PROD_MODE_CD) AS CHG_PROD_MODE_CD_SEQ";
						sOrderBy += ", TO_NUMBER(CHG_PROD_MODE_CD_SEQ), NVL(CHG_PROD_MODE_CD, '') ";
						} else if("PKG_TYP_CD2".equals(arrDim[i])){
						strDimOuter += ", T1.PKG_TYP_CD2";
						strDimGroup += " + GROUPING(T1.PKG_TYP_CD2)";
						sGroupinNetDim += ", NVL(PKG_TYP_CD2, ' ') AS PKG_TYP_CD2";
						sGroupingNetWhere += " AND A.PKG_TYP_CD2 = B.PKG_TYP_CD2 ";
						sNetDie += " AND A.PKG_TYP_CD2 = NVL(T1.PKG_TYP_CD2, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.PKG_TYP_CD2 END AS PKG_TYP_CD2";
						else{
							strDimOuterSubTotal += ", T1.PKG_TYP_CD2";		
						}		
						
						strDimOuterSeq += ", (SELECT STACK_SEQ FROM RPI_STACK_CD_VW WHERE STACK_CD = T1.PKG_TYP_CD2) AS PKG_TYP_CD2_SEQ";
						sOrderBy += ", CASE WHEN TO_NUMBER(PKG_TYP_CD2_SEQ) IS NOT NULL THEN PKG_TYP_CD2_SEQ THEN PKG_TYP_CD2 IS NULL OR NVL(PKG_TYP_CD2, '') = '' THEN ' ' ELSE PKG_TYP_CD2 END DESC";
						} else if("MOD_DEN_CD".equals(arrDim[i])){
						strDimOuter += ", T1.MOD_DEN_CD";
						strDimGroup += " + GROUPING(T1.MOD_DEN_CD)";
						sGroupinNetDim += ", NVL(MOD_DEN_CD, ' ') AS MOD_DEN_CD";
						sGroupingNetWhere += " AND A.MOD_DEN_CD = B.MOD_DEN_CD ";
						sNetDie += " AND A.MOD_DEN_CD = NVL(T1.MOD_DEN_CD, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.MOD_DEN_CD END AS MOD_DEN_CD";
						else{
							strDimOuterSubTotal += ", T1.MOD_DEN_CD";		
						}		
						
						strDimOuterSeq += ", (SELECT MOD_DEN_SEQ FROM RPI_MOD_DEN_CD_VW WHERE MOD_DEN_CD = T1.MOD_DEN_CD) AS MOD_DEN_CD_SEQ";
						sOrderBy += ", CASE WHEN INSTR(MOD_DEN_CD, 'GB') > 0 THEN TO_NUMBER(SUBSTR(MOD_DEN_CD, 1, INSTR(MOD_DEN_CD, 'GB') -1)) ELSE 0 END DESC ";
						sOrderBy += ", CASE WHEN INSTR(MOD_DEN_CD, 'GB') > 0 THEN TO_NUMBER(NVL(REPLACE(SUBSTR(MOD_DEN_CD, 1, INSTR(MOD_DEN_CD, 'GB') +2), 'G', ''), '0')) ELSE 0 END DESC, TO_NUMBER(MOD_DEN_CD_SEQ) ";						
						} else if("GBN_CD".equals(arrDim[i])){
						strDimOuter += ", T1.DATA_GBN_CD";
						strDimGroup += " + GROUPING(T1.DATA_GBN_CD)";
						sGroupinNetDim += ", NVL(DATA_GBN_CD, ' ') AS DATA_GBN_CD";
						sGroupingNetWhere += " AND A.DATA_GBN_CD = B.DATA_GBN_CD ";
						sNetDie += " AND A.DATA_GBN_CD = NVL(T1.DATA_GBN_CD, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.DATA_GBN_CD END AS DATA_GBN_CD";
						else{
							strDimOuterSubTotal += ", T1.DATA_GBN_CD";		
						}		
						
						
						sOrderBy += ", NVL(DATA_GBN_CD, '')";
						} else if("SSD_MODEL_CD".equals(arrDim[i])){
						strDimOuter += ", T1.SSD_MODEL_NM";
						strDimGroup += " + GROUPING(T1.SSD_MODEL_NM)";
						sGroupinNetDim += ", NVL(SSD_MODEL_NM, ' ') AS SSD_MODEL_NM";
						sGroupingNetWhere += " AND A.SSD_MODEL_NM = B.SSD_MODEL_NM ";
						sNetDie += " AND A.SSD_MODEL_NM = NVL(T1.SSD_MODEL_NM, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.SSD_MODEL_NM END AS SSD_MODEL_NM";
						else{
							strDimOuterSubTotal += ", T1.SSD_MODEL_NM";		
						}		
						
						
						sOrderBy += ", NVL(SSD_MODEL_NM, '')";
						} else if("UFS_IF_NM".equals(arrDim[i])){
						strDimOuter += ", T1.UFS_IF_NM";
						strDimGroup += " + GROUPING(T1.UFS_IF_NM)";
						sGroupinNetDim += ", NVL(UFS_IF_NM, ' ') AS UFS_IF_NM";
						sGroupingNetWhere += " AND A.UFS_IF_NM = B.UFS_IF_NM ";
						sNetDie += " AND A.UFS_IF_NM = NVL(T1.UFS_IF_NM, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.UFS_IF_NM END AS UFS_IF_NM";
						else{
							strDimOuterSubTotal += ", T1.UFS_IF_NM";		
						}		
						
						
						sOrderBy += ", CASE WHEN UFS_IF_NM IS NULL OR TRIM(UFS_IF_NM) = '' THEN 2 ELSE 1 END, NVL(TRIM(UFS_IF_NM), '') DESC";
						} else if("SSD_IF_NM".equals(arrDim[i])){
						strDimOuter += ", T1.SSD_IF_NM";
						strDimGroup += " + GROUPING(T1.SSD_IF_NM)";
						sGroupinNetDim += ", NVL(SSD_IF_NM, ' ') AS SSD_IF_NM";
						sGroupingNetWhere += " AND A.SSD_IF_NM = B.SSD_IF_NM ";
						sNetDie += " AND A.SSD_IF_NM = NVL(T1.SSD_IF_NM, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.SSD_IF_NM END AS SSD_IF_NM";
						else{
							strDimOuterSubTotal += ", T1.SSD_IF_NM";		
						}		
						
						
						sOrderBy += ", CASE WHEN SSD_IF_NM IS NULL OR TRIM(SSD_IF_NM) = '' THEN 2 ELSE 1 END, NVL(TRIM(SSD_IF_NM), '') DESC";
						} else if("PRFT_GBN1".equals(arrDim[i])){
						strDimOuter += ", T1.PRFT_GBN1";
						strDimGroup += " + GROUPING(T1.PRFT_GBN1)";
						sGroupinNetDim += ", NVL(PRFT_GBN1, ' ') AS PRFT_GBN1";
						sGroupingNetWhere += " AND A.PRFT_GBN1 = B.PRFT_GBN1 ";
						sNetDie += " AND A.PRFT_GBN1 = NVL(T1.PRFT_GBN1, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.PRFT_GBN1 END AS PRFT_GBN1";
						else{
							strDimOuterSubTotal += ", T1.PRFT_GBN1";		
						}		
						
						strDimOuterSeq += ", (SELECT STACK_SEQ FROM RPI_STACK_CD_VW WHERE STACK_CD = T1.PRFT_GBN1) AS PRFT_GBN1_SEQ";
						sOrderBy += ", CASE WHEN TO_NUMBER(PRFT_GBN1_SEQ) IS NOT NULL THEN PRFT_GBN1_SEQ WHEN PRFT_GBN1 IS NULL OR NVL(PRFT_GBN1, '') = '' THEN ' ' END DESC, CASE  WHEN REGEXP_LIKE(PRFT_GBN1, '[0-9]+(\\.[0-9]+)?') THEN TO_NUMBER(REGEXP_SUBSTR(NVL(PRFT_GBN1,0), '[0-9]+(\\.[0-9]+)?')) ELSE NULL END DESC, NVL(PRFT_GBN1, 0) DESC";
						} else if("PRFT_GBN2".equals(arrDim[i])){
						strDimOuter += ", T1.PRFT_GBN2";
						strDimGroup += " + GROUPING(T1.PRFT_GBN2)";
						sGroupinNetDim += ", NVL(PRFT_GBN2, ' ') AS PRFT_GBN2";
						sGroupingNetWhere += " AND A.PRFT_GBN2 = B.PRFT_GBN2 ";
						sNetDie += " AND A.PRFT_GBN2 = NVL(T1.PRFT_GBN2, ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1.PRFT_GBN2 END AS PRFT_GBN2";
						else{
							strDimOuterSubTotal += ", T1.PRFT_GBN2";		
						}		
						
						strDimOuterSeq += ", (SELECT STACK_SEQ FROM RPI_STACK_CD_VW WHERE STACK_CD = REPLACE(T1.PRFT_GBN2,'MCP_','')) AS PRFT_GBN2_SEQ";
						sOrderBy += ", CASE WHEN TO_NUMBER(PRFT_GBN2_SEQ) IS NOT NULL THEN PRFT_GBN2_SEQ WHEN PRFT_GBN2 IS NULL OR NVL(PRFT_GBN2, '') = '' THEN ' ' END DESC, CASE  WHEN REGEXP_LIKE(PRFT_GBN2, '[0-9]+(\\.[0-9]+)?') THEN TO_NUMBER(REGEXP_SUBSTR(NVL(PRFT_GBN2,0), '[0-9]+(\\.[0-9]+)?')) ELSE NULL END DESC, NVL(PRFT_GBN2, 0)";
						} else {
						strDimOuter += ", T1." + arrDim[i];
						strDimGroup += " + GROUPING(T1." + arrDim[i] +")";
						sGroupinNetDim += ", NVL(" + arrDim[i] +", ' ') AS " + arrDim[i];
						sGroupingNetWhere += " AND A." + arrDim[i] +" = B." + arrDim[i] +" ";
						sNetDie += " AND A." + arrDim[i] +" = NVL(T1." + arrDim[i] +", ' ')";
						
						if(i == 0){
							strDimOuterSubTotal += ", CASE WHEN MAX(GRP_ID) OVER() = GRP_ID THEN 'G-Total' ELSE T1." + arrDim[i] +" END AS " + arrDim[i];
						else{
							strDimOuterSubTotal += ", T1." + arrDim[i];	
						}		
						
						
						sOrderBy += ", NVL(" + arrDim[i] +", '') ";
					}
				}	
			}			
			
			sNetDie += " AND A.GRP_ID = NVL(T1.GRP_ID, 0)";			
			
			if("COLCHG".equals(strSRCTYPE)){
				sNetDie += " AND A.SCM_FAMILY_CD = NVL(T1.SCM_FAMILY_CD, ' ') AND A.UPPER_CD1 = NVL(T1.UPPER_CD1, ' ')";
			}else if("UPPER_CD2".equals(strSRCTYPE)){
				sNetDie += " AND A.SCM_FAMILY_CD = NVL(T1.SCM_FAMILY_CD, ' ') AND A.UPPER_CD1 = NVL(T1.UPPER_CD1, ' ') AND A.UPPER_CD2 = NVL(T1.UPPER_CD2, ' ') ";
			}	
			
			requestData.putField("GROUPING_NETDIE1", strDimOuter.replaceAll("T1.", "A.").replaceFirst(", ",""));
			requestData.putField("GROUPING_NETDIE2", sGroupinNetDim.replaceFirst(", ",""));
			requestData.putField("GROUPING_NETDIE3", strDimOuter.replaceAll("T1.", "A.").replaceFirst(", ",""));
			requestData.putField("GROUPING_NETDIE4", strDimGroup.replaceAll("T1.", "A.").replaceFirst("\\+",",")+ " AS GRP_ID");
			requestData.putField("GROUPING_NETDIE5", strDimGroup.replaceAll("T1.", "").replaceFirst("\\+",",")+ " AS GRP_ID");
			
			requestData.putField("GROUPING_WHERE", sGroupingNetWhere);
			requestData.putField("NETDIE_WHERE", sNetDie);
			
			if("BASE".equals(strSRCTYPE)){
				requestData.putField("DIM_OUTER", strDimOuter.substring(2));
				requestData.putField("DIM_GROUP", strDimGroup.substring(3));
				requestData.putField("DIM_OUTER_SUB_TOTAL", strDimOuterSubTotal.substring(2));
				requestData.putField("DIM_OUTER_SEQ", strDimOuterSeq);
				requestData.putField("ORDER_BY", sOrderBy.substring(2));
			} else {
				requestData.putField("DIM_OUTER", "");
				requestData.putField("DIM_GROUP", "");
				requestData.putField("DIM_OUTER_SUB_TOTAL", "");
				requestData.putField("DIM_OUTER_SEQ", "");
				requestData.putField("ORDER_BY", "");
			}
			
			if( strTechCd != null && !"".equals(strTechCd) ){
				String[] arr = strTechCd.split(",");
				List<Object> list = new ArrayList<object>();
				for (int i=0; i<arr.length; i++){
					list.add(arr[i].trim());
				}
				paramMap.put("ARR_TECH_CD", list);
			}
			if( strFabDenCd != null && !"".equals(strFabDenCd) ){
				String[] arr = strFabDenCd.split(",");
				List<Object> list = new ArrayList<object>();
				for (int i=0; i<arr.length; i++){
					list.add(arr[i].trim());
				}
				paramMap.put("ARR_FAB_DEN_CD", list);
			}
			if( strChgProdModCd != null && !"".equals(strChgProdModCd) ){
				String[] arr = strChgProdModCd.split(",");
				List<Object> list = new ArrayList<object>();
				for (int i=0; i<arr.length; i++){
					list.add(arr[i].trim());
				}
				paramMap.put("ARR_CHG_PROD_MODE_CD", list);
			}
			if( strFabDenCd != null && !"".equals(strFabDenCd) ){
				String[] arr = strFabDenCd.split(",");
				List<Object> list = new ArrayList<object>();
				for (int i=0; i<arr.length; i++){
					list.add(arr[i].trim());
				}
				paramMap.put("ARR_FAB_DEN_CD", list);
			}
			if( strAppLvl1Cd != null && !"".equals(strAppLvl1Cd) ){
				String[] arr = strAppLvl1Cd.split(",");
				List<Object> list = new ArrayList<object>();
				for (int i=0; i<arr.length; i++){
					list.add(arr[i].trim());
				}
				paramMap.put("ARR_APP_LVL_1_CD", list);
			}
			if( strPkgtypCd2 != null && !"".equals(strPkgtypCd2) ){
				String[] arr = strPkgtypCd2.split(",");
				List<Object> list = new ArrayList<object>();
				for (int i=0; i<arr.length; i++){
					list.add(arr[i].trim());
				}
				paramMap.put("ARR_PKG_TYP_CD2", list);
			}
			if( strCellTypCd != null && !"".equals(strCellTypCd) ){
				String[] arr = strCellTypCd.split(",");
				List<Object> list = new ArrayList<object>();
				for (int i=0; i<arr.length; i++){
					list.add(arr[i].trim());
				}
				paramMap.put("ARR_CELL_LAYER_TYP_CD", list);
			}
			
			IRecordSet rdPivot = null;
			rdPivot = du.dPLA03902(requestData, onlineCtx).getRecordSet("PIVOT_LIST");
			
			paramMap.put("PIVOT_STR", (String)rdPivot.get(0, "PIVOT_STR"));
			String sConvQty = (String)rdPivot.get(0, "WF_CONV_QTY_SALE_PLN_ST_O");
			String[] sArrConvQty = sConvQty.split(",");
			List<String> sListConvQty = new ArrayList<>();
			
			String sSomEqQty = (String)rdPivot.get(0, "SOM_EQ_QTY_SALE_PLN_ST_O");
			String[] sArrSomEqQty = sSomEqQty.split(",");
			List<String> sListSomEqQty = new ArrayList<>();
			
			String sCum2Yld = (String)rdPivot.get(0, "CUM2_YLD_MASTER_DATA_ST_O");
			String[] sArrCum2Yld = sCum2Yld.split(",");
			List<String> sListCum2Yld = new ArrayList<>();
			
			String sOddCum2Yld = (String)rdPivot.get(0, "ODD_CUM2_YLD_MASTER_DATA_ST_O");
			String[] sArrOddCum2Yld = sOddCum2Yld.split(",");
			List<String> sListOddCum2Yld = new ArrayList<>();
			
			String sGoodDie = (String)rdPivot.get(0, "ODD_GOOD_DIE_MASTER_DATA_ST_O");
			sGoodDie = sGoodDie.replaceAll("ODD_GOOD_DIE_MASTER_DATA", "GOOD_DIE_MASTER_DATA");
			String[] sArrGoodDie = sGoodDie.split(",");
			List<String> sListGoodDie = new ArrayList<>();
			
			String sOddGoodDie = (String)rdPivot.get(0, "ODD_GOOD_DIE_MASTER_DATA_ST_O");			
			String[] sArrOddGoodDie = sOddGoodDie.split(",");
			List<String> sListOddGoodDie = new ArrayList<>();
			
			
			String sSomDieQty = (String)rdPivot.get(0, "SOM_DIE_QTY_SALE_PLN_ST_O");
			String[] sArrSomDieQty = sSomDieQty.split(",");
			List<String> sListSomDieQty = new ArrayList<>();
			
			for(String s : sArrConvQty){
				if(s != null && !s.isEmpty()) sListConvQty.add(s);
			}
			
			for(String s : sArrSomEqQty){
				if(s != null && !s.isEmpty()) sListSomEqQty.add(s);
			}
			
			for(String s : sArrCum2Yld){
				if(s != null && !s.isEmpty()) sListCum2Yld.add(s);
			}
			
			for(String s : sArrOddCum2Yld){
				if(s != null && !s.isEmpty()) sListOddCum2Yld.add(s);
			}
			
			for(String s : sArrGoodDie){
				if(s != null && !s.isEmpty()) sListGoodDie.add(s);
			}
			
			for(String s : sArrOddGoodDie){
				if(s != null && !s.isEmpty()) sListOddGoodDie.add(s);
			}
			
			for(String s : sArrSomDieQty){
				if(s != null && !s.isEmpty()) sListSomDieQty.add(s);
			}
			
			StringBuilder sCumSb = new StringBuilder();
			StringBuilder sGoodDieSb = new StringBuilder();
			String sSchTyp = requestData.getField("SEARCH_TYPE");
			String sYear = requestData.getField("YEAR");
			int sTechGrpId = Integer.valueOf(requestData.getField("TECH_GRP_ID"));
			
			if("ODD".equals(sSchTyp)){
				for(int i=0; i<sListConvQty.size(); i++){
					sCumSb.append(", CASE WHEN " + sListConvQty.get(i) + " = 0 THEN 0 ELSE CASE WHEN MAX(GRP_ID) OVER()-1 <= GRP_ID OR GRP_ID = " + sTechGrpId);
					sCumSb.append(" THEN CASE WHEN (SELECT A.FAB_DEN_CD_NUM FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") = 0 THEN 0 ELSE ");
					sCumSb.append("(" + sListSomEqQty.get(i));
					sCumSb.append(" / " + sListConvQty.get(i) + ") / (SELECT A.FAB_DEN_CD_NUM FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") * 100 END ");
					sCumSb.append(" ELSE CASE WHEN GRP_ID = 0 THEN " + sListCum2Yld.get(i) + " ELSE CASE WHEN (SELECT A.NET_DIE_300_CNT FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") = 0 THEN 0 ELSE " + sListSomDieQty.get(i) + " / " + sListConvQty.get(i) + " / (SELECT A.NET_DIE_300_CNT FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") * 100");
					sCumSb.append(" END END END END AS " + sListCum2Yld.get(i));
					
					sGoodDieSb.append(", CASE WHEN " + sListConvQty.get(i) + " = 0 THEN 0 ELSE CASE WHEN MAX(GRP_ID) OVER()-1 <= GRP_ID OR GRP_ID = " + sTechGrpId + " THEN TO_CHAR(" + sListSomEqQty.get(i));
					sGoodDieSb.append(" / " + sListConvQty.get(i) + " ) ELSE CASE WHEN GRP_ID > 0 THEN CASE WHEN " + sListConvQty.get(i) + " = 0 THEN 0 ELSE TO_CHAR(" + sListSomDieQty.get(i) + " / " +  sListConvQty.get(i) + ") END ELSE " + sListGoodDie.get(i));
					sGoodDieSb.append(" END END END AS " + sListGoodDie.get(i));
				)
			}else{
				for(int i=0; i<sListConvQty.size(); i++){
					sCumSb.append(", CASE WHEN " + sListConvQty.get(i) + " = 0 THEN 0 ELSE CASE GRP_ID > 0 THEN CASE WHEN ");
					sCumSb.append(" THEN CASE WHEN (SELECT A.FAB_DEN_CD_NUM FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") = 0 THEN 0 ELSE ");
					sCumSb.append("(" + sListSomEqQty.get(i));
					sCumSb.append(" / " + sListConvQty.get(i) + ") / (SELECT A.FAB_DEN_CD_NUM FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") * 100 END ");
					sCumSb.append(" ELSE CASE WHEN GRP_ID = 0 THEN " + sListCum2Yld.get(i) + " ELSE CASE WHEN (SELECT A.NET_DIE_300_CNT FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") = 0 THEN 0 ELSE " + sListSomDieQty.get(i) + " / " + sListConvQty.get(i) + " / (SELECT A.NET_DIE_300_CNT FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") * 100");
					sCumSb.append(" END END END END AS " + sListCum2Yld.get(i));
					
					sGoodDieSb.append(", CASE WHEN " + sListConvQty.get(i) + " = 0 THEN 0 ELSE CASE WHEN MAX(GRP_ID) OVER()-1 <= GRP_ID OR GRP_ID = " + sTechGrpId + " THEN TO_CHAR(" + sListSomEqQty.get(i));
					sGoodDieSb.append(" / " + sListConvQty.get(i) + " ) ELSE CASE WHEN GRP_ID > 0 THEN CASE WHEN " + sListConvQty.get(i) + " = 0 THEN 0 ELSE TO_CHAR(" + sListSomDieQty.get(i) + " / " +  sListConvQty.get(i) + ") END ELSE " + sListGoodDie.get(i));
					sGoodDieSb.append(" END END END AS " + sListGoodDie.get(i));
				}
			}
			
			paramMap.put("CUM2_COL", sCumSb.toString());
			paramMap.put("GOOD_DIE_COL", sGoodDieSb.toString());
			
			String[] sParamColumn = {"CUM2_YLD_MASTER_DATA", "ODD_CUM2_YLD_MASTER_DATA", "GOOD_DIE_MASTER_DATA", "ODD_GOOD_DIE_MASTER_DATA", "WF_CONV_QTY_SALE_PLN", "SOM_EQ_QTY_SALE_PLN", "SOM_DIE_QTY_SALE_PLN",
					"ORG_QTY_SALE_PLN", "SALE_AMT_SALE_PLN", "ASP_SALE_PLN", "SALE_GRAV_SALE_PLN", "QTY_GRAV_SALE_PLN", "SALES_PROF_GRAV", "SALE_WF_SLS_PROF",
					"CNTRB_PROF_WF_SLS_PROF", "CASH_PROF_WF_SLS_PROF", "SALE_PROF_WF_SLS_PROF", "SALES_PROF_WF_SLS_PROF", "SALE_EQ_PROF", "CNTRB_PROF_EQ_PROF", 
					"CASH_PROF_EQ_PROF", "SALE_PROF_EQ_PROF", "SALES_PROF_EQ_PROF", "SALE_DIE_PROF", "CNTRB_PROF_DIE_PROF", "CASH_PROF_DIE_PROF", "SALE_PROF_DIE_PROF", "SALES_PROF_DIE_PROF", 
					"SALE_PROD_PROF", "CNTRB_PROF_PROD_PROF", "CASH_PROF_PROD_PROF", "SALE_PROF_PROD_PROF", "SALES_PROF_PROD_PROF", "SALE_YR_PROF", "CNTRB_PROF_YR_PROF", "CASH_PROF_YR_PROF", 
					"SALE_PROF_YR_PROF", "SALES_PROF_YR_PROF", "VAR_COST_WF_SLS_COST", "CASH_COST_WF_SLS_COST", "COGS_COST_WF_SLS_COST", "COO_COST_WF_SLS_COST", "COO_PROF_RATE_WF", 
					"VAR_COST_EQ_COST", "CASH_COST_EQ_COST", "COGS_COST_EQ_COST", "COO_COST_EQ_COST", "COO_PROF_RATE_EQ",
					"VAR_COST_DIE_COST", "CASH_COST_DIE_COST", "COGS_COST_DIE_COST", "COO_COST_DIE_COST", "COO_PROF_RATE_DIE",
					"VAR_COST_PROD_COST", "CASH_COST_PROD_COST", "COGS_COST_PROD_COST", "COO_COST_PROD_COST", "COO_PROF_RATE_PROD",
			"VAR_COST_YR_COST", "CASH_COST_YR_COST", "COGS_COST_YR_COST", "COO_COST_YR_COST", "COO_PROF_RATE_YR"};
			
			for(String sColumn : sParamColumn) {
				paramMap.put(sColumn			, (String)rdPivot.get(0, sColumn));
				paramMap.put(sColumn + "_ST" 	, (String)rdPivot.get(0, sColumn+"_ST"));
				if(!sColumn.equals("CUM2_YLD_MASTER_DATA") && !sColumn.equals("GOOD_DIE_MASTER_DATA") && 
				   !sColumn.equals("ODD_CUM2_YLD_MASTER_DATA") && !sColumn.equals("ODD_GOOD_DIE_MASTER_DATA") && 
				   !sColumn.equals("COO_PROF_RATE_WF") && !sColumn.equals("COO_PROF_RATE_EQ") && 
				   !sColumn.equals("COO_PROF_RATE_DIE") && !sColumn.equals("COO_PROF_RATE_PROD")) {
					   paramMap.put(sColumn + "_ST_O"		, (String)rdPivot.get(0, sColumn + "_ST_O"));
				}
			}
			
			if("Y".equals(requestData.getField("COO_PROF_RATE_WF_YN"))) {
				String sCooProfRateWf1 = (String)rdPivot.get(0, "COO_PROF_RATE_WF_ST_01");
				String[] sArrCooProfRateWf1 = sCooProfRateWf1.split("@");
				List<String> sListCooProfRateWf1 = new ArrayList<>();
				for(String s: sArrCooProfRateWf1){
					if(s != null && !s.isEmpty()) sListCooProfRateWf1.add(s);
				}
				
				String sCooProfRateWf2 = (String)rdPivot.get(0, "COO_PROF_RATE_WF_ST_02");
				String[] sArrCooProfRateWf2 = sCooProfRateWf2.split("@");
				List<String> sListCooProfRateWf2 = new ArrayList<>();
				for(String s: sArrCooProfRateWf2){
					if(s != null && !s.isEmpty()) sListCooProfRateWf2.add(s);
				}
				String sCooProfRateWf = "";
				for(int i=0; i<sListCooProfRateWf1.size(); i++){
					sCooProfRateWf += sListCooProfRateWf1.get(i) + sListCooProfRateWf2.get(i);
				}
				
				paramMap.put("COO_PROF_RATE_WF_COL", sCooProfRateWf);
				system.out.println(sCooProfRateWf);
			}
			
			if("Y".equals(requestData.getField("COO_PROF_RATE_EQ_YN"))) {
				String sCooProfRateEq1 = (String)rdPivot.get(0, "COO_PROF_RATE_EQ_ST_01");
				String[] sCooProfRateEq1 = sCooProfRateEq1.split("@");
				List<String> sListCooProfRateEq1 = new ArrayList<>();
				for(String s: sCooProfRateEq1){
					if(s != null && !s.isEmpty()) sListCooProfRateEq1.add(s);
				}
				
				String sCooProfRateEq2 = (String)rdPivot.get(0, "COO_PROF_RATE_EQ_ST_02");
				String[] sArrCooProfRateEq2 = sCooProfRateEq2.split("@");
				List<String> sListCooProfRateEq2 = new ArrayList<>();
				for(String s: sArrCooProfRateEq2){
					if(s != null && !s.isEmpty()) sListCooProfRateEq2.add(s);
				}
				String sCooProfRateEq = "";
				for(int i=0; i<sListCooProfRateEq1.size(); i++){
					sCooProfRateEq += sListCooProfRateEq1.get(i) + sListCooProfRateEq2.get(i);
				}
				
				paramMap.put("COO_PROF_RATE_EQ_COL", sCooProfRateEq);
				system.out.println(sCooProfRateEq);
			}
			
			if("Y".equals(requestData.getField("COO_PROF_RATE_DIE_YN"))) {
				String sCooProfRateDie1 = (String)rdPivot.get(0, "COO_PROF_RATE_DIE_ST_01");
				String[] sArrCooProfRateDie1 = sCooProfRateDie1.split("@");
				List<String> sListCooProfRateDie1 = new ArrayList<>();
				for(String s: sArrCooProfRateDie1){
					if(s != null && !s.isEmpty()) sListCooProfRateDie1.add(s);
				}
				
				String sCooProfRateDie2 = (String)rdPivot.get(0, "COO_PROF_RATE_DIE_ST_02");
				String[] sArrCooProfRateDie2 = sCooProfRateDie2.split("@");
				List<String> sListCooProfRateDie2 = new ArrayList<>();
				for(String s: sArrCooProfRateDie2){
					if(s != null && !s.isEmpty()) sListCooProfRateDie2.add(s);
				}
				String sCooProfRateDie = "";
				for(int i=0; i<sListCooProfRateDie1.size(); i++){
					sCooProfRateDie += sListCooProfRateDie1.get(i) + sListCooProfRateDie2.get(i);
				}
				
				paramMap.put("COO_PROF_RATE_DIE_COL", sCooProfRateDie);
				system.out.println(sCooProfRateDie);
			}
			
			if("Y".equals(requestData.getField("COO_PROF_RATE_PROD_YN"))) {
				String sCooProfRateProd1 = (String)rdPivot.get(0, "COO_PROF_RATE_PROD_ST_01");
				String[] sArrCooProfRateProd1 = sCooProfRateProd1.split("@");
				List<String> sListCooProfRateProd1 = new ArrayList<>();
				for(String s: sArrCooProfRateProd1){
					if(s != null && !s.isEmpty()) sListCooProfRateProd1.add(s);
				}
				
				String sCooProfRateProd2 = (String)rdPivot.get(0, "COO_PROF_RATE_PROD_ST_02");
				String[] sArrCooProfRateProd2 = sCooProfRateProd2.split("@");
				List<String> sListCooProfRateProd2 = new ArrayList<>();
				for(String s: sArrCooProfRateProd2){
					if(s != null && !s.isEmpty()) sListCooProfRateProd2.add(s);
				}
				String sCooProfRateProd = "";
				for(int i=0; i<sListCooProfRateProd1.size(); i++){
					sCooProfRateProd += sListCooProfRateProd1.get(i) + sListCooProfRateProd2.get(i);
				}
				
				paramMap.put("COO_PROF_RATE_PROD_COL", sCooProfRateProd);
				system.out.println(sCooProfRateProd);
			}
			requestData.putFieldMap(paramMap);
			IRecordSet rs = null;
			
			IRecordSet sDateTimeMap = du.dPLA03905(requestData, onlineCtx).getRecordSet("DATETIME_MAP");
			
			if(strChkSubTotal.equals("Y")) rs = du.dPLA03904(requestData, onlineCtx).getRecordSet("MAIN_LIST");
			else						   rs = du.dPLA03903(requestData, onlineCtx).getRecordSet("MAIN_LIST");
			
			responseData.putRecordset("DATETIME_MAP", sDateTimeMap);
			responseData.putRecordset("MAIN_LIST", rs);
			
		} catch (BizRuntimeException be){
			throw be;
		} catch (Exception e){
			throw new BizRuntimeException("E0052", e);
		}
		return responseData;
	}
	
	/**
	 * <pre> REV 조회 </pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet fPLA039QrySelectRev(IDataSet requestData, IOnlineContext onlineCtx){
		IDataSet responseData = new DataSet();
		try{
			DPLA039 du = (DPLA039) lookupDataUnit(DPLA039.class);
			IRecordSet rs = du.dPLA03901(requestData, onlineCtx).getRecordSet("REV_LIST");
			responseData.putRecordset("REV_LIST", rs);
		} catch (BizRuntimeException be){
			throw be;
		} catch (Exception e){
			throw new BizRuntimeException("E0052", e);
		}
		return responseData;	
	}
			
	/**
	 * <pre> REV 기간 조회 </pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet fPLA039QrySelectRevPeriod(IDataSet requestData, IOnlineContext onlineCtx){
		IDataSet responseData = new DataSet();
		try{
			DPLA039 du = (DPLA039) lookupDataUnit(DPLA039.class);
			IRecordSet rs = du.dPLA03906(requestData, onlineCtx).getRecordSet("MAIN_LIST");
			responseData.putRecordset("MAIN_LIST", rs);
		} catch (BizRuntimeException be){
			throw be;
		} catch (Exception e){
			throw new BizRuntimeException("E0052", e);
		}
		return responseData;	
	}
}