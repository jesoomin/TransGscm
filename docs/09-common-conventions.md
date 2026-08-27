# 공통 응답/예외 처리 규약 (Phase 2)

> `03-kickoff-plan.md` Phase 2의 "공통 응답/예외 처리 규약 확정 (사람이 먼저 설계 — 화면마다 에이전트가 제각각 만들지 않도록)" 항목에 대한 확정안이다. CLAUDE.md 핵심 원칙("절대 자동화하지 말 것: 공통 응답/예외 처리 규약, 공통 Mapper/Store 패턴은 사람이 먼저 확정한다")에 따라, 화면 변환기가 이 규약을 재발명하지 않고 그대로 참조하게 하기 위한 문서다. 여기 확정된 내용은 실제 사용 확인 전까지는 **제안(proposal)** 이며, 실사용 중 문제가 드러나면 이 문서를 먼저 갱신한 뒤 코드를 고친다.

## 왜 필요한가 — AS-IS 관찰 근거

`/legacy/PPLA047.java`, `/legacy/FPLA047.java` 실제 소스에서 반복 확인되는 패턴:

```java
// P 계층 (PPLA047.java) - 3개 메서드 전부 동일 패턴
IDataSet responseData = new DataSet();
try {
    ...
    responseData.putRecordset("MAIN_LIST", ds.getRecordSet("MAIN_LIST"));
} catch (BizRuntimeException be) {
    throw be;
} catch (Exception e) {
    throw new BizRuntimeException("E0052", new String[] {"통합 DATA 정보"}, e);
}
responseData.setOkResultMessage("I0016", new String[] {"통합 DATA 정보"});
return responseData;
```

```java
// F 계층 (FPLA047.java) - 3개 메서드 전부 동일 패턴, 생성자 형태만 다름(args 배열 없음)
} catch (BizRuntimeException be) {
    throw be;
} catch (Exception e) {
    throw new BizRuntimeException("E0052", e);
}
```

즉 AS-IS에서도 이미 "메시지 코드 + args + cause"로 표준화된 예외 하나(`BizRuntimeException`)와 "성공/경고 메시지 코드"를 얹는 응답 패턴이 화면마다 반복되고 있었다 — 이걸 그대로 TO-BE에 옮기는 것이지, 새로 설계하는 게 아니다. 확인된 메시지 코드는 `E0052`(오류), `W0024`(경고 - 데이터 없음), `I0016`(성공) 3개뿐이며, **실제 문구(한/영)는 NEXCORE 공통 메시지 테이블에만 있고 이 3개 소스 파일 어디에도 없다** — 추측하지 않고 TODO로 남긴다(CLAUDE.md "확인되지 않은 것을 추측으로 하드코딩하지 않는다").

## 확정안

### 1. 예외: `BizException` (`com.skhynix.gscm.common.BizException`)

AS-IS `BizRuntimeException`이 실제로 쓰인 두 생성자 형태를 그대로 포팅 가능하도록 유지한다(로직을 다시 설계하지 않기 위함):

- `BizException(String messageCode, Throwable cause)` — F 계층 패턴(`new BizRuntimeException("E0052", e)`)
- `BizException(String messageCode, String[] args, Throwable cause)` — P 계층 패턴(args 있음)
- `BizException(String messageCode, String[] args)` — cause 없는 경우 대비

`RuntimeException`을 상속해 catch 강제하지 않는다(AS-IS도 unchecked).

### 2. 응답 포맷: `ApiResponse<T>` (`com.skhynix.gscm.common.ApiResponse`)

AS-IS의 `IDataSet` + `setOkResultMessage(code, args)` 조합을 그대로 반영한 필드:

| 필드 | 대응하는 AS-IS 개념 |
|---|---|
| `resultCode` (`ResultCode.OK` / `ResultCode.ERROR`) | try 블록 정상 종료 여부 |
| `messageCode` | `setOkResultMessage`/`BizRuntimeException`의 code (예: `I0016`, `E0052`) |
| `message` | messageCode를 `errors.properties`로 해석 + args 치환한 최종 문구 |
| `data` | `responseData.putRecordset(...)`로 담기던 실제 페이로드 |

`{화면}Api`는 정상 흐름에서 `ApiResponse.success(data, messageCode, args)`를 반환한다. 실패는 예외로만 표현하고(`BizException` 던지기), Api/Service가 직접 실패용 `ApiResponse`를 만들지 않는다 — `GlobalExceptionHandler`가 유일한 생성 지점이다(화면마다 에이전트가 실패 응답을 제각각 조립하는 걸 막기 위함).

### 3. 예외 처리: `GlobalExceptionHandler` (`@RestControllerAdvice`)

- `BizException` → `ApiResponse.fail(messageCode, message)`
- 그 외 처리 안 된 `Exception` → 메시지 코드 없이 떨어지는 상황 자체가 AS-IS에서도 비정상이었으므로(P/F 계층 모두 `catch(Exception e)`에서 반드시 `E0052`로 감싸 재던짐), 여기 도달하면 포팅 과정에서 원본의 catch-and-wrap을 빠뜨렸다는 신호로 간주하고 고정 코드 `E9999`(신규, NEXCORE에 없음 — 매핑 실패 자체를 나타내는 전용 코드)로 감싼다.

**HTTP status는 항상 200으로 고정한다.** 성공/실패 구분은 body의 `resultCode`/`messageCode`로만 한다. 이유:
- AS-IS의 nctRid 트랜잭션 자체가 HTTP 개념이 없는 Dataset 직렬화 방식이라 "실패 시 4xx/5xx" 같은 대응 개념이 원래 없다.
- CLAUDE.md 핵심 검증 전략인 차등 테스트(레거시 Dataset 응답 ↔ 신규 REST JSON 응답 diff)가 HTTP status까지 따로 정규화할 필요 없이 body만 비교하면 되도록 단순해진다.
- 진짜 인프라 장애(DB 연결 불가 등 Spring 자체가 못 잡는 경우)만 컨테이너가 기본으로 내리는 500으로 남긴다 — 이 경우는 body도 못 만드므로 위 규약 밖이다.

### 4. 메시지 코드 외부화

`resources/message/errors.properties`(한국어 기본) / `errors_en.properties`(영어) — key는 메시지 코드, value는 `{0}`, `{1}`... 플레이스홀더가 있는 `MessageFormat` 템플릿(AS-IS `new String[] {"통합 DATA 정보"}` 인자를 그대로 대응). PLA047에서 확인된 3개 코드(`E0052`/`W0024`/`I0016`)만 우선 등록하고 **실제 문구는 비워둔 채 TODO로 표시** — NEXCORE 공통 메시지 테이블 확인 후 채울 것.

### 5. MyBatis 연동 방식: `SqlSessionTemplate` 직접 호출로 확정 (Mapper 인터페이스 도입 안 함)

`docs/07-tobe-structure.xlsx`로 확정된 AS-IS→TO-BE 파일 매핑에는 `{화면}Store`(클래스)와 `{화면}Mapper.xml`만 있고 별도의 `{화면}Mapper.java` 인터페이스는 없다. 확정된 구조에 없는 파일 종류를 새로 추가하지 않기 위해, `{화면}Store`가 `SqlSessionTemplate`을 직접 주입받아 `sqlSession.selectOne("{화면}Mapper.문statement id", params)` 형태로 호출하는 현재 `chatui/skeleton_gen.py` 방식을 그대로 확정한다(`@Mapper` 인터페이스 방식은 채택하지 않음).

## 아직 미확정 — 다음에 필요

- `E0052`/`W0024`/`I0016` 등 메시지 코드의 실제 한/영 문구 (NEXCORE 공통 메시지 테이블 확인 필요, 추측 금지)
- 요청 필드 검증(예: 필수값 누락) 실패를 `BizException`으로 표현할지, Spring `@Valid`/`BindException`으로 표현할지 — 지금까지 확인된 3개 소스 파일에는 그런 검증 코드가 없어 근거가 없다. 표본이 늘어나면 재확인
