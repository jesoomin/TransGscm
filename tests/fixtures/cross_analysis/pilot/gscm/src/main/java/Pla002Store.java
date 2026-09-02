public class Pla002Store {
    public Map<String, Object> find(Map<String, Object> params) {
        String statement = NS + "findShared";
        return sqlSession.selectOne(statement, params);
    }
}
