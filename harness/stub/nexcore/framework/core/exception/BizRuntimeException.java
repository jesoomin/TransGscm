package nexcore.framework.core.exception;

public class BizRuntimeException extends RuntimeException {
    private final String code;

    public BizRuntimeException(String code) { super(code); this.code = code; }
    public BizRuntimeException(String code, Throwable cause) { super(code, cause); this.code = code; }

    /** 원본이 메시지 인자 배열까지 넘기는 형태(`new BizRuntimeException("E0052", args, e)`)도 있다. */
    public BizRuntimeException(String code, String[] args, Throwable cause) {
        super(code, cause);
        this.code = code;
    }

    public BizRuntimeException(String code, String[] args) { super(code); this.code = code; }

    public String getCode() { return code; }
}
