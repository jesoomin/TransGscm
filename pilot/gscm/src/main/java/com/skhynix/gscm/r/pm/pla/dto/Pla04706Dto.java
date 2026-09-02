package com.skhynix.gscm.r.pm.pla.dto;

import lombok.Data;

// Mapper의 dPLA04706 select parameterType/resultType(둘 다 Pla04706Dto)에서 자동 추출.
// Pla04701Dto와 마찬가지로 단순 조회라 요청/응답 필드를 한 클래스에 같이 담았다.
@Data
public class Pla04706Dto {

    /** AS-IS 바인드 변수명: PLN_END_YM */
    private String plnEndYm;

    /** AS-IS 바인드 변수명: PLN_REV */
    private String plnRev;

    /** AS-IS 바인드 변수명: PLN_START_YM */
    private String plnStartYm;

    /** AS-IS 바인드 변수명: PLN_YW */
    private String plnYw;

    /** AS-IS 바인드 변수명: WORK_YEAR */
    private String workYear;

}