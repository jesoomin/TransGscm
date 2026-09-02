package com.skhynix.gscm.r.pm.pla.dto;

import lombok.Data;

import java.util.List;
import java.util.Map;

// Mapper resultType이 아니라 Pla047Service.pla04702() 안에서 실제로 호출하는
// resDto.setRs(...) / resDto.setDatetimeMap(...) 세터 사용처에서 역추출했다
// (dPLA04703/04704/04705의 resultType=map이라 이 응답 DTO 자체는 Mapper에 안 나타남).
@Data
public class Pla04702ResponseDto {

    // dPLA04703/dPLA04704(subtotal 여부에 따라 분기) 조회 결과 그리드
    private List<Map<String, Object>> rs;

    // dPLA04705(마지막 갱신 시각) 조회 결과
    private Map<String, Object> datetimeMap;

}