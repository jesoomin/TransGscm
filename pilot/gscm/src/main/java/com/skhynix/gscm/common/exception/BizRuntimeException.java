package com.skhynix.gscm.common.exception;

import lombok.Getter;

// [초안 - docs/09-common-response-convention.md 참고, 확정 전] AS-IS 실 소스(FPLA047.java 등)에서
// 확인되는 딱 하나의 실사용 패턴만 그대로 받을 수 있게 만들었다:
//     catch (BizRuntimeException be) { throw be; }
//     catch (Exception e) { throw new BizRuntimeException("E0052", e); }
// 즉 "코드 + 원인(cause)" 생성자가 실제로 쓰인다. 코드만 있고 원인이 없는 경우, 메시지를 직접
// 지정하는 경우도 있을 수 있어 오버로드를 추가해뒀지만 이건 실사용처를 아직 못 찾은 추정이다.
@Getter
public class BizRuntimeException extends RuntimeException {

    private final String code;

    public BizRuntimeException(String code) {
        super(code);
        this.code = code;
    }

    public BizRuntimeException(String code, Throwable cause) {
        super(code, cause);
        this.code = code;
    }

    public BizRuntimeException(String code, String message) {
        super(message);
        this.code = code;
    }

}
