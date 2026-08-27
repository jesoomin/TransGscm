# 7주차 산출물 정리 (1~5주차 템플릿 작성)

> 이 문서는 소속 AI Agent 육성 프로그램의 주차별 산출물 템플릿을 **G-SCM 차세대 전환 Agent(v2, 백엔드 전용 범위)** 기준으로 채운 것이다. 내용은 전부 이 저장소의 실제 문서(@CLAUDE.md, @docs/01-project-plan.md, @docs/02-architecture.md, @docs/05-proposal-v2.md, @docs/06-mentor-feedback.md, @docs/03-kickoff-plan.md, @docs/08-conversion-verification.md)와 실제 코드(`agents/`, `chatui/`)에서 근거를 가져왔다. 아직 구현되지 않은 부분은 "계획(미착수)"로 명시하고 추측으로 채우지 않았다 — CLAUDE.md 핵심 원칙("확인되지 않은 것을 추측으로 하드코딩하지 않는다")을 문서 작성에도 동일하게 적용했다.
>
> 범위 기준: **UI(Nexacro xfdl/React)는 이번 Agent 산출물이 아니다.** 서버(Controller/Service/Store/Mapper)까지가 산출물이며, 화면은 그대로 두고 nctRid 계약을 유지하는 REST API를 만든다. 프로그램 템플릿에 등장하는 "Agent", "도구", "RAG" 같은 범용 용어는 이 프로젝트의 실제 산출물인 **업로드→변환 챗팅 UI(`chatui/app.py`)와 그 뒤에서 동작하는 결정론적 변환기+LLM 포팅 파이프라인**에 맞춰 구체화했다.

---

## 1주차: 역량 및 기술 스택 확인

### 1. 현재 보유 역량
- **Python 숙련도**: 초급~중급 → 이번 PoC 진행 중 실무 구현 경험을 실제로 축적함 — 정규식/`xml.dom.minidom` 기반 경량 파서(`chatui/converters.py`, `skeleton_gen.py`, `validators.py`), Azure OpenAI SDK 연동(`agents/llm_gateway.py`), `oracledb`를 통한 Oracle DB 연동(`agents/db.py`) 등을 직접 작성·검증함. 다만 `javalang`/`tree-sitter`/`lxml` 같은 정식 파서 라이브러리는 아직 도입하지 않고 경량 정규식 기반으로 대체 중 — 정확한 AST 기반 파싱은 남은 과제
- **AI/ML 경험**: 전통 ML보다 LLM 기반 Agent 시스템 구축 중심
- **LLM 활용 경험**: 사내 SKHy GaiA LLM 프레임워크로 Analysis/Simulation/Validation Agent 기능 구축 + 이번 프로젝트에서 사내 LLM Gateway(Azure OpenAI 호환, `agents/llm_gateway.py`)를 이용한 단발 instruction 프롬프트 기반 코드 포팅(`chatui/app.py`의 `_port_method`) 구현·검증(PLA047)
- **RAG/Agent 구현 경험**: 유
  - P-MIX Simulation Agent — Multi-Agent 구조(Analysis/Simulation/Validation) 구현
  - Orchestrator 설계: 자연어 질의 → Agent 할당 → 기능 실행 → 결과 구조화
  - Domain Knowledge: md 파일 구축 → 프롬프트 반영(경량 프롬프트 주입형, 벡터 검색 기반 RAG는 아직 미적용)
- **프로젝트 경험**
  - P-MIX Simulation Agent(수행 중) — GaiA 기반 Multi-Agent/Orchestrator 구현
  - G-SCM Nexacro14 + NEXCORE(Spring, PU/FU/DU/XSQL) 개발·유지보수 — 이번 전환 프로젝트 도메인 지식의 원천
  - **G-SCM 차세대 전환 Agent PoC(현재 진행 중)** — 결정론적 변환기(iBatis→MyBatis, BizUnit→Controller/Service/Store/Dto 골격) v0, LLM 포팅 모듈, 변환기와 분리된 검증기 3종(정적 검증·품질/보안 스캐너·화면 간 중복 분석)을 실제로 구현하고 PLA047 1건으로 end-to-end 검증까지 완료

### 2. 학습 필요 영역
| 영역 | 현재 상태 | 필요 학습 |
|---|---|---|
| LangChain/LangGraph 기초 | 미사용 (GaiA로 유사 기능 구현 경험만 있음) | GaiA 대비 LangGraph의 상태(State)/그래프 노드 설계 방식 학습 후 한계 지점에서만 도입 검토 |
| 정식 파서(AST) 도입 | 현재는 정규식/`xml.dom.minidom` 기반 경량 파서로 규칙 변환·well-formed 검사를 처리 중(`converters.py`/`skeleton_gen.py`/`validators.py`) — 멘토 코멘트가 권한 "언어별 경량 파서"보다도 더 가벼운 정규식 수준 | `.BIZUNIT` XML은 lxml, Java(BizUnit)는 javalang/tree-sitter로 교체해 태그 중첩·타입 시그니처를 구조적으로 다뤄야 정확도가 오름(@docs/06-mentor-feedback.md §B "무거운 정적분석기 대신 경량 파서 조합") |
| RAG 구현 | md 정적 삽입 수준, 임베딩 클라이언트(`agents/llm_gateway.py`의 `embed()`)는 준비됐으나 호출부 미구현 | FAISS/Chroma 기반 동적 예시 검색으로 고도화 (파일럿 20~30화면이 코퍼스가 됨, @docs/06-mentor-feedback.md §C) |
| Multi-Agent 시스템 설계 | Analysis/Simulation/Validation 3분업 경험 있음, 이번 프로젝트는 변환기(Translator)와 검증기(Validator) 분리까지만 코드로 구현됨 | ReCodeAgent식 Analyzer/Planner/Translator/Validator 4분업 구조로 재설계 (@docs/06-mentor-feedback.md §B) |
| Vector DB 활용(FAISS/Chroma) | 미사용 | 임베딩 저장/유사도 검색 API, 화면 유형별 few-shot 검색 파이프라인 |
| 프롬프트 엔지니어링 | 화면 유형 구분 없는 단일 고정 instruction 프롬프트 1종만 구현(`chatui/app.py`의 `_port_method`) — 재시도 상한, 구조화 출력 강제는 아직 없음 | 화면 유형별 동적 프롬프트 분기, 구조화 출력 강제, 재시도 상한(2~3회)을 둔 Reflection 프롬프트(@docs/06-mentor-feedback.md §C) |
| API 개발(FastAPI) | 미사용 | 변환 Agent를 서비스화할 때 필요 (현재는 Streamlit 로컬 앱) |
| UI 개발(Streamlit) | 사용 중이며 계속 고도화 중(`chatui/app.py`) — 화면별 탭 구성, 변환 진행 상태 바, 검증/스캔 결과 이슈 목록, 원클릭 복사 등 이미 구현 | 파일럿이 20~30화면으로 늘어날 때의 화면 목록/필터/일괄 조회 UX 설계 |
| 정적 분석 도구 연동(Maven/Gradle) | `pom.xml` 등 빌드 환경 미구축이라 실제 컴파일 검증 없음 — 대신 `validators.py`가 중괄호 균형·계층 간 참조 등 경량 정적 검사만 수행 | Spring 프로젝트 골격(pom.xml) 구축 후 실제 `javac`/Maven 빌드 연동 |

### 3. 기술 스택 선호도
- 오케스트레이션: 사내 GaiA 프레임워크 우선 재사용, 한계 확인 시 LangGraph 검토(@CLAUDE.md 기술 스택)
- LLM 호출: 사내 LLM Gateway(AI Talent Lab, Azure OpenAI 호환) — `agents/llm_gateway.py`, 허용 모델 화이트리스트(`ALLOWED_MODELS`)로 임의 모델명 사용을 코드 레벨에서 차단, 기본 모델은 `gpt-4.1`(`LLM_GATEWAY_DEFAULT_MODEL`)
- 코드 파싱: **목표 스택**은 `.BIZUNIT` XML은 lxml, Java(BizUnit)는 javalang/tree-sitter, `.xjs`의 `transaction()` 추출용 경량 JS AST 파서(babel/tree-sitter)이나, **현재 실제 구현은 `re`(정규식) + `xml.dom.minidom`(well-formed 검사)만으로 v0를 완성한 상태** — PLA047 1건에서는 충분히 동작했지만 화면이 늘어나면 정식 파서로 교체가 필요할 것으로 예상(@docs/06-mentor-feedback.md §B)
- 검색/예시 저장: FAISS 또는 Chroma (파일럿 20~30건이 RAG 코퍼스, 아직 미착수)
- 서비스화: FastAPI (아직 미착수, 현재는 Streamlit 로컬 전용)
- 리뷰/변환 UI: Streamlit(`chatui/app.py`) — 업로드→골격 생성→검증/스캔→LLM 포팅→저장까지 전체 흐름이 탭 기반으로 이미 동작
- 검증: Maven/Gradle(Java 빌드, pom.xml 미구축이라 실제 컴파일 검증은 아직 안 됨) + 차등 테스트 하네스(레거시 nctRid ↔ 신규 REST, 아직 미착수) — 그 전 단계로 `chatui/validators.py`(정적 검증)와 `chatui/quality_scanner.py`(품질/보안 스캔)는 이미 동작하며 결과를 DB에 기록
- DB: 로컬 Oracle(`RPLS_ADM`/`xe`, `.env`) — `agents/db.py`/`agents/db_schema.sql`로 `CONV_FILE`/`CONV_ISSUE` 테이블 연동 이미 검증됨, 원본 SHA-256 해시 기반 캐시 조회(`get_cached_status_bulk`)까지 구현
- 형상관리: Git 브랜치/PR, 계층별(Store/Service/Api/Mapper) 분리 커밋 원칙

### 4. 프로젝트 관심 도메인
- **1순위 도메인**: 제조/유통(SCM) — G-SCM 담당 업무와 직결, 1,416개 실제 화면이라는 규모의 과제
- **2순위 도메인**: 개발자 생산성/DevTools(코드 마이그레이션 자동화 일반)
- **관심 사유**: 실제 운영 중인 레거시 시스템 전환이라 학습 내용을 즉시 실무 검증(빌드 통과율, 사람 수정 라인 비율 등 정량 지표)까지 연결할 수 있음

### 5. 8주(→ 실제 일정은 7주) 목표 설정
- **기술 목표**: GaiA/Multi-Agent 경험을 코드 변환 도메인으로 확장해 **"코드 분석(결정론적 골격 생성) → 규칙 기반 변환/LLM 포팅 → 정적 검증·품질 스캔 → 이슈 피드백"**으로 이어지는 백엔드 전용 End-to-End 변환 파이프라인 PoC를 완성한다. **화면(Nexacro xfdl)은 이번 범위에서 전환하지 않으며, React 화면 전환도 이번 Agent의 산출물이 아니다** — 대상은 어디까지나 Java(BizUnit)/XSQL을 Spring/MyBatis 구조(Controller/Service/Store/Dto/Mapper)로 옮기는 서버 계층뿐이다(@CLAUDE.md 핵심 원칙). 오케스트레이션은 사내 GaiA 프레임워크를 우선 재사용하고, 한계가 확인되는 지점(4-에이전트 분업, 화면 유형별 동적 라우팅 등)에서만 LangGraph 도입을 검토한다. 현재까지 이미 구현된 결정론적 변환기(`chatui/converters.py`, `skeleton_gen.py`), LLM 포팅 모듈(`agents/llm_gateway.py`), 그리고 변환기와 분리된 검증 계층 3종 — 정적 검증기(`validators.py`), 품질/보안 스캐너(`quality_scanner.py`), 화면 간 중복 분석기(`cross_analysis.py`) — 를 기반으로, 8주차까지 **nctRid 매핑 그래프 구축과 차등 테스트 하네스(Phase 1)** 를 이어붙여 "변환됨"이 아니라 "기능이 맞음"까지 검증하는 파이프라인으로 확장하는 것을 기술 목표로 삼는다
- **비즈니스 목표**: 화면 유형별 대표 파일럿(PLA047 포함 20~30건 목표, 현재 1건 진행)을 통해 **화면당 전환 공수 55% 절감**(원 산정 10일 → 평균 4.5일 수준)을 실측 데이터로 검증한다. 90% 이상의 낙관적 절감률은 제안하지 않으며(@CLAUDE.md "하지 말아야 할 것"), 1차 자동변환 커버리지는 "화면 변환율"이 아니라 **결정론적으로 처리 가능한 영역(iBatis→MyBatis, BizUnit→골격, DTO 생성)의 규칙 기반 처리 비율**로 측정한다 — 이미 PLA047 골격/XSQL 변환 및 정적 검증(Api/Store/Dto/계층간참조 PASS)으로 실증됨
- **성장 목표**: Lv.3 Middle AI 개발자로서 "생성 잘하는 것"이 아니라 "결정론/LLM 경계를 올바르게 긋고 검증 가능한 파이프라인을 설계하는 역량"을 증명

---

## 2주차: 문제 정의 및 서비스 기획

### 프로젝트명
G-SCM 차세대 전환 Agent (v2 — 백엔드 전용 범위)

### 배경 및 문제 정의
- **현재 상황(As-Is)**
  - NEXCORE(SK그룹 표준 Spring 기반 BizUnit 프레임워크)가 화면의 단일 진입점 nctRid(예: `RPLA04701`) 요청을 받아 P→F→D BizUnit 순서로 처리하고, D BizUnit이 XSQL(iBatis)로 실제 쿼리를 실행한다
  - 화면 1,416개 전부가 이 구조를 따르지만, 화면-nctRid 매핑이 문자열 규칙과 완전히 일치하지 않아 화면마다 소스를 직접 추적해야 함
  - **v2 범위**: 이번 Agent는 서버(Controller/Service/Store/Mapper)까지만 자동 전환한다. 화면 자체의 재구현은 이 프로젝트의 산출물이 아니다 — nctRid 계약만 그대로 유지해, 화면이 추후 어떤 형태로 다시 만들어지든 지금 만든 API를 그대로 호출할 수 있게 한다
- **Pain Point**
  - 화면당 평균 10일(2주 원 산정) 이상 소요 예상 → 전체 1,416화면 규모로는 감당 불가능한 공수
  - 화면-nctRid 매핑을 코드베이스에서 매번 수작업으로 추적 — 이 과정 자체가 전체 공수의 상당 비중을 차지, **이 프로젝트 최대 리스크**(@docs/06-mentor-feedback.md §1)
  - 반복 패턴(P/F/D/XSQL 4종 세트)임에도 미자동화 → 화면 수만큼 동일 작업 반복
  - 개발자별 이원화로 코드 품질/구조 편차 발생
  - 원본 소스 자체의 결함(예: PLA047의 `FPLA047.java` 컴파일 에러, `.bizunit` XML 선언 손상)이 섞여 있어 "그대로 옮기면 되는" 화면과 "업무 규칙만 추출해야 하는" 화면이 혼재
- **기회 요인**
  - PU/FU/DU/XSQL 계층·네이밍 컨벤션이 강제되어 있어 파싱/템플릿화에 유리 — 멘토 코멘트: "NEXCORE 조합은 AlphaTrans/ReCodeAgent가 가정하는 것보다 자동화에 유리한 편. 계층과 네이밍이 강제되어 있어 파싱이 된다"(@docs/06-mentor-feedback.md 서두)
  - iBatis→MyBatis 문법 변환은 결정론적 규칙만으로 처리 가능
  - F/D BizUnit의 업무 로직·SQL은 Nexacro와 무관 — 새로 설계할 필요 없이 그대로 포팅
  - 단일 진입점(nctRid) + 고정 응답 포맷 구조 덕분에 차등 테스트(differential testing)가 깔끔하게 성립(@docs/06-mentor-feedback.md §3)

### 목표 사용자(Target User)
- **G-SCM 전환 프로젝트 투입 개발자**(사내·외주) — 화면별로 P/F/D/XSQL 세트를 업로드해 변환 결과(골격+포팅 코드)를 받고, 검증 이슈를 확인한 뒤 승인/수정하는 주 사용자
- **PL/PM** — 화면별 진행 상태(`/tracking/conversion-verification.csv`, `CONV_FILE`/`CONV_ISSUE` DB)를 보고 전체 공수·리스크를 파악
- **QA 담당자** — 차등 테스트 결과(레거시 vs 신규 API diff)로 기능적 정확성을 검토

### 프로젝트 목표
- **정성적 목표**
  - 목표 1: nctRid↔BizUnit↔XSQL 매핑을 사람이 매번 코드베이스를 헤매며 추적하지 않도록 인덱스화(선행 정적 분석, @docs/06-mentor-feedback.md §1·§J 1순위)
  - 목표 2: 결정론적으로 풀리는 변환(문법 치환, 골격 생성)을 100% 규칙 기반으로 자동화해 LLM은 꼭 필요한 영역(F BizUnit 로직 포팅)에만 투입(§2)
  - 목표 3: 변환기(Translator)와 검증기(Validator)를 분리 설계해 향후 다른 SK 계열 전환 프로젝트에도 검증 자산을 재사용 가능하게 함(§D)
  - 목표 4: 공통 응답/예외 처리·메시지 코드 규약을 사람이 먼저 확정해, 화면마다 에이전트가 제각각 구현하는 "개발자별 이원화"가 재현되지 않게 함(§2 "절대 자동화하지 말 것")
- **정량적 목표(KPI)**

| 성과 지표 | 목표 수치 | 측정 방법 | 현재 수준 |
|---|---|---|---|
| 화면당 평균 전환 소요시간(이번 8주 PoC 목표) | 10일 → 평균 4.5일 수준(**55% 절감**) | 파일럿 20~30건 실측 | 약 10일(전면 수작업 시 산정치) |
| 1차 자동변환 커버리지(규칙 기반 골격+iBatis→MyBatis) | 0% → 결정론적 변환 가능 영역 100% 규칙 기반 처리 | `chatui/skeleton_gen.py`/`chatui/converters.py` 산출물 중 규칙 기반으로 완결된 비율 | PLA047 기준: Api/Store/Dto 골격, XSQL 규칙 변환 검증됨(S001) |
| 정적 검증(빌드 전 단계) 통과율 | 화면별 Api/Store/Dto/계층간참조 PASS | `chatui/validators.py` → `CONV_FILE.BUILD_CHECK` | PLA047: Api/Store/Dto/계층간참조 PASS, Service/XSQL은 원본 결함으로 의도된 FAIL |
| 품질/보안 스캔 이슈 검출 | 화면별 이슈 전량 `CONV_ISSUE`에 기록·집계 | `chatui/quality_scanner.py` → `CONV_ISSUE` | PLA047 실측: `${...}` SQL 인젝션 후보 339건, 문자열 연결 SQL 13건, 원본 버그(FIXME) 31건 |
| 사람 수정 라인 비율(핵심 대리 지표, @docs/06-mentor-feedback.md §H) | 낮을수록 좋음, 파일럿 후 기준치 설정 | `/tracking/conversion-verification.csv` 화면별 기록 | 아직 코드 생성 전 단계라 대부분 N/A(미생성) |
| 매핑 그래프 자동 추출 성공률 | 80~90%(나머지 10~20%는 사람이 보완, 멘토 경험치, §1) | 화면↔nctRid↔BizUnit↔XSQL 그래프 구축 후 실패 목록 비율 | 미착수(Phase 1) |

> 55%는 이번 8주 PoC에서 실측·검증하려는 이 프로젝트 자체의 목표치다. 멘토 코멘트(§4)의 65~70%는 파일럿 20~30건을 거쳐 도구·공통 컴포넌트까지 자산화된 이후, 프로젝트 전체 규모(1,416화면)에 적용할 때의 장기 권장치로 별도 취급한다 — 8주 안에 65~70%를 약속하지 않는다.

### 핵심 기능 정의
멘토 코멘트 §J "적용 우선순위"(매핑 그래프 → 차등 테스트 → 공통 규약/KB → 결정론적 변환기 → 파일럿 → LLM 파이프라인 → Reflection) 순서를 그대로 따른다. 구현 상태는 실제 코드 기준으로 표시했다.

1. **nctRid 매핑 인덱스 구축기** *(Phase 1, 미착수 — 최우선)*: `.xjs`의 `transaction()` 호출부 → nctRid 추출, NEXCORE 설정 → nctRid→P BizUnit 매핑, JavaParser로 P→F→D 콜그래프 추적, D BizUnit→XSQL namespace/queryId 매핑을 이어 화면↔API↔SQL 전체 그래프 구축
2. **차등 테스트 하네스** *(Phase 1, 미착수 — 변환기보다 먼저)*: 동일 입력을 레거시 nctRid와 신규 REST API에 호출해 응답 diff로 검증
3. **공통 응답/예외 처리 규약 + NEXCORE 관용구 KB** *(Phase 2, 미착수)*: 공통 팝업 호출·코드도우미·메시지 코드 표준화 등을 사람이 먼저 확정 — 에이전트가 화면마다 제각각 만들지 않도록 강제 컨텍스트로 주입
4. **결정론적 변환기** *(구현됨)*: iBatis→MyBatis 문법 변환(`chatui/converters.py`), BizUnit 메서드 시그니처→Controller/Service/Store 골격 생성, `.BIZUNIT`(또는 역추출한 필드)→DTO 생성(`chatui/skeleton_gen.py`) — PLA047로 검증됨
5. **검증기 3종(변환기와 분리된 모듈)** *(구현됨)*: 정적 검증기(`validators.py` — 중괄호 균형, 미완료 포팅 스텁, 계층 간 호출 대상 존재, Mapper.xml well-formed), 품질/보안 스캐너(`quality_scanner.py` — SQL 인젝션 후보, 하드코딩 자격증명, 잔존 NEXCORE 의존, 원본 버그 집계), 화면 간 중복 분석기(`cross_analysis.py` — 화면 간 동일 Service/Store/Mapper 로직 탐지)
6. **LLM 포팅 모듈** *(구현됨, 사람이 명시적으로 트리거)*: F BizUnit의 계산·분기 로직을 NEXCORE 의존만 제거하고 Spring Service 메서드로 옮기는 메서드 단위 LLM 호출(`agents/llm_gateway.py` + `chatui/app.py`의 포팅 탭). 원본 결함은 고치지 않고 `// FIXME(원본 버그)`로 보존
7. **파일럿 20~30화면** *(Phase 3, 진행 중 — PLA047 1건)*: 유형별 대표 화면으로 변환 레시피·실측 공수를 확보해 RAG 코퍼스·벤치마크로 자산화

### 기대 효과
- **근거**: F/D BizUnit의 업무 로직·SQL(대부분)은 그대로 포팅되고, 신규로 개발하는 부분은 NEXCORE 프레임워크 의존 제거 + REST Controller/DTO 계층에 집중되므로 절감폭이 큼
- 업무 효율화: 이번 8주 PoC 목표는 화면당 평균 10일 대비 **55% 단축**(평균 약 4.5일). 90% 이상은 약속하지 않으며, 프로젝트 전체 규모로 확장될 때의 멘토 권장 목표(65~70%, 화면 유형별 차등)는 파일럿 확대 이후 별도로 재산정한다
- 품질 향상: 결정론적 변환기가 화면마다 동일한 규칙을 적용해 개발자 간 코드 편차 감소, 검증기 3종이 이슈를 빠짐없이 `CONV_ISSUE`에 기록해 리뷰 사각지대를 줄임
- 비용 절감: 파일럿 실측 이후 확정(도구 자체 개발 공수·공통 컴포넌트 구축 공수를 ROI 계산에 반드시 포함)

### 범위 및 제약사항
- **In Scope**: `dev-rp-online/src/java/gscm/` 이하 서버 소스(P/F/D BizUnit, `.BIZUNIT`, XSQL) → Controller/Service/Store/Dto/Mapper.xml 자동 전환, 하드코딩 메시지 코드 → `errors*.properties` 외부화, nctRid 1:1 매핑을 유지하는 REST API 설계
- **Out of Scope**: 화면 자체의 재구현(디자인·프레임워크 불문 — 별도 트랙), DB 스키마 변경, `DCOT998`류 화면에 안 묶인 공통/배치 BizUnit, 무인 자동 커밋/배포(사람 리뷰 필수)
- **제약사항**
  - nctRid 매핑 자동 추출 파서 선행 필요(Phase 1 최우선)
  - `.BIZUNIT` XML 스키마가 비어있는 경우가 많아 코드 실사용값 역추출 필요
  - P BizUnit이 순수 진입점인지 화면별 검증 로직이 섞여있는지 화면별 확인 필요(PLA047 1건은 순수 위임 확인, 표본 확대 필요)
  - 소스코드 외부 LLM 전송에 대한 사내 보안 정책 확인 필요
  - DB 접속정보·LLM Gateway API 키는 `.env`에만 두고 어떤 문서/코드에도 커밋하지 않음

### 2주차 부록 — 멘토 요구사항 및 추가 요구사항 정리
(@docs/06-mentor-feedback.md 전문 분석, 이번 프로젝트 문서/코드에 실제로 반영된 지점을 함께 표시. 멘토 코멘트 원문은 UI/React 트랙까지 포괄하지만, 이 프로젝트(v2)는 백엔드 전용이므로 "반영된 지점" 열은 백엔드에 적용 가능한 부분만 서술했다)

| # | 멘토 요구사항 | 이 프로젝트에 반영된 지점 | 상태 |
|---|---|---|---|
| §1 | nctRid 매핑 인덱스를 가장 먼저 구축 — LLM이 아니라 선행 정적 분석 과제로 분리. `.xjs`→transaction()→svcID, NEXCORE 설정→P BizUnit, JavaParser 콜그래프, D BizUnit→XSQL namespace 4단계를 이어 그래프 DB화. 자동 추출 실패분(경험상 10~20%)만 사람이 보완 | @docs/03-kickoff-plan.md Phase 1 전체가 이 요구사항 그대로 구성됨 | 계획 수립 완료, 실행 미착수 |
| §2 | 결정론적 변환(iBatis→MyBatis, BizUnit→Controller 골격 등)에는 LLM을 쓰지 않고, LLM은 실제 계산·분기 로직 포팅 등 기계적 치환이 안 되는 영역에만 투입. 공통 응답/예외/그리드 등 공통 모듈은 사람이 먼저 확정 | @CLAUDE.md 핵심 원칙 + @docs/02-architecture.md "결정론적/LLM 경계" 표로 명문화, `chatui/converters.py`·`chatui/skeleton_gen.py`(규칙 기반) vs `agents/llm_gateway.py`(LLM 포팅) 코드 분리로 실제 구현. 원문의 xfdl/AG-Grid 관련 항목은 v2 범위(UI 미전환)라 제외 | 반영 완료(설계+코드) |
| §3 | "변환된다"≠"맞다" — 차등 테스트(differential testing)를 파일럿보다 먼저 구축, 프론트는 사람 리뷰 전제로 공수 산정 | @docs/02-architecture.md "검증 전략" 섹션, @docs/03-kickoff-plan.md Phase 1에 하네스 구축 명시 | 계획만 있음, 구축 미착수(Phase 1 최우선 과제) |
| §4 | 공수 추정 현실화 — 화면 유형별 차등(40~50%/30~40%/15~20%), 평균 3일·65~70% 절감으로 조정, 90% 이상 약속 금지 | @docs/01-project-plan.md "v2 KPI 조정" 섹션에 표 그대로 반영, @CLAUDE.md "하지 말아야 할 것"에 "90% 이상 절감 약속 금지" 명문화 | 반영 완료. 단, 이번 8주 PoC 자체 목표는 이보다 보수적인 **55% 절감**으로 별도 설정(위 KPI 표 참고) — 65~70%는 파일럿 확대 후 전체 프로젝트 목표로 재검토 |
| §5 | 1,416개 전체가 아니라 구조적 클러스터링 후 유형별 대표 20~30화면 파일럿. 목표는 "화면이 돌아간다"가 아니라 "유형별 변환 레시피 + 실측 공수 확보" | @docs/03-kickoff-plan.md Phase 3 | 계획만 있음, 파일럿 1건(PLA047) 진행 중 |
| §6 | Dataset 상태 모델(rowState) 의미 손실, 동기→비동기 전환 리스크 | @docs/02-architecture.md "리스크" 섹션에서 v2 범위 재해석(백엔드 전용이라 직접 영향은 적으나 화면이 다시 만들어질 차기 트랙을 위해 API 설계 시점에 고려) | 반영 완료(문서화, 실제 결정은 차기 화면 트랙에서 — 이번 프로젝트 범위 밖) |
| §A | 5-fragment 분해(.xfdl/.xjs/Dataset/BizUnit/XSQL), 콜그래프 역순 번역(XSQL→D→F→P→API), 스켈레톤 우선, 실패분을 정상 산출물로 취급 | @CLAUDE.md 핵심 원칙("화면 하나를 통째로 넣지 말고 5개 fragment로", "콜그래프 역순", "스켈레톤 먼저") — v2는 UI fragment 제외, `.BIZUNIT`/P/F/D/XSQL 5종으로 재정의 | 반영 완료(설계), 실패 리포트 자동 생성은 미착수 |
| §B | ReCodeAgent 4-에이전트 분업(Analyzer/Planner/Translator/Validator), 경량 파서 조합, Planner가 계획을 파일로 고정 | @docs/03-kickoff-plan.md Phase 4에 4역할 분리 명시. `conversion-plan.json` 산출 항목이 Phase 2에 있음(미착수) | 계획만 있음, 4-에이전트 분업·plan.json 모두 미착수 |
| §C | RAG few-shot(파일럿 결과물이 코퍼스), 화면 유형별 동적 프롬프트, Reflection 재시도 상한 2~3회 | @CLAUDE.md 기술 스택에 FAISS/Chroma 명시, @docs/03-kickoff-plan.md Phase 4~5 | 미착수 |
| §D | 검증기를 변환기와 독립 모듈로 분리, 의미분석→테스트작성→실행→수리→판정 역할 분리 | @CLAUDE.md 핵심 원칙("변환기와 검증기는 분리한다"), `chatui/validators.py`가 `chatui/converters.py`/`skeleton_gen.py`와 완전히 별도 모듈로 이미 구현됨 | 반영 완료(설계+코드), 수리(Fix) 에이전트는 미착수 |
| §E | plan.md+tasks.json 계획 영속화, 작업 유형별 전문 실행기 라우팅, 관용구 KB, 작업 단위 커밋, 결정론적 도구와 결합 | @CLAUDE.md "작업 단위로 커밋한다"(Store/Service/Api/Mapper 계층별 커밋), `conversion-plan.json`은 Phase 2 항목 | 커밋 규칙 반영 완료, plan.json/관용구 KB 미착수 |
| §F | Refactor(구조보존) vs Reimagine(재설계) 이원화, 단순화면은 Refactor 80%, 복합/결함화면은 Reimagine 20% | @CLAUDE.md 핵심 원칙에 명문화, PLA047의 `FPLA047` 로직처럼 원본 자체 결함 있는 케이스를 Reimagine 후보 예시로 실제 사용 중(@docs/08-conversion-verification.md 트랙 컬럼) | 반영 완료(설계+트래킹 테이블 컬럼) |
| §G | 트랜스파일러 먼저, LLM은 나머지 / 컴파일러·타입체커 피드백 순환 / Strangler Fig로 레거시·신규 공존 | @CLAUDE.md 핵심 원칙("결정론적으로 가능한 변환은 LLM에 맡기지 않는다", "Strangler Fig") | 반영 완료 |
| §H | 화면 20~30개 내부 벤치마크, 컴파일 통과율/렌더 성공률/API diff 일치율/사람 수정 라인 비율 측정 | @docs/08-conversion-verification.md 검증 테이블에 "사람 수정 라인 비율" 컬럼이 이미 설계됨(파일럿 이후 KPI 실측용) | 반영 완료(설계), 실측 데이터는 파일럿 확대 후 |
| §I | TransCoder류 학습 기반 변환·완전 자율 에이전트·범용 다국어 프레임워크는 의도적으로 배제 | @CLAUDE.md "하지 말아야 할 것"에 동일하게 명문화(학습 모델 신규 훈련 금지, SWE-agent류 자율 탐색 금지, 범용 다국어 전환기 설계 금지) | 반영 완료 |
| §J | 적용 우선순위: ①매핑 그래프 ②차등 테스트 ③공통 컴포넌트/규약 ④결정론적 변환기 ⑤파일럿 ⑥LLM 파이프라인 ⑦Reflection — 1~4번이 성패의 80% | @CLAUDE.md "지금 해야 할 일" 섹션과 @docs/03-kickoff-plan.md Phase 순서가 그대로 이 우선순위를 따름 | 순서 반영 완료, 실행은 ④(결정론적 변환기 v0)가 가장 앞서 있고 ①·②는 아직 착수 전 — **다음 착수 순서는 이 우선순위 역전을 바로잡아 Phase 1(매핑 그래프+차등 테스트)부터 진행하는 것이 필요** |

**추가 요구사항(문서에서 확인된 것)**: DB 접속정보·LLM Gateway API 키 등 자격증명은 어떤 파일에도 커밋하지 않는다(@CLAUDE.md "로컬 개발 환경"), 결과물은 반드시 빌드/린트 통과 + 사람 리뷰 후에만 완료로 인정한다(@CLAUDE.md 핵심 원칙), 화면 단위 변환 없이 여러 화면을 한 번에 일괄 처리하는 스크립트를 파일럿 검증 전에 만들지 않는다(@CLAUDE.md "하지 말아야 할 것").

---

## 3주차: 시나리오 수립

### 핵심 사용자 시나리오

**시나리오 1: 단순조회/CRUD 화면 Refactor 변환**

- **ID**: SC-001
- **상황**: 개발자가 단순조회 또는 CRUD 성격의 화면(P/F/D BizUnit + `.BIZUNIT` + XSQL 세트가 정상적으로 파싱/컴파일되는 경우)을 챗팅 UI에 업로드해 1:1 구조보존 변환을 받는 상황
- **목표**: 사람이 손대는 라인을 최소화하면서 Controller/Service/Store/Dto/Mapper.xml 골격과 규칙 기반 변환 결과를 빠르게 확보
- **사전 조건**: 대상 화면의 P/F/D `.java`, `.bizunit`, D BizUnit용 `.xsql` 파일이 확보되어 있고 XML/Java 문법상 파싱 가능한 상태
- **상세 흐름**

| 단계 | 사용자 행동 | 시스템 동작 | 비고 |
|---|---|---|---|
| 1 | P/F/D `.java` + `.bizunit` + `.xsql` 업로드, 화면ID 입력(예: `PLA047`) | 파일 종류 자동 식별, 원본 해시 계산 후 이전 변환 이력 조회(`get_cached_status_bulk`) | 이전에 PASS했고 원본 변경 없으면 "이전 변환 PASS" 배지 표시 |
| 2 | "1단계: 골격 생성" 실행 | `skeleton_gen.generate_skeletons()`로 Api/Service/Store/Dto 골격 생성, `converters.convert_xsql_fragment()`로 iBatis→MyBatis 변환 (전부 규칙 기반, LLM 미호출) | 트랙(Refactor)에 대응 |
| 3 | 결과 확인(정적 검증 자동 실행) | `validators.validate_screen()`으로 계층 간 참조·Mapper well-formed 검사, `quality_scanner.run_review()`로 취약점/원본버그 스캔, 결과를 `CONV_FILE`/`CONV_ISSUE`에 저장 | PASS/FAIL 배지로 표시 |
| 4 | 이슈 없으면 리뷰 후 "저장" | `pilot/{screen}/`에 파일 저장, 자동 커밋은 하지 않음(사람 승인 필요) | CLAUDE.md 원칙 준수 |

- **입력 예시**: `PPLA047.java`, `FPLA047.java`, `DPLA047.java`, `PPLA047.bizunit`, `FPLA047.bizunit`, `DPLA047.bizunit`, `DPLA047.xsql`
- **기대 출력**: `Pla047Api.java`, `Pla047Service.java`(Service 본문은 TODO 스텁), `Pla047Store.java`, `Pla047Dto.java`, `Pla047Mapper.xml`, 정적 검증 리포트(PASS/FAIL별 이슈 목록)
- **성공 기준**
  - 기준 1: Api/Store/Dto/계층간참조 정적 검증 PASS
  - 기준 2: iBatis→MyBatis 변환 후 Mapper.xml이 well-formed XML

**시나리오 2: 복합/원본결함 화면 Reimagine 변환 + LLM 포팅**

- **ID**: SC-002
- **상황**: F BizUnit 내부 로직이 복잡하거나(계산·분기 다수) 원본 자체에 컴파일 에러 등 결함이 있는 화면(PLA047의 `FPLA047.java`가 실제 사례)을 변환하는 상황
- **목표**: 원본 로직을 재설계하지 않고 그대로 포팅하되, NEXCORE 프레임워크 의존만 제거하고 원본 결함은 `FIXME` 주석으로 보존
- **사전 조건**: 1단계 골격 생성이 끝나 있고, Service 파일에 `PORT_START`/`UnsupportedOperationException` 스텁이 존재
- **상세 흐름**

| 단계 | 사용자 행동 | 시스템 동작 | 비고 |
|---|---|---|---|
| 1 | "포팅" 탭에서 F 메서드 선택 후 LLM 포팅 실행 | `agents.llm_gateway.chat()`으로 메서드 단위 단발 프롬프트 호출(“로직은 하나도 빠짐없이 유지, NEXCORE 의존만 제거, 원본 결함은 고치지 말고 FIXME로 표시”) | `chatui/app.py`의 `_port_method()` |
| 2 | 포팅 결과 자동 반영 | `splice_ported_method()`로 Service 파일의 해당 스텁 교체, 즉시 재검증(`validate_screen`)·재스캔(`run_review`) 실행 | 실험적 기능임을 UI에 경고 문구로 명시 |
| 3 | 사람이 원본과 줄 단위 대조 | 사람이 diff를 직접 검토(자동 완료 처리 없음) | 500줄 이상 메서드는 부분 누락 위험 — 대조 필수 |
| 4 | 승인 또는 재포팅(재시도) | 승인 시 저장, 문제 있으면 프롬프트/메서드 단위로 재시도 | 재시도 상한은 아직 코드로 강제되지 않음(Phase 5 항목) |

- **입력 예시**: `FPLA047.java`의 특정 메서드 본문(예: 대시보드 체크 여부 판단 로직)
- **기대 출력**: NEXCORE API(`IDataSet`/`lookupDataUnit` 등) 호출이 `store.dXXXX(...)` 형태로 치환된 Service 메서드, 원본 컴파일 에러 구간은 `// FIXME(원본 버그): ...` 주석 포함
- **성공 기준**
  - 기준 1: 원본의 계산·분기 로직이 하나도 누락되지 않음(사람 대조로 확인)
  - 기준 2: 포팅 후 정적 검증에서 미완료 스텁(`PORT_START` 등)이 남아있지 않음

**시나리오 3: 차등 테스트를 통한 변환 정확성 검증** *(현재 하네스 미구축 — 설계 시나리오)*

- **ID**: SC-003
- **상황**: 골격 생성+LLM 포팅이 끝난 화면의 REST API가 레거시 nctRid 응답과 실제로 동일한 결과를 내는지 확인해야 하는 상황
- **목표**: "문법상 변환됨"이 아니라 "기능적으로 맞음"을 기계적으로 검증
- **사전 조건**: 로컬 Oracle DB에 레거시 nctRid 경로와 신규 REST API 경로가 모두 붙어 있음 (Phase 1, 아직 미착수)
- **상세 흐름**

| 단계 | 사용자 행동 | 시스템 동작 | 비고 |
|---|---|---|---|
| 1 | 동일 입력 파라미터로 검증 실행 요청 | 레거시 nctRid 호출 + 신규 REST API 호출을 병렬 실행 | 아직 미구현 |
| 2 | - | 두 응답(IDataSet 직렬화 vs JSON)을 정규화 후 diff | 아직 미구현 |
| 3 | 결과 확인 | 불일치 시 `CONV_ISSUE`에 기록, 일치 시 차등 테스트 PASS로 `CONV_FILE` 갱신 | @docs/08-conversion-verification.md "차등 테스트 검증" 컬럼과 연결 |

- **입력 예시**: `RPLA04701` 호출 파라미터 세트
- **기대 출력**: 정규화된 diff 결과(일치/불일치 필드 목록)
- **성공 기준**
  - 기준 1: 핵심 필드 100% 일치
  - 기준 2: 불일치 발생 시 원인(필드명/타입/null 처리 등)이 리포트에 특정됨

### 시나리오 우선순위 매트릭스

| 시나리오 | 비즈니스 가치 | 구현 난이도 | PoC 포함 |
|---|---|---|---|
| SC-001 (Refactor 변환) | 높음 (전체 화면의 40~50% 비중) | 낮음~중간 | 네 (이미 골격 구현됨) |
| SC-002 (Reimagine + LLM 포팅) | 높음 (리스크가 가장 큰 15~20% 화면을 커버) | 높음 | 네 (LLM 포팅 탭 구현됨, 검증은 사람 리뷰 의존) |
| SC-003 (차등 테스트) | 매우 높음 (멘토 코멘트 §3, §J — 검증 없이는 신뢰 불가) | 높음 (DB 이중 연동+응답 정규화 필요) | 아니오 (Phase 1로 별도 착수 필요, 이번 PoC 범위 밖) |

---

## 4주차: 상세 설계 및 개발 환경 구축

### Agent 페르소나 및 시스템 프롬프트(Identity)

| 항목 | 정의 내용 |
|---|---|
| **Agent 이름** | G-SCM 화면 전환 코파일럿 (내부 명칭, `chatui/app.py` 업로드→변환 챗팅 UI) |
| **주요 역할** | 화면 1개 분량의 P/F/D BizUnit + `.BIZUNIT` + XSQL을 입력받아, 결정론적 규칙으로 Controller/Service/Store/Dto/Mapper.xml 골격을 생성하고, 요청 시 F BizUnit의 업무 로직을 Service 메서드로 LLM 포팅한다 |
| **핵심 목표** | 원본 업무 로직(계산·분기·SQL)을 재설계 없이 정확히 보존하면서 NEXCORE 프레임워크 의존만 Spring/MyBatis 방식으로 치환하는 것 — "새로운 로직을 잘 만드는 것"이 목표가 아니다 |
| **톤앤매너** | 확정적으로 단정하지 않는다. 원본 결함이나 스키마 불명확 지점은 추측 대신 TODO/WARNING/FIXME로 명시하고 사람 확인을 요구한다 |
| **제약 사항** | 결정론적으로 풀리는 변환(문법 치환, 시그니처 매핑)에 LLM을 쓰지 않는다 / SQL·업무 규칙을 새로 설계하지 않는다 / 원본 컴파일 에러를 임의로 고치지 않는다(FIXME로만 표시) / 사람 승인 없이 자동 커밋·배포하지 않는다 |

### 워크플로우 및 오케스트레이션(Workflow & Logic)

**2.1 처리 로직**
- **Step 1 (Input Analysis)**: 업로드된 파일명·확장자로 fragment 종류(P/F/D `.java`, `.bizunit`, `.xsql`)를 식별하고, 화면ID(prefix)를 추출한다. 원본 SHA-256 해시로 이전 변환 이력을 조회해 재작업 여부를 사람에게 먼저 알려준다(`agents/db.py`의 `get_cached_status_bulk`)
- **Step 2 (Tool Selection)**: fragment 종류와 완결 여부에 따라 분기한다 — `.xsql`은 항상 규칙 기반 변환기(`converters.py`)로, BizUnit 시그니처는 항상 골격 생성기(`skeleton_gen.py`)로 처리한다. F BizUnit의 메서드 본문처럼 기계적 치환이 안 되는 영역만 사람이 명시적으로 "포팅" 버튼을 눌러야 LLM Gateway를 호출한다 — 자동으로 LLM을 트리거하지 않는다
- **Step 3 (Execution & Response)**: 골격/변환/포팅 결과를 즉시 정적 검증(`validators.py`)과 품질 스캔(`quality_scanner.py`)에 통과시켜 이슈를 화면에 노출하고, "저장" 버튼을 눌러야만 `pilot/{screen}/`에 파일이 생성된다(자동 커밋 없음)

**2.2 상태 관리**
- 화면 단위 Streamlit `session_state`로 관리: `skeleton_files`(생성된 파일 딕셔너리), `validation_results`, `review_findings`, `ported_methods_{screen_id}`(포팅 완료된 메서드 집합)
- 화면을 새로 업로드하면 세션 상태가 해당 화면ID로 재초기화됨 — 여러 화면을 한 세션에서 뒤섞어 처리하지 않는다
- **LangGraph 등 그래프 기반 오케스트레이션은 아직 도입하지 않았다.** 현재는 Streamlit의 조건부 렌더링 + 명시적 버튼 트리거로 스텝을 구성한 결정론적 파이프라인이며, GaiA/LangGraph로의 편입은 4-에이전트(Analyzer/Planner/Translator/Validator, @docs/06-mentor-feedback.md §B) 분업이 필요해지는 Phase 4에서 재검토한다

### 도구(Tools) 및 함수 명세(Capability)

| 도구명(Function Name) | 기능 설명 | 입력 파라미터 | 출력 데이터 |
|---|---|---|---|
| `converters.convert_xsql_fragment` | iBatis XSQL → MyBatis Mapper.xml 변환(규칙 기반). `#var#`→`#{var}`, `$var$`→`${var}`, `isEqual/isNotEqual`→`<if>`, `isNotEmpty+iterate`→`<if>+<foreach>` | `xsql_text: str` | `ConversionResult`(mybatis_xml, issues 목록) |
| `skeleton_gen.generate_skeletons` | P/F/D BizUnit 메서드 시그니처 → Controller/Service/Store 골격 생성. P→F 위임 호출을 본문에서 찾아 Api→Service 연결까지 매핑 | P/F/D java 소스, 화면ID, 패키지 정보 | `SkeletonResult`(files 딕셔너리, issues) |
| `skeleton_gen.extract_dto_fields` / `generate_dto` | `.BIZUNIT` `<fields/>`가 비어있을 때 `getField`/`putRecordset` 실사용값에서 DTO 필드 역추출 | bizunit XML, P/F java 소스 | DTO 필드 목록(비어있으면 TODO+WARNING) |
| `agents.llm_gateway.chat` | F BizUnit 메서드 본문을 Spring Service 메서드로 LLM 포팅(단발 instruction 프롬프트) | `messages: list[dict]`, `model: str`(허용 목록 화이트리스트 검사) | 포팅된 Java 메서드 코드 문자열 |
| `agents.llm_gateway.embed` | 텍스트를 임베딩 벡터로 변환 (RAG 코퍼스 구축용, 현재 호출부 미구현) | `texts: list[str]`, `model: str` | 임베딩 벡터 목록 |
| `validators.validate_screen` | 화면 단위 정적 검증 — 중괄호 균형, 미완료 포팅 스텁, 계층 간 호출 대상 존재, Mapper.xml well-formed | `files: dict[str, str]`, `prefix: str` | `list[ValidationResult]`(PASS/FAIL + issues) |
| `quality_scanner.run_review` | 규칙 기반 품질/보안 스캔 — `${...}` SQL 인젝션 후보, 문자열 연결 SQL, 하드코딩 자격증명(BLOCKER), 잔존 NEXCORE 의존, 원본 버그 집계 | `files: dict[str, str]`, `prefix: str` | `dict[str, list[ConversionIssue]]` |
| `quality_scanner.llm_review` | (선택) LLM 기반 코드 리뷰 — 코드 미수정, 세션 내 표시만, DB 미저장 | `java_text: str` | 리뷰 텍스트 |
| `cross_analysis.analyze_pilot_folder` | `pilot/` 전체를 훑어 화면 간 동일 Service/Store 메서드·Mapper SQL 중복 탐지 | `pilot_root: Path` | `CrossAnalysisResult`(중복 그룹 목록) |
| `db.upsert_conv_file` / `db.record_issues` | 변환/검증 결과를 로컬 Oracle `CONV_FILE`/`CONV_ISSUE` 테이블에 기록 | 화면ID, 계층, 파일명, 해시, BUILD_CHECK 등 | DB 레코드 |
| `db.get_cached_status_bulk` | 화면 목록의 이전 변환 상태를 원본 해시 기준으로 일괄 조회(캐시 힌트, 자동 스킵은 아님) | `screen_ids: list[str]` | `dict[(screen, layer, file), status]` |

### 지식 베이스 및 메모리 전략(Context & Memory)

**4.1 RAG(검색 증강 생성) 전략** — *현재 미구현, Phase 4~5 계획*
- **참조 데이터 소스(예정)**: 파일럿에서 검증 완료된 화면들(`pilot/{screen}/`)의 변환 결과, 향후 축적될 NEXCORE 관용구 KB(공통 팝업 호출, 코드도우미, 파일업로드 패턴)
- **청킹 방식(예정)**: BizUnit 메서드 단위(자연스러운 경계 — 현재 `extract_method_bodies`가 이미 메서드 단위로 쪼개고 있어 청킹 단위로 그대로 재사용 가능)
- **임베딩 모델**: `text-embedding-3-small`(기본) / `text-embedding-3-large`(고정밀 필요 시) — `agents/llm_gateway.py`에 이미 화이트리스트로 등록됨, 호출부만 미구현
- **Vector DB**: FAISS 또는 Chroma (@CLAUDE.md 기술 스택), 파일럿 20~30건이 최초 코퍼스가 됨
- **현재 상태**: RAG 없이 단일 고정 프롬프트로 LLM 포팅을 수행 중(`chatui/app.py`의 `_port_method`) — 화면 유형별 동적 프롬프트 분기, few-shot 주입은 아직 적용 안 됨

**4.2 대화 메모리(Conversation History)**
- **메모리 유형**: 자유 대화형 챗봇이 아니라 화면 단위 세션 상태(윈도우 버퍼에 가까움) — 이전 화면의 대화/변환 이력을 다음 화면 처리에 자동으로 이어주지 않는다
- **저장 전략**: 브라우저(Streamlit) 세션이 유지되는 동안만 `session_state`에 보관, 화면을 새로 업로드하면 초기화. 영속 기록은 DB(`CONV_FILE`/`CONV_ISSUE`)와 `pilot/` 산출물로만 남긴다 — "대화"가 아니라 "산출물"이 진실의 원천(source of truth)

### 핵심 에이전트 기술 스택

| 구분 | 선정 전략/기술 | 선정 사유(논리적 근거) |
|---|---|---|
| **LLM Model** | `gpt-4.1`(기본, `LLM_GATEWAY_DEFAULT_MODEL`) — 필요 시 `gpt-4.1-mini`/`gpt-4o`/`gpt-5` 계열로 교체 가능(허용 목록 내) | 사내 LLM Gateway가 지원하는 모델로 제한, 결정론적 변환에는 아예 LLM을 호출하지 않아 비용을 최소화 |
| **Agent Framework** | 현재: 규칙 기반 파이프라인 + Streamlit 직접 오케스트레이션 (LangGraph/GaiA 미도입) | 화면 변환은 탐색이 아니라 고정된 스텝(골격→검증→포팅→재검증)이라 자유 탐색형 프레임워크보다 명시적 파이프라인이 안전(@docs/06-mentor-feedback.md §I "완전 자율 에이전트는 이 프로젝트엔 안 맞음") |
| **Prompt Strategy** | Instruction Prompting, 메서드 단위 단발 호출(현재) → 화면 유형별 동적 프롬프트 + few-shot(예정, §C) | 지금은 화면 1건(PLA047)만 검증되어 프롬프트를 유형별로 분기할 근거(코퍼스)가 아직 부족 — 파일럿이 늘어나면 도입 |
| **Output Parsing** | 코드 펜스 제거 후 원문 Java 코드 문자열 그대로 파싱(`_strip_code_fence`), JSON Mode/Structured Output 미사용 | 포팅 결과가 코드 블록 그 자체이며, 구조화가 필요한 부분(이슈 목록 등)은 이미 결정론적 스캐너·검증기가 타입이 명확한 dataclass(`ConversionIssue`, `ValidationResult`)로 반환하므로 LLM에 JSON 강제를 요구할 필요가 적음 |
| **Monitoring** | 현재: 없음(콘솔/Streamlit 화면 출력 수준) → 예정: LangSmith/Langfuse 또는 자체 DB 로깅 확장 | 토큰 사용량·포팅 재시도 추적이 Phase 5(Reflection·수리 루프) 도입 시 필요해짐 |

### 개발 환경
- 로컬 Oracle DB(`RPLS_ADM`, SID `xe`, `localhost:1521`) — `sqlplus` 접속 검증 완료(2026-08-14)
- LLM Gateway(`https://skax.ai-talentlab.com`, Azure OpenAI 호환) — 클라이언트 코드(`agents/llm_gateway.py`) 작성 완료, 이 개발 환경엔 Python이 없어 실행 검증은 `python agents/llm_gateway_smoketest.py`로 별도 확인 필요
- `.env`/`.env.example` 분리로 자격증명 커밋 방지
- 실행: `pip install -r requirements.txt` → `streamlit run chatui/app.py` → `http://localhost:8501`

---

## 5주차: PoC 모듈 구현

### 핵심 구현 내용

**1.1 에이전트 워크플로우(Agent Workflow)**
- **구현 기능**: 화면 fragment 종류에 따른 변환 방식 라우팅(규칙 기반 vs LLM 포팅)
- **동작 원리**: 업로드된 파일을 P/F/D `.java`, `.bizunit`, `.xsql`로 식별한 뒤, `.xsql`과 BizUnit 시그니처는 항상 결정론적 변환기로 보내고, F BizUnit의 메서드 본문만 사람이 명시적으로 트리거해야 LLM Gateway로 라우팅한다. 변환 직후 자동으로 정적 검증·품질 스캔을 실행해 이슈를 결과 화면에 통합 표시한다
- **주요 기술**: Python(정규식/문자열 기반 파서, `javalang`/`tree-sitter`는 미도입 — 현재는 경량 정규식 기반), Streamlit 세션 상태, `agents/llm_gateway.py`(Azure OpenAI 호환 클라이언트)

**1.2 도구(Tool) 및 함수 연동**
- **구현 기능**: F BizUnit 메서드 본문의 LLM 포팅 → Service 파일의 스텁 자동 교체
- **동작 원리**: `extract_method_bodies()`로 F BizUnit에서 메서드별 본문을 분리 → 고정 instruction 프롬프트(원본 로직 보존, NEXCORE 의존만 제거, 원본 결함은 FIXME로 보존, D BizUnit 호출을 `store.dXXXX(...)`로 치환)로 `agents.llm_gateway.chat()` 호출 → 응답에서 코드 펜스 제거 → `splice_ported_method()`로 Service 파일의 `PORT_START` 스텁을 실제 코드로 치환 → 즉시 재검증
- **주요 기술**: Python 문자열 스플라이싱, `agents.llm_gateway.chat`(OpenAI SDK 호환), Custom Tool Definition(함수 단위 도구화)

**1.3 데이터 및 메모리(RAG & Context)**
- **구현 기능**: 화면별 변환/검증 이력을 DB에 영속화하고, 원본 해시 기준으로 재작업 여부를 힌트로 제공
- **동작 원리**: 변환 실행 시 `agents/db.py`의 `upsert_conv_file()`이 화면ID/계층/파일명/원본 SHA-256 해시/`BUILD_CHECK` 상태를 로컬 Oracle `CONV_FILE`에 기록하고, 발견된 이슈는 `record_issues()`로 `CONV_ISSUE`에 `detected_by`(어느 모듈이 탐지했는지)와 함께 개별 행으로 쌓인다. 화면 목록을 열 때 `get_cached_status_bulk()`가 해시가 동일하고 이전에 PASS한 화면을 한 번의 쿼리로 미리 표시한다
- **주요 기술**: `oracledb`(python-oracledb), SHA-256 콘텐츠 해싱, SQL upsert/ALTER TABLE 기반 스키마 진화(`ensure_schema()`)
- **RAG(벡터 검색) 자체는 아직 미구현** — 임베딩 클라이언트(`agents.llm_gateway.embed`)는 준비되어 있으나 파일럿 코퍼스가 1건(PLA047)뿐이라 검색이 의미가 없어 Phase 4로 미룸(추측치로 미리 만들지 않음)

### 주요 문제 해결 및 기술 리서치

| 이슈 구분 | 문제 상황 및 원인 | 리서치 및 해결 과정 |
|---|---|---|
| **원본 무결성** | PLA047 `.bizunit` 3종 XML 선언 손상(따옴표 불일치, `<description>`/`</dedication>` 태그 불일치)으로 파싱 불가 | **리서치**: 태그 불일치를 스택 기반으로 검사하는 방법 확인 **적용**: `chatui/converters.py`에 스택 기반 태그 검사 로직을 넣어 `DPLA047.xsql`에서 실제 불일치 지점 2건(4718행 `isNotEqual`이 4840행에서 `</isEqual>`로 잘못 닫힘, 5179행 `</isNotEqual>`가 매칭되는 여는 태그 없음)을 정확히 특정 |
| **원본 컴파일 에러** | `FPLA047.java`/`PPLA047.java`가 중괄호 누락, 미선언 변수(`du`), `ArrayList<object>` 등으로 컴파일 불가 | **리서치**: 원본을 임의로 고치지 않고 어떻게 변환을 진행할지(CLAUDE.md "원본 재정정 후 포팅" 원칙) 검토 **적용**: LLM 포팅 프롬프트에 "원본에 컴파일 에러나 미선언 변수가 있어도 고치지 말고 그대로 옮긴 뒤 `// FIXME(원본 버그)`로 표시"를 명시적으로 지시 |
| **DTO 필드 역추출 불완전** | RPLA04702/03은 F BizUnit이 `getFieldMap()`을 통째로 넘겨 개별 필드명을 소스에서 특정할 수 없음 | **리서치**: 추측으로 필드를 채우는 대신 실패를 명시적으로 남기는 방법 검토(CLAUDE.md "추측 금지") **적용**: `extract_dto_fields`가 이 경우 TODO+WARNING으로 표시해 사람이 확인하도록 설계, RPLA04701(15개 필드 전부 채워짐)과 대비되는 케이스로 남김 |
| **성능/기타** | 5,000줄 넘는 Mapper.xml을 화면에 그대로 렌더링하면 페이지 전체가 무한 스크롤됨 | **리서치**: Streamlit 컴포넌트 내부 스크롤 옵션 확인 **적용**: `st.container(height=450)`로 고정 높이 스크롤 박스를 만들고, 40줄 초과 시 기본은 미리보기만 표시 후 "펼치기" 체크박스로 전체 보기 전환 |

### 핵심 동작 검증

**[검증 시나리오: PLA047 XSQL → Mapper.xml 규칙 기반 변환 + 정적 검증]**

- **입력**: `DPLA047.xsql`의 `S001` 쿼리(iBatis 문법, `#var#`/`isNotEmpty`/`iterate` 포함)
- **에이전트 동작**:
  1. `convert_xsql_fragment(xsql_text)` 호출 → `#var#`→`#{var}`, `isNotEmpty`+`iterate`→`<if>`+`<foreach>` 등 규칙 적용
  2. `_check_well_formed()`로 변환 결과가 유효한 XML인지 자동 확인
  3. `validate_mapper_file()`로 statement id 중복·바인드 표현식 짝을 검사해 `CONV_FILE.BUILD_CHECK` 기록
  4. 원본 태그 불일치가 남아있는 나머지 구간(S002~S006 등)은 FAIL로 정직하게 표시(임의로 고쳐서 PASS로 만들지 않음)
- **최종 결과** (@docs/08-conversion-verification.md 실측 기록 기준):
  - Api/Store/Dto/계층간참조: **PASS**
  - Service: 원본 중괄호 누락 버그를 그대로 보존한 결과 의도대로 **FAIL**(정상 동작 — 원본을 임의로 고치지 않았다는 증거)
  - XSQL: 알려진 태그 불일치로 의도대로 **FAIL**
  - 품질 스캐너(`quality_scanner.run_review`) 실측: `Pla047Mapper.xml`에서 `${...}`(SQL 인젝션 후보) **339건**, `Pla047Service.java`에서 문자열 연결 SQL **13건**, 포팅 후 보존된 원본 버그(`FIXME`) **31건** — 전부 `CONV_ISSUE`에 실제 저장 확인

이 검증은 "화면이 그럴듯하게 변환됐다"가 아니라 **"결정론적으로 맞는 부분은 PASS, 원본이 실제로 깨진 부분은 정직하게 FAIL로 표시한다"**는 것을 실제 데이터로 보여준다 — 이는 CLAUDE.md 핵심 원칙("변환된다"≠"맞다", 추측 금지)이 코드 수준에서 지켜지고 있음을 확인하는 근거다.
