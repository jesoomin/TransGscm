package nexcore.framework.core.data;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * NEXCORE DataSet의 최소 재현.
 *
 * 값 보관은 LinkedHashMap 하나로 충분하다 - AS-IS 코드가 쓰는 건 필드 맵과 레코드셋 두 가지뿐이다.
 * `getField`가 String을 돌려주는 건 원본 시그니처 그대로다(AS-IS는 모든 필드를 문자열로 다뤘다).
 */
public class DataSet implements IDataSet {
    private final Map<String, Object> fields = new LinkedHashMap<String, Object>();
    private final Map<String, IRecordSet> recordsets = new LinkedHashMap<String, IRecordSet>();

    @Override
    public String getField(String name) {
        Object v = fields.get(name);
        return v == null ? null : String.valueOf(v);
    }

    @Override
    public void setField(String name, Object value) { fields.put(name, value); }

    @Override
    public Map<String, Object> getFieldMap() { return fields; }

    @Override
    public void putFieldMap(Map<String, Object> map) {
        if (map != null && map != fields) { fields.putAll(map); }
    }

    @Override
    public void putRecordset(String name, IRecordSet rs) { recordsets.put(name, rs); }

    @Override
    public IRecordSet getRecordSet(String name) { return recordsets.get(name); }

    private String resultCode;

    @Override
    public void setOkResultMessage(String code, String[] args) { this.resultCode = code; }

    @Override
    public String harnessResultCode() { return resultCode; }

    /** 하네스가 결과를 비교할 때 쓰는 접근자 - 원본 API에는 없다. */
    public Map<String, IRecordSet> harnessRecordsets() { return recordsets; }
}
