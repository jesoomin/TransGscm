package com.skhynix.gscm.common;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * BizException(AS-IS BizRuntimeException 대체)을 ApiResponse.fail(...)로 변환하는 유일한 지점.
 * {화면}Api/{화면}Service는 실패 응답을 직접 조립하지 않고 BizException만 던진다 -
 * docs/09-common-conventions.md 참고.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    @Autowired
    private MessageCodeResolver messageCodeResolver;

    @ExceptionHandler(BizException.class)
    public ResponseEntity<ApiResponse<Object>> handleBizException(BizException e) {
        String message = messageCodeResolver.resolve(e.getMessageCode(), e.getArgs());
        return ResponseEntity.ok(ApiResponse.fail(e.getMessageCode(), message));
    }

    /**
     * AS-IS의 P/F 계층은 catch(Exception e) 블록에서 반드시 BizRuntimeException("E0052", ...)로
     * 감싸 재던졌다. 여기까지 원본 예외가 그대로 도달했다는 건 포팅 과정에서 그 catch-and-wrap을
     * 빠뜨렸다는 신호로 본다 - 신규 코드 E9999(NEXCORE에 없음, 매핑 실패 전용)로 표시한다.
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Object>> handleUnexpected(Exception e) {
        String message = messageCodeResolver.resolve("E9999", new String[] {e.getMessage()});
        return ResponseEntity.ok(ApiResponse.fail("E9999", message));
    }
}
