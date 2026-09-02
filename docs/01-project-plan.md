# G-SCM 차세대 전환 Agent — 1~2주차 기획서

> **v2 안내 (2026-08-14)**: 2주차 "문제 정의 및 서비스 기획" 섹션은 이후 @docs/05-proposal-v2.md로 갱신되었고, 범위도 UI(xfdl→React) 제외·백엔드(Java/XSQL→Spring/MyBatis) 전용으로 좁혀졌다. 아래 2주차 내용은 **v1 이력**으로 남겨두고, 현재 유효한 내용은 @docs/05-proposal-v2.md + @CLAUDE.md를 따른다. 1주차(역량/기술스택) 내용은 범위 변경과 무관하게 유효하다.

### v2 KPI 조정 (@docs/06-mentor-feedback.md §4 반영)
제안서(@docs/05-proposal-v2.md)의 "화면당 10일→2일(80%↓)"은 낙관적이다. 멘토 코멘트는 화면 유형별로 차등 추정할 것을 권한다 — **이 수치를 제안서/보고에 쓸 기준값으로 삼는다.**

| 화면 유형 | 비중(추정) | 자동화 후 소요 |
|---|---|---|
| 단순 조회/그리드 | 40~50% | 1~2일 (리뷰 중심) |
| 조회+상세+CRUD | 30~40% | 3~4일 |
| 복합 화면·리포트·특수 로직 | 15~20% | 5~7일 |

평균 약 3일 → 원래 10일 대비 **65~70% 절감**(90% 이상은 약속하지 않는다). 여기에 도구 자체 개발 공수(팀 3~5명 × 4~6개월)와 공통 응답/예외 규약·메시지 코드 표준화 구축 공수를 ROI 계산에 반드시 포함한다.

**핵심 대리지표**: 컴파일 통과율 · API 응답 diff 일치율에 더해 **"사람 수정 라인 비율"**(자동 생성 코드 대비 사람이 손댄 라인 수 비율)을 반드시 함께 추적한다 — 이게 실제 공수 절감률의 가장 직접적인 대리 지표다. `/tracking/conversion-verification.csv`에 화면별로 누적한다.

## 1주차: 역량 및 기술 스택 확인

### 1. 현재 보유 역량
- **Python 숙련도**: 초급~중급 (실무 구현 경험 적음, 프레임워크 기반 Agent 구성·활용 위주)
- **AI/ML 경험**: 전통 ML보다 LLM 기반 Agent 시스템 구축 중심
- **LLM 활용 경험**: 사내 SKHy GaiA LLM 프레임워크로 Analysis/Simulation/Validation Agent 기능 구축
- **RAG/Agent 구현 경험**: 유
  - P-MIX Simulation Agent — Multi-Agent 구조(Analysis/Simulation/Validation) 구현
  - Orchestrator 설계: 자연어 질의 → Agent 할당 → 기능 실행 → 결과 구조화
  - Domain Knowledge: md 파일 구축 → 프롬프트 반영 (경량 프롬프트 주입형)
- **프로젝트 경험**
  - P-MIX Simulation Agent (수행 중) — GaiA 기반 Multi-Agent/Orchestrator 구현
  - G-SCM Nexacro14 + nexcore(Spring, PU/FU/DU/XSQL) 개발·유지보수

### 2. 학습 필요 영역
- **재사용 가능(기보유)**: Orchestrator/Multi-Agent 설계, 프롬프트 기반 Domain Knowledge 반영
- **신규 보강 필요**
  - Python 실무 구현 — 파일 파싱, 코드 생성, 문자열/AST 처리
  - 코드 파싱 — xfdl(XML): lxml / Java: javalang, tree-sitter
  - RAG 고도화 — md 정적 삽입 → FAISS/Chroma 기반 동적 예시 검색 (1,416화면 스케일 대응)
  - 코드 변환 특화 프롬프트 엔지니어링 — few-shot 설계, 구조화 출력(diff, 파일 단위 코드) 강제
  - 코드 검증 자동화 — Validation Agent에 Maven/Gradle, ESLint/tsc 연동
  - API 개발(FastAPI) — 변환 Agent 서비스화
  - UI 개발(Streamlit) — 리뷰 대시보드

### 3. 기술 스택 선호도
- 오케스트레이션: 사내 GaiA 프레임워크 (우선 재사용, 한계 시 LangGraph 보완)
- 코드 생성: Claude API
- 코드 파싱: lxml(xfdl), javalang/tree-sitter(Java)
- 검색/예시 저장: FAISS / Chroma
- 서비스화: FastAPI
- 리뷰 대시보드: Streamlit
- 검증: Maven/Gradle(Java), ESLint/tsc(TypeScript)
- 형상관리: Git 브랜치/PR

### 4. 프로젝트 관심 도메인
- 1순위: 제조/유통(SCM) — G-SCM 담당 업무와 직결
- 2순위: 개발자 생산성/DevTools
- 관심 사유: 1,416개 화면이라는 실제 과제로 학습 내용을 즉시 실무 적용 및 정량 검증 가능

### 5. 8주 목표 설정 (2026-08-20 갱신 — 진행된 구현 반영)
- 기술 목표: LangGraph 기반 "코드 분석 → 병렬 생성 → 정적 검증 → 피드백"으로 이어지는 End-to-End
  자동 변환 파이프라인 PoC 완성(`agents/workflow_graph.py`). 여기에 결정론적 변환기(iBatis→MyBatis,
  BizUnit→Controller/Service/Store 골격), tree-sitter 기반 Java AST 파서(오류 복구 파서 — AS-IS
  원본이 컴파일 안 되는 경우가 흔해 채택), 변환기/검증기(Validator)/품질·보안 스캐너(Quality
  Scanner) 3단 분리, 원본 재변환 스킵을 위한 해시 캐싱, 화면 간 중복·영향도 분석까지 포함한
  자동화 체계를 구축한다 — 애초 계획한 "Multi-Agent 파이프라인 PoC" 하나보다 범위가 넓어졌다.
- 비즈니스 목표: **화면(UI/xfdl)은 이번 범위에서 전환하지 않는다** — 전환 대상은 화면이 호출하는
  서버(Java/XSQL) 로직이며, 그 결과물(Controller/Service/Store/Mapper)을 이후 별도 트랙에서 만들
  React 화면이 그대로 호출할 수 있는 REST 구조로 만드는 것이 목표다. 대상 화면 10건의 서버 로직
  1차 변환율 70% 이상 달성, 화면당 전환 공수 55% 절감 검증(자동 생성 대비 사람 수정 라인 비율을
  대리 지표로 실측)
- 성장 목표: Lv.3 Middle AI 개발자로서 1,416개 화면 규모 실전 적용 역량 증명

---

## 2주차: 문제 정의 및 서비스 기획 (v1, 이력 — 현재는 @docs/05-proposal-v2.md 참고)

### 프로젝트명
G-SCM 차세대 전환 Agent

### 배경 및 문제 정의
- **As-Is**
  - 프론트: Nexacro14(Dataset 기반 UI) / 백엔드: NEXCORE(SK그룹 표준 Spring 프레임워크, BizUnit 단위 개발)
  - NEXCORE 통신 구조: Nexacro Dataset ↔ UIAdapter가 직렬화 → nctRid 단일 진입점으로 P→F→D BizUnit 순차 호출 → D BizUnit이 XSQL(iBatis) 실행
  - 전환 대상: 1,416개 화면 → React + AG-Grid
  - Nexacro 엔진/런처 설치 확인 등 불필요한 접속 단계 존재
  - 솔루션(패키지 제품) 기반 → 확장성 제약
  - 화면-서비스 매핑(nctRid)이 문자열 규칙과 불일치 → 화면마다 소스 추적 필요
- **Pain Point**
  - 화면당 평균 1주(5일) 이상 소요 → 총 1,416주(약 27.2 인년) 규모 공수
  - 접속/엔진 체크 단계로 사용자 경험 저하
  - 확장성 제약으로 기능 추가·UI 커스터마이징 한계
  - 반복 패턴임에도 미자동화 → 화면 수만큼 중복 작업
  - 개발자별 이원화 → 코드 품질/구조 편차
- **기회 요인**
  - PU/FU/DU/XSQL의 명확한 계층·네이밍 컨벤션 → 파싱/템플릿화 용이
  - iBatis→MyBatis 문법 변환 → 규칙 기반 자동화 친화적
  - LLM + 규칙 기반 결합 → 레이아웃/AG-Grid/이벤트 로직까지 커버
  - Agent 기반 자동 변환 → 프로젝트 전체 공수 절감 기대

### 핵심 인사이트: 재사용 vs 신규개발
- **바꿔야 할 건 로직이 아니라 통신 계층이다** — F/D BizUnit의 비즈니스 로직·SQL은 Nexacro와 무관하며, Nexacro에 종속된 부분은 UIAdapter의 Dataset 직렬화 방식과 P 계층의 nctRid 라우팅뿐
- **교체 대상(신규 개발)**: Nexacro 화면 → React+AG-Grid / UIAdapter·디스패처·P BizUnit → REST Controller
- **재사용 대상(거의 그대로)**: F BizUnit(비즈니스 로직 그대로) / D BizUnit+XSQL(SQL 문법만 MyBatis로 변환)
- **변경 없음**: DB 스키마
- 화면당 실제 신규 개발 비중은 Controller/DTO/화면 등 20~30% 수준으로 추정 — 나머지 70~80%는 검증된 기존 로직 재활용

### 목표 사용자
- G-SCM 전환 프로젝트 투입 개발자 (프론트엔드/백엔드, 사내·외주)
- 변환 결과 검토·승인 PL/PM, QA 담당자

### 프로젝트 목표
- **정성적 목표**
  - 목표1: 반복 화면 전환 작업 자동화
  - 목표2: 전환 코드 구조적 일관성 확보 (개발자별 편차 최소화)
  - 목표3: 사내 AI 기술 내재화 및 재사용 자산화
- **정량적 목표(KPI)**
  - 화면당 평균 전환 소요시간: 5일 → 2일 이하(60%+ 단축) / 측정: 파일럿 10~20건 실측 / 현재: 약 5일
  - 1차 자동변환 커버리지: 0% → 70% 이상 / 측정: 빌드·린트 통과율 / 현재: 0%(전량 수작업)
  - 총 소요 공수: 약 1,416인주 → 500~600인주 / 측정: 파일럿 결과 스케일링 / 현재: 약 1,416인주(추정)
  - 전환 후 결함율: 수작업 대비 동등 이하 / 측정: 리뷰·QA 결함 건수 비교 / 현재: 측정 예정
  - ※ 파일럿 이후 검증·조정 필요한 초기 가정치

### 핵심 기능 정의
1. AS-IS 소스 자동 분석기 — xfdl/PU/FU/DU/XSQL 파싱 → 화면-서비스-nctRid 매핑 포함 IR 생성
2. REST Controller 자동 생성 — nctRid 디스패처·P BizUnit을 화면·기능 단위 REST 엔드포인트로 대체, 내부적으로 기존 F BizUnit을 그대로 호출
3. BIZUNIT 메타데이터 기반 DTO/인터페이스 자동 생성 — .BIZUNIT XML 파싱 → Java DTO + TypeScript 인터페이스 자동 생성
4. React(AG-Grid) 변환 엔진 — 화면(xfdl) → React 컴포넌트, 대용량 그리드는 AG-Grid 서버사이드 row model에 맞춘 API로 설계
5. 자동 검증·리뷰 리포트 — 빌드/린트 통과 여부, diff, 리뷰 우선순위 산정 대시보드

### 기대 효과
- **근거**: 전체 재작성이 아니라 Nexacro 종속 통신 계층(20~30%)만 교체하고 검증된 F/D 로직(70~80%)은 재사용하는 전략 → 절감폭이 큼
- 업무 효율화: 화면당 처리시간 약 60% 단축 (5일→2일)
- 품질 향상: 자동 변환으로 개발자 간 코드 편차 감소
- 비용 절감: 전체 기준 약 800~900인주(15~17인년) 공수 절감 기대 (파일럿 후 확정)
- 사용성/확장성 개선: 엔진/런처 접속 단계 제거, 솔루션 기반 확장성 제약 해소

### 범위 및 제약사항
- **In Scope**: 1,416개 xfdl 화면 + PU/FU/DU/XSQL 자동 변환(REST Controller·DTO 생성, AG-Grid 매핑, 데이터 바인딩, 이벤트, API 연동), F/D BizUnit 로직 재사용, DB 스키마 유지 전제 iBatis→MyBatis 변환
- **Out of Scope**: DB 스키마 변경, 신규 기능 추가, 무인 자동배포(리뷰 필수), DCOT998류 공통/배치 BizUnit(화면 미연동, 별도 트랙)
- **제약사항**
  - nctRid 매핑 자동 추출 파서 선행 필요
  - UIAdapter의 실제 서블릿/URL 패턴 및 nctRid 라우팅 코드 확인 필요
  - .BIZUNIT XML 스키마(필드/타입 정의 포맷) 확인 필요
  - P BizUnit이 순수 진입점 역할만 하는지, 화면별 검증 로직이 섞여있는지 확인 필요 (섞여 있으면 Controller 흡수 난이도 상승)
  - 소스코드 외부 LLM 전송 보안 정책 확인 필요
