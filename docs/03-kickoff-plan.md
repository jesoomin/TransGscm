# 착수 세부 실행 계획

이 문서는 실제 코드 작업을 시작하기 전에 무엇부터, 어떤 순서로 할지를 정리한다. Phase 0이 끝나지 않으면 Phase 1 이후 작업 대부분이 가정(assumption) 위에 쌓이게 되므로, Phase 0을 건너뛰지 않는다.

## Phase 0 — 사전 확보 (착수 즉시, 코드 작성 전)
- [ ] UIAdapter의 서블릿/URL 패턴 및 nctRid 라우팅 코드 확보
- [ ] `.BIZUNIT` XML 샘플 1세트 확보 및 스키마(필드/타입 정의 포맷) 파악
- [x] PPLA047.JAVA / FPLA047.JAVA / DPLA047.JAVA / DPLA047.XSQL 실제 소스 1세트 확보 — `/legacy`에 확보됨. 단, **소스 자체에 무결성 문제 발견** (아래 참고), 재확보 또는 원본 대조 필요
- [x] P BizUnit이 순수 진입점인지, 화면별 검증 로직이 섞여 있는지 코드로 확인 — PPLA047.java 확인 결과 **순수 위임(delegation)만 수행**, 검증 로직 없음. `PLA047` 1건 기준 확인, 나머지 화면은 표본 확대 필요
- [ ] 소스코드 외부 LLM 전송 관련 사내 보안 정책 확인 (폐쇄망/사내 LLM 게이트웨이 필요 여부)
- [ ] 1,416개 전체 화면 목록·메뉴구조 전체본 확보 — 현재 `docs/메뉴구조.xlsx`에 화면(xfdl) 42건 + PLA047/COT998 백엔드 경로 세트만 확보된 상태, 전체본 아님
- [x] AS-IS 원본 소스를 `/legacy` 폴더에 정리 — PLA047 세트(P/F/D BizUnit + XSQL) 확보됨, 단 아직 플랫 구조라 CLAUDE.md의 원본 경로 구조로 재정리 필요
- [ ] **(신규, 2026-08-12 발견) `/legacy`의 PLA047 소스 무결성 문제 해결** — `.bizunit` XML 3종 모두 XML 선언 손상으로 파싱 불가(닫는/여는 따옴표 불일치, `<description>`/`</dedication>` 태그 불일치), `FPLA047.java`/`PPLA047.java`는 컴파일 에러 다수(중괄호 누락, 미선언 변수 `du`, `ArrayList<object>` 등), `DPLA047.xsql`은 `S002`가 2706행에서 열려 2850행에서 `</isEqual>`로 잘못 닫히고 `S003~S006`이 아예 정의되어 있지 않음(D BizUnit이 호출하는 6개 중 2개만 존재). 원본 재확보 또는 원인 확인 전까지 이 화면의 F/D 로직 재사용을 신뢰할 수 없음

## Phase 1 — 파일럿 샘플 선정 및 소규모 실험 (1주차)
- [ ] 화면 유형별(단순조회 / 그리드 / 입력폼 / 복합화면) 대표 화면 10~20개 선정
- [ ] xfdl 파서 프로토타입 (lxml) — 화면 구조를 중간표현(IR)으로 추출
- [ ] `.BIZUNIT` XML 파서 프로토타입 — 입출력 필드/타입 스키마 추출
- [ ] 사내 GaiA 프레임워크로 "파일 읽기 → 분석 → 구조화 출력" Agent 최소 실험 — 기존 Orchestrator를 코드 변환 도메인에 그대로 적용할 수 있는지 검증
- [ ] 실험 결과를 바탕으로 GaiA 재사용 가능 여부 1차 결론 — 안 되면 LangGraph 등 대안 검토로 조기 전환

## Phase 2 — 변환 엔진 골격 구현 (2주차)
- [ ] Parsing Agent: xfdl / `.BIZUNIT` / XSQL → IR 생성 로직 구현
- [x] Conversion Agent: IR → React 컴포넌트 + REST Controller 스켈레톤 생성 (Claude API 연동) — PLA047 한정 REST Controller 초안 작성(`pilot/PLA047/Pla047Controller.java`). 수작업 1건 검증 단계, Agent화는 아직. FPLA047 컴파일 에러로 실제 빌드는 안 됨
- [x] iBatis → MyBatis 문법 변환 규칙 기반 모듈 구현 (표 기반 치환 — 우선 자동화율 가장 높은 영역) — PowerShell 정규식 스크립트로 규칙 4종(`isEqual`→`if`, `isNotEqual`→`if`, `isNotEmpty`+`iterate`→`if`+`foreach`, `#x#`/`$x$`→`#{x}`/`${x}`) 기계적 치환 검증. PLA047의 `queryCommon` 프래그먼트(2,680행) + `S001`에 적용해 XML 파서로 결과물 유효성 확인(`pilot/PLA047/DPLA047-mapper.xml`). 화면 1건 표본 — 일반화된 Agent/모듈로 만들려면 더 많은 화면으로 규칙 검증 필요
- [ ] Validation Agent: 생성된 코드에 대해 빌드(Maven/Gradle)·린트(ESLint/tsc) 자동 실행

## Phase 3 — 파일럿 검증 및 KPI 재조정
- [ ] Phase 1에서 선정한 화면 10~20건에 대해 실제 변환 실행
- [ ] 화면당 소요시간, 자동변환 커버리지(빌드/린트 통과율) 실측
- [ ] 실측치를 기준으로 @docs/01-project-plan.md의 KPI(화면당 2일, 커버리지 70% 등) 재조정
- [ ] 리뷰 대시보드(Streamlit) 초안 — diff 확인, 자동 통과/부분 검토/수동 검토 분류

## 진행 시 유의사항
- Phase 0에서 확인한 사실이 @docs/02-architecture.md의 가정과 다르면, 코드를 먼저 짜지 말고 문서부터 갱신한다
- 화면 10~20건 파일럿 전까지는 전체 1,416개 화면에 대한 일괄 처리 스크립트를 만들지 않는다
- 매 Phase 종료 시 이 문서의 체크박스를 갱신해 진행 상황을 추적한다
