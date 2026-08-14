# 착수 세부 실행 계획 (v2 — 백엔드 전용 범위)

이 문서는 실제 코드 작업을 시작하기 전에 무엇부터, 어떤 순서로 할지를 정리한다. **순서는 @docs/06-mentor-feedback.md §J "적용 우선순위"를 그대로 따른다: 1~4번이 프로젝트 성패의 80%이고 LLM은 6번에서야 등장한다.** 이 순서를 바꾸지 않는다.

> v2 변경사항: UI(xfdl→React) 전환이 범위에서 빠지고 서버(Java/XSQL) 전환만 남았다. 이전 Phase 0~3(v1)에서 확보한 사실은 대부분 유효해 아래로 이관했다.

## Phase 0 — 사전 확보 (착수 즉시, 코드 작성 전)
- [ ] UIAdapter의 서블릿/URL 패턴 및 nctRid 라우팅 코드 확보
- [ ] `.xjs` 스크립트의 `transaction()` 호출부 → nctRid 문자열 추출 규칙 확인 (UI는 전환 안 하지만 화면↔nctRid 대응은 여전히 필요)
- [ ] `.BIZUNIT` XML 샘플 1세트 확보 및 스키마(필드/타입 정의 포맷) 파악 — 지금까지 본 3개(PLA047)는 전부 `<fields/>` 비어있음, 실제로 항상 비는지 다른 화면으로 확인 필요
- [x] PPLA047.JAVA / FPLA047.JAVA / DPLA047.JAVA / DPLA047.XSQL 실제 소스 1세트 확보 — `/legacy`에 확보됨. **소스 자체에 무결성 문제 있음** (아래 참고), 재확보 또는 원본 대조 필요
- [x] P BizUnit이 순수 진입점인지, 화면별 검증 로직이 섞여 있는지 코드로 확인 — PPLA047.java 확인 결과 **순수 위임(delegation)만 수행**, 검증 로직 없음. `PLA047` 1건 기준, 나머지 화면은 표본 확대 필요
- [ ] 소스코드 외부 LLM 전송 관련 사내 보안 정책 확인 (폐쇄망/사내 LLM 게이트웨이 필요 여부)
- [ ] 1,416개 전체 화면 목록·메뉴구조 전체본 확보 — 현재 `docs/메뉴구조.xlsx`(v1, xfdl 포함)와 `docs/07-tobe-structure.xlsx`(v2, PLA047 AS-IS/TO-BE 1건)만 있음, 전체본 아님
- [x] AS-IS 원본 소스를 `/legacy` 폴더에 정리 — PLA047 세트(P/F/D BizUnit + XSQL) 확보됨
- [ ] **`/legacy`의 PLA047 소스 무결성 문제 해결** — `.bizunit` XML 3종은 아직 XML 선언 손상(따옴표 불일치, `<description>`/`</dedication>` 태그 불일치)으로 파싱 불가. `FPLA047.java`/`PPLA047.java`는 아직 컴파일 에러 다수(중괄호 누락, 미선언 변수 `du`, `ArrayList<object>` 등). **`DPLA047.xsql`은 2026-08-14 중 갱신되어 `S001~S006`이 전부 정의되고 `</sqlMap>`으로 닫히는 등 대폭 개선됨** — `chatui/converters.py`에 넣은 스택 기반 태그 검사로 확인한 결과 태그 불일치 2건 확정: ① 4718행 `<isNotEqual property="CHKDASHBOARDYN">`가 4840행에서 `</isEqual>`로 잘못 닫힘 ② 5179행 `</isNotEqual>`가 매칭되는 여는 태그 없이 단독 존재. 이 2곳만 고치면 XSQL은 유효한 XML이 될 가능성이 높다(EOF까지 태그 총량은 우연히 맞음)
- [x] `.bizunit` 3종 + `FPLA047.java`/`PPLA047.java`도 변환 대상에서 제외하지 않는다 — 확인됨(아래 참고). 원본이 깨져 있어도 스킵하지 않고 `.BIZUNIT`은 코드 실사용값(getField/putField) 역추출로, Java는 원본 정정 후 포팅으로 진행
- [x] 로컬 Oracle DB(`RPLS_ADM`, localhost:1521, SID=`xe`) 접속 확인 — `sqlplus`로 검증 완료(2026-08-14): 로그인 성공, 실제 SERVICE_NAME도 `xe`, DB_NAME=`XE`. **주의: 사용자가 전달한 "service_name=GSCM"은 Oracle 서비스명이 아니라 DB 접속 도구에 저장된 연결 프로파일 이름이었음** — `GSCM`을 서비스명으로 접속 시도하면 ORA-12514(서비스 없음) 발생, 실제로는 SID `xe` 사용. `.env`에 검증된 JDBC URL(`jdbc:oracle:thin:@localhost:1521:xe`) 반영 완료. 스키마 접근 권한(테이블 조회 등)은 아직 세부 검증 안 함

## Phase 1 — nctRid 매핑 그래프 + 차등 테스트 하네스 (변환기보다 먼저)
멘토 코멘트 §1, §3. 이게 없으면 에이전트가 화면마다 코드베이스를 헤매며 환각을 낸다.
- [ ] `.xjs` → `transaction()` 호출부 → nctRid 추출 (정적 분석, LLM 아님). 동적 문자열 조합이면 부분 평가/상수 전파 필요
- [ ] NEXCORE 설정에서 nctRid → P BizUnit 클래스 매핑 추출
- [ ] JavaParser로 P → F → D 콜그래프 추적
- [ ] D BizUnit → XSQL namespace + queryId 매핑
- [ ] 위 4단계를 이어 화면↔API↔SQL 전체 그래프를 DB(또는 구조화 파일)로 구축. 자동 추출 실패 케이스(문자열 규칙 불일치, 경험상 전체 10~20%)는 사람이 채운다
- [ ] 차등 테스트 하네스 구축: 동일 입력 → 레거시 nctRid 호출 / 신규 REST 호출 → 정규화 후 diff. 로컬 Oracle DB(`.env`)에 두 경로를 붙여서 파일럿 전에 먼저 동작 확인

## Phase 2 — 공통 규약 + 결정론적 변환기 + 업로드→변환 챗팅 UI
화면 하나를 통째로 넣지 않는다 — `.BIZUNIT`/P/F/D/XSQL 5개 fragment로 나눠 처리하고, **콜그래프 역순(XSQL → Store → Service → Api)** 으로 하위부터 확정한다. 상위(Api) 시그니처를 먼저 잡고 하위를 끼워 맞추지 않는다.
- [ ] 공통 응답/예외 처리 규약 확정 (사람이 먼저 설계 — 화면마다 에이전트가 제각각 만들지 않도록)
- [ ] 메시지 코드 표준화: AS-IS 하드코딩 코드(`E0052`, `W0024`, `I0016` 등) → `errors.properties`/`errors_en.properties` 추출 규칙
- [x] iBatis → MyBatis 변환 모듈 v0 — `chatui/converters.py`. PLA047에서 검증한 4종 규칙(`isEqual`/`isNotEqual`/`isNotEmpty`+`iterate`/바인드 변수) + 멘토 코멘트의 `isNull`/`isNotNull`/`isGreaterThan` 등/`dynamic prepend`도 규칙만 준비. **실제로 검증된 건 PLA047뿐**이라 다른 화면 XSQL에 돌려서 결과를 반드시 확인할 것. 변환 후 XML well-formed 여부까지 자동 체크해서 경고로 보여줌(원본 태그 불일치를 여기서 잡아냄)
- [x] BizUnit 메서드 시그니처 → Controller(`{화면}Api`)/Service/Store 골격 생성기 v0 — `chatui/skeleton_gen.py`. PLA047 실 소스로 동작 검증: P 메서드가 실제로 호출하는 F 메서드를 본문에서 찾아 Api→Service 연결까지 정확히 맞춤(단순 이름 매칭이 아님). D 메서드는 `dbSelect("S00N", ...)` 호출에서 매퍼 statement id를 뽑아 Store가 참조하도록 생성. **골격만 규칙 기반, Service 메서드 본문은 항상 TODO 스텁 — LLM 포팅은 별도 단계**
- [x] `.BIZUNIT` 필드 → DTO 생성기 — `chatui/skeleton_gen.py`의 `extract_dto_fields`/`generate_dto` (규칙 기반, LLM 아님). `.BIZUNIT`의 `<fields/>`가 비어있을 때 nctRid(P 메서드)별로 요청 필드는 delegate F 메서드의 `getField` 호출, 응답 필드는 P 메서드의 `putRecordset` 호출에서 역추출. PLA047로 검증: RPLA04701은 15개 요청 필드 전부 채워짐, RPLA04702/03은 F가 `getFieldMap()`을 통째로 넘기는 구조라 개별 필드를 못 찾아 TODO+WARNING으로 표시(추측하지 않고 사람 확인 필요 처리). 필드 타입은 전부 String/`List<Map<>>`로 잠정 지정(원본에 실제 타입 미선언)
- [ ] 화면별 변환 전에 `conversion-plan.json`(대상 fragment, 트랙(Refactor/Reimagine), 예상 산출 파일 목록)을 먼저 생성해 고정 — 계획 없이 바로 코드 생성하지 않는다
- [x] **업로드→변환 챗팅 UI v0** — `chatui/app.py` (Streamlit, 로컬 전용). 화면 1개 분량 P/F/D `.java`/`.bizunit`+XSQL을 업로드하면 위 결정론적 변환기를 돌려 결과를 화면에 보여주고, "저장" 버튼을 눌러야만 `pilot/{screen}/`에 파일이 생긴다(자동 커밋 없음). Service 로직 LLM 포팅은 별도 버튼으로 분리(실험적, 결과 검토 필수 문구 표시). 실행: `pip install -r requirements.txt` 후 `streamlit run chatui/app.py` → `http://localhost:8501`. 이 개발 환경엔 Streamlit이 없어 UI 자체는 실행 검증 못 함(내부 변환 로직만 PLA047 실 소스로 검증됨)
- [x] Validation(정적 검증, 1단계) — `chatui/validators.py` 신규 구현(변환기와 분리된 검증기, CLAUDE.md "Translator/Validator 분리" 원칙). Maven/Gradle 프로젝트(pom.xml, 의존성)가 아직 없어 진짜 컴파일은 못 하지만, 그 전 단계로 정적 검사를 한다: Java 파일 중괄호 균형(문자열/주석 인식), LLM 포팅 후 남은 PORT_START 스텁 탐지, 계층 간 실제 호출 대상 존재 확인(Api의 service.xxx() → Service 정의 여부, Service의 store.xxx() → Store 정의 여부, Store가 참조하는 매퍼 statement id → Mapper.xml 존재 여부), Mapper.xml well-formed 여부·statement id 중복·바인드 표현식 짝. 결과는 PASS/FAIL로 `CONV_FILE.BUILD_CHECK`에 저장되고 실패 이슈는 `CONV_ISSUE`에 `detected_by='chatui/validators.py'`로 쌓인다. PLA047로 실 DB 검증: Api/Store/Dto/계층간참조 PASS, Service는 원본 버그(중괄호 누락) 보존 때문에 의도대로 FAIL, XSQL은 알려진 태그 불일치로 의도대로 FAIL — 전부 실제로 CONV_FILE/CONV_ISSUE에 기록됨 확인. **실제 Maven 빌드/기동 검증은 여전히 미착수** — pom.xml 등 빌드 환경 구축이 선행되어야 함

## Phase 3 — 파일럿 20~30화면 (자체 벤치마크 구축 겸함)
- [ ] 전체 화면을 컴포넌트 구성 + transaction 개수 + 그리드 유무 기준으로 구조적 클러스터링
- [ ] 유형별 대표 화면 4~5개씩, 총 20~30개 선정 (단순조회/그리드, 조회+상세+CRUD, 복합화면·리포트·특수로직)
- [ ] 화면별로 **Refactor(1:1 구조보존) / Reimagine(업무규칙만 추출해 재설계) 트랙**을 사람이 결정 — 단순조회·CRUD는 대부분 Refactor, 복합화면·원본 자체가 망가진 화면(예: PLA047의 FPLA047처럼 컴파일도 안 되는 경우)은 Reimagine 후보로 분류
- [ ] Phase 1~2 결과로 실제 변환 실행, `/tracking` 검증 테이블(@docs/08-conversion-verification.md)에 화면별 결과 기록 — 특히 **사람 수정 라인 비율**(자동 생성 대비 리뷰 중 수정한 라인 비율)을 반드시 기록. 이게 실제 공수 절감률의 대리 지표(@docs/06-mentor-feedback.md §H)
- [ ] 변환 규칙·프롬프트·공통 컴포넌트를 자산화 (이후 RAG 코퍼스로 사용)
- [ ] 유형별 실측 공수로 전체 계획 재산정 — 목표는 "화면이 돌아간다"가 아니라 "유형별 변환 레시피와 실측 공수 확보". @docs/01-project-plan.md의 v2 KPI 조정치(평균 3일, 65~70% 절감)와 실측을 비교

## Phase 4 — LLM 에이전트 파이프라인
- [ ] Analyzer / Planner / Translator / Validator 역할 분리 (ReCodeAgent 구조 차용, @docs/06-mentor-feedback.md §B)
- [ ] 화면 유형별 프롬프트 분기 (단일 프롬프트로 전체 처리 시도하지 않음)
- [ ] 유사 화면 벡터 검색 → few-shot 주입 (RAG, 파일럿 결과물이 코퍼스)

## Phase 5 — Reflection·수리 루프
- [ ] 컴파일 에러 / 빌드 에러를 피드백으로 재생성, 재시도 상한 2~3회
- [ ] 검증(Validator)과 수리(Fix) 역할 분리, 최종 판정자 별도

## 로컬 Oracle DB
- 호스트/포트/계정/비밀번호는 `.env`(프로젝트 루트, 커밋 제외)에 설정. `.env.example`에 키 이름만 공유.
- 용도: Phase 1의 차등 테스트 하네스(레거시 vs 신규 API 응답 비교), Phase 2 이후 Store 계층 실제 쿼리 동작 확인.
- 실제 커넥션 테스트(JDBC 접속 확인)는 아직 실행 안 함 — 다음 세션에서 확인 필요.

## 진행 시 유의사항
- Phase 0~1에서 확인한 사실이 @docs/02-architecture.md의 가정과 다르면, 코드를 먼저 짜지 말고 문서부터 갱신한다
- 화면 20~30건 파일럿 전까지는 전체 1,416개 화면에 대한 일괄 처리 스크립트를 만들지 않는다
- 결정론적으로 풀리는 변환에 LLM을 쓰지 않는다 (CLAUDE.md "하지 말아야 할 것" 참고)
- 매 Phase 종료 시 이 문서의 체크박스를 갱신해 진행 상황을 추적한다
