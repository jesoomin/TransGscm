package nexcore.framework.core.exception;

public class BizRuntimeException extends RuntimeException {
    private final String code;

    public BizRuntimeException(String code) { super(code); this.code = code; }
    public BizRuntimeException(String code, Throwable cause) { super(code, cause); this.code = code; }

    public String getCode() { return code; }
}
