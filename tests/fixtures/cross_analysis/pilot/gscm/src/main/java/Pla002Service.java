public class Pla002Service {
    public Map<String, Object> find(Map<String, Object> request) {
        String value = request.get("status").toString();
        return Map.of("value", value, "ok", true);
    }
}
