package com.skhynix.gscm.r.pm.pla.dto;

import lombok.Data;

// Mapper의 dPLA04701 select parameterType/resultType(둘 다 Pla04701 계열)에서 자동 추출.
// 요청 필드(PLN_YW)와 SELECT 결과 컬럼을 한 클래스에 같이 담았다 - 원본 select가 요청/응답에
// 같은 이름 패턴의 타입을 썼기 때문(단순 코드성 조회라 왕복 DTO를 분리할 실익이 적음).
// TODO: 필드 타입은 전부 String으로 잠정 지정(원본에 실제 타입 미선언) - 실제 쿼리 결과 보고 조정할 것.
@Data
public class Pla04701Dto {

    /** AS-IS 바인드 변수명: APPLY_CTN */
    private String applyCtn;

    /** AS-IS 바인드 변수명: CODE */
    private String code;

    /** AS-IS 바인드 변수명: COST_PLN_REV */
    private String costPlnRev;

    /** AS-IS 바인드 변수명: PLN_END_YM */
    private String plnEndYm;

    /** AS-IS 바인드 변수명: PLN_START_YM */
    private String plnStartYm;

    /** AS-IS 바인드 변수명: PLN_TYP_CD */
    private String plnTypCd;

    /** AS-IS 바인드 변수명: PLN_YW */
    private String plnYw;

    /** AS-IS 바인드 변수명: SOM_PLN_REV */
    private String somPlnRev;

    /** AS-IS 바인드 변수명: VALUE */
    private String value;

    /** AS-IS 바인드 변수명: YLD_PLN_REV */
    private String yldPlnRev;

}