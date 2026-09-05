package gscm.fwk.base;

import java.util.HashMap;
import java.util.Map;

/**
 * AS-IS BizUnit의 상위 클래스 최소 재현.
 *
 * 실제 NEXCORE는 컨테이너에서 DataUnit 인스턴스를 찾아 주지만, 이 하네스는 **D 계층을 양쪽에
 * 동일한 가짜로 고정**하는 게 목적이므로 등록된 스텁을 그대로 돌려준다. 그래야 SQL·DB가 변수에서
 * 빠지고 **F 계층 업무 로직의 동등성만** 남는다.
 */
public abstract class ProcessUnit {
    private static final Map<Class<?>, Object> REGISTRY = new HashMap<Class<?>, Object>();

    /** 하네스가 D 계층 스텁을 미리 꽂아둔다. */
    public static void registerDataUnit(Class<?> type, Object instance) {
        REGISTRY.put(type, instance);
    }

    public static void clearRegistry() { REGISTRY.clear(); }

    @SuppressWarnings("unchecked")
    protected <T> T lookupDataUnit(Class<T> type) {
        Object found = REGISTRY.get(type);
        if (found == null) {
            throw new IllegalStateException(
                "하네스에 등록되지 않은 DataUnit: " + type.getName()
                + " - registerDataUnit()으로 먼저 꽂아야 한다");
        }
        return (T) found;
    }

    /**
     * D 계층이 SQL을 실행하는 지점. **실제 SQL은 돌리지 않고 하네스가 주입한 캔드 응답을 준다.**
     *
     * SQL 동등성은 이미 다른 층(agents/diff_test.py - AS-IS/TO-BE SQL을 같은 DB에 실행해 비교)이
     * 담당한다. 여기서 또 다루면 무엇을 재는 실험인지가 흐려지므로, D 계층을 양쪽 동일한 상수로
     * 고정해서 **F 계층 업무 로직의 동등성만** 변수로 남긴다.
     */
    protected nexcore.framework.core.data.IRecordSet dbSelect(
            String stmtId, Object param, nexcore.framework.core.data.IOnlineContext ctx) {
        return CannedData.recordSet();
    }

    /** 원본이 D 계층을 FunctionUnit으로 잘못 조회하는 경우(원본 결함)도 그대로 재현한다. */
    @SuppressWarnings("unchecked")
    protected <T> T lookupFunctionUnit(Class<T> type) {
        Object found = REGISTRY.get(type);
        if (found == null) {
            throw new IllegalStateException(
                "하네스에 등록되지 않은 FunctionUnit: " + type.getName());
        }
        return (T) found;
    }
}
