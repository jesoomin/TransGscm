package nexcore.framework.core.data;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class RecordSet implements IRecordSet {
    private final List<Map<String, Object>> rows;

    public RecordSet() { this.rows = new ArrayList<Map<String, Object>>(); }
    public RecordSet(List<Map<String, Object>> rows) { this.rows = rows; }

    @Override public int getRecordCount() { return rows == null ? 0 : rows.size(); }
    @Override public List<Map<String, Object>> getRows() { return rows; }
}
