# 착수 세부 실행 계획 (1단계 — 서버 전환)

이 문서는 실제 코드 작업을 시작하기 전에 무엇부터, 어떤 순서로 할지를 정리한다. **순서는 @docs/06-mentor-feedback.md §J "적용 우선순위"를 그대로 따른다: 1~4번이 프로젝트 성패의 80%이고 LLM은 6번에서야 등장한다.** 이 순서를 바꾸지 않는다.

> 범위는 전환 프로그램 1단계(서버 Java/XSQL → Spring/MyBatis)다. 화면(xfdl → React)은 2단계 별도 트랙이므로 이 계획에 포함하지 않는다.

## Phase 0 — 사전 확보 (착수 즉시, 코드 작성 전)
- [ ] UIAdapter의 서블릿/URL 패턴 및 nctRid 라우팅 코드 확보
- [ ] `.xjs` 스크립트의 `transaction()` 호출부 → nctRid 문자열 추출 규칙 확인 (화면 자체는 2단계 몫이지만 화면↔nctRid 대응은 1단계에 필요)
- [ ] `.BIZUNIT` XML 샘플 1세트 확보 및 스키마(필드/타입 정의 포맷) 파악 — 지금까지 본 3개(PLA047)는 전부 `<fields/>` 비어있음, 실제로 항상 비는지 다른 화면으로 확인 필요
- [x] PPLA047.JAVA / FPLA047.JAVA / DPLA047.JAVA / DPLA047.XSQL 실제 소스 1세트 확보 — `/legacy`에 확보됨. **소스 자체에 무결성 문제 있음** (아래 참고), 재확보 또는 원본 대조 필요
- [x] P BizUnit이 순수 진입점인지, 화면별 검증 로직이 섞여 있는지 코드로 확인 — PPLA047.java 확인 결과 **순수 위임(delegation)만 수행**, 검증 로직 없음. `PLA047` 1건 기준, 나머지 화면은 표본 확대 필요
- [ ] 소스코드 외부 LLM 전송 관련 사내 보안 정책 확인 (폐쇄망/사내 LLM 게이트웨이 필요 여부)
- [ ] 1,416개 전체 화면 목록·메뉴구조 전체본 확보 — 현재 `docs/메뉴구조.xlsx`(xfdl 포함, 2단계 참고용)와 `docs/07-tobe-structure.xlsx`(PLA047 AS-IS/TO-BE 1건)만 있음, 전체본 아님
- [x] AS-IS 원본 소스를 `/legacy` 폴더에 정리 — PLA047 세트(P/F/D BizUnit + XSQL) 확보됨
- [ ] **`/legacy`의 PLA047 소스 무결성 문제 해결** — `.bizunit` XML 3종은 아직 XML 선언 손상(따옴표 불일치, `<description>`/`</dedication>` 태그 불일치)으로 파싱 불가. `FPLA047.java`/`PPLA047.java`는 아직 컴파일 에러 다수(중괄호 누락, 미선언 변수 `du`, `ArrayList<object>` 등). **`DPLA047.xsql`은 2026-08-14 중 갱신되어 `S001~S006`이 전부 정의되고 `</sqlMap>`으로 닫히는 등 대폭 개선됨** — `chatui/converters.py`에 넣은 스택 기반 태그 검사로 확인한 결과 태그 불일치 2건 확정: ① 4718행 `<isNotEqual property="CHKDASHBOARDYN">`가 4840행에서 `</isEqual>`로 잘못 닫힘 ② 5179행 `</isNotEqual>`가 매칭되는 여는 태그 없이 단독 존재. 이 2곳만 고치면 XSQL은 유효한 XML이 될 가능성이 높다(EOF까지 태그 총량은 우연히 맞음)
- [x] `.bizunit` 3종 + `FPLA047.java`/`PPLA047.java`도 변환 대상에서 제외하지 않는다 — 확인됨(아래 참고). 원본이 깨져 있어도 스킵하지 않고 `.BIZUNIT`은 코드 실사용값(getField/putField) 역추출로, Java는 원본 정정 후 포팅으로 진행
- [x] 로컬 Oracle DB(`RPLS_ADM`, localhost:1521, SID=`xe`) 접속 확인 — `sqlplus`로 검증 완료(2026-08-14): 로그인 성공, 실제 SERVICE_NAME도 `xe`, DB_NAME=`XE`. **주의: 사용자가 전달한 "service_name=GSCM"은 Oracle 서비스명이 아니라 DB 접속 도구에 저장된 연결 프로파일 이름이었음** — `GSCM`을 서비스명으로 접속 시도하면 ORA-12514(서비스 없음) 발생, 실제로는 SID `xe` 사용. `.env`에 검증된 JDBC URL(`jdbc:oracle:thin:@localhost:1521:xe`) 반영 완료. 스키마 접근 권한(테이블 조회 등)은 아직 세부 검증 안 함

## Phase 1 — nctRid 매핑 그래프 + 차등 테스트 하네스 (변환기보다 먼저)
멘토 코멘트 §1, §3. 이게 없으면 에이전트가 화면마다 코드베이스를 헤매며 환각을 낸다.

**DB 재구축(2026-08-28)**: `agents/db.py`의 `CONV_FILE`/`CONV_METHOD`/`CONV_METHOD_CALL`/`CONV_ISSUE`를
로컬 Oracle(RPLS_ADM)에서 전부 DROP 후 최신 `agents/db_schema.sql`(METHOD_ID FK, CONV_METHOD.NCTRID
포함)로 재생성 - 사용자가 명시적으로 요청. 기존에 쌓여있던 CONV_FILE 282행/CONV_ISSUE 1291행은
날아갔다(우리 도구 자체의 메타데이터라 재실행하면 다시 쌓인다, AS-IS 업무 데이터 아님).

- [ ] `.xjs` → `transaction()` 호출부 → nctRid 추출 (정적 분석, LLM 아님). **보류(2026-08-28) - 이
      리포지토리에도, 로컬에 붙어있는 AS-IS 소스 트리(`C:/project/gscm/workspace`)에도 `.xjs` 실제
      샘플이 하나도 없어 검증할 방법이 없다.** 샘플 없이 정규식 규칙을 짜면 CLAUDE.md "확인되지
      않은 nctRid 매핑 규칙을 추측으로 하드코딩하지 않는다" 원칙에 어긋나서 일부러 안 짰다 - 실제
      `.xjs` 샘플이 확보되면 착수.
- [x] NEXCORE 설정에서 nctRid → P BizUnit 클래스 매핑 추출 — **`.bizunit`의 `<method>/<transactionId>`로
      대체** (NEXCORE 라우팅 설정 원본은 아직 미확보). `agents/nctrid_graph.py`의 `analyze_screen()`이
      `skeleton_gen.extract_nctrid_map()`을 그대로 재사용.
- [x] P → F → D 콜그래프 추적 — `agents/nctrid_graph.py`. 기존 `skeleton_gen.py`의 `find_delegate_call`은
      "안전하게 자동 포팅 가능한 단순 위임 1건"만 찾도록 설계돼 있어 그래프용으로는 부족했다 - 새로
      `find_all_calls()`(메서드 본문에서 실제 호출되는 후보를 전부 찾음)를 `skeleton_gen.py`에 추가하고
      이걸로 전체 콜그래프를 잡는다. **실제 검증**: `C:/project/gscm/workspace/.../pm/pla/plab`의 PLA047에서
      `fPLA047QrySelectMainList` 1개 메서드가 D 메서드 4개(dPLA04702~05)를 호출하는 걸 정확히 잡아냄 -
      기존 "단순 위임" 탐지기는 이런 복합 호출을 아예 못 봤다(설계상 의도적으로 스킵).
- [x] D BizUnit → XSQL namespace + queryId 매핑 — 기존 `skeleton_gen.py`의 statement id 추출 로직을
      `extract_d_stmt_ids()`로 공개 함수화(원래 `generate_skeletons()` 안에 인라인돼 있던 걸 재사용
      가능하게 뺌), `nctrid_graph.py`가 그대로 씀.
- [x] 위 3단계(`.xjs` 제외)를 이어 화면↔BizUnit↔SQL 그래프를 DB로 구축 — `agents/nctrid_graph.py`
      (`analyze_screen`/`persist_screen`/`analyze_folder`, CLI: `python agents/nctrid_graph.py <폴더>`).
      CONV_FILE(P/F/D/XSQL 파일)·CONV_METHOD(메서드별, NCTRID 포함)·CONV_METHOD_CALL(콜그래프 엣지)에
      적재. **50화면 전체(`C:/project/gscm/workspace/.../pm/pla/plab`, PLA001~050) 대상 실행 검증**:
      CONV_FILE 200행, CONV_METHOD 721행, CONV_METHOD_CALL 498행 적재 확인. nctRid는 **PLA047 3건만
      확정**(RPLA04701/02/03) - `.bizunit` 파일이 이 fixture에 PLA047 것밖에 없어서 나머지 49화면
      171개 P 메서드는 전부 "UNRESOLVED"로 정직하게 남겼다(추측 채움 없음, CLI가 화면별 미해결 목록을
      그대로 출력). `db.find_duplicate_methods()`로 화면 간 완전 동일 로직(복붙) 여부도 확인 - 50화면
      전부 대상으로 돌려본 결과 0건(구조는 비슷해도 본문까지 완전히 같은 메서드는 없었음, 정직한 결과).
- [x] **UI_ID별 nctRid 평탄화 매핑표 추가(2026-08-28, 사용자 확인 반영)** — 사용자가 실사용 지식으로
      두 가지를 확정해줬다: ① 화면ID(UI_ID)는 "U-"+P BizUnit 클래스명(예: `U-PPLA047`) ② nctRid는
      `.bizunit`으로 확정 안 되면 P 메서드명 자체(예: `pPLA04701`)로 봐도 된다 - 이걸로 171개
      UNRESOLVED가 전부 해소된다. `agents/db_schema.sql`에 `NCTRID_MAP`(UI_ID/SCREEN_ID/NCTRID/
      NCTRID_SOURCE/P_METHOD/F_METHOD/D_METHOD/MAPPER_STMT_ID) 신규 테이블 추가,
      `agents/nctrid_graph.py`의 `build_nctrid_map_rows()`가 이 규칙대로 CONFIRMED_BIZUNIT(.bizunit
      값) 또는 DERIVED_FROM_METHOD_NAME(P 메서드명)으로 소스를 구분해 채운다. `agents/db.py`의
      `replace_nctrid_map()`(화면 단위 DELETE 후 INSERT, F/D가 NULL일 수 있어 upsert 대신 이 방식)/
      `get_nctrid_map()` 추가. **로컬 Oracle DB에 실제 반영 및 검증 완료**: 50화면 재실행 →
      NCTRID_MAP 226행(UI_ID 50개, distinct NCTRID 174개 = P 메서드 전수와 일치), CONFIRMED_BIZUNIT
      6행(PLA047), DERIVED_FROM_METHOD_NAME 220행(나머지 49화면). **참고(자동 적용 안 함)**: PLA047
      한 건으로 보면 CONFIRMED 값이 정확히 "R"+P메서드에서 앞 소문자 p를 뗀 대문자와 일치한다
      (`pPLA04701`→`RPLA04701`) - 표본 1건뿐이라 나머지 49화면에 이 변환을 추측 적용하지 않고
      코드 docstring에만 관찰 기록으로 남겼다. MAPPER_STMT_ID는 AS-IS XSQL 원본 id(S00N)이며
      TO-BE Mapper.xml의 최종 id(D 메서드명 자체)와 다르다는 점도 문서화함.
- [x] **파일 단위 식별자 컬럼 추가(2026-08-28, 사용자 요청)** — `NCTRID_MAP`에 `PU_ID`/`FU_ID`/`DU_ID`/
      `XSQL_ID` 추가. 화면당 P/F/D BizUnit 파일과 XSQL 파일이 각각 1개씩이라는 CLAUDE.md AS-IS
      구조를 그대로 반영해 "P"/"F"/"D"+SCREEN_ID로 기계적으로 채운다(파일이 실제로 없으면 NULL,
      추측 안 함). 메서드명을 몰라도 nctRid 하나가 물리적으로 어느 AS-IS 파일 4종(.java 3개+.xsql
      1개)에 걸쳐있는지 바로 보이게 하는 게 목적. 50화면 재실행으로 로컬 DB 반영 검증: 226행 전부
      4개 컬럼 채워짐(NULL 0건 - 이 fixture는 50화면 전부 P/F/D/XSQL 4종을 갖추고 있음).
- [x] **정정(2026-08-28) - 지금까지 50화면 실행은 불완전한 사본이었다.** `C:/project/gscm/workspace/...`
      경로는 PLA047만 `.bizunit` 3종을 갖고 나머지 49화면은 `.java`/`.xsql`만 있는 **부분 사본**이었다
      (그래서 이전 실행마다 "PLA047 3건만 CONFIRMED, 나머지 171개 DERIVED" 결과가 나왔다). 리포지토리
      안의 `sample_data/legacy-u-pla001-050/`(+ 생성기 `tools/generate_pla_scenario.py`)이 **진짜
      완전한 사본**이다 - 사용자가 준 PLA047 7개 원본 파일(P/F/D java+bizunit, D xsql)을 화면 코드/
      nctRid 문자열만 결정론적으로 치환해 50벌 복제한 테스트 시나리오(`sample_data/README.md`에
      명시: "이 세트는 테스트용이며 실제 레거시 원본으로 취급하면 안 된다"). 이 완전한 사본으로
      재실행한 결과 **nctRid 150/150 전부 CONFIRMED_BIZUNIT**(P 메서드 3개×50화면), 미해결 항목 0건 -
      `NCTRID_MAP` 300행 전부 확정값으로 갱신됨. 부수 확인: `pPLA0NN0M` -> `RPLA0NN0M`("R"+메서드
      접미사 대문자) 규칙이 150/150 정확히 일치했는데, 생성기 자체가 `RPLA047(\d{2})` -> `RPLA0NN\1`
      정규식 치환으로 이 패턴을 그대로 복제하는 구조라 **이 fixture 안에서의 일치는 생성기 설계의
      재확인이지 실제 NEXCORE 규칙의 독립적 검증은 아니다** - 진짜 검증은 여전히 PLA047 1건뿐이므로
      추측 적용은 계속 보류.
- [x] 차등 테스트 하네스 구축 — **범위를 SQL/Store 계층으로 좁혀서 실제로 동작하는 버전을 만들었다.**
      원래 그림(레거시 nctRid HTTP 호출 vs 신규 REST HTTP 호출 diff)은 NEXCORE 레거시 서버와 Spring
      Boot 신규 서버가 둘 다 떠 있어야 하는데, 이 개발 환경엔 mvn/java 자체가 없어(Phase 2 Maven
      검증 기록과 동일한 한계) 둘 다 띄울 수 없다. 대신 `agents/diff_test.py`가 AS-IS XSQL과
      `converters.py`/`skeleton_gen.py`로 만든 TO-BE MyBatis SQL을 **같은 로컬 Oracle DB에 직접
      실행**해서 결과를 비교한다(동적 태그 없는 정적 바인드 SELECT만 지원 - 범위를 부풀리지 않음).
      **실제 DPLA047.xsql(S001~S006)로 검증**: S001(dPLA04701)은 PMI_PLN_REV에 마킹된 테스트용
      1행을 넣고(`PLN_REV='ZZTEST01'`, 실행 후 바로 삭제) AS-IS/TO-BE 양쪽에서 정확히 동일한 1행이
      나오는 걸 확인(PASS) - iBatis→MyBatis 변환이 최소한 이 statement에서는 의미를 안 바꿨다는 첫
      실증 사례. S002~004는 동적 태그가 있어 SKIPPED(정직하게 미지원 표시), **S005/S006은 실행
      자체가 에러**로 나왔는데 하네스 버그가 아니라 진짜 문제였다 - S005는 로컬 DB의
      `PMO_PROFBLT_IMPROV_PROD` 테이블에 `DATA_GBN_CD` 컬럼이 없음(ORA-00904, 로컬 스키마가
      운영과 다를 수 있다는 신호), S006은 **원본 XSQL 자체가 문법 오류**(`FROM MAD_CALENDAR A
      (SELECT ...) B` - 서브쿼리 앞에 콤마/JOIN이 빠짐, ORA-00933)다. 결과는 `CONV_FILE.DIFF_TEST_CHECK`
      + `CONV_ISSUE`(`detected_by='agents/diff_test.py'`)에 실제로 기록됨을 확인. **다음 단계**: 동적
      태그(`<if>`/`<isEqual>` 등) 케이스까지 지원하려면 이 하네스 자체가 iBatis/MyBatis 조건식을
      평가하는 미니 템플릿 엔진을 가져야 함(아직 없음) - HTTP 레벨(Service/API) diff는 Spring Boot가
      실제로 뜰 수 있는 환경이 생겨야 착수 가능.
- [x] **더미 데이터 자동 생성 (2026-09-01, 멘토 피드백 반영)** — 피드백: "실제 전환이 완료된 건지,
      AS-IS/TO-BE 수행 결과가 같은지 확인할 방법이 없다." 위 차등 테스트 하네스는 바인드 파라미터를
      사람이 손으로 채워야 의미 있었다(안 채우면 둘 다 0행이라 "같다"가 trivial하게 참이 됨 - S001
      검증 때 테스트 행을 손으로 INSERT/DELETE했었음). `agents/dummy_data.py`(신규)가 그 손작업을
      자동화한다: WHERE 절의 단순 조건(`컬럼 = 'literal'`, `컬럼 = #bind#`, `컬럼 != 'literal'`)을
      정적으로 읽어서 그 조건을 만족하는 최소한의 더미 행을 만들고(NOT NULL 컬럼은 타입별 기본값,
      DATE는 SYSDATE), 같은 값으로 AS-IS/TO-BE를 실행 → 비교 → **finally에서 항상 삭제**한다.
      더미 행은 매번 새로 만드는 `ZZDIFFTEST_<8자리 랜덤>` 태그로 표시해 실수로 남아도 바로
      식별 가능. `agents/diff_test.py`에 `run_dummy_diff_test()` 추가, `chatui/app.py`에
      "🧪 차등 테스트 (더미 데이터 자동 생성)" 버튼 추가(단일 화면 탭 / 배치 상세보기 탭 양쪽,
      `_render_diff_test()` 공유 함수). **실제 DPLA047.xsql 6개 statement로 검증**: S001은
      완전 자동으로(사람 개입 0) PMI_PLN_REV에 더미 행을 만들어 AS-IS/TO-BE 양쪽 PASS 확인,
      S002~004는 동적 태그라 SKIPPED, S005는 이전과 동일한 진짜 스키마 문제(DATA_GBN_CD 컬럼
      없음)로 ERROR, S006은 FROM 절에 테이블이 하나가 아니라고 정확히 판단하지 못해(서브쿼리를
      감지 못함) 대신 "MAD_CALENDAR 테이블이 이 스키마에 없음"으로 SKIPPED - 결과적으로 안전하게
      건너뛰긴 했지만 이유 문구가 정확하진 않았다(알려진 한계, 추후 서브쿼리 FROM 절 감지 보강
      필요). 두 테이블(PMI_PLN_REV, PMO_PROFBLT_IMPROV_PROD) 모두 테스트 후 더미 행 0건 남음을
      직접 쿼리로 재확인(cleanup 신뢰성 검증). **범위 한계**: 다중 테이블 JOIN, DATE 바인드 컬럼,
      BETWEEN/서브쿼리 조건은 자동 생성 미지원 - 추측으로 잘못된 더미 데이터를 넣지 않고 SKIPPED로
      정직하게 남긴다.

## Phase 2 — 공통 규약 + 결정론적 변환기 + 업로드→변환 챗팅 UI
화면 하나를 통째로 넣지 않는다 — `.BIZUNIT`/P/F/D/XSQL 5개 fragment로 나눠 처리하고, **콜그래프 역순(XSQL → Store → Service → Api)** 으로 하위부터 확정한다. 상위(Api) 시그니처를 먼저 잡고 하위를 끼워 맞추지 않는다.
- [ ] 공통 응답/예외 처리 규약 확정 (사람이 먼저 설계 — 화면마다 에이전트가 제각각 만들지 않도록) — **초안 작성함(2026-08-28), 아직 미확정.** `docs/09-common-response-convention.md`에 초안 + 열린 질문(HTTP status 정책 등) 정리. 코드는 `pilot/gscm/.../common/controller/CommonApiResponse.java`(createError 추가)/`common/exception/BizRuntimeException.java`(신규)/`common/exception/GlobalExceptionHandler.java`(신규) + `resources/message/errors*.properties`(E0052만, 원문 미확인이라 잠정 문구로 표시) + `resources/application.properties`(MessageSource 연결). 실제 `mvn compile`로 검증: 새 클래스들은 문제없이 컴파일되고, 기존에 알려진 `Pla047Service.java` 실패만 그대로 남음. **아직 skeleton_gen.py 생성 템플릿에는 반영 안 함** - 사람 확정 후 반영할 것.
- [ ] 메시지 코드 표준화: AS-IS 하드코딩 코드(`E0052`, `W0024`, `I0016` 등) → `errors.properties`/`errors_en.properties` 추출 규칙
- [x] **AI 추천 (2026-08-29, 멘토 논의 반영 — UI 명칭은 "AI 추천"으로 확정)** — **범위(사용자 확인)**: 실제
      React/TypeScript 코드나 xfdl 전환은 하지 않는다(1단계 범위 원칙 그대로 유지). 백엔드
      DTO의 "모양"(JSON 타입·페이지네이션 래핑)만 React가 쓰기 편하게 LLM이 대안 제안하는
      opt-in 비교 기능. `chatui/react_variant.py`(신규) `recommend_react_variant()` — 기존
      `extract_dto_fields()`가 뽑은 요청/응답 필드 목록을 LLM에 보내 JSON 스펙(필드별 타입/
      nullable, 리스트 래핑 여부, 추천 이유)을 받고, **원본 필드 목록과 대조해 LLM이 없는 필드를
      지어내면 BLOCKER 이슈로 자동 차단**(프롬프트 지시만 믿지 않음). `chatui/app.py`의
      "📄 변환 결과" 탭에 "🎨 AI 추천" expander 추가 - nctRid별로 버튼을
      눌러야 호출되고(자동 실행 아님), 기존 규칙 기반 Dto.java와 나란히 비교해서 보여준다.
      **자동 저장/자동 배선 안 됨** - 순수 검토용, 채택하려면 사람이 Service 어댑터 코드를 직접
      작성해야 한다는 안내 문구를 생성물에 포함. **실제 PLA047 3개 nctRid로 LLM Gateway 실호출
      검증**: RPLA04701(응답 2개 레코드셋)·04702·04703 전부 0건의 조작된 필드로 정상 생성 확인,
      평균 응답 시간 4.3초/건(1회 측정). **알려진 한계**: 응답 필드는 레코드셋 이름 수준까지만
      알고 있어(예: `MAIN_LIST`) 실제 컬럼 단위 스키마는 모른다 - 컬럼까지 알려면 Mapper.xml의
      SELECT 절을 추가로 파싱해야 하는데 이번엔 안 함, 그래서 리스트 응답의 `Item` 내부가 비어
      나오는 경우가 있음(정직한 한계, 추측으로 안 채움).
      **속도 검토**: 화면 1개 nctRid 1개당 LLM 호출 1회(~4초) - 메서드별로 부르는 F 포팅과 달리
      "화면당 1회"라 F 메서드 여러 개 있어도 배로 늘지 않는다. 지금도 여전히 버튼을 눌러야만
      호출되는 opt-in 기능이고, `_run_batch_generate`(전체 자동 진행 생성 단계)에는 자동으로
      끼워 넣지 않았다 - 화면 수만큼 순차 호출이 추가되면(50화면 기준 체감 +3~4분) 그때는
      `agents/workflow_graph.py`의 `Send()` 병렬 패턴처럼 병렬화가 필요하므로, 지금은 그 문제
      자체가 발생하지 않게 인터랙티브 opt-in 범위로 좁혀뒀다.
      **UI 반영 위치 정정(2026-08-29)**: 처음엔 단일 화면 흐름(`tab_result`)에만 넣었는데,
      사용자가 실제로 쓰는 화면은 "전체 자동 진행" 배치 결과의 화면별 상세보기
      (`_render_batch_screen_detail`)라 거기엔 없어서 "안 보인다"는 피드백을 받음 - 이 함수에
      네 번째 탭 "🎨 AI 추천"을 추가하고, `_run_batch_generate`가 이미 `entry["buckets"]`로
      들고 있던 원본 P/F/D 텍스트를 그대로 넘겨받아 단일 화면 흐름과 동일하게 동작하도록
      맞췄다. 두 진입점(단일 화면 탭 / 배치 상세보기 탭) 모두에서 확인 가능.
      **범위 확장(2026-08-29, 사용자 요청)**: DTO 하나만 추천하던 걸 **Api/Service/Store/
      Mapper/Dto 5개 파일 단위**로 확장, 설명 캡션은 삭제. LLM 호출은 여전히 화면당 nctRid
      1회뿐(필드 타입/래핑 스펙만 받음) - 나머지 4개 파일은 그 결과로부터 **결정론적으로 파생**
      시킨다(LLM을 5번 부르지 않음, 5개 파일이 서로 다른 얘기를 할 위험도 없앰). 두 화면
      (단일 화면 tab_result / 배치 상세보기)에 중복 구현돼있던 걸 `_render_ai_recommendation()`
      공유 함수로 합쳐서 한쪽만 고치고 잊어버리는 문제를 없앴다. **Api 추천 정확도 개선**: 실제
      위임 메서드 이름을 `_find_delegate_call()`로 기존 Api.java 텍스트에서 찾아 쓴다(추측
      플레이스홀더가 아니라 진짜 식별자) - PLA047 실 소스로 검증: `pPLA04701` -> 실제 위임
      메서드 `fPLA047QrySelectMainList`를 정확히 찾아 Api/Service 추천 양쪽에 일관되게 사용,
      0건의 조작된 필드로 5개 파일 전부 정상 생성 확인. Service 추천의 필드 변환 코드도 NEXCORE
      Dataset이 값을 전부 String으로 담는 관례를 반영해 `Double.valueOf(String.valueOf(...))`
      식으로 만든다(단순 캐스팅은 실제로 `ClassCastException`이 나서 고침). Store는 "변경 없음"을,
      Mapper.xml은 "구조 예시(미검증)"을 추천하도록 정직하게 범위를 좁혔다 - 컬럼 단위 SELECT
      스키마를 모르는 채로 추측하지 않는다.
- [x] iBatis → MyBatis 변환 모듈 v0 — `chatui/converters.py`. PLA047에서 검증한 4종 규칙(`isEqual`/`isNotEqual`/`isNotEmpty`+`iterate`/바인드 변수) + 멘토 코멘트의 `isNull`/`isNotNull`/`isGreaterThan` 등/`dynamic prepend`도 규칙만 준비. **실제로 검증된 건 PLA047뿐**이라 다른 화면 XSQL에 돌려서 결과를 반드시 확인할 것. 변환 후 XML well-formed 여부까지 자동 체크해서 경고로 보여줌(원본 태그 불일치를 여기서 잡아냄)
- [x] BizUnit 메서드 시그니처 → Controller(`{화면}Api`)/Service/Store 골격 생성기 v0 — `chatui/skeleton_gen.py`. PLA047 실 소스로 동작 검증: P 메서드가 실제로 호출하는 F 메서드를 본문에서 찾아 Api→Service 연결까지 정확히 맞춤(단순 이름 매칭이 아님). D 메서드는 `dbSelect("S00N", ...)` 호출에서 매퍼 statement id를 뽑아 Store가 참조하도록 생성. **골격만 규칙 기반, Service 메서드 본문은 항상 TODO 스텁 — LLM 포팅은 별도 단계**
- [x] `.BIZUNIT` 필드 → DTO 생성기 — `chatui/skeleton_gen.py`의 `extract_dto_fields`/`generate_dto` (규칙 기반, LLM 아님). `.BIZUNIT`의 `<fields/>`가 비어있을 때 nctRid(P 메서드)별로 요청 필드는 delegate F 메서드의 `getField` 호출, 응답 필드는 P 메서드의 `putRecordset` 호출에서 역추출. PLA047로 검증: RPLA04701은 15개 요청 필드 전부 채워짐, RPLA04702/03은 F가 `getFieldMap()`을 통째로 넘기는 구조라 개별 필드를 못 찾아 TODO+WARNING으로 표시(추측하지 않고 사람 확인 필요 처리). 필드 타입은 전부 String/`List<Map<>>`로 잠정 지정(원본에 실제 타입 미선언)
- [x] 화면별 변환 전에 `conversion-plan.json`(대상 fragment, 트랙(Refactor/Reimagine), 예상 산출 파일 목록)을 먼저 생성해 고정 — 계획 없이 바로 코드 생성하지 않는다. **`agents/conversion_plan.py`(2026-09-04)**. LLM 미사용(전부 정적 분석)이라 변환 결과에 의존하지 않고 변환 **전에** 돌 수 있다. 파이프라인에서는 `plan_all` 노드가 그래프 맨 앞(`START -> plan_all -> convert_all`)에서 돌면서 `tracking/conversion-plans/{화면}-conversion-plan.json`에 기록한다 — `pilot/`이 아니라 추적용 폴더에 쓰는 이유는 "승인 전까지 pilot/엔 아무 파일도 안 생긴다"는 보장을 깨지 않으면서 계획은 정의상 승인 *이전에* 있어야 하기 때문. 담는 내용: 5개 fragment 존재 여부·줄수·SHA-256, nctRid 목록, 예상 산출 파일과 TO-BE 경로·변환 방식, LLM 포팅 대상 메서드, 단순 위임(규칙 기반 생성) 메서드, 예상 LLM 호출 수, 트랙(항상 `UNDECIDED` — CLAUDE.md/Phase 3가 "사람이 결정"이라 자동 배정하지 않음)과 판단 근거 신호. **PLA047 실측**: LLM 포팅 대상 1건(`fPLA047QrySelectMainList`)·단순 위임 2건으로 정확히 갈렸고, `track_signals.as_is_unbalanced_braces`가 `F.java: 14`를 잡아내 "원본이 그대로는 컴파일 안 됨"(=CLAUDE.md가 든 Reimagine 후보 기준)을 자동으로 표시했다. 계획서가 드러낸 비효율은 곧바로 고쳤다(아래 항목 참고). UI는 화면별 상세보기에 "📋 변환 계획" 탭으로 노출(Streamlit `AppTest`로 렌더링 검증).
- [x] **업로드→변환 챗팅 UI v0** — `chatui/app.py` (Streamlit, 로컬 전용). 화면 1개 분량 P/F/D `.java`/`.bizunit`+XSQL을 업로드하면 위 결정론적 변환기를 돌려 결과를 화면에 보여주고, "저장" 버튼을 눌러야만 `pilot/{screen}/`에 파일이 생긴다(자동 커밋 없음). Service 로직 LLM 포팅은 별도 버튼으로 분리(실험적, 결과 검토 필수 문구 표시). 실행: `pip install -r requirements.txt` 후 `streamlit run chatui/app.py` → `http://localhost:8501`. 이 개발 환경엔 Streamlit이 없어 UI 자체는 실행 검증 못 함(내부 변환 로직만 PLA047 실 소스로 검증됨)
- [x] Validation(정적 검증, 1단계) — `chatui/validators.py` 신규 구현(변환기와 분리된 검증기, CLAUDE.md "Translator/Validator 분리" 원칙). Maven/Gradle 프로젝트(pom.xml, 의존성)가 아직 없어 진짜 컴파일은 못 하지만, 그 전 단계로 정적 검사를 한다: Java 파일 중괄호 균형(문자열/주석 인식), LLM 포팅 후 남은 PORT_START 스텁 탐지, 계층 간 실제 호출 대상 존재 확인(Api의 service.xxx() → Service 정의 여부, Service의 store.xxx() → Store 정의 여부, Store가 참조하는 매퍼 statement id → Mapper.xml 존재 여부), Mapper.xml well-formed 여부·statement id 중복·바인드 표현식 짝. 결과는 PASS/FAIL로 `CONV_FILE.BUILD_CHECK`에 저장되고 실패 이슈는 `CONV_ISSUE`에 `detected_by='chatui/validators.py'`로 쌓인다. PLA047로 실 DB 검증: Api/Store/Dto/계층간참조 PASS, Service는 원본 버그(중괄호 누락) 보존 때문에 의도대로 FAIL, XSQL은 알려진 태그 불일치로 의도대로 FAIL — 전부 실제로 CONV_FILE/CONV_ISSUE에 기록됨 확인.
- [x] Maven 빌드 검증(실제 `mvn compile`) — `pilot/gscm/pom.xml`(최소 스캐폴드, 사내 표준 parent POM/내부 리포지토리 좌표는 미확인이라 공개 Maven Central 좌표로만 채움 — TODO로 표시) + `chatui/validators.py`의 `check_maven_build()`. app.py 사이드바 "🔨 Maven 빌드 검증" 버튼에서 실행. `com.skhynix.gscm.common.controller.CommonApiResponse`(Pla047Api.java가 참조하지만 어디에도 정의돼 있지 않던 클래스)도 실사용 시그니처(`createSuccess(T)`)만 채워 최소 구현으로 추가함 - 나머지(에러 팩토리 등)는 플랫폼팀 확정 필요.
  - **2026-08-28 갱신 - 실제 `mvn compile` 통과/실패 확인 완료.** 이 PC엔 mvn이 PATH에 없었지만 `C:\sqldeveloper\jdk\jre`에 SQL Developer가 번들한 JDK 17(java/javac 둘 다 동작)이 이미 있었다 - Maven 공식 배포본(`apache-maven-3.9.9`)만 `~/dev-tools/`에 압축 해제로 추가(관리자 권한/설치 프로그램/전역 PATH 변경 없음). `chatui/validators.py`에 `_find_local_mvn_and_java_home()`을 추가해 PATH에 없으면 이 두 위치를 자동으로 찾아 `JAVA_HOME`/`PATH`를 이 프로세스 안에서만 세팅하고 `mvn -q compile`을 실행하도록 바꿨다(전역 환경변수는 안 건드림). **실제 실행 결과**: `pilot/gscm` 전체(Pla001~050 Api/Service/Store/Dto/Mapper + CommonApiResponse) 중 **`Pla047Service.java` 딱 하나만 실패**(`'else' without 'if'`, `'catch' without 'try'` 등) - 이건 원본 FPLA047 BizUnit 자체의 중괄호 누락 버그를 "고치지 않고 그대로 보존"하기로 한 의도된 결과와 정확히 일치한다(CLAUDE.md "원본이 깨져 있어도 정정 후 포팅" 원칙 - Service 로직 포팅은 별도 LLM 단계 몫). 나머지 파일은 전부 컴파일 통과 - 결정론적 골격 생성기(`skeleton_gen.py`)가 만든 코드가 문법적으로 실제로 유효하다는 첫 실증.
- [x] 추적 DB를 파일 단위(CONV_FILE)에서 함수 단위까지 세분화 — `agents/db_schema.sql`에 `CONV_METHOD`(파일 하나 안의 메서드별 행 - AS-IS/TO-BE 이름, 본문 해시, 매퍼 statement id, 변환 방식)와 `CONV_METHOD_CALL`(P→F, F→D 위임 콜그래프 엣지) 추가, `CONV_ISSUE`에 `METHOD_ID`(nullable FK) 추가해 이슈를 파일 전체가 아니라 정확히 어느 메서드에서 났는지까지 연결. `chatui/skeleton_gen.py`의 `generate_skeletons()`가 골격 생성과 동시에 이 레지스트리(`SkeletonResult.methods`/`method_calls`)를 뽑고, `agents/db.py`의 `upsert_conv_method`/`link_method_call`로 적재하며, `find_duplicate_methods()`로 BODY_HASH가 같은 메서드를 화면 경계 넘어 찾아 "화면 간 복붙된 동일 로직" 후보를 뽑을 수 있게 했다(멘토 코멘트의 "NEXCORE 관용구 KB" 자산화와 연결). `chatui/app.py`의 두 DB 저장 경로(배치 파이프라인, 단일 화면 저장) 모두 파일 upsert → 메서드/콜그래프 적재 → 메서드-연결 이슈 기록 순으로 재구성. 합성 P/F/D 예제로 콜그래프·해시·issue.method_name 연결까지 검증 완료, 실제 Oracle DB(CONV_METHOD 실제 INSERT/조회)는 이 환경에 python-oracledb 접속 자체를 못 해봐서 미검증 - 다음에 DB 붙는 환경에서 `db.ensure_schema()`가 기존 CONV_ISSUE 테이블에 METHOD_ID를 무사히 ALTER하는지부터 확인할 것. ~~LangGraph 경로(`agents/workflow_graph.py`)는 아직 메서드 레지스트리를 안 돌려줘서 이 경로로 저장하면 CONV_METHOD/CONV_METHOD_CALL은 비어있다~~ → **2026-09-02에 해소됨**, 아래 항목 참고.

## Phase 2.5 — 7단계 LangGraph 파이프라인 통합 + 영향도 분석 (2026-09-02)

**배경**: 그동안 `chatui/app.py`가 1단계(규칙기반) → 2단계(LLM 포팅) → 검증 → 스캔 → (opt-in)AI 추천
→ (opt-in)차등 테스트 → 저장을 사람이 버튼을 하나씩 눌러 진행시켰다. `agents/workflow_graph.py`에
LangGraph StateGraph가 있었지만 `run_screen_conversion()`이 `.invoke()`(단발 블로킹 호출)만 써서
화면에는 "버튼 누르면 스피너 돌다 결과가 한꺼번에 뜨는" 것으로만 보였다 - 실제 LangGraph가 단계별로
진행 중이라는 게 안 보인다는 사용자 피드백("AI 에이전트가 순차적으로 판단하며 진행하는 느낌이 없다").
요청: 폴더 업로드 → 아래 7단계가 LangGraph 기반으로 순서대로 진행되는 걸 화면에서 실시간으로 보여주고,
화면별 미사용/중복 함수를 잡는 영향도 분석도 추가.

```
1. 1단계 규칙기반 변환 (LLM 미사용)   2. 2단계 LLM 포팅   3. 정적 검증   4. 품질·취약점 스캔
5. AI 추천 변환 소스   [사람 승인 후 저장]   6. 전체 화면 교차 분석   7. Maven 빌드 검증
```

**핵심 설계 결정**: 6·7단계는 `chatui/cross_analysis.py`/`chatui/validators.py`가 **디스크에
저장된 `pilot/` 트리를 직접 읽는 함수**라(메모리 상 결과가 아니라) 저장이 선행돼야 물리적으로
실행 가능하다. 그런데 CLAUDE.md "사람 리뷰 없는 자동 저장/배포 금지" 원칙상 1~5단계 결과를 승인
없이 자동으로 `pilot/`에 쓸 수 없다. 그래서 파이프라인은 **1~5단계(LangGraph로 자동 진행) → 사람이
"승인하고 저장" 버튼 클릭 → 저장 → 6~7단계(저장 직후 자동 진행)** 구조로 만들었다 - "7단계 전부
무인 자동"은 이 프로젝트 안전 원칙과 상충해서 그대로는 못 하고, 승인 지점 하나만 남겼다. 화면 여러
개는 **단계 단위로 다 같이** 진행한다(화면 A를 끝까지 다 하고 화면 B로 안 넘어감) - "1단계: 전체
화면 규칙기반 변환" 다음에 "2단계: 전체 화면 중 포팅 필요한 메서드 LLM 포팅"으로 넘어가는 식.

**구현**:
- `agents/workflow_graph.py` — 화면 1개용 `ScreenState`/`build_graph()`/`run_screen_conversion()`은
  그대로 두고(파일 업로드 모드가 여전히 이 경로를 씀), 폴더 전체용 `PipelineState`/
  `build_pipeline_graph()`/`run_pipeline_part_a()`를 추가했다. 새 노드(`convert_all`/
  `port_one_screen_method`/`splice_all`/`validate_all`/`scan_all`/`ai_recommend_one`)는 전부
  화면 1개용 로직(`_convert_screen`로 추출, `splice_ported_method`, `validate_screen`,
  `run_review`, `react_variant.recommend_react_variant`)을 화면마다 또는 (화면,메서드)/
  (화면,nctRid) 단위로 `Send` 병렬 디스패치해서 부르는 얇은 래퍼일 뿐이다 - 변환/검증/스캔/AI추천
  로직은 한 줄도 다시 안 짰다. 진행 상태는 `graph.stream(state, stream_mode=["updates","values"])`로
  뽑는다 - "updates"로 방금 끝난 노드 이름을 받아 UI를 갱신하고, "values"의 마지막 항목을 LangGraph가
  리듀서로 정확히 합친 최종 상태로 그대로 쓴다(수동으로 다시 합치면 실수하기 쉬워서 안 함).
  **부수 발견/수정**: `_convert_screen`이 기존엔 `finalize_mapper_document()`(DOCTYPE/namespace/
  select id 정리)를 안 불러서 이 그래프 경로의 Mapper.xml만 다른 경로(수동 배치)보다 덜 정리된
  상태로 나오는 차이가 있었다 - 이번에 맞춰서 고쳤다(실제 PLA047로 재검증: DOCTYPE 정상, `<sqlMap>`
  잔재 없음 확인).
- `agents/impact_analysis.py`(신규) — `find_unused_methods()`: 새 정적분석기가 아니라 이미 있는
  `CONV_METHOD_CALL`(P→F, F→D 콜그래프)의 역방향 조회다. P 계층(nctRid 진입점)에서 시작해 콜그래프를
  타고 내려가도 **한 번도 CALLEE로 안 나오는 F/D 메서드**를 찾는다. **알려진 한계**: 콜그래프가 P→F,
  F→D만 잡아서(F가 다른 F를, D가 다른 D를 내부 호출하는 경우는 없음) 오탐 가능 - 확정 판정이 아니라
  "검토 후보" 목록으로만 취급. 삭제는 하지 않는다(조회 전용). 실제 DB(50화면치 CONV_METHOD_CALL)로
  검증: 49건 후보 확인(예: 여러 화면에서 반복되는 `fCommonCodeQry`가 P→F 콜그래프에 안 잡힘 - 실제
  검토가 필요한 신호). 중복 함수는 이미 있던 `agents/db.py`의 `find_duplicate_methods()`를 그대로
  재사용(새로 안 만듦).
- `chatui/app.py` — 폴더 모드의 "화면 1개 선택→탭" 흐름과 "전체 자동 진행(구 `_run_batch_generate`)"
  두 갈래를 **위 파이프라인 하나로 통합**했다(대상 화면 멀티셀렉트 → 1~5단계 진행 상태 표시 → 화면별
  결과 확인(`_render_batch_screen_detail` 그대로 재사용) → 승인·저장(`_run_batch_save` 그대로
  재사용, `_pipeline_state_to_batch_results()`로 입력 모양만 새로 어댑팅) → 6~7단계 자동 진행 →
  중복/미사용 함수·Maven 결과 표시). **`_run_batch_generate`는 완전히 대체돼서 삭제했다**(죽은 코드로
  안 남김). 파일 업로드 모드(화면 1개)는 이 개편 범위 밖 - 기존 단일 화면 탭 흐름 그대로 유지.
- **검증**: `sample_data/legacy-u-pla001-050/`의 실제 화면(PLA047+PLA001/PLA002)으로
  `run_pipeline_part_a()`를 CLI에서 직접 호출해 1~5단계 전부 실행 확인(진행 콜백이 정확한 순서로
  호출됨, 화면 2개의 포팅 대상 메서드가 함께 병렬 디스패치됨, AI 추천 6건 전부 정상 생성, LLM 호출
  에러 0건). `_pipeline_state_to_batch_results()` 출력이 `_run_batch_save()`가 기대하는 키를
  전부 갖추는지 별도로 확인(실제 pilot/ 파일을 건드리지 않는 격리된 방식으로). `find_unused_methods()`
  실 DB 검증 완료(위 참고). `streamlit run` 헤드리스 부팅 스모크 테스트 통과. **못 한 것**: 브라우저가
  없어 실제 클릭 흐름(버튼 활성화, `st.empty()` 갱신 타이밍 등)은 시각적으로 확인 못 했다 - 로직/
  데이터 흐름은 전부 실제 함수 호출로 검증했지만, 화면에 예쁘게 그려지는지는 사용자 확인 필요.

**후속 개선(2026-09-02, 사용자 요청)**:
- **단계별 진행률에 총량/잔여 표시** — 기존엔 "N건 처리됨"처럼 분모 없이 카운트만 늘어나서
  "총 몇 건 중 몇 건 남았는지" 알 수 없었다. 2단계(LLM 포팅) 총량은 1단계(`convert_all`)가 끝나야
  알 수 있어(화면마다 Service.java 존재+F 메서드 유무에 달림) `convert_all`의 진행 콜백 partial에서
  `pending_methods`를 바로 합산해 분모로 쓴다. 5단계(AI 추천) 총량은 원본 P/F/.bizunit 텍스트만
  있으면 `extract_dto_fields()`로 파이프라인 시작 전에 미리 계산 가능해서(포팅 결과와 무관, 결정론적
  함수) 버튼 클릭 시점에 바로 뽑아둔다. 1·3·4단계(convert_all/validate_all/scan_all)는 원래 화면
  전체를 한 번에 처리하는 단일 노드라 "N/M 진행 중"처럼 중간값을 보여줄 수 없고(과장이라 안 함),
  대신 완료 시 "전체 M개 화면"으로 분모를 보여준다. **알려진 한계**: 2단계는 LLM 호출 실패 시
  재시도가 있어(`max_retries`, 호출 실패 한정) 재시도 라운드 중엔 진행 카운트가 일시적으로 분모를
  넘어설 수 있다 - 드문 경우라 별도 보정 로직은 안 넣었다(정직하게 남은 한계로 문서화).
- **사이드바 교차분석/Maven 버튼 제거, 메인 파이프라인으로 통합** — `chatui/app.py` 사이드바에
  "교차 분석 실행"/"mvn compile 실행" 버튼이 메인 파이프라인의 6~7단계(승인·저장 직후 자동 실행)와
  별개로 남아있어서, 똑같은 함수(`analyze_pilot_folder`/`check_maven_build`)를 두 곳에서 따로
  호출해야 하는 "두 개의 병렬 구현, 하나는 잊혀짐" 패턴이 반복될 위험이 있었다(이 프로젝트에서 이미
  여러 번 실제로 겪은 문제 - AI 추천, Maven 에러 메시지 등). 처음엔 사이드바의 독립 버튼 두 개만
  지우고 "지금은 메인 파이프라인에서 자동 실행된다"는 안내 문구를 남겼는데, 사용자가 그 안내 문구와
  사이드바 자체를 완전히 없애 달라고 요청해(2026-09-02) `with st.sidebar:` 블록 전체(LLM Gateway
  상태 표시 포함)를 삭제했다 - 로직은 Part A/B(메인 파이프라인)에만 남고, 사이드바라는 진입점
  자체가 사라졌다.
- **6~7단계를 저장 이전(승인 게이트 이전)으로 이동 - 임시 사본 미리보기(2026-09-02)** — 사용자
  요청: "파이프라인에 6단계(교차분석)·7단계(Maven 빌드)까지 포함되어야 하고, 그 다음에 사람이
  승인·저장하는 구조여야 한다." 원래 설계(Phase 2.5 최초 버전)는 6~7단계가 **디스크에 저장된
  `pilot/` 트리를 직접 읽는** `cross_analysis.analyze_pilot_folder()`/`validators.check_maven_build()`
  라서 저장 이후에만 돌릴 수 있다고 보고 저장 뒤(Part B)로 미뤄뒀었는데, 이걸 저장 **전**으로
  당기려면 아직 승인 안 된 배치를 어딘가에 반영해야 검증이 된다. `pilot/`에 직접 쓰면(나중에
  지운다 해도) "저장 전까지 pilot/에 아무 파일도 안 생긴다"는 기존 보장이 깨지므로, 대신
  `chatui/app.py`에 `_write_batch_files_to_dir()`(배치 파일을 임의 폴더에 `tobe_relpath()` 규칙
  그대로 쓰는 헬퍼)와 `_run_stage_6_7_preview()`(임시 디렉터리에 실제 `pilot/` 전체를
  `shutil.copytree`로 복사 + 이번 배치 파일을 그 위에 겹쳐쓴 뒤, 그 **임시 사본**을 대상으로
  `analyze_pilot_folder`/`check_maven_build`를 그대로 돌리고, 끝나면 `finally`에서 임시 폴더를
  항상 삭제)를 추가했다 - `agents/dummy_data.py`의 "만들고 확인하고 항상 지운다" 패턴과 동일한
  격리 방식이다. 파이프라인 버튼 하나로 1~7단계가 전부 진행되고, 그 결과를 다 보여준 뒤에야
  "승인하고 저장" 버튼이 실제 `pilot/`과 DB에 반영한다(저장 후 6~7단계를 다시 돌리지 않음 -
  미리보기와 동일한 내용이라 중복 실행 불필요). **알려진 한계**: `db.find_duplicate_methods()`/
  `agents.impact_analysis.find_unused_methods()`는 CONV_METHOD/CONV_METHOD_CALL(DB) 기준이고
  이번 배치는 저장 전이라 DB에 없어서, 이 두 조회는 **이미 저장된 과거 화면 기준으로만** 정확하다
  (이번 배치 자신의 메서드는 안 잡힘) - UI에 이 한계를 명시했다. 디스크 기반 `analyze_pilot_folder`
  노트와 Maven 빌드는 이번 배치를 포함해서 정확하다. **검증**: 가짜 화면 1개(`ZZTEST999`)를 배치에
  섞어 `_run_stage_6_7_preview()`를 실제로 호출 - 실행 전후로 진짜 `pilot/` 디렉터리 스냅샷이
  완전히 동일함을 확인(격리 확인), 교차분석 노트가 기존 50화면 + 새 화면 합쳐 51개로 정확히
  나왔음을 확인(병합 확인), DB 기준 중복 6건/미사용 후보 49건(기존 세션에서 확인한 수치와 일치),
  Maven 빌드는 기존에 알려진 `Pla047Service.java`의 원본 버그 하나만 실패로 잡고 새로 넣은
  `Zzt999Service.java`는 정상 컴파일됨을 확인 - 임시 사본이 실제 트리 상태를 정확히 재현한다는
  뜻이다.
- **콜그래프 정확도 개선 + 오류 함수 탐지 + 통합 대시보드(2026-09-03, 사용자 요청 - "의미없는
  탐지보다는 실제로 미사용함수 및 오류 함수 등 대시보드 형태로")** — 소스를 직접 재검토해서 두
  가지 근본 원인을 찾아 고쳤다:
  1. **파이프라인 저장 경로의 콜그래프가 "단순 위임 1건"만 기록했다.** `chatui/skeleton_gen.py`의
     `generate_skeletons()`가 `method_calls`에 넣는 엣지는 코드 생성에 실제로 쓴 위임 1건뿐이라,
     계산/분기가 있어 LLM 포팅이 필요한 메서드(F 메서드가 D를 여러 개 부르는 실제로 흔한 경우 -
     예: `fPLA047QrySelectMainList`가 D 4개를 호출)는 호출이 전부 콜그래프에서 빠져 있었다.
     `agents/nctrid_graph.py`(CLI 경로)는 애초에 `find_all_calls()`로 전체를 잡아서 문제없었지만,
     실제 화면에서 쓰는 파이프라인 저장 경로는 그렇지 않았다 - "두 경로, 하나는 불완전"이었던
     것. `generate_skeletons()` 끝에 `find_all_calls()` 기반 완전 탐색을 추가해 해소했다(실
     PLA047로 검증: 엣지 5개 -> 9개, 빠졌던 D 메서드 4개가 전부 채워짐).
  2. **F->F/D->D 내부 호출이 콜그래프 어디에도 없었다**(기존에 문서화된 한계) - 한정자 없는
     호출(`method(...)`, `du.method(...)`처럼 `.`이 안 붙는 형태)을 잡는 `find_bare_calls()`를
     신설해 `generate_skeletons()`와 `agents/nctrid_graph.py` 양쪽에 추가했다.
  3. **"오류 함수" 탐지가 데이터 자체가 없어서 비어있었다.** `agents/impact_analysis.py`에
     `find_error_methods()`(메서드에 귀속된 BLOCKER 이슈·ORIGINAL_BUG을 집계)를 새로 만들었는데,
     실제로 돌려보니 0건이 나왔다 - 원인을 추적해보니 `chatui/validators.py`의 `ValidationIssue`와
     `chatui/quality_scanner.py`가 만드는 이슈 대부분이 애초에 `method_name`을 채우지 않아서
     `agents/db.py`의 `record_issues()`가 CONV_ISSUE.METHOD_ID를 연결할 방법이 없었다(둘 다
     line_no는 있었다). `ValidationIssue`에 `method_name` 필드를 추가하고, 두 모듈에 각자
     독립적인(변환기/검증기/스캐너 분리 원칙 유지) `_method_line_ranges()`/`_attribute_methods()`
     헬퍼를 넣어 line_no로 소속 메서드를 역추정해 채우게 했다. `chatui/app.py`의 저장 경로(배치/
     단일 화면 둘 다) 중 계층 간 참조(CROSS_LAYER_REF) 이슈를 기록하는 지점이 `method_id_by_name`을
     아예 안 넘기고 있던 것도 같이 고쳤다(P/F/D method_ids를 합쳐서 넘기도록).
  4. **부수 발견 - 진짜 오탐 버그**: `scan_deprecated_nexcore_calls()`가 코드가 아니라
     `skeleton_gen.py`가 남긴 TODO 주석 자체("NEXCORE 의존(IDataSet/IOnlineContext/
     lookupDataUnit)만 제거하고...")의 API 이름 언급을 코드로 오인해서, 아직 LLM 포팅 안 된
     스텁 메서드마다 전부 가짜 WARNING을 냈다(실 PLA047로 재현 확인). 주석 라인(`//`로 시작)은
     건너뛰도록 고쳤다 - 정확히 "의미없는 탐지"의 실제 사례였다.

  새로 만든 것: `agents/impact_analysis.py`의 `find_error_methods()`/`build_impact_dashboard()`
  (미사용+오류를 위험도 점수로 합쳐 정렬 - `risk_score = BLOCKER*3 + WARNING*1 + 미사용*2 +
  원본버그*1`). `chatui/app.py`의 6~7단계 미리보기 결과에 있던 "미사용 함수 후보" 불릿 목록을
  이 통합 대시보드(`st.dataframe` 표 - 화면/계층/메서드/케이스/위험도)로 교체했다.

  **검증**: 실 PLA047 소스로 콜그래프 개선 확인(위 1번), 실 DB 라운드트립 테스트로
  `find_error_methods()`/`build_impact_dashboard()`가 BLOCKER 이슈를 실제로 메서드에 연결해서
  집계함을 확인(합성 화면 `ZZTEST996`/`ZZTEST997`/`ZZTEST998`으로 테스트 후 CONV_ISSUE/
  CONV_METHOD/CONV_FILE 정리해서 DB에 흔적 안 남김), `st.dataframe` 렌더링을 Streamlit
  `AppTest`로 예외 없이 확인. ~~**알려진 한계**: 브레이스 불일치처럼 스택이 한번 어긋나면 보고
  줄 번호가 실제 문제 지점이 아니라 그 뒤 아무 메서드로 쏠릴 수 있다~~ → **2026-09-04에 해소됨**
  (아래 "의존성 주입 + 수리 루프" 3번 참고 - 메서드 단위 균형 검사로 바꿔서 정확히 귀속된다).

- **의존성 계약 주입 + 검증-수리 루프 + 변경 사유(2026-09-04, 사용자 요청 - AlphaTrans/
  ReCodeAgent/AWS Transform 검토 반영)** — 사용자가 "함수 간 의존성(map/list 형변환 포함)을
  분석해 Planner를 LLM과 일관되게 적용하고, 오류가 있으면 다시 고쳐 재수행하며, 변경 가이드를
  제공하라"고 요청. 먼저 실제 논문을 확인해서 근거를 맞췄다([AlphaTrans, FSE 2025](https://arxiv.org/html/2410.24117v4),
  [ReCodeAgent](https://arxiv.org/html/2604.07341v1)):
  - AlphaTrans는 프래그먼트마다 **콜러/콜리, 입출력 타입, 임포트, 상속 관계**를 메타데이터로
    뽑아 콜그래프 역순으로 번역한다 - 이 프로젝트가 이미 하고 있는 것(5-fragment 분해, 역순
    변환, `CONV_METHOD_CALL`)과 거의 같고, **빠져 있던 건 "그 메타데이터를 LLM 프롬프트에 실제로
    넣는 것"** 하나였다. 실측 수치도 확인: 문법 정확도 96.40% vs 기능 동등성 25.14% - 의존성
    인식 번역만으로는 정확도가 안 따라온다는 뜻이라, 검증 기반 수리 루프가 정당화된다.
  - ReCodeAgent의 Analyzer는 **타 언어의 관용적 라이브러리 대체**를 찾는 게 핵심인데, 이 프로젝트는
    닫힌 집합(NEXCORE API)을 결정론적 템플릿으로 치환하는 문제라 그 부분은 해당 없음 - 도입하지
    않았다(범용성 명목으로 안 쓰는 기능을 만들지 않는다).

  **반영한 것 3가지**:
  1. **의존성 계약 주입** - `_dispatch_ports_all()`이 콜그래프(`skel_method_calls`)에서 그 F
     메서드가 실제 호출하는 D 메서드 목록을 뽑아 프롬프트에 명시(`_callee_note`). LLM이 Store
     메서드 이름을 추측하지 않고 이미 생성된 이름을 그대로 쓰게 해서 `UNRESOLVED_STORE_CALL`을
     사전 차단한다. 여기에 NEXCORE Dataset 관례(모든 값이 String이라 직접 캐스팅하면
     ClassCastException - 실제로 겪은 사례)도 고정 지침으로 넣었다.
  2. **검증-수리 루프** - `validate_all -> repair_gate -> port_one_screen_method(수리 프롬프트)
     -> splice_all -> validate_all` 순환을 추가(MatchFixAgent/ACToR 패턴, §D). **LLM이 포팅한
     메서드에 귀속된 BLOCKER만** 대상이고(규칙 기반 생성물은 제외 - LLM이 고칠 문제가 아님),
     라운드 상한(`max_repair_retries`, 기본 2, UI에서 조절)이 있는 고정 파이프라인이다 - CLAUDE.md
     "완전 자율 탐색형 에이전트를 만들지 않는다"에 맞춰 무한 재분석 루프는 의도적으로 안 만들었다.
  3. **변경 사유(변경 가이드)** - 포팅/수리 결과 첫 줄에 `// AI 변경 요약:` / `// AI 수정:`
     주석을 남기게 했다(react_variant.py의 `rationale`과 같은 패턴).

  **이 과정에서 발견해 고친 실제 결함 2건**:
  - `splice_ported_method()`가 PORT 마커를 지워버려서 **수리 결과가 조용히 버려졌다** - 마커를
    유지하도록 바꿔 재스플라이스가 가능하게 했다. "아직 포팅 안 됨" 판정은 마커가 아니라 스텁
    본문(`UnsupportedOperationException`)으로 하도록 `_check_unspliced_markers()`도 같이 바꿈.
  - `_check_brace_balance()`가 파일 전체 스택 방식이라 **어느 메서드가 깨졌는지 구조적으로 알 수
    없었다**(중괄호 하나가 빠지면 뒤 '}'들이 역할을 당겨써서 결국 클래스 '{'가 미닫힘으로 남음).
    메서드 조각별로 균형을 따로 보는 `_check_method_brace_balance()`를 추가해 정확히 귀속시킨다 -
    이게 없으면 가장 흔한 BLOCKER인 중괄호 오류가 수리 루프에 아예 안 잡혔다(실측 확인).

  **검증**: LLM을 목(mock)으로 바꿔 "1차 포팅은 깨진 코드 → 수리 요청엔 고친 코드"를 결정론적으로
  재현 - 노드 순서가 `...validate_all → repair_gate → port_one_screen_method → splice_all →
  validate_all → repair_gate → scan_all`로 정확히 돌고, 1라운드 만에 정적 검증 통과(`issues: []`),
  수리 주석 반영 확인. 예산 소진 케이스(2라운드 후 포기 → scan_all)도 별도 확인. 실 LLM 1화면
  (PLA047) 실행에서는 LLM이 주입된 콜리 이름을 그대로 사용(`store.dPLA04702/03/04/05`)하고 변경
  요약 주석을 생성, 전 파일 정적 검증 통과. 포팅 실패(스텁 잔존) 케이스에서 PORTING_INCOMPLETE
  귀속도 정상. pytest·헤드리스 부팅 통과. **못 한 것**: 브라우저가 없어 UI 클릭 흐름은 여전히
  미검증이고, 지금 fixture가 PLA047 복제 50벌이라 **유형 다양성이 없어** 수리 루프의 라운드 수·
  프롬프트 문구가 다른 유형 화면에도 맞는지는 Phase 3 이후에 재확인해야 한다.

- **위 작업에 대한 자기 비판과 후속 정정(2026-09-04)** — 사용자가 "적용한 게 잘 한 것인지
  비판적으로 다시 검토하라"고 해서 되짚은 결과 두 가지를 인정하고 고쳤다:
  1. **틀린 지침을 프롬프트에 넣었었다(수정 완료)**. 처음엔 "Map<String,Object> 값은 전부
     String으로 담긴다"고 단정해서 넣었는데, 그건 **AS-IS(NEXCORE Dataset)의 관례지 TO-BE의
     사실이 아니다** - TO-BE에서 이 Map은 출처마다 타입이 다르다(요청은 Jackson JSON 역직렬화라
     숫자가 Integer/Double, store 반환값은 MyBatis/Oracle 매핑이라 BigDecimal/Timestamp, AS-IS에서
     그대로 온 값만 String). 방어적 변환을 시키는 의도는 맞았지만 LLM에게 틀린 데이터 모델을
     가르치고 있었다. `_VALUE_TYPE_NOTE`로 이름과 문구를 바꿔 "타입이 고정돼 있지 않다"는 사실만
     남기고 방어적 변환 + null 처리를 요구하도록 정정했다.
  2. **수리 루프의 효용을 과대평가했었다(설계는 유지, 기대치만 정정)**. ① 요즘 LLM은 중괄호를
     거의 안 틀려서 실제로는 잘 안 걸린다(실 LLM 실행에선 첫 시도에 전부 통과했고, 테스트는 깨진
     코드를 일부러 주입해야 했다). ② 가장 현실적인 트리거였을 `UNRESOLVED_STORE_CALL`은 같이 넣은
     콜리 이름 주입이 예방해버려서 **두 변경이 서로를 잡아먹는다**. ③ 무엇보다 정적 검증만
     피드백으로 쓰므로 AlphaTrans 기준 이미 96.4%였던 *문법* 쪽만 개선하고, 정작 문제인 *기능
     동등성 25.1%* 쪽은 못 건드린다. 그래도 만드는 과정에서 기존 코드의 실제 결함 2건(splice가
     수리 결과를 버리던 문제, 중괄호 오류가 메서드에 귀속 안 되던 문제)을 찾아 고쳤으므로 순효과는
     남았다. **기능 동등성을 건드리려면 포팅된 Service를 실제로 실행할 수단(테스트 동반 생성 또는
     Spring Boot 기동)이 필요하다 - 그게 없다는 게 이 프로젝트의 진짜 병목**이고, AlphaTrans/
     ReCodeAgent가 레포의 기존 테스트로 검증하는 것과 갈리는 지점이다(Phase 4~5 과제로 남김).

- **2단계 LLM 호출 낭비 제거(2026-09-04)** — 위 계획서(`conversion_plan.py`)가 "포팅 호출 3건 중
  1건만 반영됨"을 드러내서 원인을 파봤더니, 추정보다 더 나빴다. `_convert_screen()`이
  `pending_methods`에 **F 메서드를 전부** 담고 있었는데, 그중 단순 위임 메서드는 이미 규칙 기반
  코드(`return store.dXXX(dto);`)로 생성돼 PORT_START/PORT_END 스텁이 없다 → LLM 결과가
  `splice_ported_method`에서 버려진다 → 버려지니 `ported_methods`에 영영 안 들어간다 →
  `route_after_splice_all`이 "아직 안 된 메서드"로 보고 **재시도 라운드마다 또 호출**한다.
  **PLA047 실측: 유효 1건에 LLM 호출 5건(80% 낭비), 단순 위임 2건은 각각 2회씩 호출됨.** 단순
  비효율이 아니라 재시도 루프가 성공할 수 없는 대상을 계속 재시도하던 버그다.
  `_convert_screen()`이 `skel.methods` 중 `conversion_method == "LLM_PENDING"`인 것만 pending에
  담도록 고쳤다 - 생성기가 스스로 남긴 기록을 신뢰하는 방식이라 `detect_simple_delegation`을
  다시 부르는 것보다 두 판정이 어긋날 위험이 없다. **결과: 호출 5건 → 1건.** 단일 화면
  ScreenState 그래프도 같은 `_convert_screen()`을 쓰므로 함께 고쳐졌다. 부수 효과로
  `route_after_splice_all`의 재시도 판정과 `repair_gate`의 수리 대상 필터도 정확해졌다(규칙 기반
  생성물이 더 이상 후보로 안 잡힘). **검증**: 목 LLM로 호출 1건·단순 위임 규칙 코드 보존·전
  항목 검증 통과 확인, 실 LLM 1화면 실행에서도 노드 순서가
  `plan_all → convert_all → port(1회) → splice_all → validate_all → repair_gate → scan_all`로
  깔끔하게 정리되고 전 파일 검증 통과. 계획서의 `estimated_llm_calls`도 더 이상 존재하지 않는
  낭비를 보고하지 않도록 `porting`/`porting_skipped_rule_based`로 정정했다.

- **멘토 코멘트 미반영 항목 재점검 + 조회 전용 가정 노출(2026-09-04)** — 사용자가 "멘토 의견 중
  반영 안 된 부분을 비판적으로 다시 검토하라"고 해서 §1~§J를 코드로 대조했다. 확인된 것만 적는다.

  **실제로 고친 것 — D 계층 조회(SELECT) 전용 가정(멘토 §6의 insert/update/delete 리스크)**:
  변환 체인 전체가 SELECT만 가정하고 있었다 - `extract_d_stmt_ids`는 `dbSelect`만 인식,
  Store 생성은 무조건 `sqlSession.selectOne(...)`, `finalize_mapper_document`는 `<select>`만
  정규화. 확보한 원본(PLA047)이 `dbSelect` 6개·`<select>` 6개로 **조회 전용**이라 이 경로는 한 번도
  검증된 적이 없다. **그런데 지원을 지금 만들지는 않았다** - insert/update 샘플이 하나도 없어서
  본 적 없는 패턴에 규칙을 짜는 건 CLAUDE.md "확인되지 않은 규칙 추측 금지" 위반이기 때문이다.
  대신 **미지원을 조기에, 이름 붙여 드러내도록** 했다: `skeleton_gen.extract_d_db_calls()`/
  `unsupported_db_verbs()`(verb 화이트리스트를 두지 않고 `db<Verb>("id")` 호출을 있는 그대로 잡아
  dbSelect가 아닌 것만 보고), Store 생성 시 해당 메서드 위에 `// TODO(미지원 verb: dbInsert)`
  주석 + `UNSUPPORTED_DB_VERB` BLOCKER 이슈(메서드 귀속), 그리고 변환 **전에** 계획서
  (`conversion-plan.json`)의 `unsupported_db_verbs`/`track_signals.has_unsupported_db_verbs`와
  UI 계획 탭 경고로 노출. 예전에는 이런 화면이 `TODO_확인필요_xxx` → `MISSING_STATEMENT`로 늦고
  엉뚱한 메시지로만 걸렸다. **검증**: 합성 D 파일(dbSelect/dbInsert/dbUpdate+dbDelete 혼합)로
  메서드별 verb 정확 탐지(다중 verb 포함)·BLOCKER 이슈·주석 생성 확인, 실제 PLA047에서는 오탐 0건
  (미지원 verb 없음, 전 항목 검증 통과) 확인.

  **검토했지만 "지금 하면 안 된다"고 판단한 것(이유 포함)**:
  - **공통 응답/예외 규약을 생성 템플릿에 주입(멘토 §J 우선순위 3번)** — `CommonApiResponse` 등이
    `skeleton_gen.py`/`_port_prompt` 어디에도 주입돼 있지 않은 게 사실이다. 하지만 `docs/09`가
    아직 **미확정**(HTTP status 정책 등 열린 질문)이라, 지금 주입하면 멘토가 §2에서 경고한 바로 그
    상황("공통 모듈은 사람이 먼저 확정하고 그 다음 강제 컨텍스트로 주입")이 뒤집힌다. **사람 결정
    대기 항목이지 코드 과제가 아니다.**
  - **진짜 javac 에러를 수리 루프에 피드백(멘토 §G)** — 저장 전 임시 사본으로 real javac 에러를
    이미 만들고 있어 연결은 가능하다. 하지만 ① 수리 루프 자체가 거의 안 걸리는 게 실측이라 트리거를
    강화해도 효용이 없고 ② Maven이 pilot 트리 **전체**를 빌드해 라운드마다 수 분 + 다른 화면의 기존
    오류가 섞인다. 비용 대비 효용이 나쁘다.
  - **HUMAN_EDIT_RATIO 측정(멘토 §H, "가장 중요")** — `CONV_FILE.HUMAN_EDIT_RATIO` 컬럼만 있고 한
    번도 채운 적이 없는 게 맞다(코드에 기록 지점 0개). 다만 아직 사람이 리뷰·수정한 화면이 0건이라
    지금 측정하면 빈 값만 나온다 - **측정 시점이 아직 안 왔다.**
  - **MCP 도입** — 리포지토리에 MCP 흔적은 하나도 없다. 도입하지 않기로 판단한 이유: ① MCP의 핵심
    가치는 모델이 도구를 동적으로 고르는 것인데 CLAUDE.md/멘토 §I가 똑같이 "완전 자율 탐색형
    에이전트를 만들지 않는다(1,416회 반복엔 고정 파이프라인이 낫다)"고 못 박았다 ② 진짜 병목(유형
    다양성, 실행 가능한 검증) 중 아무것도 해결하지 못한다 ③ **미루는 비용이 0이다** - `agents/*.py`가
    이미 Streamlit 의존 없는 순수 함수라 나중에 얇은 어댑터로 감싸면 된다. 나중에 한다면 범위는
    **읽기 전용 조회**(nctRid 조회, 영향도 질의, 미사용 함수)로 한정하고 변환 실행은 노출하지 않는다.
  - **정당하게 막혀 있는 것**: 파일럿 유형 다양성(§5), RAG(§C, 프로젝트가 스스로 연기), `.xjs`
    추출(§1, 샘플 없음), Refactor/Reimagine 분류(§F, 사람 결정+다양성 필요), 테스트 동반 생성(§B,
    포팅 코드를 실행할 환경 자체가 없음 - 이게 기능 동등성 25% 격차의 근본 원인).

  **다음 후보로 남긴 것**: 사용자가 제안한 **영향도 질의 팝업**. → **2026-09-04에 구현했다(아래
  항목). 이때 "Phase 3 대기"라고 한 내 분류가 틀렸다는 걸 확인했다** - 콜그래프가 이미 실데이터로
  채워져 있어(콜엣지 890·메서드 1034·화면 50) 지금 바로 만들고 검증할 수 있었다.

- **화면별 인수인계 문서 자동 생성(2026-09-04, 멘토 §A "실패분 리포트")** — 멘토 §A의 *"변환 실패를
  예외가 아닌 정상 산출물로 취급. '미변환 사유 + 수동 처리 가이드'를 화면별로 자동 생성"* 항목.
  그동안 이슈는 CONV_ISSUE(DB)와 Streamlit UI에만 있어서, 실제로 뒷일을 하는 사람이 "이 화면에서
  자동으로 안 된 게 뭐고 내가 뭘 해야 하나"를 보려면 UI를 클릭해 돌아다녀야 했다 - 이 팀이 산출물을
  zip으로 주고받는 워크플로라 화면당 문서 하나가 실제로 더 쓸모 있다.
  `agents/handoff_report.py`(신규): `build_handoff_report(entry)`가 계획서·생성 이슈·정적 검증·
  품질 스캔·LLM 호출 실패를 사람이 읽을 순서로 재구성한 마크다운을 만들고, `write_reports()`가
  `tracking/conversion-reports/{화면}-handoff.md`로 쓴다(계획서와 같은 이유로 `pilot/`이 아님).
  **새로 계산하는 값이 없다** - 판정을 다시 하지 않고 이미 나온 결과를 모아 배치만 바꾼다.
  구성: ①자동 변환을 신뢰하면 안 되는 이유(미지원 verb) ②AS-IS 원본이 컴파일 안 되는 상태 경고
  ③LLM 포팅 실패로 스텁이 남은 메서드 ④BLOCKER ⑤WARNING ⑥(접힘)INFO ⑦자동 변환 산출물 표
  ⑧LLM이 포팅해서 반드시 사람 리뷰가 필요한 메서드. 각 이슈에는 **그 타입에 대해 확인된 조치**를
  붙인다 - `issue_type`을 `grep`으로 전수 확인해 실제 존재하는 타입에만 가이드를 달았고, 표에 없는
  타입은 없는 처리법을 지어내지 않고 원본 메시지만 보여준다.
  UI에는 화면별 상세보기에 "📝 인수인계" 탭으로 붙였다(복사 버튼 포함).
  **검증**: 문제를 일부러 심은 화면(D 메서드를 dbInsert로 바꾸고 LLM 포팅 실패를 주입)으로 실행해
  미지원 verb 경고·원본 손상 경고·포팅 실패·BLOCKER/WARNING·산출물 표가 모두 정확히 나오는 것 확인,
  정상 2화면(PLA047/PLA001) 파이프라인 실 실행에서 문서 자동 생성 확인. **부수 발견**: 중첩 함수에서
  `out += [...]`(증강 대입)를 써서 `UnboundLocalError`가 났다 - `extend()`로 고쳤다.

- **영향도 역추적(blast radius) + 질의 팝업(2026-09-04)** — 사용자가 "남은 것들도 적용 가능한지
  다시 비판적으로 검증하라"고 해서 재점검하다가 **내 이전 분류가 틀렸다는 걸 발견했다**. 영향도
  질의를 "Phase 3(유형 다양성) 대기"로 미뤄뒀는데, 실제로 확인해보니 이 기능은 다양성이 아니라
  **콜그래프 데이터**만 있으면 되고 그건 이미 DB에 있었다(연결된 콜엣지 890, 메서드 1034, 화면 50,
  NCTRID_MAP 300행). 막힌 게 아니라 그냥 안 만든 것이었다 - 게다가 이건 첫 비판 검토 때 내가
  "역방향 영향도는 역BFS만 있으면 된다"고 직접 제안해놓고 계속 미룬 항목이다.
  `agents/impact_analysis.find_impact_of_method()`: 콜그래프를 **역방향 BFS**로 타고 올라가
  대상 메서드를 (간접적으로라도) 호출하는 모든 메서드와 그로 인해 영향받는 화면·nctRid를 돌려준다.
  `find_unused_methods()`가 "아무도 안 부르는 것"을 찾는 정방향 도달성 분석이라면 이건 반대 방향이다.
  Oracle 재귀 쿼리 대신 엣지를 한 번에 읽어 파이썬 BFS로 도는데(그래프가 작아 부담 없음), DB 방언에
  얽히지 않고 로직을 눈으로 검증할 수 있어서다. **LLM을 쓰지 않는다** - 결정론적 조회라 답에 근거를
  그대로 붙일 수 있고 CLAUDE.md 원칙에도 맞는다(사용자가 처음 제안할 때 "LLM이 분석"을 떠올렸지만,
  이 질문은 그래프 순회로 정확히 답이 나오므로 LLM을 넣을 이유가 없다).
  UI는 `@st.dialog` 팝업(`_show_impact_dialog`)이고, **파이프라인을 돌리지 않아도** 쓸 수 있게
  폴더 스캔 직후에 버튼을 뒀다(이번 실행 결과가 아니라 DB 적재분을 보기 때문).
  **검증 중 발견해 고친 것**: PLA047은 nctRid가 잘 나오는데 PLA001은 P 계층까지 역추적이 닿았는데도
  nctRid가 비었다. 원인은 `CONV_METHOD.NCTRID`가 화면마다 어느 시점·어느 소스로 분석됐는지에 따라
  비어 있을 수 있다는 것(PLA001은 `.bizunit` 부분 사본 시절 데이터). `NCTRID_MAP`(완전본 기준 300행)
  으로 폴백하도록 붙이고, 값의 출처(`nctrid_source`)를 결과에 같이 표시해 어디서 온 값인지 숨기지
  않게 했다. **검증**: 독립적으로 답을 아는 사례로 대조 - `dPLA04702` → `fPLA047QrySelectMainList`
  (depth 1) → `pPLA04701`(depth 2, RPLA04701)이 정확히 나옴, PLA001은 폴백으로 RPLA00101/00102
  확인, 49개 화면에 흩어진 `fCommonCodeQry`는 호출자 0으로 나오며(기존 "미사용 후보 49건" 결과와
  일치) 한계 노트를 같이 표시, 없는 메서드는 안내 문구. 결과 렌더링(metric/표/노트)도 실데이터로
  `AppTest` 검증. **못 한 것**: `@st.dialog` 안의 `st.form` 제출은 AppTest가 노출하지 않아 실제
  클릭 흐름은 브라우저 없이 확인 못 했다(이 프로젝트의 다른 UI와 같은 한계).

- **공통 응답/예외 규약 상태 정정(2026-09-04)** — 문서에 "`Pla047Api.java`가 `CommonApiResponse`를
  참조한다"고 적혀 있었지만 **지금은 사실이 아니다**. 확인 결과 `skeleton_gen.py`는 Api를
  `ResponseEntity.ok(...)`로 생성하고, `pilot/`의 어떤 Api 파일도 `CommonApiResponse`를 참조하지
  않는다(grep 0건). 즉 `pilot/gscm/.../common/`의 공통 클래스들은 **아무 것도 생성·사용하지 않는
  고아 코드** 상태다. 규약 자체가 미확정(HTTP status 정책 등)이라 생성기에 주입하는 건 여전히
  사람 확정 이후지만, "이미 반영돼 있다"는 오해는 없어야 해서 사실을 여기 남긴다.

- **추론 로그 가시화 + CLI 진입점(2026-09-05)** — 계기는 AI Master 심사의 시연 영상 제출 가이드다.
  가이드가 *"UI에서 처리 결과만 보여주는 경우 → 기술 구현 확인이 어려워 평가에 불리"*, *"핵심 로그가
  담긴 터미널/콘솔 화면은 반드시 포함"*, *"Agent의 추론 과정이 보여지는 로그로 증명해야 기술 깊이를
  평가받을 수 있다"*고 못 박고 있고, 5분 구성 중 1:30~3:30(40%)이 "Planning / Self-Correction 단계
  확대"다. 그런데 확인해보니 **`agents/workflow_graph.py`의 logging/print 호출이 0건**이었다 -
  파이프라인이 판단은 하는데(어떤 메서드를 LLM에 보낼지, 검증 실패를 수리로 되돌릴지, 예산을
  소진했으니 포기할지) 그게 `progress_cb`로 Streamlit UI에만 흘러가서 **터미널에는 아무것도 안 남는
  상태**였다. 추론이 없는 게 아니라 안 보이는 것이었다.

  `agents/reasoning_log.py`(신규) - 단계/이벤트 종류(PLAN/OBSERVE/DECIDE/CONTEXT/TOOL/VALIDATE/
  REFLECT/REPAIR/PASS/BLOCK)별로 정렬된 구조화 로그를 콘솔에 출력한다. **원칙: 없는 추론을 지어내지
  않는다** - 로그 문구를 만들어내는 게 아니라 이미 코드가 내린 결정을 그대로 받아 적는다(호출부가
  전부 실제 분기 지점에 있고, 인자는 그 시점의 실제 값이다). 기본은 꺼져 있어 Streamlit 경로는
  영향받지 않는다(`GSCM_REASONING_LOG=1` 또는 `log.enable()`).
  `agents/run_pipeline.py`(신규) - `python -m agents.run_pipeline <폴더> [--screens ...] [--dry-run]`.
  UI와 **동일한** `run_pipeline_part_a()`를 부르고 저장은 하지 않는다(승인 게이트 앞에서 멈춤).
  `--dry-run`은 LLM을 호출하지 않아 키·네트워크 없이 계획→규칙기반변환→검증→게이트 경로를 그대로
  재현한다(시연 리허설용).

  **이 로그를 붙이자마자 드러난 실제 결함 2건(둘 다 수정함)**:
  1. **포팅 전량 실패가 "성공"으로 보고됐다.** `PORTING_INCOMPLETE`(스텁 잔존)가 `WARNING`이라,
     `--dry-run`으로 LLM 호출 6건이 전부 실패했는데도 실행 요약이 **"잔여 BLOCKER 0건"**으로 나왔다.
     스텁이 남으면 컴파일은 되지만 런타임에 `UnsupportedOperationException`을 던지므로 "이 상태로는
     정상 동작을 보장할 수 없음"이라는 BLOCKER 정의에 정확히 해당한다(주차별 산출물에 정리한 판정
     체계에도 "포팅 스텁 잔존"을 BLOCKER 예시로 적어놨는데 코드와 어긋나 있었다). BLOCKER로 승격하고,
     대신 `_find_repairable_targets()`에서는 이 타입을 **제외**했다 - "포팅된 코드의 오류를 고쳐라"는
     수리 프롬프트에 스텁 본문을 넣으면 고칠 대상이 없어 무의미한 호출이 된다. 포팅 실패 재시도는
     `route_after_splice_all`의 `max_retries`가 담당하는 별개 메커니즘이다. 수정 후 같은 실행에서
     정직하게 **"잔여 BLOCKER 6건"**으로 바뀌는 것 확인.
  2. **병렬 브랜치가 서로의 로그를 깨뜨렸다.** `Send` 병렬 포팅 중 한 이벤트의 본문과 근거 줄 사이에
     다른 브랜치 출력이 끼어들어 로그가 뒤섞였다(영상에서 그대로 깨져 보인다). 이벤트 하나를
     원자적으로 내보내도록 락을 걸어 해소.

  **부수 확인 - 벤치마크 세트의 한계**: `PLA081-110_migration_sample`(30화면, 5도메인)로 돌려보니
  **nctRid가 0건**으로 잡힌다. 이 세트에 `.bizunit` 파일이 없기 때문이다(P/F/D `.java` + `.xsql`만
  있음). 즉 **"nctRid 자동 확정률 100%"는 `sample_data/legacy-u-pla001-050/` 기준 수치이지 이
  세트에는 성립하지 않는다** - 지표를 보고할 때 어느 세트 기준인지 반드시 함께 적어야 한다.

## Phase 3 — 파일럿 20~30화면 (자체 벤치마크 구축 겸함)
- [ ] 전체 화면을 컴포넌트 구성 + transaction 개수 + 그리드 유무 기준으로 구조적 클러스터링
- [ ] 유형별 대표 화면 4~5개씩, 총 20~30개 선정 (단순조회/그리드, 조회+상세+CRUD, 복합화면·리포트·특수로직)
- [ ] 화면별로 **Refactor(1:1 구조보존) / Reimagine(업무규칙만 추출해 재설계) 트랙**을 사람이 결정 — 단순조회·CRUD는 대부분 Refactor, 복합화면·원본 자체가 망가진 화면(예: PLA047의 FPLA047처럼 컴파일도 안 되는 경우)은 Reimagine 후보로 분류
- [ ] Phase 1~2 결과로 실제 변환 실행, `/tracking` 검증 테이블(@docs/08-conversion-verification.md)에 화면별 결과 기록 — 특히 **사람 수정 라인 비율**(자동 생성 대비 리뷰 중 수정한 라인 비율)을 반드시 기록. 이게 실제 공수 절감률의 대리 지표(@docs/06-mentor-feedback.md §H)
- [ ] 변환 규칙·프롬프트·공통 컴포넌트를 자산화 (이후 RAG 코퍼스로 사용)
- [ ] 유형별 실측 공수로 전체 계획 재산정 — 목표는 "화면이 돌아간다"가 아니라 "유형별 변환 레시피와 실측 공수 확보". @docs/01-project-plan.md의 KPI 기준값(평균 3일, 65~70% 절감)과 실측을 비교

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
- 화면 20~30건 파일럿 전까지는 전체 1,416개 화면에 대한 일괄 처리 스크립트를 만들지 않는다. **예외(2026-08-28, 2026-09-02 갱신)**: 사용자가 명시적으로 요청해 폴더 안 화면 전체를 1~5단계(규칙기반→LLM포팅→검증→스캔→AI추천)까지 LangGraph로 자동 진행시킨다(`agents/workflow_graph.run_pipeline_part_a`, `chatui/app.py` 폴더 모드). 대상 화면은 멀티셀렉트로 사람이 직접 고르고(기본값 전체지만 좁혀서 돌릴 수 있음), 저장(6~7단계로 넘어가는 지점)은 여전히 "승인하고 저장" 버튼을 사람이 눌러야만 진행된다. git 커밋은 여전히 사람이 함. CLAUDE.md "하지 말아야 할 것"에도 같은 예외를 기록해뒀다.
- 결정론적으로 풀리는 변환에 LLM을 쓰지 않는다 (CLAUDE.md "하지 말아야 할 것" 참고)
- RAG(FAISS/Chroma)·프롬프트 엔지니어링·FastAPI 서비스화(Phase 4~6)는 파일럿 20~30화면이 끝나기 전까지 착수하지 않는다(2026-08-28 사용자 확인 - Maven 빌드 검증만 우선 강화하기로 함). ESLint/tsc는 1단계 범위(서버 전환)에 해당 사항 없음 - 2단계 UI 트랙의 검증 수단이다
- 매 Phase 종료 시 이 문서의 체크박스를 갱신해 진행 상황을 추적한다
