package gscm.r.pm.plab.biz;

import nexcore.framework.core.data.DataSet;
import nexcore.framework.core.data.IDataSet;
import nexcore.framework.core.data.IOnlineContext;
import nexcore.framework.core.data.IRecordSet;

/**
 * <ul>
 * <li>업무 그룹명 : GSCM/경영관리/제품MIX/계획분석</li> 
 * <li>단위업무명 : [DU] 제품별 장당 수익</li> 
 * <li>설   명 : <pre>제품별 장당 수익</pre></li> 
*/
public class DPLA050 extends gscm.fwk.base.ProcessUnit{
	public DPLA050(){
		super();
	}
	
	/**
	 * <pre> Rev 조회 </pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet dPLA05001(IDataSet requestData, IOnlineContext onlineCtx){
		IDataSet responseData = new DataSet();
		IRecordSet rs = dbSelect("S001", requestData.getFieldMap(), onlineCtx);
		responseData.putRecordset("REV_LIST", rs);
		return responseData;
	}
	
	/**
	 * <pre>장당 수익성분석 조회(부분쿼리작성) </pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet dPLA05002(IDataSet requestData, IOnlineContext onlineCtx){
		IDataSet responseData = new DataSet();
		IRecordSet rs = dbSelect("S002", requestData.getFieldMap(), onlineCtx);
		responseData.putRecordset("PIVOT_LIST", rs);
		return responseData;
	}
	
	/**
	 * <pre>장당 수익성분석 조회</pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet dPLA05003(IDataSet requestData, IOnlineContext onlineCtx){
		IDataSet responseData = new DataSet();
		IRecordSet rs = dbSelect("S003", requestData.getFieldMap(), onlineCtx);
		responseData.putRecordset("MAIN_LIST", rs);
		return responseData;
	}
	
	/**
	 * <pre>장당 수익성분석 조회(Sub Total 적용)</pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet dPLA05004(IDataSet requestData, IOnlineContext onlineCtx){
		IDataSet responseData = new DataSet();
		IRecordSet rs = dbSelect("S004", requestData.getFieldMap(), onlineCtx);
		responseData.putRecordset("MAIN_LIST", rs);
		return responseData;
	}
	
	/**
	 * <pre>장당 수익성분석 업데이트 시각 조회</pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet dPLA05005(IDataSet requestData, IOnlineContext onlineCtx){
		IDataSet responseData = new DataSet();
		IRecordSet rs = dbSelect("S005", requestData.getFieldMap(), onlineCtx);
		responseData.putRecordset("DATETIME_MAP", rs);
		return responseData;
	}
	
	/**
	 * <pre>REV 기간 조회</pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet dPLA05006(IDataSet requestData, IOnlineContext onlineCtx){
		IDataSet responseData = new DataSet();
		IRecordSet rs = dbSelect("S006", requestData.getFieldMap(), onlineCtx);
		responseData.putRecordset("MAIN_LIST", rs);
		return responseData;
	}	
}