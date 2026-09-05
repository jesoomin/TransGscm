package nexcore.framework.core.data;

import java.util.Map;

/** NEXCORE IDataSet의 최소 재현. AS-IS 소스가 실제로 호출하는 메서드만 둔다. */
public interface IDataSet {
    String getField(String name);
    void setField(String name, Object value);
    Map<String, Object> getFieldMap();
    void putFieldMap(Map<String, Object> map);
    void putRecordset(String name, IRecordSet rs);
    IRecordSet getRecordSet(String name);

    /** 결과 메시지 설정 - P 계층이 "권한 없음"·"조회 결과 없음"을 알릴 때 쓴다(원본에서 195회 사용). */
    void setOkResultMessage(String code, String[] args);

    /** 하네스 비교용 - 설정된 메시지 코드(없으면 null). 원본 API에는 없다. */
    String harnessResultCode();
}
