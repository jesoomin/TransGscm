# 아키텍처 분석: NEXCORE(AS-IS) → Spring/MyBatis(TO-BE)

> 이 문서는 전환 프로그램 **1단계 = 서버(Java/XSQL) 전환** 아키텍처만 다룬다. 화면(xfdl → React)은 2단계 별도 트랙이며, nctRid 계약을 통해 1단계 산출물을 그대로 소비한다. 근거는 @docs/05-proposal.md, 멘토 코멘트는 @docs/06-mentor-feedback.md.

## AS-IS: NEXCORE 구조
NEXCORE는 SK그룹 표준 Java Spring 기반 애플리케이션 프레임워크로, 업무 로직을 BizUnit 단위로 개발한다. G-SCM에서는 화면 하나당 P(Presentation)/F(Function)/D(Data) 3개 BizUnit과 XSQL(iBatis SQL 매핑) 세트로 구성되어 있다.

요청 흐름:
- Nexacro 화면이 Dataset을 구성해 트랜잭션을 호출한다 (예: `nctRid = RPLA04701`)
- UIAdapter가 Nexacro의 Dataset을 서버의 IDataSet 객체로 직렬화해 전달한다
- nctRid 하나로 들어온 요청이 공통 디스패처를 거쳐 P → F → D BizUnit 순서로 호출된다
- D BizUnit이 `dbSelect("S00N", paramMap, ctx)` 형태로 XSQL(iBatis) SQL을 실행한다
- 응답은 다시 IDataSet으로 감싸져 UIAdapter를 통해 Nexacro Dataset으로 돌아간다

## TO-BE: Spring/MyBatis 구조 (1단계 범위)
Nexacro 화면은 그대로 두고, 그 화면이 호출하던 nctRid 트랜잭션과 **동일한 계약**을 갖는 REST API를 새로 만든다. 나중에 확정된 디자인으로 React 화면이 만들어지면, 지금 만든 API를 그대로 호출한다 (Strangler Fig — 레거시와 신규 API가 당분간 공존).

`docs/07-tobe-structure.xlsx`로 확정된 매핑 (추측 아님, PLA047 기준 확인):

| AS-IS | TO-BE | 역할 |
|---|---|---|
| UIAdapter + nctRid 디스패처 + P BizUnit | `{화면}Api` (Controller) | REST 엔드포인트. nctRid 1개 = 엔드포인트 1개로 1:1 매핑 유지 (범용 CRUD/그리드 API로 재설계하지 않음). **P가 순수 위임이 아니면(권한 게이트·결과 메시지·레코드셋 선별) 그 흐름도 함께 포팅해야 한다 — 위임 한 줄로 만들면 로직이 사라진다** |
| F BizUnit | `{화면}Service` | 업무 로직 포팅. NEXCORE 프레임워크 의존 제거, 로직(계산·분기)은 그대로 |
| D BizUnit + XSQL | `{화면}Store` + `{화면}Mapper.xml` | 데이터 접근 포팅. SQL은 MyBatis 문법으로만 변환 |
| `.BIZUNIT` XML | `{화면}Dto` | 입출력 스키마. 필드가 비어있으면 AS-IS 코드의 `getField`/`putField` 실사용 값에서 역추출 |
| 하드코딩 메시지 코드 | `resources/message/errors*.properties` | 국제화 대비 외부화 (AS-IS엔 없던 신규 산출물) |
| DB 스키마 | 변경 없음 | — |

패키지: `com.skhynix.gscm.r.{p1}.{p2}` (AS-IS의 `{p2}b` 서브패키지는 사라짐).

## 결정론적 변환 / LLM 변환의 경계
멘토 코멘트(@docs/06-mentor-feedback.md §2) 기준. 여기를 잘못 그으면 비용은 쓰고 품질은 안 나온다.

**100% 규칙 기반 (LLM 쓰지 않음)**
- iBatis → MyBatis: `#var#`→`#{var}`, `$var$`→`${var}`, `<isEqual>/<isNotEqual>`→`<if>`, `<isNotEmpty>`+`<iterate>`→`<if>`+`<foreach>`
- P/F/D BizUnit 메서드 시그니처 → Controller/Service/Store 골격 (클래스·메서드 이름, 파라미터 자리)
- `.BIZUNIT` XML(또는 역추출한 필드) → DTO 클래스 골격

**LLM 필요**
- P BizUnit의 오케스트레이션(여러 F 호출 순서, 권한 게이트 조기 반환, 결과 유무 분기, 반환할
  레코드셋 선별)을 Api 메서드 본문으로 포팅 — 순수 위임인 P는 여전히 규칙 기반 한 줄이다
- F BizUnit 내부의 실제 계산·분기 로직을 Service 메서드 본문으로 포팅 (기계적 1:1 치환이 안 되는 부분 — 특히 NEXCORE 전용 API 호출부)
- `.BIZUNIT` 필드가 비어있을 때 실사용 코드에서 필드 스키마 추론
- 에러 메시지 코드(`E0052` 등) → `errors.properties` 매핑 시 문맥에 맞는 메시지 문구 정리

**절대 자동화하지 말 것**
- 공통 응답/예외 처리 규약, 공통 Mapper/Store 패턴은 사람이 먼저 확정한다. 화면마다 에이전트가 제각각 만들면 지금의 "개발자별 이원화" 문제가 그대로 재현된다.

## 검증 전략: 차등 테스트(Differential Testing)
"변환된다"와 "맞다"는 다른 문제다 — 문법 정확도가 높아도 기능적 정확성은 별개로 검증해야 한다.

```
동일 입력 → [레거시 nctRid 호출]   → IDataSet 응답 ┐
                                                    ├→ 정규화 후 diff
동일 입력 → [신규 REST API 호출]   → JSON 응답     ┘
```
NEXCORE가 단일 진입점(nctRid)에 고정된 Dataset 포맷을 쓰기 때문에 이 비교가 깔끔하게 성립한다. 로컬 Oracle DB(`.env` 설정, @CLAUDE.md "로컬 개발 환경" 참고)에 두 경로를 동시에 붙여서 이 하네스를 파일럿보다 먼저 구축한다.

변환기(Translator)와 검증기(Validator)는 별도 모듈로 분리한다 — 나중에 변환기를 바꿔도 검증 자산(차등 테스트 하네스, 결과 리포트)이 살아남게 하기 위함.

## 선결 확인 필요 사항 (Phase 0)
- UIAdapter의 실제 서블릿/URL 패턴 및 nctRid 라우팅 코드 — nctRid 매핑 그래프 구축의 전제
- `.xjs` 스크립트의 `transaction()` 호출부 → nctRid 문자열 추출 규칙 (동적 조합인 경우 부분 평가 필요) — **화면 자체는 2단계 몫이지만, 어떤 화면이 어떤 nctRid를 쓰는지 알아야 TO-BE API와 대응시킬 수 있어 이 분석은 1단계에 필요**
- `.BIZUNIT` XML의 실제 스키마 (필드/타입 정의 포맷) — 비어있는 경우가 많아 대체 추출 규칙 필요
- ~~P BizUnit이 순수 진입점 역할만 하는지~~ → **표본을 넓혀 확인 완료(2026-09-05): 순수 위임이 아니다.** PLA047 1건만 볼 때는 순수 위임이었지만 `PLA081-110_migration_sample` 30화면을 전수 확인하니 30/30이 권한 게이트(`AUTH_YN` 확인 후 조기 반환)를 갖고 있고, `setOkResultMessage` 호출 195건, `getRecordSet`으로 특정 레코드셋만 골라 담는 코드 165건이 있다. 즉 P는 **여러 F를 순서대로 부르고 분기하는 오케스트레이션 계층**이다. 그래서 Api를 위임 한 줄로 생성하면 이 로직이 통째로 사라진다 — 실제로 그렇게 생성하고 있었고, L3 실행 하네스가 Api 계층 0/9로 잡아냈다(`agents/equivalence_test.py`). 지금은 `skeleton_gen.detect_p_orchestration()`이 이런 P를 골라내 Api를 LLM 포팅 대상으로 남긴다
- 소스코드 외부 LLM 전송에 대한 사내 보안 정책
- 로컬 Oracle DB 접속 가능 여부 및 스키마(`RPLS_ADM`) 접근 권한 확인

## 리스크 (멘토 코멘트 §6, 1단계 범위에서 재해석)
- **Dataset 상태 모델**: Nexacro의 `rowState`(insert/update/delete 플래그)는 프론트 개념이라 1단계(서버 전환) 범위에선 직접 영향은 적지만, API가 트랜잭션 단위(nctRid 1:1)를 유지하는 한 D BizUnit의 개별 insert/update/delete 메서드 단위 그대로 Store 메서드로 옮기면 된다. 이후 2단계 React 트랙에서 그리드 dirty tracking을 어떻게 표현할지는 **API 설계 시점에 미리 고려**해야 나중에 API를 다시 바꾸지 않는다.
- **동기 호출 유지**: 지금은 REST도 기존과 동일하게 동기 요청/응답으로 유지한다. Nexacro `transaction()` 콜백 → `async/await` 재작성은 2단계 React 트랙의 문제이므로 여기서 미리 비동기로 설계하지 않는다.
