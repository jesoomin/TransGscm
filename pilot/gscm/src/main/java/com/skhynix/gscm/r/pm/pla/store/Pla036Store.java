package com.skhynix.gscm.r.pm.pla.store;

import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Map;

// TODO: MyBatis 연동 방식(SqlSessionTemplate 직접 호출 vs @Mapper 인터페이스)이 아직 사내 컨벤션으로
// 확정되지 않아 SqlSessionTemplate 방식으로 임시 작성했다 - 실제 컨벤션 확인 후 조정할 것.
@Repository
public class Pla036Store {

    private static final String NS = "com.skhynix.gscm.r.pm.pla.store.Pla036Store.";

    @Autowired
    private SqlSessionTemplate sqlSession;

    public Map<String, Object> dCommonCodeQry(Map<String, Object> params) {
        return sqlSession.selectOne(NS + "dCommonCodeQry", params);
    }

    public Map<String, Object> dAuthCheck(Map<String, Object> params) {
        return sqlSession.selectOne(NS + "dAuthCheck", params);
    }

    public Map<String, Object> dHistoryQry(Map<String, Object> params) {
        return sqlSession.selectOne(NS + "dHistoryQry", params);
    }

    public Map<String, Object> dPLA03601(Map<String, Object> params) {
        return sqlSession.selectOne(NS + "dPLA03601", params);
    }

    public Map<String, Object> dPLA03602(Map<String, Object> params) {
        return sqlSession.selectOne(NS + "dPLA03602", params);
    }

}