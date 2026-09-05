package gscm.fwk.base;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import nexcore.framework.core.data.IDataSet;
import nexcore.framework.core.data.IRecordSet;
import nexcore.framework.core.data.RecordSet;

/**
 * AS-IS와 TO-BE 양쪽이 **같은 값**을 받도록 고정하는 캔드 데이터.
 *
 * 이 하네스의 핵심 설계다 - D 계층(SQL)을 양쪽에 동일한 상수로 고정하면, 두 실행 결과의 차이는
 * 오직 **F 계층 업무 로직의 포팅 차이**에서만 나온다. 그래야 "기능 동등성"이라는 측정이 무엇을
 * 재는지 분명해진다.
 */
public final class CannedData {
    private CannedData() {}

    private static int rowCount = 2;

    /** 하네스가 케이스별로 행 수를 바꿔가며(0행/1행/N행) 분기 경로를 훑는다. */
    public static void setRowCount(int n) { rowCount = n; }

    public static List<Map<String, Object>> rows() {
        List<Map<String, Object>> out = new ArrayList<Map<String, Object>>();
        for (int i = 0; i < rowCount; i++) {
            Map<String, Object> row = new LinkedHashMap<String, Object>();
            row.put("TGT_CD", "T" + i);
            row.put("DTL_SEQ", String.valueOf(i));
            row.put("METRIC_VALUE", String.valueOf(100 + i));
            row.put("METRIC_TYPE", "QTY");
            out.add(row);
        }
        return out;
    }

    public static IRecordSet recordSet() { return new RecordSet(rows()); }

    /** 어떤 이름으로 recordset을 물어도 같은 행을 돌려주는 DataSet. */
    public static IDataSet dataSet() { return new CannedDataSet(); }

    private static final class CannedDataSet extends nexcore.framework.core.data.DataSet {
        @Override public IRecordSet getRecordSet(String name) { return recordSet(); }
    }
}
