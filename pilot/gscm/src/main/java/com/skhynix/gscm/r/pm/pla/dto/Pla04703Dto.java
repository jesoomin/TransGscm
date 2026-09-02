package com.skhynix.gscm.r.pm.pla.dto;

import lombok.Data;

// Api(GET /pla04703, "리비전 기간 조회")가 바인딩하는 요청 DTO. Service.pla04703()가 이 값을
// 그대로 pla047Store.dPLA04706(dto)에 넘기므로, dPLA04706 select가 바인딩하는 PLN_YW를 포함한다.
// TODO: PLN_YW 외 실제 화면 요청 필드가 더 있는지는 원본 P/F BizUnit 확인 전까지 미정.
@Data
public class Pla04703Dto {

    /** AS-IS 바인드 변수명: PLN_YW */
    private String plnYw;

}