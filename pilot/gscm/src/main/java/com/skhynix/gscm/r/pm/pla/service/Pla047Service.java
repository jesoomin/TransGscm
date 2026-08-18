package com.skhynix.gscm.r.pm.pla.service;

import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;

import java.util.Map;

@Service
public class Pla047Service {

    @Autowired
    private Pla047Store store;

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA047QrySelectMainList(Map<String, Object> request) {
	Map<String, Object> responseData = new java.util.HashMap<String, Object>();
	
	try{
		Map<String,Object> paramMap = request;
		
		String strDim = (String) request.get("DIM");
		String sOrderBy = "";
		String strTechCd		= (String) request.get("TECH_CD");
		String strFabDenCd		= (String) request.get("FAB_DEN_CD");
		String strChgProdModCd	= (String) request.get("CHG_PROD_MODE_CD");
		String strAppLvl1Cd		= (String) request.get("APP_LVL_1_CD");
		String strPkgtypCd2		= (String) request.get("PKG_TYP_CD2");
		String strCellTypCd		= (String) request.get("CELL_LAYER_TYP_CD");
		String strSRCTYPE		= (String) request.get("SRCTYPE");
		String strChkSubTotal	= (String) request.get("CHK_SUBTOTAL");
		
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
					// FIXME(원본 버그): 원본의 if 블록에 중괄호/else 구문이 깨져 있음
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
		
		request.put("GROUPING_NETDIE1", strDimOuter.replaceAll("T1.", "A.").replaceFirst(", ",""));
		request.put("GROUPING_NETDIE2", sGroupinNetDim.replaceFirst(", ",""));
		request.put("GROUPING_NETDIE3", strDimOuter.replaceAll("T1.", "A.").replaceFirst(", ",""));
		request.put("GROUPING_NETDIE4", strDimGroup.replaceAll("T1.", "A.").replaceFirst("\\+",",")+ " AS GRP_ID");
		request.put("GROUPING_NETDIE5", strDimGroup.replaceAll("T1.", "").replaceFirst("\\+",",")+ " AS GRP_ID");
		
		request.put("GROUPING_WHERE", sGroupingNetWhere);
		request.put("NETDIE_WHERE", sNetDie);
		
		if("BASE".equals(strSRCTYPE)){
			request.put("DIM_OUTER", strDimOuter.substring(2));
			request.put("DIM_GROUP", strDimGroup.substring(3));
			request.put("DIM_OUTER_SUB_TOTAL", strDimOuterSubTotal.substring(2));
			request.put("DIM_OUTER_SEQ", strDimOuterSeq);
			request.put("ORDER_BY", sOrderBy.substring(2));
		} else {
			request.put("DIM_OUTER", "");
			request.put("DIM_GROUP", "");
			request.put("DIM_OUTER_SUB_TOTAL", "");
			request.put("DIM_OUTER_SEQ", "");
			request.put("ORDER_BY", "");
		}
		
		if( strTechCd != null && !"".equals(strTechCd) ){
			String[] arr = strTechCd.split(",");
			// FIXME(원본 버그): 원본은 ArrayList<object>()로 선언하여 컴파일 에러
			java.util.List<Object> list = new java.util.ArrayList<Object>();
			for (int i=0; i<arr.length; i++){
				list.add(arr[i].trim());
			}
			paramMap.put("ARR_TECH_CD", list);
		}
		if( strFabDenCd != null && !"".equals(strFabDenCd) ){
			String[] arr = strFabDenCd.split(",");
			// FIXME(원본 버그): 원본은 ArrayList<object>()로 선언하여 컴파일 에러
			java.util.List<Object> list = new java.util.ArrayList<Object>();
			for (int i=0; i<arr.length; i++){
				list.add(arr[i].trim());
			}
			paramMap.put("ARR_FAB_DEN_CD", list);
		}
		if( strChgProdModCd != null && !"".equals(strChgProdModCd) ){
			String[] arr = strChgProdModCd.split(",");
			// FIXME(원본 버그): 원본은 ArrayList<object>()로 선언하여 컴파일 에러
			java.util.List<Object> list = new java.util.ArrayList<Object>();
			for (int i=0; i<arr.length; i++){
				list.add(arr[i].trim());
			}
			paramMap.put("ARR_CHG_PROD_MODE_CD", list);
		}
		if( strFabDenCd != null && !"".equals(strFabDenCd) ){
			String[] arr = strFabDenCd.split(",");
			// FIXME(원본 버그): 원본은 ArrayList<object>()로 선언하여 컴파일 에러
			java.util.List<Object> list = new java.util.ArrayList<Object>();
			for (int i=0; i<arr.length; i++){
				list.add(arr[i].trim());
			}
			paramMap.put("ARR_FAB_DEN_CD", list);
		}
		if( strAppLvl1Cd != null && !"".equals(strAppLvl1Cd) ){
			String[] arr = strAppLvl1Cd.split(",");
			// FIXME(원본 버그): 원본은 ArrayList<object>()로 선언하여 컴파일 에러
			java.util.List<Object> list = new java.util.ArrayList<Object>();
			for (int i=0; i<arr.length; i++){
				list.add(arr[i].trim());
			}
			paramMap.put("ARR_APP_LVL_1_CD", list);
		}
		if( strPkgtypCd2 != null && !"".equals(strPkgtypCd2) ){
			String[] arr = strPkgtypCd2.split(",");
			// FIXME(원본 버그): 원본은 ArrayList<object>()로 선언하여 컴파일 에러
			java.util.List<Object> list = new java.util.ArrayList<Object>();
			for (int i=0; i<arr.length; i++){
				list.add(arr[i].trim());
			}
			paramMap.put("ARR_PKG_TYP_CD2", list);
		}
		if( strCellTypCd != null && !"".equals(strCellTypCd) ){
			String[] arr = strCellTypCd.split(",");
			// FIXME(원본 버그): 원본은 ArrayList<object>()로 선언하여 컴파일 에러
			java.util.List<Object> list = new java.util.ArrayList<Object>();
			for (int i=0; i<arr.length; i++){
				list.add(arr[i].trim());
			}
			paramMap.put("ARR_CELL_LAYER_TYP_CD", list);
		}
		
		Object rdPivot = null;
		rdPivot = store.dPLA04702(request);
		
		// FIXME(원본 버그): 원본은 IRecordSet rdPivot.get(0, ...) 사용, Map 기반으로는 동일 인터페이스가 없어 강제 캐스팅으로 포팅
		paramMap.put("PIVOT_STR", (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("PIVOT_STR"));
		String sConvQty = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("WF_CONV_QTY_SALE_PLN_ST_O");
		String[] sArrConvQty = sConvQty.split(",");
		java.util.List<String> sListConvQty = new java.util.ArrayList<>();
		
		String sSomEqQty = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("SOM_EQ_QTY_SALE_PLN_ST_O");
		String[] sArrSomEqQty = sSomEqQty.split(",");
		java.util.List<String> sListSomEqQty = new java.util.ArrayList<>();
		
		String sCum2Yld = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("CUM2_YLD_MASTER_DATA_ST_O");
		String[] sArrCum2Yld = sCum2Yld.split(",");
		java.util.List<String> sListCum2Yld = new java.util.ArrayList<>();
		
		String sOddCum2Yld = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("ODD_CUM2_YLD_MASTER_DATA_ST_O");
		String[] sArrOddCum2Yld = sOddCum2Yld.split(",");
		java.util.List<String> sListOddCum2Yld = new java.util.ArrayList<>();
		
		String sGoodDie = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("ODD_GOOD_DIE_MASTER_DATA_ST_O");
		sGoodDie = sGoodDie.replaceAll("ODD_GOOD_DIE_MASTER_DATA", "GOOD_DIE_MASTER_DATA");
		String[] sArrGoodDie = sGoodDie.split(",");
		java.util.List<String> sListGoodDie = new java.util.ArrayList<>();
		
		String sOddGoodDie = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("ODD_GOOD_DIE_MASTER_DATA_ST_O");			
		String[] sArrOddGoodDie = sOddGoodDie.split(",");
		java.util.List<String> sListOddGoodDie = new java.util.ArrayList<>();
		
		
		String sSomDieQty = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("SOM_DIE_QTY_SALE_PLN_ST_O");
		String[] sArrSomDieQty = sSomDieQty.split(",");
		java.util.List<String> sListSomDieQty = new java.util.ArrayList<>();
		
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
		String sSchTyp = (String) request.get("SEARCH_TYPE");
		String sYear = (String) request.get("YEAR");
		int sTechGrpId = Integer.valueOf((String) request.get("TECH_GRP_ID"));
		
		if("ODD".equals(sSchTyp)){
			// FIXME(원본 버그): 변수 i가 선언되지 않은 상태로 사용됨
			sCumSb.append(", CASE WHEN " + sListConvQty.get(i) + " = 0 THEN 0 ELSE CASE WHEN MAX(GRP_ID) OVER()-1 <= GRP_ID OR GRP_ID = " + sTechGrpId);
			sCumSb.append(" THEN CASE WHEN (SELECT A.FAB_DEN_CD_NUM FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") = 0 THEN 0 ELSE ");
			sCumSb.append("(" + sListSomEqQty.get(i));
			sCumSb.append(" / " + sListConvQty.get(i) + ") / (SELECT A.FAB_DEN_CD_NUM FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") * 100 END ");
			sCumSb.append(" ELSE CASE WHEN GRP_ID = 0 THEN " + sListCum2Yld.get(i) + " ELSE CASE WHEN (SELECT A.NET_DIE_300_CNT FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") = 0 THEN 0 ELSE " + sListSomDieQty.get(i) + " / " + sListConvQty.get(i) + " / (SELECT A.NET_DIE_300_CNT FROM G_NETDIE A WHERE A.MQHYT = " + sYear + " " + sNetDie + ") * 100");
			sCumSb.append(" END END END END AS " + sListCum2Yld.get(i));
			
			sGoodDieSb.append(", CASE WHEN " + sListConvQty.get(i) + " = 0 THEN 0 ELSE CASE WHEN MAX(GRP_ID) OVER()-1 <= GRP_ID OR GRP_ID = " + sTechGrpId + " THEN TO_CHAR(" + sListSomEqQty.get(i));
			sGoodDieSb.append(" / " + sListConvQty.get(i) + " ) ELSE CASE WHEN GRP_ID > 0 THEN CASE WHEN " + sListConvQty.get(i) + " = 0 THEN 0 ELSE TO_CHAR(" + sListSomDieQty.get(i) + " / " +  sListConvQty.get(i) + ") END ELSE " + sListGoodDie.get(i));
			sGoodDieSb.append(" END END END AS " + sListGoodDie.get(i));
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
			paramMap.put(sColumn			, (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get(sColumn));
			paramMap.put(sColumn + "_ST" 	, (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get(sColumn+"_ST"));
			if(!sColumn.equals("CUM2_YLD_MASTER_DATA") && !sColumn.equals("GOOD_DIE_MASTER_DATA") && 
			   !sColumn.equals("ODD_CUM2_YLD_MASTER_DATA") && !sColumn.equals("ODD_GOOD_DIE_MASTER_DATA") && 
			   !sColumn.equals("COO_PROF_RATE_WF") && !sColumn.equals("COO_PROF_RATE_EQ") && 
			   !sColumn.equals("COO_PROF_RATE_DIE") && !sColumn.equals("COO_PROF_RATE_PROD")) {
				   paramMap.put(sColumn + "_ST_O"		, (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get(sColumn + "_ST_O"));
			}
		}
		
		if("Y".equals((String) request.get("COO_PROF_RATE_WF_YN"))) {
			String sCooProfRateWf1 = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("COO_PROF_RATE_WF_ST_01");
			String[] sArrCooProfRateWf1 = sCooProfRateWf1.split("@");
			java.util.List<String> sListCooProfRateWf1 = new java.util.ArrayList<>();
			for(String s: sArrCooProfRateWf1){
				if(s != null && !s.isEmpty()) sListCooProfRateWf1.add(s);
			}
			
			String sCooProfRateWf2 = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("COO_PROF_RATE_WF_ST_02");
			String[] sArrCooProfRateWf2 = sCooProfRateWf2.split("@");
			java.util.List<String> sListCooProfRateWf2 = new java.util.ArrayList<>();
			for(String s: sArrCooProfRateWf2){
				if(s != null && !s.isEmpty()) sListCooProfRateWf2.add(s);
			}
			String sCooProfRateEq = "";
			// FIXME(원본 버그): sListCooProfRateEq1, sListCooProfRateEq2 미선언 변수 사용
			for(int i=0; i<sListCooProfRateEq1.size(); i++){
				sCooProfRateEq += sListCooProfRateEq1.get(i) + sListCooProfRateEq2.get(i);
			}
			
			paramMap.put("COO_PROF_RATE_EQ_COL", sCooProfRateEq);
			// FIXME(원본 버그): system.out.println 오탈자
			System.out.println(sCooProfRateEq);
		}
		
		if("Y".equals((String) request.get("COO_PROF_RATE_DIE_YN"))) {
			String sCooProfRateDie1 = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("COO_PROF_RATE_DIE_ST_01");
			String[] sArrCooProfRateDie1 = sCooProfRateDie1.split("@");
			java.util.List<String> sListCooProfRateDie1 = new java.util.ArrayList<>();
			for(String s: sArrCooProfRateDie1){
				if(s != null && !s.isEmpty()) sListCooProfRateDie1.add(s);
			}
			
			String sCooProfRateDie2 = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("COO_PROF_RATE_DIE_ST_02");
			String[] sArrCooProfRateDie2 = sCooProfRateDie2.split("@");
			java.util.List<String> sListCooProfRateDie2 = new java.util.ArrayList<>();
			for(String s: sArrCooProfRateDie2){
				if(s != null && !s.isEmpty()) sListCooProfRateDie2.add(s);
			}
			String sCooProfRateDie = "";
			for(int i=0; i<sListCooProfRateDie1.size(); i++){
				// FIXME(원본 버그): sCooProfRateDie가 아니라 sCooProfRateEq에 누적함
				sCooProfRateEq += sListCooProfRateDie1.get(i) + sListCooProfRateDie2.get(i);
			}
			
			paramMap.put("COO_PROF_RATE_DIE_COL", sCooProfRateDie);
			// FIXME(원본 버그): system.out.println 오탈자
			System.out.println(sCooProfRateDie);
		}
		
		if("Y".equals((String) request.get("COO_PROF_RATE_PROD_YN"))) {
			String sCooProfRateProd1 = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("COO_PROF_RATE_PROD_ST_01");
			String[] sArrCooProfRateProd1 = sCooProfRateProd1.split("@");
			java.util.List<String> sListCooProfRateProd1 = new java.util.ArrayList<>();
			for(String s: sArrCooProfRateProd1){
				if(s != null && !s.isEmpty()) sListCooProfRateProd1.add(s);
			}
			
			String sCooProfRateProd2 = (String)((java.util.Map)((java.util.List)((java.util.Map)rdPivot).get("PIVOT_LIST")).get(0)).get("COO_PROF_RATE_PROD_ST_02");
			String[] sArrCooProfRateProd2 = sCooProfRateProd2.split("@");
			java.util.List<String> sListCooProfRateProd2 = new java.util.ArrayList<>();
			for(String s: sArrCooProfRateProd2){
				if(s != null && !s.isEmpty()) sListCooProfRateProd2.add(s);
			}
			String sCooProfRateProd = "";
			for(int i=0; i<sListCooProfRateProd1.size(); i++){
				// FIXME(원본 버그): sCooProfRateProd가 아니라 sCooProfRateEq에 누적함
				sCooProfRateEq += sListCooProfRateProd1.get(i) + sListCooProfRateProd2.get(i);
			}
			
			paramMap.put("COO_PROF_RATE_PROD_COL", sCooProfRateProd);
			// FIXME(원본 버그): system.out.println 오탈자
			System.out.println(sCooProfRateProd);
		}
		request.putAll(paramMap);
		Object rs = null;
		
		Object sDateTimeMap = store.dPLA04705(request);
		
		if(strChkSubTotal.equals("Y")) rs = store.dPLA04704(request);
		else						   rs = store.dPLA04703(request);
		
		responseData.put("DATETIME_MAP", sDateTimeMap);
		responseData.put("MAIN_LIST", rs);
		
	} catch (RuntimeException be){
		throw be;
	} catch (Exception e){
		throw new RuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA047QrySelectRev(Map<String, Object> request) {
	Map<String, Object> responseData = new HashMap<String, Object>();
	try {
		Object rs = store.dPLA04701(request).get("REV_LIST");
		responseData.put("REV_LIST", rs);
	} catch (BizRuntimeException be) {
		throw be;
	} catch (Exception e) {
		throw new BizRuntimeException("E0052", e);
	}
	return responseData;
}

    // LLM 포팅됨 - 사람 리뷰 필요(CLAUDE.md: 리뷰 없는 커밋 금지)
public Map<String, Object> fPLA047QrySelectRevPeriod(Map<String, Object> request) {
    Map<String, Object> responseData = new java.util.HashMap<>();
    try {
        // FIXME(원본 버그): 원본은 requestData, onlineCtx를 사용하나 메서드/본문 내 미선언 상태임. 원본 그대로 유지 대상이므로 request를 requestData로 치환하고 onlineCtx는 제거하여 포팅함.
        Map<String, Object> duResult = store.dPLA04706(request);
        Object rs = duResult.get("MAIN_LIST");
        responseData.put("MAIN_LIST", rs);
    } catch (BizRuntimeException be) {
        throw be;
    } catch (Exception e) {
        throw new BizRuntimeException("E0052", e);
    }
    return responseData;
}

}