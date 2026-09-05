package com.skhynix.gscm.common.exception;

/** TO-BE 공통 예외의 최소 재현 - pilot/gscm의 common 모듈과 같은 시그니처. */
public class BizRuntimeException extends RuntimeException {
    private final String code;

    public BizRuntimeException(String code) { super(code); this.code = code; }
    public BizRuntimeException(String code, Throwable cause) { super(code, cause); this.code = code; }

    public String getCode() { return code; }
}
