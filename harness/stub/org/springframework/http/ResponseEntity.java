package org.springframework.http;

/**
 * Spring `ResponseEntity`의 최소 재현 - 하네스가 Api 계층을 호출해 본문을 꺼내는 데만 쓴다.
 *
 * 실제 Spring을 끌어오지 않는 이유는 스텁 원칙과 같다: HTTP 서버를 띄우는 게 목적이 아니라
 * **Api 메서드가 무엇을 돌려주는지**를 보는 게 목적이라, 래퍼 한 겹만 있으면 충분하다.
 */
public class ResponseEntity<T> {
    private final T body;

    private ResponseEntity(T body) { this.body = body; }

    public static <T> ResponseEntity<T> ok(T body) { return new ResponseEntity<T>(body); }

    public T getBody() { return body; }
}
