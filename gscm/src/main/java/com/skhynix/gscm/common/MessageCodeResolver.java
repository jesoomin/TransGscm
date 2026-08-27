package com.skhynix.gscm.common;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.MessageSource;
import org.springframework.context.i18n.LocaleContextHolder;
import org.springframework.stereotype.Component;

/**
 * 메시지 코드(예: E0052, W0024, I0016) -> resources/message/errors*.properties 문구로 해석한다.
 * AS-IS의 {@code new String[] {"통합 DATA 정보"}} 같은 args를 MessageFormat {0}, {1}... 로 치환한다.
 *
 * 코드에 해당하는 문구가 아직 properties에 채워지지 않은 경우(TODO 상태)에도 예외로 죽지 않고
 * 코드 자체를 그대로 반환한다 - 문구 미확정이 전체 플로우를 막지 않게 하기 위함.
 */
@Component
public class MessageCodeResolver {

    private final MessageSource messageSource;

    @Autowired
    public MessageCodeResolver(MessageSource messageSource) {
        this.messageSource = messageSource;
    }

    public String resolve(String messageCode, String[] args) {
        try {
            return messageSource.getMessage(messageCode, args, LocaleContextHolder.getLocale());
        } catch (Exception e) {
            return messageCode;
        }
    }
}
