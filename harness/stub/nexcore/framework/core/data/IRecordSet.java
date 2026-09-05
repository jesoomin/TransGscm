package nexcore.framework.core.data;

import java.util.List;
import java.util.Map;

/** NEXCORE IRecordSet의 최소 재현 - 하네스가 쓰는 표면만 구현한다. */
public interface IRecordSet {
    int getRecordCount();
    List<Map<String, Object>> getRows();
}
