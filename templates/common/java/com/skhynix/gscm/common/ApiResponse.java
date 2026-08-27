package com.skhynix.gscm.common;

/**
 * 모든 {화면}Api 응답을 감싸는 공통 봉투. AS-IS의 IDataSet + setOkResultMessage(code, args)
 * 조합에 대응한다 - docs/09-common-conventions.md 참고.
 *
 * HTTP status는 항상 200으로 고정하고(진짜 인프라 장애 제외), 성공/실패 구분은
 * resultCode/messageCode로만 한다 - 레거시 nctRid Dataset 응답과 신규 REST JSON 응답을
 * 차등 테스트(diff)할 때 body만 비교하면 되도록 하기 위함.
 */
public class ApiResponse<T> {

    private final ResultCode resultCode;
    private final String messageCode;
    private final String message;
    private final T data;

    private ApiResponse(ResultCode resultCode, String messageCode, String message, T data) {
        this.resultCode = resultCode;
        this.messageCode = messageCode;
        this.message = message;
        this.data = data;
    }

    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(ResultCode.OK, null, null, data);
    }

    public static <T> ApiResponse<T> success(T data, String messageCode, String message) {
        return new ApiResponse<>(ResultCode.OK, messageCode, message, data);
    }

    public static <T> ApiResponse<T> fail(String messageCode, String message) {
        return new ApiResponse<>(ResultCode.ERROR, messageCode, message, null);
    }

    public ResultCode getResultCode() {
        return resultCode;
    }

    public String getMessageCode() {
        return messageCode;
    }

    public String getMessage() {
        return message;
    }

    public T getData() {
        return data;
    }
}
