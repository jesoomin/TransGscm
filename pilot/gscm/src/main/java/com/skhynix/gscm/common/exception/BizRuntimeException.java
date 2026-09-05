package com.skhynix.gscm.common.exception;

import lombok.Getter;

// [초안 - docs/09-common-response-convention.md 참고, 확정 전] AS-IS 실 소스에서 확인되는
// 실사용 패턴을 그대로 받을 수 있게 만든다:
//     catch (BizRuntimeException be) { throw be; }
//     catch (Exception e) { throw new BizRuntimeException("E0052", e); }
//     catch (Exception e) { throw new BizRuntimeException("E0052", new String[] {"목록"}, e); }
//
// 정정(2026-09-05): 원래 여기 "실사용 패턴은 (코드, 원인) 하나뿐"이라고 적혀 있었지만 그건
// PLA047 한 건만 보고 쓴 문장이었다. PLA081-110 코퍼스를 세어보니 (코드, 메시지 인자, 원인)
// 3-인자 형태가 60개 파일에서 105회 쓰인다 - 이 생성자가 없으면 원본을 그대로 옮긴 포팅 코드가
// 컴파일되지 않는다. 실제로 L3 실행 하네스가 Api 계층을 컴파일하면서 처음 잡아냈다.
@Getter
public class BizRuntimeException extends RuntimeException {

    private final String code;

    /** AS-IS의 `new String[] {...}` 메시지 인자. 안 쓰는 호출 형태에서는 null이다. */
    private final String[] args;

    public BizRuntimeException(String code) {
        super(code);
        this.code = code;
        this.args = null;
    }

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

    public BizRuntimeException(String code, String[] args, Throwable cause) {
        super(code, cause);
        this.code = code;
        this.args = args;
    }

}
