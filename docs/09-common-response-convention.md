# 공통 응답/예외 처리 규약 (초안 — 확정 전, 검토 필요)

> **이 문서는 초안이다.** CLAUDE.md 원칙("공통 응답/예외 처리 규약, 공통 Mapper/Store 패턴은 사람이 먼저 확정한다 — 화면마다 에이전트가 제각각 만들면 지금의 개발자별 이원화 문제가 재현된다")에 따라, 여기 나온 형태를 그대로 자동 반영하지 않는다. 검토 후 확정되면 `chatui/skeleton_gen.py`의 Api 생성 템플릿에 반영하고, 그 전까지 생성기는 지금 형태(응답 래핑 없이 `ResponseEntity<T>` 그대로 반환)를 유지한다.

## 왜 필요한가
지금 `pilot/gscm/.../common/controller/CommonApiResponse.java`는 실사용 시그니처(`createSuccess(T)`) 하나만 채운 임시 스텁이다. 성공 응답만 있고 실패 응답 형태가 없어서, 화면마다 에러를 다르게 처리하게 될 위험이 있다 — 이게 이번 프로젝트가 고치려는 "개발자별 이원화" 문제 그 자체다.

AS-IS 코드(`FPLA047.java` 등 실 소스)에서 확인되는 패턴은 이거 하나뿐이다:
```java
try {
    ...
} catch (BizRuntimeException be) {
    throw be;                                   // 이미 분류된 예외는 그대로 위로 전파
} catch (Exception e) {
    throw new BizRuntimeException("E0052", e);  // 그 외는 전부 제네릭 코드로 감쌈
}
```
`E0052`가 실제 코드에서 반복적으로 쓰이는 걸 확인했다.

**갱신(2026-09-05) — `W0024`/`I0016`의 실사용처를 찾았다.** 아래 "결정이 필요한 것" 2번은 "W/I 코드가 예외로 던져지는지, 성공 응답에 곁들이는 안내 메시지인지 실사용 사례가 없어 확인 불가"였는데, `PLA081-110_migration_sample`의 P BizUnit 30개를 전수 확인해 답이 나왔다:

```java
// PPLA096.pPLA09601 — 권한 없음
responseData.setOkResultMessage("W0024", new String[] {"조회권한"});
return responseData;                       // 예외가 아니라 정상 반환
...
responseData.setOkResultMessage("I0016", new String[] {"품질감사결과관리 목록"});
return responseData;
```

메서드 이름부터 `setOk...`이고, 던지지 않고 그대로 반환한다 — **W/I는 예외가 아니라 성공 응답에 실리는 안내 메시지**다. 실측: P 파일 30/30이 이 패턴을 쓰고, `setOkResultMessage` 호출이 195건, 그중 권한 게이트(`AUTH_YN` 확인 후 조기 반환)가 30/30 화면에 있다. `E`(예외로 던짐)와 `W`/`I`(성공 응답에 실림)는 **전달 경로가 다르다**.

이건 규약 설계에 직접 영향을 준다 — `CommonApiResponse`의 `code`/`message`를 실패 전용으로 두면 W/I를 실을 자리가 없다. 다만 **어떤 형태로 실을지는 여기서 정하지 않는다**(사람 확정 대상). 그때까지 생성기는 그 자리를 비워두고 `// TODO(응답 규약 미확정)` 주석만 남긴다.

> 이 미확정 상태는 측정에도 그대로 드러난다: L3 실행 하네스 기준 Api 계층의 **데이터 > 페이로드는 9/9(100%) 일치하는데 엄격 일치는 0/9**이고, 그 차이가 전부 이 메시지 코드다(`agents/equivalence_test.py`, `tracking/equivalence-5screens.json`). 규약이 정해지면 닫히는 격차이지 변환 실패가 아니다.

## 제안하는 구조

### 1. 응답 래퍼 — `CommonApiResponse<T>`
```java
package com.skhynix.gscm.common.controller;

@Getter
public class CommonApiResponse<T> {
    private final boolean success;
    private final T data;       // 실패 시 null
    private final String code;  // 성공 시 null, 실패 시 AS-IS 코드(E0052 등)
    private final String message; // 성공 시 null, 실패 시 사람이 읽을 문구

    public static <T> CommonApiResponse<T> createSuccess(T data) { ... }
    public static CommonApiResponse<Void> createError(String code, String message) { ... }
}
```
기존 `createSuccess(T)`는 그대로 유지하고 `createError`만 추가하는 안 — 이미 있는 호출부를 안 건드린다.

### 2. 예외 타입 — `BizRuntimeException`
AS-IS 실사용 형태를 그대로 받을 수 있게 한다. **정정(2026-09-05)**: 원래 `(코드, 원인)` 하나뿐이라고 적었는데 그건 PLA047 1건 기준이었다. PLA081-110 코퍼스에서는 `new BizRuntimeException("E0052", new String[] {"목록"}, e)` 3-인자 형태가 60개 파일에서 105회 쓰인다 — 생성자가 없어서 포팅된 Api가 컴파일되지 않았고(L3 하네스가 잡음) `String[] args`를 받는 생성자를 추가했다. AS-IS 호출 형태를 그대로 받을 수 있게, 코드+원인 생성자를 최소한으로 둔다. F/D 로직을 LLM으로 포팅할 때 원본의 `throw new BizRuntimeException(...)` 호출을 고치지 않고 그대로 옮길 수 있어야 하므로, AS-IS 생성자 시그니처와 최대한 맞춘다.

### 3. 전역 예외 처리 — `GlobalExceptionHandler` (`@RestControllerAdvice`)
- `BizRuntimeException` → `code`로 메시지 리소스(`errors.properties`) 조회해서 `CommonApiResponse.createError(code, message)` 반환
- 그 외 처리 안 된 `Exception` → `E0052`(제네릭 코드)로 동일하게 감싸서 반환
- **미정(확인 필요): HTTP status를 뭘로 할지.** 두 가지 안이 있다:
  - **안 A (권장): 정상적인 REST 관례대로 4xx/5xx 사용.** 새 REST API는 Nexacro가 호출하지 않고(UI는 2단계 트랙) 2단계 React 화면이 호출할 새 소비자라, NEXCORE 시절 "항상 200, 바디 안에서 성공/실패 구분" 관행을 유지할 이유가 없다. `E`(시스템 오류)=500, 그 외(업무 규칙 위반으로 추정)=400 정도로 단순하게 시작.
  - **안 B: 항상 200 반환, 바디의 `success` 필드로만 구분.** 예전 NEXCORE Dataset 응답 관행과 그대로 맞춰서, 클라이언트 쪽 분기 로직을 더 단순하게 유지하고 싶을 때.
  - 이 초안은 **안 A**로 작성했다 — 다른 결정이면 `GlobalExceptionHandler` 한 곳만 고치면 된다.

### 4. 메시지 외부화 — `resources/message/errors.properties` / `errors_en.properties`
```properties
# E0052: NEXCORE 원본에서 "예상 못한 예외를 잡았을 때" 쓰던 제네릭 코드
# (FPLA047 등 여러 화면에서 실사용 확인됨). 원본 NEXCORE 공통 메시지 리소스의 정확한 문구는
# 아직 못 찾았다 - 아래 문구는 TO-BE에서 임시로 붙인 잠정 문구다(원문 그대로 옮긴 게 아님).
E0052=시스템 처리 중 오류가 발생했습니다. 관리자에게 문의하세요.
```
**주의**: `E0052`의 원래 NEXCORE 메시지 문구를 확인 못 했다. 지금 문구는 새로 지어낸 잠정 텍스트이지 원본 포팅이 아니다 — CLAUDE.md "로직은 새로 짜지 않고 포팅한다" 원칙과 결이 다른 유일한 예외라 여기 명시한다. 원본 문구를 찾으면 교체해야 한다. `W0024`/`I0016` 등 다른 코드는 실제 사용처를 발견하기 전까지 추가하지 않는다(추측 코드 생성 금지).

## 결정이 필요한 것 (검토 후 알려주면 반영)
1. HTTP status 정책 — 안 A(4xx/5xx) vs 안 B(항상 200)
2. ~~`W`/`I` 코드가 예외로 던져지는지, 안내 메시지인지~~ → **확인됨(위 갱신 참고): 성공 응답에 실리는 안내 메시지다.** 남은 결정은 *어떤 형태로 실을지*다 — ①`CommonApiResponse`에 `notice`(코드+인자) 필드를 추가 ②`data` Map 안에 예약 키를 두기 ③성공 응답에도 `code`/`message`를 허용. 정해지기 전까지 생성기는 이 자리를 비워둔다
3. `code`/`message` 필드명이 사내 다른 프로젝트 컨벤션과 겹치는 이름이 있는지(플랫폼팀 컨벤션 확인 필요 — CLAUDE.md에 이미 있는 TODO)
4. 확정되면 `chatui/skeleton_gen.py`의 Api 템플릿을 `ResponseEntity.ok(service.xxx(...))` → `ResponseEntity.ok(CommonApiResponse.createSuccess(service.xxx(...)))`로 바꿀지 여부(지금은 안 바꿈)
