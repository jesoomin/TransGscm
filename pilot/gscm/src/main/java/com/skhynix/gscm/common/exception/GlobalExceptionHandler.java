package com.skhynix.gscm.common.exception;

import com.skhynix.gscm.common.controller.CommonApiResponse;
import org.springframework.context.MessageSource;
import org.springframework.context.NoSuchMessageException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.Locale;

// [초안 - docs/09-common-response-convention.md 참고, 확정 전]
//
// HTTP status 정책은 "안 A"(코드 접두어에 따라 4xx/5xx 구분)로 잠정 작성했다 - 문서에 "안 B"(항상
// 200)도 같이 적어뒀으니 검토 후 다른 안이면 이 클래스만 고치면 된다(호출부 Api/Service는 영향 없음).
//
// code가 "E"로 시작하면 시스템 오류(500), 그 외(W/I 등 - 아직 실사용 사례를 못 찾아 추정)는
// 업무 규칙 위반으로 보고 400으로 보낸다. 이 구분 자체가 확인된 사실이 아니라 추정이라는 점을
// 문서에도 남겨뒀다.
@RestControllerAdvice
public class GlobalExceptionHandler {

    private final MessageSource messageSource;

    public GlobalExceptionHandler(MessageSource messageSource) {
        this.messageSource = messageSource;
    }

    @ExceptionHandler(BizRuntimeException.class)
    public ResponseEntity<CommonApiResponse<Void>> handleBizException(BizRuntimeException e, Locale locale) {
        String code = e.getCode();
        String message = resolveMessage(code, locale, e.getMessage());
        HttpStatus status = (code != null && code.startsWith("E"))
                ? HttpStatus.INTERNAL_SERVER_ERROR
                : HttpStatus.BAD_REQUEST;
        return ResponseEntity.status(status).body(CommonApiResponse.createError(code, message));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<CommonApiResponse<Void>> handleUnexpected(Exception e, Locale locale) {
        // AS-IS의 "catch(Exception e){ throw new BizRuntimeException("E0052", e); }" 관행과
        // 맞춰 분류 안 된 예외는 전부 제네릭 코드 E0052로 감싼다.
        String message = resolveMessage("E0052", locale, "시스템 처리 중 오류가 발생했습니다.");
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(CommonApiResponse.createError("E0052", message));
    }

    private String resolveMessage(String code, Locale locale, String fallback) {
        if (code == null) {
            return fallback;
        }
        try {
            return messageSource.getMessage(code, null, locale);
        } catch (NoSuchMessageException ex) {
            return fallback;
        }
    }

}
