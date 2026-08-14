package com.skhynix.gscm.r.pm.pla.store;

import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Map;

// TODO: MyBatis 연동 방식(SqlSessionTemplate 직접 호출 vs @Mapper 인터페이스)이 아직 사내 컨벤션으로
// 확정되지 않아 SqlSessionTemplate 방식으로 임시 작성했다 - 실제 컨벤션 확인 후 조정할 것.
@Repository
public class Pla047Store {

    @Autowired
    private SqlSessionTemplate sqlSession;

    public Map<String, Object> dPLA04701(Map<String, Object> params) {
        return sqlSession.selectOne("Pla047Mapper.S001", params);
    }

    public Map<String, Object> dPLA04702(Map<String, Object> params) {
        return sqlSession.selectOne("Pla047Mapper.S002", params);
    }

    public Map<String, Object> dPLA04703(Map<String, Object> params) {
        return sqlSession.selectOne("Pla047Mapper.S003", params);
    }

    public Map<String, Object> dPLA04704(Map<String, Object> params) {
        return sqlSession.selectOne("Pla047Mapper.S004", params);
    }

    public Map<String, Object> dPLA04705(Map<String, Object> params) {
        return sqlSession.selectOne("Pla047Mapper.S005", params);
    }

    public Map<String, Object> dPLA04706(Map<String, Object> params) {
        return sqlSession.selectOne("Pla047Mapper.S006", params);
    }

}