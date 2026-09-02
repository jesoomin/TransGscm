package gscm.r.pm.plab.biz;

import nexcore.framework.core.data.DataSet;
import nexcore.framework.core.data.IDataSet;
import nexcore.framework.core.data.IOnlineContext;
import nexcore.framework.core.exception.BizRuntimeException;

/**
 * <ul>
 * <li>업무 그룹명 : GSCM/경영관리/제품MIX/계획분석</li> 
 * <li>단위업무명 : [PU] 제품별 장당 수익</li> 
 * <li>설   명 : <pre>제품별 장당 수익</pre></li> 
*/
public class PPLA043 extends gscm.fwk.base.ProcessUnit{
	public PPLA043(){
		super();
	}
	
	/**
	 * <pre> 장당 수익성분석 조회 </pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet pPLA04301 (IDataSet){
		IDataSet responseData = new DataSet();
		try{
			FPLA043 fu = (FPLA043) lookupFunctionUnit(FPLA043.class);
			IDataSet ds = fu.fPLA043QrySelectMainList(requestData, onlineCtx);
			
			responseData.putRecordset("DATETIME_MAP", ds.getRecordSet("DATETIME_MAP"));
			if(ds.getRecordSet("MAIN_LIST").getRecordCount() > 0){
				responseData.putRecordset("MAIN_LIST", ds.getRecordSet("MAIN_LIST"));
			}else{
				responseData.setOkResultMessage("W0024", new String[] {"통합 DATA 정보"});	
			}
		} catch (BizRuntimeException be) {
			throw be;
		} catch (Exception e){
			throw new BizRuntimeException("E0052", new String[] {"통합 DATA 정보"}, e);	
		}
		responseData.setOkResultMessage("I0016", new String[] {"통합 DATA 정보"});	
		return responseData;
	}
	
	/**
	 * <pre> Rev 조회 </pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet pPLA04302 (IDataSet){
		IDataSet responseData = new DataSet();
		try{
			FPLA043 fu = (FPLA043) lookupFunctionUnit(FPLA043.class);
			IDataSet ds = fu.fPLA043QrySelectRev(requestData, onlineCtx);
			
			if(ds.getRecordSet("REV_LIST").getRecordCount() > 0){
				responseData.putRecordset("REV_LIST", ds.getRecordSet("REV_LIST"));
			}else{
				responseData.setOkResultMessage("W0024", new String[] {"REV 정보"});	
			}
		} catch (BizRuntimeException be) {
			throw be;
		} catch (Exception e){
			throw new BizRuntimeException("E0052", new String[] {"REV 정보"}, e);	
		}
		responseData.setOkResultMessage("I0016", new String[] {"REV 정보"});	
		return responseData;
	}
	
	/**
	 * <pre> Rev 기간 조회 </pre>
	 *
	 * @param requestData 요청정보 DataSet 객체
	 * @param onlineCtx 여청 컨텍스트 정보
	 * @return 처리결과 DataSet 객체
	*/
	public IDataSet pPLA04303 (IDataSet){
		IDataSet responseData = new DataSet();
		try{
			FPLA043 fu = (FPLA043) lookupFunctionUnit(FPLA043.class);
			IDataSet ds = fu.fPLA043QrySelectRevPeriod(requestData, onlineCtx);
			
			if(ds.getRecordSet("MAIN_LIST").getRecordCount() > 0){
				responseData.putRecordset("MAIN_LIST", ds.getRecordSet("MAIN_LIST"));
			}else{
				responseData.setOkResultMessage("W0024", new String[] {"REV PERIOD 정보"});	
			}
		} catch (BizRuntimeException be) {
			throw be;
		} catch (Exception e){
			throw new BizRuntimeException("E0052", new String[] {"REV PERIOD 정보"}, e);	
		}
		responseData.setOkResultMessage("I0016", new String[] {"REV PERIOD 정보"});	
		return responseData;
	}
}