# 3주차: 사용자 관점 시나리오 수립계획서

> 이 문서는 @docs/01-project-plan.md "목표 사용자"(전환 개발자 / PL·PM·QA)와 @CLAUDE.md 핵심 원칙(계획 파일로 고정, Translator/Validator 분리, 사람 리뷰 없는 자동 커밋 금지)을 실제 시나리오로 구체화한 것이다. 가상의 화면이 아니라 현재 `/legacy`에 확보된 유일한 실 소스 세트인 **PLA047**(GSCM/경영관리/제품MIX/계획분석 — "제품별 장당 수익" 조회 화면)과, 이미 동작 검증된 `chatui/app.py`/`converters.py`/`skeleton_gen.py`/`validators.py`/`quality_scanner.py` 파이프라인을 근거로 작성했다. 입출력 필드명·nctRid·파일명은 전부 `legacy/PPLA047.java`, `legacy/FPLA047.java`, `legacy/DPLA047.xsql`, @docs/08-conversion-verification.md에서 실제로 확인된 값이다.

> **범위 한계**: PLA047 1개 화면(그것도 단순조회형)만 파일럿이 끝난 상태이므로, 아래 시나리오는 "전환 개발자가 화면을 변환한다" / "PM·QA가 변환 결과를 승인한다"는 **공통 골격 시나리오**다. @docs/03-kickoff-plan.md Phase 3(구조적 클러스터링, 유형별 4~5개 대표 화면)이 끝나면 조회+상세+CRUD형, 복합화면·Reimagine 트랙형 시나리오를 추가로 채워야 한다 — 지금 단계에서 유형별 시나리오까지 확정하는 것은 추측이므로 하지 않는다.

---

### 핵심 사용자 시나리오

**시나리오 1 : 전환 개발자가 화면 골격을 규칙 기반으로 1차 변환한다**

* ID : SC-001

* 상황 : G-SCM 전환 프로젝트에 투입된 백엔드 개발자가, 파일럿 대상 화면 PLA047의 AS-IS 소스(P/F/D BizUnit `.java`, `.bizunit`, `DPLA047.xsql`)를 `/legacy`에서 확보한 뒤, 로컬에서 `streamlit run chatui/app.py`로 띄운 업로드→변환 챗팅 UI에 화면 하나를 통째로 넣지 않고 5개 fragment 단위로 넣어 TO-BE 골격을 생성하려는 상황

* 목표 : 결정론적 규칙 기반 변환기(iBatis→MyBatis, BizUnit→Controller/Service/Store 골격, `.BIZUNIT`→Dto)로 `Pla047Api`/`Pla047Service`/`Pla047Store`/`Pla047Dto`/`Pla047Mapper.xml` 골격을 생성하고, 변환 중 자동 추출이 실패한 항목(미변환/경고)을 빠짐없이 확인한다

* 사전 조건 :
  - `/legacy`에 `PPLA047.java`, `FPLA047.java`, `DPLA047.java`, `DPLA047.xsql`, `{P,F,D}PLA047.bizunit` 확보됨
  - `.env`에 로컬 Oracle(`RPLS_ADM`/`xe`) 접속정보 설정됨
  - `chatui/app.py`가 로컬 8501 포트에서 기동 중

* 상세 흐름

| 단계 | 사용자 행동 | 시스템 동작 | 비고 |
| -- | ------ | ------ | -- |
| 1 | AS-IS 폴더 경로(`legacy/`)를 입력하고 화면(PLA047)을 선택한다 | 경로에서 `p1`/`p2` 패키지(`pm`/`pla`)를 자동 감지하고, `AS_IS_CONTENT_HASH`로 이전 변환 이력을 조회해 "이전 변환 PASS, 원본 변경 없음" 여부를 화면 목록에 미리 표시한다(자동 스킵은 하지 않음) | 원본이 바뀌었으면 캐시를 무시하고 새로 변환해야 함 |
| 2 | "1단계: 규칙 기반 변환 실행" 버튼을 클릭한다 | `converters.py`로 `DPLA047.xsql`의 `#var#`/`$var$`/`<isEqual>`/`<isNotEqual>`을 MyBatis 문법으로 치환하고, `skeleton_gen.py`로 P→F→D 호출 관계를 추적해 `Pla047Api`→`Pla047Service`→`Pla047Store` 골격과 `Pla047Dto`를 생성한다 | Service 메서드 본문은 전부 TODO 스텁 — LLM 포팅은 별도 버튼 |
| 3 | "⚠️ 주의/미변환 항목" expander를 펼쳐 확인한다 | RPLA04702/03처럼 F가 `getFieldMap()`을 통째로 넘겨 개별 요청 필드를 추출하지 못한 경우, XSQL의 태그 불일치(`isNotEqual`↔`isEqual` 미스매치 등)로 well-formed 검증에 실패한 경우를 WARNING/FAIL로 나열한다 | 여기서 나온 항목은 추측으로 채우지 않고 사람이 직접 확인 |
| 4 | "🛡️ 코드 품질/취약점 스캔" 버튼을 클릭한다 | `quality_scanner.py`가 생성된 `Pla047Mapper.xml`의 `${...}`(SQL 인젝션 후보) 건수, `Pla047Service.java`의 문자열 연결 SQL 건수, 원본 버그 보존(`FIXME`) 건수, 하드코딩 자격증명(`HARDCODED_CREDENTIAL`, BLOCKER) 여부를 스캔해 표시한다 | BLOCKER는 다른 항목과 분리해 즉시 검토 대상으로 강조 |
| 5 | 결과를 검토한 뒤 "저장" 버튼을 클릭한다 | `pilot/PLA047/` 하위에 TO-BE 파일을 실제로 쓰고, `CONV_FILE`/`CONV_ISSUE` 테이블에 파일별 `BUILD_CHECK`와 이슈를 기록한다 | 저장 전까지는 파일이 디스크에 생기지 않음 — 자동 커밋 없음(CLAUDE.md) |

* 입력 예시

```
AS-IS 폴더 경로: legacy/
대상 화면: PLA047
업로드 fragment: PPLA047.java, FPLA047.java, DPLA047.java, DPLA047.xsql,
                 PPLA047.bizunit, FPLA047.bizunit, DPLA047.bizunit
```

* 기대 출력

```
생성 파일: gscm/src/main/java/com/skhynix/gscm/r/pm/pla/Controller/Pla047Api.java
           gscm/src/main/java/com/skhynix/gscm/r/pm/pla/service/Pla047Service.java
           gscm/src/main/java/com/skhynix/gscm/r/pm/pla/store/Pla047Store.java
           gscm/src/main/java/com/skhynix/gscm/r/pm/pla/dto/Pla047Dto.java
           gscm/src/main/resources/mapper/r/pm/pla/Pla047Mapper.xml
경고 3건: RPLA04702 요청 필드 미추출(TODO), RPLA04703 요청 필드 미추출(TODO),
          Pla047Mapper.xml 태그 불일치 지점(라인 4718/5179 인근)
품질 스캔: ${...} 339건, 문자열 연결 SQL 13건, FIXME(원본 버그 보존) 31건, HARDCODED_CREDENTIAL 0건
```

* 성공 기준

  * 기준 1: `Pla047Api`/`Pla047Service`/`Pla047Store`/`Pla047Dto`/`Pla047Mapper.xml` 골격이 전부 생성되고, Mapper.xml은 well-formed 여부가 PASS/FAIL로 명시적으로 표시된다(태그 불일치가 있으면 조용히 넘어가지 않고 FAIL로 뜬다)
  * 기준 2: 화면 저장 전 발견된 모든 이슈(미변환 경고 + 품질 스캔 결과)가 `CONV_ISSUE`에 기록되어, 저장 시점에 개발자가 빠뜨린 항목이 없다

**시나리오 2 : PL/PM·QA가 차등 테스트와 정적 검증 결과로 변환 결과를 승인한다**

* ID : SC-002

* 상황 : 개발자가 SC-001로 골격 생성 + LLM 포팅까지 마친 PLA047 화면에 대해, PL/PM 또는 QA 담당자가 배포(커밋) 승인 여부를 결정해야 하는 상황. CLAUDE.md 원칙상 "사람 리뷰 없는 자동 커밋/배포는 금지"이므로 이 승인 절차 없이는 다음 화면으로 넘어갈 수 없다

* 목표 : 레거시 nctRid(`RPLA04701`)와 신규 REST API에 동일 입력을 넣어 응답을 diff로 비교(차등 테스트)하고, `validators.py`의 `BUILD_CHECK` 결과·`quality_scanner.py`의 품질 스캔 결과를 함께 근거로 승인 또는 보류를 결정한다

* 사전 조건 :
  - 로컬 Oracle DB(`RPLS_ADM`/`xe`)에 레거시 nctRid 경로와 신규 REST 경로가 동시에 접속 가능한 상태
  - SC-001 저장 시점에 `CONV_FILE.BUILD_CHECK`, `CONV_ISSUE`가 이미 채워져 있음

* 상세 흐름

| 단계 | 사용자 행동 | 시스템 동작 | 비고 |
| -- | ------ | ------ | -- |
| 1 | `tracking/conversion-verification.csv` 또는 `CONV_FILE` 조회로 PLA047 파일별 `BUILD_CHECK` 상태를 확인한다 | Api/Store/Dto/계층간참조는 PASS, Service는 원본 버그(중괄호 누락) 보존으로 FAIL, XSQL은 알려진 태그 불일치로 FAIL임을 그대로 보여준다 | 원본 결함이 원인인 FAIL은 "재작성"이 아니라 "원본 정정 후 재포팅" 대상으로 구분 |
| 2 | 차등 테스트 하네스에 동일 입력(`DIM`, `TECH_CD`, `SRCTYPE`, `CHK_SUBTOTAL`, `YEAR`, `TECH_GRP_ID` 등)을 넣어 레거시/신규를 동시 호출한다 | 레거시 `IDataSet` 응답과 신규 JSON 응답을 정규화한 뒤 필드 단위로 diff한다 | "변환된다"와 "맞다"는 별개(@docs/02-architecture.md 검증 전략) |
| 3 | 품질 스캔 결과에서 `HARDCODED_CREDENTIAL`, `DEPRECATED_NEXCORE_API` 잔존 여부를 확인한다 | BLOCKER(`HARDCODED_CREDENTIAL`)가 하나라도 있으면 승인 버튼을 비활성화하거나 강조 경고로 표시한다 | BLOCKER는 즉시 사람 검토 대상 |
| 4 | diff 불일치 또는 FAIL 항목에 대해 담당 개발자에게 코멘트를 남긴다 | `CONV_ISSUE`에 리뷰 코멘트/블로커 사유를 갱신한다 | "확인 필요" 식 모호한 코멘트 금지(@docs/08 상태값 규칙) |
| 5 | 모든 BLOCKER가 해소된 뒤 리뷰 상태를 "승인"으로 변경한다 | 리뷰 상태가 "승인"이 된 파일만 커밋/배포 대상 목록에 편입한다 | 빌드 PASS와 리뷰 승인은 별개 조건(둘 다 필요) |

* 입력 예시

```
nctRid: RPLA04701
요청 필드: DIM="APP_LVL_1_CD,TECH_CD", SRCTYPE="BASE", CHK_SUBTOTAL="N",
           SEARCH_TYPE="NORMAL", YEAR="2026", TECH_GRP_ID="1"
```

* 기대 출력

```
레거시 응답(IDataSet): DATETIME_MAP, MAIN_LIST(N건)
신규 응답(JSON):        datetimeMap, mainList(N건)
diff 결과: 필드 단위 일치/불일치 목록 (불일치 0건이면 PASS)
리뷰 상태: 검토중 → 승인(모든 BLOCKER 해소 시)
```

* 성공 기준

  * 기준 1: 차등 테스트 diff가 100% 일치하거나, 불일치 항목이 전부 사유와 함께 `CONV_ISSUE`에 기록된다
  * 기준 2: BLOCKER급 품질 이슈(자격증명 하드코딩 등)가 0건인 상태에서만 리뷰 상태가 "승인"으로 전환된다

### 시나리오 우선순위 매트릭스

|        |              |              |         |
| ------ | ------------ | ------------ | ------- |
| 시나리오   | 비즈니스 가치      | 구현 난이도       | PoC 포함  |
| SC-001 | 높음(1,416화면 파이프라인의 반복 진입점) | 중간(v0 이미 동작 검증됨, 화면 유형 확장 시 재검증 필요) | 네 |
| SC-002 | 높음(멘토 코멘트 §3 핵심 — 문법 정확도와 기능 정확성은 별개) | 높음(차등 테스트 하네스 자체가 아직 미구축, @docs/03-kickoff-plan.md Phase 1 진행중) | 네 |

> 다음 갱신 시점: @docs/03-kickoff-plan.md Phase 1(nctRid 매핑 그래프 + 차등 테스트 하네스)과 Phase 3(파일럿 20~30화면 클러스터링)이 진행되면, 조회+상세+CRUD형(SC-003 후보)과 복합화면·Reimagine 트랙형(SC-004 후보) 시나리오를 실제 대표 화면 소스가 확보된 뒤 추가한다.
