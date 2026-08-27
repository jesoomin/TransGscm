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
- [ ] **`/legacy`의 PLA047 소스 무결성 문제 해결** — `.bizunit` XML 3종은 아직 XML 선언 손상(따옴표 불일치, `<description>`/`</dedication>` 태그 불일치)으로 파싱 불가. `FPLA047.java`/`PPLA047.java`는 아직 컴파일 에러 다수(중괄호 누락, 미선언 변수 `du`, `ArrayList<object>` 등). **`DPLA047.xsql`의 태그 불일치 2건은 수정 완료**: ① 4840행 `</isEqual>` → `</isNotEqual>`(4718행에서 연 태그와 짝을 맞춤) ② 5179행의 매칭되는 여는 태그 없는 단독 `</isNotEqual>` 삭제. 두 곳을 고친 뒤 스택 기반 태그 검사(열림/닫힘 전수 대조)와 `xml.dom.minidom` 파싱 모두 통과 확인 — `DPLA047.xsql` 전체가 유효한 XML이 됐다. `chatui/converters.py`로 재변환한 `gscm/.../Pla047Mapper.xml`도 `chatui/validators.py`의 `check_mapper_xml` PASS로 재확인(이전엔 XML_PARSE_ERROR로 BLOCKER였음). SQL 내용은 건드리지 않았다 - 오직 태그 이름/유무만 고쳤다(git diff 4줄). 남은 무결성 문제(`.bizunit` 3종, `FPLA047.java`/`PPLA047.java` 컴파일 에러)는 여전히 미해결
- [x] `.bizunit` 3종 + `FPLA047.java`/`PPLA047.java`도 변환 대상에서 제외하지 않는다 — 확인됨(아래 참고). 원본이 깨져 있어도 스킵하지 않고 `.BIZUNIT`은 코드 실사용값(getField/putField) 역추출로, Java는 원본 정정 후 포팅으로 진행
- [x] 로컬 Oracle DB(`RPLS_ADM`, localhost:1521, SID=`xe`) 접속 확인 — `sqlplus`로 검증 완료(2026-08-14): 로그인 성공, 실제 SERVICE_NAME도 `xe`, DB_NAME=`XE`. **주의: 사용자가 전달한 "service_name=GSCM"은 Oracle 서비스명이 아니라 DB 접속 도구에 저장된 연결 프로파일 이름이었음** — `GSCM`을 서비스명으로 접속 시도하면 ORA-12514(서비스 없음) 발생, 실제로는 SID `xe` 사용. `.env`에 검증된 JDBC URL(`jdbc:oracle:thin:@localhost:1521:xe`) 반영 완료. 스키마 접근 권한(테이블 조회 등)은 아직 세부 검증 안 함

## Phase 1 — nctRid 매핑 그래프 + 차등 테스트 하네스 (변환기보다 먼저)
멘토 코멘트 §1, §3. 이게 없으면 에이전트가 화면마다 코드베이스를 헤매며 환각을 낸다.

**2026-08-27 접근 변경(사용자 확인, 실무 경험 기반)**: nctRid는 P BizUnit(PU) 소스의 public 메서드명과
사실상 동일하다(`PPLA047.java`의 `pPLA04701` = nctRid `RPLA04701`). 화면ID는 `U-{P클래스명}` 형식이고,
하나의 PU가 여러 FU를 호출할 수 있는 구조다. UI 소스(.xjs)나 NEXCORE 설정을 거치지 않아도 **P/F/D
BizUnit Java 소스(파일명 규칙 + 메서드 호출부)만으로 nctRid↔P↔F↔D↔XSQL 콜그래프 전체를 정적으로 구성할
수 있다** - 아래 두 항목(`.xjs` 추출, NEXCORE 설정 매핑)은 더 이상 선행 조건이 아니므로 접근 방식을
변경한다(@docs/04-glossary.md "nctRid"/"화면ID" 참고).

- [x] ~~`.xjs` → `transaction()` 호출부 → nctRid 추출~~ — **불필요로 확인(사용자, 2026-08-27)**: nctRid=P 메서드명이라 Java 소스만으로 충분. `.xjs` 파싱 자체가 이번 범위(UI 미전환)에 안 맞기도 했음(CLAUDE.md 핵심 원칙)
- [x] ~~NEXCORE 설정에서 nctRid → P BizUnit 클래스 매핑 추출~~ — **불필요로 확인(사용자, 2026-08-27)**: P 클래스명 자체가 화면ID(`U-{P클래스명}`)이므로 별도 설정 조회가 필요 없음
- [x] **P → F → D 콜그래프 추적 + D → XSQL statement 매핑 — `agents/nctrid_mapper.py` 신규 구현**. JavaParser 대신 `chatui/skeleton_gen.py`가 이미 검증한 정규식 기반 추출 함수(`extract_methods`/`extract_method_bodies`/`extract_nctrid_map`)를 재사용하고, D→XSQL statement id 추출(`dbSelect("S00N", ...)`)은 `skeleton_gen.py`에서 `extract_d_statement_ids()`로 뽑아내 공용 함수로 분리한 뒤 재사용(중복 방지). 호출 매칭은 **변수명이 아니라 메서드명 존재 여부**로 한다 - FPLA047.java 35행처럼 D 유닛을 `lookupFunctionUnit()`으로 조회하거나 `fu`/`du` 변수명이 메서드마다 뒤섞이는 원본 결함이 있어도 안전하게 동작하도록 함(원본을 고치지 않고 그 위에서 강건하게 동작하는 방식 선택). PLA047 실 소스로 검증: `pPLA04701`(nctRid `RPLA04701`) → `fPLA047QrySelectMainList` → `dPLA04702/03/04/05`(S002~S005) 4개 전부, `pPLA04702`(`RPLA04702`) → `fPLA047QrySelectRev` → `dPLA04701`(S001), `pPLA04703`(`RPLA04703`) → `fPLA047QrySelectRevPeriod` → `dPLA04706`(S006) - 총 6행, 전부 사전에 사람이 직접 대조한 값과 정확히 일치 확인
- [x] 화면↔API↔SQL 그래프를 구조화 파일 + DB로 구축 — `tracking/nctrid-map.csv`(사람이 보는 요약본, `write_csv()`)와 `agents/db_schema.sql`의 신규 `NCTRID_MAP` 테이블(+`agents/db.py`의 `replace_nctrid_map()`) 둘 다 준비. **DB 쪽은 이 개발 환경에 Oracle 접속이 없어 실행 검증은 못 함**(코드는 기존 `upsert_conv_file`/`record_issues`와 동일한 패턴) - CSV 쪽은 PLA047 실 데이터로 저장까지 확인. 자동 추출 실패 케이스(F/D 메서드 호출을 못 찾은 행)는 `비고` 열에 "원본 확인 필요"로 남기고 추측하지 않는다
- [ ] 화면이 여러 개 쌓이면(파일럿 20~30개) 자동 추출 실패율이 실제로 10~20%대인지 표본으로 재확인 — 지금은 PLA047 1건뿐이라 아직 통계적으로 의미 없음
- [ ] 차등 테스트 하네스 구축: 동일 입력 → 레거시 nctRid 호출 / 신규 REST 호출 → 정규화 후 diff. 로컬 Oracle DB(`.env`)에 두 경로를 붙여서 파일럿 전에 먼저 동작 확인 (**다음 착수 예정**)

## Phase 2 — 공통 규약 + 결정론적 변환기 + 업로드→변환 챗팅 UI
화면 하나를 통째로 넣지 않는다 — `.BIZUNIT`/P/F/D/XSQL 5개 fragment로 나눠 처리하고, **콜그래프 역순(XSQL → Store → Service → Api)** 으로 하위부터 확정한다. 상위(Api) 시그니처를 먼저 잡고 하위를 끼워 맞추지 않는다.
- [x] 공통 응답/예외 처리 규약 확정 — @docs/09-common-conventions.md. `com.skhynix.gscm.common`에 `ApiResponse`/`ResultCode`/`BizException`/`GlobalExceptionHandler`/`MessageCodeResolver` 템플릿 작성(`templates/common/`), PLA047 실 소스(`PPLA047.java`/`FPLA047.java`)에서 관찰된 `BizRuntimeException(code, args, cause)` 패턴 그대로 대응시킴. Spring 6 실 클래스패스로 `mvn compile` 검증 완료(임시 프로젝트, 저장소에는 남기지 않음). `skeleton_gen.py`의 Api 골격도 `ApiResponse`를 쓰도록 갱신하고 Store의 MyBatis 연동 방식(SqlSessionTemplate 직접 호출) 미확정 TODO를 확정으로 정리함. 메시지 코드(`E0052`/`W0024`/`I0016`) 실제 문구는 여전히 TODO(NEXCORE 공통 메시지 테이블 확인 필요)
- [ ] 메시지 코드 표준화: AS-IS 하드코딩 코드(`E0052`, `W0024`, `I0016` 등) → `errors.properties`/`errors_en.properties` 추출 규칙
- [x] iBatis → MyBatis 변환 모듈 v0 — `chatui/converters.py`. PLA047에서 검증한 4종 규칙(`isEqual`/`isNotEqual`/`isNotEmpty`+`iterate`/바인드 변수) + 멘토 코멘트의 `isNull`/`isNotNull`/`isGreaterThan` 등/`dynamic prepend`도 규칙만 준비. **실제로 검증된 건 PLA047뿐**이라 다른 화면 XSQL에 돌려서 결과를 반드시 확인할 것. 변환 후 XML well-formed 여부까지 자동 체크해서 경고로 보여줌(원본 태그 불일치를 여기서 잡아냄)
- [x] BizUnit 메서드 시그니처 → Controller(`{화면}Api`)/Service/Store 골격 생성기 v0 — `chatui/skeleton_gen.py`. PLA047 실 소스로 동작 검증: P 메서드가 실제로 호출하는 F 메서드를 본문에서 찾아 Api→Service 연결까지 정확히 맞춤(단순 이름 매칭이 아님). D 메서드는 `dbSelect("S00N", ...)` 호출에서 매퍼 statement id를 뽑아 Store가 참조하도록 생성. **골격만 규칙 기반, Service 메서드 본문은 항상 TODO 스텁 — LLM 포팅은 별도 단계**
- [x] `.BIZUNIT` 필드 → DTO 생성기 — `chatui/skeleton_gen.py`의 `extract_dto_fields`/`generate_dto` (규칙 기반, LLM 아님). `.BIZUNIT`의 `<fields/>`가 비어있을 때 nctRid(P 메서드)별로 요청 필드는 delegate F 메서드의 `getField` 호출, 응답 필드는 P 메서드의 `putRecordset` 호출에서 역추출. PLA047로 검증: RPLA04701은 15개 요청 필드 전부 채워짐, RPLA04702/03은 F가 `getFieldMap()`을 통째로 넘기는 구조라 개별 필드를 못 찾아 TODO+WARNING으로 표시(추측하지 않고 사람 확인 필요 처리). 필드 타입은 전부 String/`List<Map<>>`로 잠정 지정(원본에 실제 타입 미선언)
- [ ] 화면별 변환 전에 `conversion-plan.json`(대상 fragment, 트랙(Refactor/Reimagine), 예상 산출 파일 목록)을 먼저 생성해 고정 — 계획 없이 바로 코드 생성하지 않는다
- [x] **업로드→변환 챗팅 UI v0** — `chatui/app.py` (Streamlit, 로컬 전용). 화면 1개 분량 P/F/D `.java`/`.bizunit`+XSQL을 업로드하면 위 결정론적 변환기를 돌려 결과를 화면에 보여주고, "저장" 버튼을 눌러야만 `pilot/{screen}/`에 파일이 생긴다(자동 커밋 없음). Service 로직 LLM 포팅은 별도 버튼으로 분리(실험적, 결과 검토 필수 문구 표시). 실행: `pip install -r requirements.txt` 후 `streamlit run chatui/app.py` → `http://localhost:8501`. **2026-08-27 정정**: 처음 작성 시점엔 이 환경에 Streamlit이 없어 내부 변환 로직만 검증했지만, 이후 `pip install streamlit`으로 실제 설치해 Streamlit 공식 테스트 프레임워크(`streamlit.testing.v1.AppTest`)로 앱 실행 자체도 검증했다(아래 참고) - 이 환경엔 브라우저가 없어 실제 렌더링/클릭 UX까지는 여전히 못 봄.

**2026-08-27 추가: 전체 전환 현황 그리드 + 실패 상세 팝업.** 지금까지는 화면을 하나씩 골라야 그 화면의 상태만 볼 수 있었는데, 상단에 전체 화면 기준 집계(총 전환 건수/성공 건수/실패 건수/전환율)를 그리드로 보여주는 `_render_conversion_summary()`를 추가했다. 데이터 출처는 `agents/db.py`의 `CONV_FILE`(화면을 변환하고 "DB에도 기록"을 켠 채 저장할 때마다 쌓이는 테이블) - 화면 하나는 그 안의 파일(P/F/D/XSQL/DTO 등) 중 `BUILD_CHECK='FAIL'`이 하나라도 있으면 실패로 센다(CLAUDE.md: 빌드 통과해야 완료). `agents/db.py`에 `get_screen_summary()`(화면별 집계)/`get_failed_files()`(실패 파일 목록)/`get_issues_for_files()`(파일별 실패 사유)를 신규 추가했다. "전환 실패 건수" 열을 클릭하거나(Streamlit 1.35+ 데이터프레임 컬럼 선택, `on_select`/`selection_mode="single-column"`) 버튼을 누르면 `st.dialog`(Streamlit 1.37+) 팝업으로 실패한 파일별 상세(화면ID/계층/AS-IS·TO-BE 파일명/실패 사유/이슈 건수)를 그리드로 보여준다. 이 환경에 실제 Oracle DB는 없어서(자격증명 없음) `agents.db`를 `unittest.mock`으로 목킹해 `streamlit.testing.v1.AppTest`로 검증했다: (1) DB 미연결 시 안내 메시지로 안전하게 폴백 (2) 화면 2개(성공 1/실패 1) 목 데이터로 그리드 집계(총 2/성공 1/실패 1/50.0%)가 정확함 (3) 실패 상세 버튼 클릭 시 팝업에 올바른 실패 파일·사유가 뜸 - 세 경우 모두 예외 없이 통과. `use_container_width`(제거 예정 API, 이미 지난 날짜에 경고 발생)는 `width="stretch"`로 바로 교체해서 씀. 실제 Oracle DB로 여러 화면 데이터를 쌓은 뒤 최종 확인은 여전히 필요.
- [x] Validation(정적 검증, 1단계) — `chatui/validators.py` 신규 구현(변환기와 분리된 검증기, CLAUDE.md "Translator/Validator 분리" 원칙). **2026-08-27 정정**: 처음 작성 시점엔 Maven/Gradle 프로젝트(pom.xml, 의존성)가 없어 진짜 컴파일은 못 했지만, 이후 `gscm/pom.xml`을 구축하면서 더 이상 사실이 아니게 됨 - 아래에 그 경과가 그대로 기록돼 있다. 최초엔 진짜 컴파일 대신 정적 검사만 했다: Java 파일 중괄호 균형(문자열/주석 인식), LLM 포팅 후 남은 PORT_START 스텁 탐지, 계층 간 실제 호출 대상 존재 확인(Api의 service.xxx() → Service 정의 여부, Service의 store.xxx() → Store 정의 여부, Store가 참조하는 매퍼 statement id → Mapper.xml 존재 여부), Mapper.xml well-formed 여부·statement id 중복·바인드 표현식 짝. 결과는 PASS/FAIL로 `CONV_FILE.BUILD_CHECK`에 저장되고 실패 이슈는 `CONV_ISSUE`에 `detected_by='chatui/validators.py'`로 쌓인다. PLA047로 실 DB 검증: Api/Store/Dto/계층간참조 PASS, Service는 원본 버그(중괄호 누락) 보존 때문에 의도대로 FAIL, XSQL은 알려진 태그 불일치로 의도대로 FAIL — 전부 실제로 CONV_FILE/CONV_ISSUE에 기록됨 확인. **실제 Maven 빌드 검증**: `gscm/pom.xml`(Spring Boot 3.3.4 parent, Java 21, spring-boot-starter-web/mybatis-spring-boot-starter/ojdbc11) 신규 작성, `docs/09-common-conventions.md`의 공통 클래스(`templates/common/`)와 PLA047 골격(Api/Service/Store/Dto + Mapper.xml)을 `gscm/src/main/...` 실 소스 트리에 배치하고 `cd gscm && mvn compile` 실행까지 확인 — BUILD SUCCESS(clean 재빌드로도 재확인). 이 과정에서 `skeleton_gen.py`의 실제 버그(Api→Service, Service→Store가 서로 다른 서브패키지인데 import 문을 생성하지 않아 컴파일 실패)를 발견해 고침. `Pla047Mapper.xml`의 태그 불일치(XML_PARSE_ERROR)는 이후 `/legacy/DPLA047.xsql` 원본 수정(Phase 0 참고)으로 해결 완료 - `chatui/validators.py`의 `check_mapper_xml` PASS로 확인. **2026-08-27 정정**: 위 BUILD SUCCESS는 그 시점에 `Pla047Service.java`가 (골격 재생성으로) 빈 TODO 스텁이었을 때 얻은 결과였다. 이후 `pilot/gscm/`에 남아있던 이 파일의 실제 LLM 포팅 결과(원본 FPLA047.java 버그 보존)를 `gscm/`으로 복원하자 `mvn compile`이 다시 실패한다(else-without-if 11건 등, 전부 원본 버그) - `docs/08-conversion-verification.md`의 "스테이징과 실제 빌드 모듈의 드리프트" 절 참고. `Pla047Service.java`를 임시 스텁으로 바꿔서 재빌드하면 나머지(common/*, Api, Store, Dto, Mapper.xml 리소스)는 여전히 전부 컴파일된다 - 이 화면이 Reimagine 후보라는 기존 판단과 일치하는, 예상된 결과다. **2026-08-27 추가**: `chatui/validators.py`에 `run_maven_compile()`을 구현해 `chatui/app.py`에 "🔨 실제 mvn compile 실행" 버튼을 붙였다 - subprocess로 실제 `mvn -q compile`을 `gscm/`에서 실행하고 BUILD SUCCESS/FAILURE와 `[ERROR]` 로그를 화면에 보여준다. mvn 바이너리나 `gscm/pom.xml`이 없는 환경에서는 안내 메시지만 내고 안전하게 건너뛴다. 이 환경엔 Streamlit이 없어 버튼 클릭 자체는 못 해봤지만 `run_maven_compile()` 함수는 직접 호출해 검증: (1) 정상 케이스 - 현재 `Pla047Service.java`의 알려진 실패를 51건의 `[ERROR]`로 정확히 재현 (2) 모듈 없음 케이스 - 존재하지 않는 경로를 줬을 때 `available=False`로 안전하게 폴백. 정적 검증(`validate_screen`)과는 여전히 자동으로 연동되지 않는 별도 버튼이다. **Spring 컨텍스트 기동(`mvn spring-boot:run`)과 실제 DB 연동/차등 테스트는 여전히 미착수**

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
