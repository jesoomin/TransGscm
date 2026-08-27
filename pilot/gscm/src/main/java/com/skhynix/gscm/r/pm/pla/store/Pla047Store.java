package com.skhynix.gscm.r.pm.pla.store;

import org.mybatis.spring.SqlSessionTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Map;

// MyBatis 연동 방식: SqlSessionTemplate 직접 호출로 확정(docs/09-common-conventions.md #5).
// docs/07-tobe-structure.xlsx 확정 구조에 없는 별도 Mapper 인터페이스는 도입하지 않는다.
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