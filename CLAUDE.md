# G-SCM 차세대 전환 Agent

## 프로젝트 개요
Nexacro14(프론트) + NEXCORE(백엔드, Spring 기반 BizUnit 프레임워크) 조합으로 만들어진 레거시 화면 1,416개를, React + AG-Grid + REST API 기반으로 자동 전환하는 AI Agent를 개발한다. 배경·목표·KPI 등 상세 내용은 @docs/01-project-plan.md 참고.

## 핵심 원칙 (가장 중요)
- **F/D BizUnit의 비즈니스 로직은 재작성하지 않고 재사용한다.** 새로 만드는 건 통신 계층(Controller/DTO)과 프론트엔드뿐이다. 이게 이 프로젝트 전체 전략의 핵심이다.
- SQL은 iBatis(XSQL) 문법을 MyBatis 문법으로 **변환만** 한다. 쿼리 로직 자체를 새로 짜지 않는다.
- 변환 결과는 반드시 빌드/린트를 통과해야 완료로 인정한다. 사람 리뷰 없는 자동 커밋/배포는 금지.
- `DCOT998`류처럼 화면에 안 묶인 공통·배치 BizUnit은 이번 변환 범위에서 제외한다.

## AS-IS → TO-BE 요약
- Nexacro 화면(Dataset) → React + AG-Grid
- UIAdapter + nctRid 디스패처 + P BizUnit → REST Controller (신규 개발)
- F BizUnit → 그대로 재사용
- D BizUnit + XSQL → 그대로 두고 SQL 문법만 변환
- DB 스키마 → 변경 없음
- 상세 아키텍처와 근거는 @docs/02-architecture.md 참고

## 기술 스택
- 오케스트레이션: 사내 GaiA LLM 프레임워크 우선 (코드 파싱/생성 워크플로우에 한계가 확인되면 LangGraph 검토)
- 코드 생성: Claude API
- 파싱: lxml(xfdl, .BIZUNIT XML), javalang 또는 tree-sitter(Java)
- 검색/예시 저장: FAISS 또는 Chroma
- 서비스화: FastAPI / 리뷰 대시보드: Streamlit
- 검증: Maven·Gradle(Java 빌드), ESLint·tsc(TypeScript)
- 형상관리: Git 브랜치/PR

## 프로젝트 구조 (제안 — 실제 착수 시 조정)
```
/agents        Parsing / Conversion / Validation Agent 구현
/parsers       xfdl, .BIZUNIT XML, Java, XSQL 파서
/templates     React·Controller·Mapper 코드 생성 템플릿
/pilot         파일럿 화면 10~20건 변환 결과물
/legacy        AS-IS 원본 소스 (아래 "레거시 소스 정리" 참고)
/docs          기획·아키텍처·계획 문서
```

## 레거시 소스 정리
기존 소스(AS-IS)는 `/legacy` 하위에 원본 저장소 경로 구조를 그대로 유지하며 정리한다. 임의로 재배치하지 않는다 — 원본 경로가 곧 화면-서비스 추적의 근거가 된다. 실제 경로 규칙은 @docs/메뉴구조.xlsx 로 확인된 것만 반영한다.
```
/legacy
  /dev-ui/gscm/{대분류 U_XX}/{소분류}/{화면ID}.xfdl
    예) U_RP/PA/U-RPA047.xfdl
  /dev-rp-online/src/java/gscm/r/{p1}/{p2}/{p2}b/biz/{P|F|D}{화면}.JAVA, .BIZUNIT
  /dev-rp-online/src/java/gscm/r/{p1}/{p2}/{p2}b/db/{D}{화면}.XSQL
    예) r/pm/pla/plab/biz/PPLA047.JAVA, r/pm/pla/plab/db/DPLA047.XSQL
```
- `dev-ui`는 Nexacro 화면(xfdl) 원본, `dev-rp-online`은 NEXCORE 서버(PU/FU/DU Java, .BIZUNIT XML, XSQL) 원본이다.
- 화면에 안 묶인 `DCOT998`류 공통·배치 BizUnit도 동일 구조로 들어오되, 변환 범위에서는 제외(핵심 원칙 참고).
- `docs/메뉴구조.xlsx`는 현재 전체 1,416개 중 일부 샘플만 담고 있다 — 전체본 확보 전까지는 이 샘플 범위 안에서만 작업한다.

## 용어
nctRid, BizUnit, PU/FU/DU, UIAdapter 등 낯선 용어는 @docs/04-glossary.md 참고 후 코드에 반영한다. 짐작으로 새 용어를 만들어내지 않는다.

## 지금 해야 할 일
착수 단계의 구체적 태스크는 @docs/03-kickoff-plan.md 참고. Phase 0(사전 확보 항목)가 끝나지 않으면 이후 파서·변환 로직 작업이 전부 막히므로 최우선으로 처리한다.

## 하지 말아야 할 것
- P BizUnit / UIAdapter 코드를 확인 없이 삭제하지 않는다 — 화면별 검증 로직이 섞여 있을 수 있음
- DB 스키마 변경을 전제로 하는 제안을 하지 않는다
- 확인되지 않은 nctRid 매핑 규칙을 추측으로 하드코딩하지 않는다 — 반드시 실제 소스/문서에서 확인 후 반영
- 화면 단위 변환 없이 여러 화면을 한 번에 일괄 처리하는 스크립트를 먼저 만들지 않는다 (파일럿 검증 전까지는 소규모로 반복)
