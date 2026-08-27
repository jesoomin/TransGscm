package com.skhynix.gscm.common;

/**
 * AS-IS NEXCORE {@code BizRuntimeException}의 TO-BE 대체.
 *
 * P/F BizUnit(예: PPLA047.java, FPLA047.java)에서 실제로 쓰인 두 생성자 형태를
 * 그대로 포팅 가능하게 유지한다 - docs/09-common-conventions.md 참고.
 */
public class BizException extends RuntimeException {

    private final String messageCode;
    private final String[] args;

    /** F 계층 패턴: {@code new BizRuntimeException("E0052", e)} */
    public BizException(String messageCode, Throwable cause) {
        super(cause);
        this.messageCode = messageCode;
        this.args = new String[0];
    }

    /** P 계층 패턴: {@code new BizRuntimeException("E0052", new String[] {"..."}, e)} */
    public BizException(String messageCode, String[] args, Throwable cause) {
        super(cause);
        this.messageCode = messageCode;
        this.args = args != null ? args : new String[0];
    }

    /** cause 없이 코드+args만 있는 경우 대비 */
    public BizException(String messageCode, String[] args) {
        this.messageCode = messageCode;
        this.args = args != null ? args : new String[0];
    }

    public String getMessageCode() {
        return messageCode;
    }

    public String[] getArgs() {
        return args;
    }
}
