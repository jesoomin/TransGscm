package com.skhynix.gscm.common.controller;

import lombok.Getter;

// [초안 - docs/09-common-response-convention.md 참고, 확정 전] createSuccess(T)는 실제 사용 중이던
// 시그니처라 그대로 뒀고, createError(code, message)를 이번에 추가했다(GlobalExceptionHandler가
// 씀). CLAUDE.md 원칙("공통 응답/예외 처리 규약은 사람이 먼저 확정한다")대로, 이 형태는 초안이며
// 검토·확정 전까지 chatui/skeleton_gen.py의 Api 생성 템플릿에는 반영하지 않았다.
@Getter
public class CommonApiResponse<T> {

    private final boolean success;
    private final T data;      // 실패 시 null
    private final String code;    // 성공 시 null, 실패 시 AS-IS 메시지 코드(E0052 등)
    private final String message; // 성공 시 null, 실패 시 사람이 읽을 문구

    private CommonApiResponse(boolean success, T data, String code, String message) {
        this.success = success;
        this.data = data;
        this.code = code;
        this.message = message;
    }

    public static <T> CommonApiResponse<T> createSuccess(T data) {
        return new CommonApiResponse<>(true, data, null, null);
    }

    public static CommonApiResponse<Void> createError(String code, String message) {
        return new CommonApiResponse<>(false, null, code, message);
    }

}
