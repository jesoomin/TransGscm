package com.skhynix.gscm.common.exception;

/** TO-BE 공통 예외의 최소 재현 - pilot/gscm의 common 모듈과 같은 시그니처. */
public class BizRuntimeException extends RuntimeException {
    private final String code;
    private final String[] args;

    public BizRuntimeException(String code) { super(code); this.code = code; this.args = null; }

    public BizRuntimeException(String code, Throwable cause) {
        super(code, cause);
        this.code = code;
        this.args = null;
    }

    public BizRuntimeException(String code, String message) {
        super(message);
        this.code = code;
        this.args = null;
    }

    // AS-IS가 실제로 가장 많이 쓰는 형태다(PLA081-110 코퍼스 60개 파일에서 105회).
    // 포팅된 코드는 원본 로직을 그대로 옮기므로 이 시그니처가 없으면 컴파일되지 않는다.
    public BizRuntimeException(String code, String[] args, Throwable cause) {
        super(code, cause);
        this.code = code;
        this.args = args;
    }

    public String getCode() { return code; }

    public String[] getArgs() { return args; }
}
