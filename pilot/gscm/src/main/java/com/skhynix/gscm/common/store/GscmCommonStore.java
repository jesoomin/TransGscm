package com.skhynix.gscm.common.store;

import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Map;

// 화면 간 공통 로직 - 자동 생성(python -m agents.common_methods --emit).
// 무엇을 여기에 둘지는 config/common-methods.json(사람 확정)이 정한다. 화면별 Service/Store는
// 같은 이름의 메서드를 그대로 노출하되 본문만 이 클래스로 위임하므로, 호출부는 바뀌지 않는다.
@Repository
public class GscmCommonStore {

    private static final String NS = "com.skhynix.gscm.common.store.GscmCommonStore.";

    @Autowired
    private SqlSessionTemplate sqlSession;

    public Map<String, Object> dAuthCheck(Map<String, Object> params) {
        return sqlSession.selectOne(NS + "dAuthCheck", params);
    }

    public Map<String, Object> dCommonCodeQry(Map<String, Object> params) {
        return sqlSession.selectOne(NS + "dCommonCodeQry", params);
    }

    public Map<String, Object> dExcelDownQry(Map<String, Object> params) {
        return sqlSession.selectOne(NS + "dExcelDownQry", params);
    }

}
