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
}
