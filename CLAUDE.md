# G-SCM 차세대 전환 Agent (v2)

> 이 문서는 2026-08-14 범위 재정의 이후 버전이다. v1(화면까지 React로 전환)은 @docs/01-project-plan.md, @docs/02-architecture.md 이력에 남아있으나 **현재 유효한 범위는 이 문서 기준**이다. 제안서 원문은 @docs/05-proposal-v2.md, 멘토 코멘트 원문은 @docs/06-mentor-feedback.md 참고.

## 프로젝트 개요
Nexacro14(프론트) + NEXCORE(백엔드, Spring 기반 BizUnit 프레임워크) 조합으로 만들어진 레거시 화면 1,416개 중 **서버(Java/XSQL)만** React가 호출할 수 있는 구조로 자동 전환하는 AI Agent를 개발한다. **Nexacro 화면(xfdl) 자체는 이번 범위에서 전환하지 않는다** — UI는 추가 디자인 변경 가능성이 있어 별도 트랙으로 분리한다. 기존 트랜잭션(nctRid) 계약은 그대로 유지해서, 나중에 만들어질 React 화면이 지금 변환하는 API를 그대로 호출할 수 있게 한다.

## 핵심 원칙 (가장 중요)
- **UI(xfdl/Nexacro)는 전환하지 않는다.** 이번 Agent의 산출물은 서버(Controller/Service/Store/Mapper)까지다. React 화면은 별도 트랙에서, 확정된 디자인으로 나중에 만들어지며 여기서 만든 API를 그대로 호출한다.
- **F/D BizUnit의 업무 로직(계산·분기·SQL)은 새로 작성하지 않고 그대로 옮긴다(포팅).** 단, NEXCORE 프레임워크 의존 코드(`IDataSet`/`IOnlineContext`/`lookupFunctionUnit` 등)는 Spring/MyBatis 방식으로 치환해야 한다 — 이 치환 자체가 이번 프로젝트에서 새로 개발하는 부분이지, 로직을 다시 설계하는 게 아니다.
- SQL은 iBatis(XSQL) 문법을 MyBatis 문법으로 **변환만** 한다. 쿼리 로직 자체를 새로 짜지 않는다.
- **결정론적으로 가능한 변환은 LLM에 맡기지 않는다.** iBatis→MyBatis, BizUnit 메서드 시그니처→Controller/Service/Store 골격, `.BIZUNIT` 필드→DTO는 규칙 기반 변환기로 처리한다. LLM은 표로 명시된 영역에만 쓴다 (@docs/02-architecture.md의 "결정론적/LLM 경계" 표 참고).
- **nctRid 매핑 인덱스 구축이 최우선이다.** 화면↔nctRid↔BizUnit↔XSQL 그래프가 없으면 이후 모든 작업이 코드베이스를 헤매며 추측하게 된다 — 이건 LLM 문제가 아니라 선행 정적 분석 과제다.
- **변환기(Translator)와 검증기(Validator)는 분리한다.** 검증 로직이 변환 로직에 섞이면 변환기를 바꿀 때마다 검증 자산도 같이 깨진다.
- **차등 테스트(differential testing)로 검증한다.** 동일 입력을 레거시 nctRid와 신규 REST API에 각각 호출해 응답을 diff로 비교한다. "변환된다"와 "맞다"는 다른 문제라는 걸 전제로 한다.
- **Strangler Fig — 한 번에 다 바꾸지 않는다.** 레거시(NEXCORE)와 신규(Spring/React) API가 당분간 공존하는 걸 정상 상태로 취급한다.
- **콜그래프 역순으로 진행한다: XSQL → Store → Service → Api.** 하위 계층(SQL/데이터 접근)이 확정돼야 상위 계층(Service/Controller) 시그니처가 안 흔들린다. Api부터 먼저 잡고 Store를 나중에 끼워 맞추지 않는다.
- **스켈레톤 먼저, LLM은 빈 본문만 채운다.** 클래스·메서드·DTO 골격은 규칙 기반으로 100% 확정한 뒤에 LLM을 호출한다. 골격까지 LLM에 맡기면 화면마다 구조가 미묘하게 달라진다.
- **화면 하나를 통째로 넣지 말고 5개 fragment로 나눠 처리한다**: `.BIZUNIT`(스키마) / P Java / F Java / D Java / XSQL. 각 fragment 단위로 검증·리뷰가 가능해야 한다.
- **화면(스크린)마다 변환 전에 계획을 파일로 고정한다** (`conversion-plan.json` 등). 계획 없이 바로 코드를 생성하지 않는다 — 계획이 있어야 리뷰·재현·재실행이 가능하다. **구현됨(2026-09-04)**: `agents/conversion_plan.py`, 파이프라인의 `plan_all` 노드가 `convert_all`보다 먼저 돌면서 `tracking/conversion-plans/{화면}-conversion-plan.json`에 기록한다(LLM 미사용, 전부 정적 분석). 트랙(Refactor/Reimagine)은 자동으로 정하지 않고 항상 `UNDECIDED`로 두며 판단 근거만 `track_signals`에 채운다 — 트랙 결정은 사람 몫이다.
- **Refactor(구조보존) / Reimagine(재설계) 두 트랙으로 나눈다.** 단순조회·CRUD류(다수)는 1:1 구조보존 변환, 복합화면·특수 로직·원본 자체가 이미 망가진 화면(예: PLA047의 FPLA047 로직처럼 원본 자체에 결함이 많은 경우)은 업무 규칙만 추출해 재설계하는 Reimagine 트랙으로 뺀다. 전부 같은 방식으로 밀어붙이지 않는다.
- **작업 단위로 커밋한다.** 화면 하나가 거대 단일 커밋으로 나오면 아무도 리뷰할 수 없다 — Store/Service/Api/Mapper 등 계층별로 나눠 커밋한다.
- 변환 결과는 반드시 빌드/린트를 통과해야 완료로 인정한다. 사람 리뷰 없는 자동 커밋/배포는 금지.
- `DCOT998`류처럼 화면에 안 묶인 공통·배치 BizUnit은 이번 변환 범위에서 제외한다.
- DB 접속정보·LLM Gateway API 키 등 모든 자격증명은 어떤 파일에도 커밋하지 않는다 (아래 "로컬 개발 환경" 참고).

## AS-IS → TO-BE 매핑
`docs/07-tobe-structure.xlsx`(AS_IS/TO-BE 시트)로 확정된 실제 패키지 구조. 추측 아님 — PLA047 화면 기준 확인된 값.

| AS-IS | TO-BE | 비고 |
|---|---|---|
| `P{화면}` (P BizUnit) | `{화면}Api` — `Controller/` 폴더 | nctRid 진입점 → REST 엔드포인트. 원본 트랜잭션 구조 유지 |
| `F{화면}` (F BizUnit) | `{화면}Service` — `service/` 폴더 | 업무 로직 포팅 |
| `D{화면}` (D BizUnit) | `{화면}Store` — `store/` 폴더 | 데이터 접근 포팅 |
| `.BIZUNIT` XML (입출력 메타) | `{화면}Dto` — `dto/` 폴더 | 필드가 비어있는 경우 AS-IS 코드의 `getField`/`putField` 실사용 값에서 역추출 (추측 금지) |
| `{화면}.XSQL` (iBatis) | `{화면}Mapper.xml` — `resources/mapper/...` | 문법만 변환 |
| 하드코딩 메시지 코드(`E0052`, `W0024`, `I0016` 등) | `resources/message/errors.properties`, `errors_en.properties` | 국제화 대비 외부화 (신규) |

패키지 규칙(PLA047 기준 확인): `com.skhynix.gscm.r.{p1}.{p2}` (AS-IS의 `{p2}b` 서브패키지는 TO-BE에서 사라짐). 예:
```
gscm/src/main/java/com/skhynix/gscm/r/pm/pla/
  Controller/Pla047Api.java
  dto/Pla047Dto.java
  service/Pla047Service.java
  store/Pla047Store.java
gscm/src/main/resources/
  mapper/r/pm/pla/Pla047Mapper.xml
  message/errors.properties
  message/errors_en.properties
```
> `Controller`만 대문자로 시작하고 `dto/service/store`는 소문자다 — 엑셀 원본 그대로이며 임의로 통일하지 않았다. 다른 화면에서도 이 표기가 일관되는지 표본이 늘어나면 재확인 필요.

상세 아키텍처(결정론적/LLM 경계, 검증 전략)는 @docs/02-architecture.md 참고.

## 기술 스택
- 오케스트레이션: 사내 GaiA LLM 프레임워크 우선 (한계 확인되면 LangGraph 검토)
- **LLM 호출: 사내 LLM Gateway(AI Talent Lab, Azure OpenAI 호환, `https://skax.ai-talentlab.com`)를 통해 접근.** 허용 모델은 `gpt-4.1`/`gpt-4.1-mini`/`gpt-4o`/`gpt-4o-mini`/`gpt-5`/`gpt-5-mini`/`gpt-5.4`/`text-embedding-3-large`/`text-embedding-3-small`/`text-embedding-ada-002` — 이 목록 밖 모델명은 쓰지 않는다. 클라이언트 구현은 `agents/llm_gateway.py`. 결정론적 변환 영역에는 쓰지 않는다(위 핵심 원칙 참고)
- 파싱: `.BIZUNIT` XML은 lxml, Java(BizUnit)는 javalang 또는 tree-sitter. **xfdl 파서는 불필요**(UI 미전환)하지만, **`.xjs`의 `transaction()` 호출부에서 nctRid 문자열을 추출하기 위한 경량 JS AST 파서(babel 또는 tree-sitter)는 여전히 필요**하다 — 화면을 변환하진 않지만 화면↔nctRid 매핑을 알아야 하기 때문. 무거운 정적분석기(CodeQL류) 대신 언어별 경량 파서 조합으로 충분하다
- 검색/예시 저장: FAISS 또는 Chroma (파일럿 20~30건이 RAG 코퍼스가 됨)
- 서비스화: FastAPI
- **업로드→변환 챗팅 UI**: `docs/07-tobe-structure.xlsx`의 AS_IS 시트 기준 폴더6(`gscm`, 즉 `dev-rp-online/src/java/gscm/` 이하)부터 업로드하면 TO-BE 구조 파일로 변환해주는 대화형 도구. 상세는 @docs/03-kickoff-plan.md
- 검증: Maven·Gradle(Java 빌드), 차등 테스트 하네스(레거시 nctRid ↔ 신규 REST diff)
- DB: 로컬 Oracle (자격증명은 `.env`, 커밋 금지 — 아래 참고)
- 형상관리: Git 브랜치/PR

## 프로젝트 구조 (제안 — 실제 착수 시 조정)
```
/agents        Parsing / Conversion / Validation Agent 구현, LLM Gateway 클라이언트(llm_gateway.py)
/chatui        업로드→변환 챗팅 UI (Streamlit, 로컬 전용) - converters.py(iBatis→MyBatis), skeleton_gen.py(Api/Service/Store/Dto 골격 + TO-BE 폴더경로), validators.py(변환기와 분리된 정적 검증기), app.py
/parsers       .BIZUNIT XML, Java, XSQL 파서 (xfdl 파서는 범위 아님)
/templates     Controller/Service/Store/Mapper 코드 생성 템플릿
/pilot         파일럿 화면 20~30건 변환 결과물 (유형별 4~5개씩)
/tracking      화면·파일별 변환 검증 테이블 (@docs/08-conversion-verification.md 참고)
/legacy        AS-IS 원본 소스 (아래 "레거시 소스 정리" 참고)
/docs          기획·아키텍처·계획 문서
.env           로컬 DB·LLM Gateway API 키 등 민감정보 (커밋 금지, .gitignore 처리)
.env.example   .env 형식 예시 (커밋 대상, 값은 더미)
```

## 레거시 소스 정리
`docs/07-tobe-structure.xlsx`의 AS_IS 시트 기준 경로만 확인된 것으로 취급한다.
```
/legacy
  /dev-rp-online/src/java/gscm/r/{p1}/{p2}/{p2}b/biz/{P|F|D}{화면}.JAVA, .BIZUNIT
  /dev-rp-online/src/java/gscm/r/{p1}/{p2}/{p2}b/db/{D}{화면}.XSQL
    예) r/pm/pla/plab/biz/PPLA047.JAVA, r/pm/pla/plab/db/DPLA047.XSQL
```
- xfdl(`dev-ui`)은 이번 범위가 아니므로 신규로 `/legacy`에 정리하지 않는다. 기존에 들어온 xfdl 샘플(`docs/메뉴구조.xlsx` v1)은 이력 참고용으로만 남긴다.
- 화면에 안 묶인 `DCOT998`류 공통·배치 BizUnit도 동일 구조로 들어오되, 변환 범위에서는 제외.

## 로컬 개발 환경 (DB·API 키 등 민감정보)
- 로컬 Oracle DB 연결 정보(호스트/포트/계정/비밀번호)와 LLM Gateway API 키는 `.env`에만 둔다. `.env`는 `.gitignore`로 커밋 제외 처리되어 있다 — **절대 CLAUDE.md, docs/, 코드에 직접 값을 적지 않는다.**
- `.env.example`에 키 이름과 더미 값만 커밋해서 형식을 공유한다.
- 새 세션에서 DB/LLM Gateway 연결이 필요하면 `.env` 존재 여부와 키 이름만 확인하고, 값 자체를 문서·커밋 메시지·대화창에 옮기지 않는다. 비밀키는 사용자가 `.env`에 직접 입력하도록 안내한다(채팅에 붙여넣지 않도록).
- Oracle DB는 2026-08-14 `sqlplus`로 접속 검증 완료: SID `xe`, `RPLS_ADM` 계정. LLM Gateway는 `agents/llm_gateway.py`로 클라이언트 코드는 작성했지만 이 개발 환경엔 Python이 없어 실행 검증은 못 했다 — API 키를 `.env`에 채운 뒤 `python agents/llm_gateway_smoketest.py`로 직접 확인할 것.

## 용어
nctRid, BizUnit, PU/FU/DU, UIAdapter 등은 @docs/04-glossary.md 참고. Controller(Api)/Service/Store 같은 TO-BE 신규 용어도 같은 문서에 정리되어 있다. 짐작으로 새 용어를 만들어내지 않는다.

## 지금 해야 할 일
착수 단계 태스크는 @docs/03-kickoff-plan.md 참고 — 멘토 코멘트(@docs/06-mentor-feedback.md)의 "적용 우선순위"를 그대로 따른다: ①nctRid 매핑 그래프 ②차등 테스트 하네스 ③공통 응답/예외/메시지 코드 규약 ④결정론적 변환기(iBatis→MyBatis, BizUnit→Controller/Service/Store 골격) ⑤파일럿 20~30화면 ⑥LLM 파이프라인 ⑦Reflection·수리 루프. **1~4번이 프로젝트 성패의 80%이고 LLM은 6번에서야 등장한다** — 순서를 바꾸지 않는다.

## 하지 말아야 할 것
- P BizUnit / UIAdapter 코드를 확인 없이 삭제하지 않는다 — 화면별 검증 로직이 섞여 있을 수 있음
- DB 스키마 변경을 전제로 하는 제안을 하지 않는다
- 확인되지 않은 nctRid 매핑 규칙을 추측으로 하드코딩하지 않는다 — 반드시 실제 소스/문서에서 확인 후 반영
- 화면 단위 변환 없이 여러 화면을 한 번에 일괄 처리하는 스크립트를 먼저 만들지 않는다 (파일럿 검증 전까지는 소규모로 반복). **예외(2026-08-28, 2026-09-02 갱신)**: 사용자가 이 원칙과 배치되는 걸 알고도 명시적으로 폴더 전체 자동 진행을 요청해, `chatui/app.py`의 폴더 모드가 대상 화면(멀티셀렉트, 기본 전체)에 대해 1~7단계를 자동 진행한다 - 1~5단계(규칙기반 변환→LLM 포팅→정적 검증→품질/취약점 스캔→AI 추천)는 `agents/workflow_graph.run_pipeline_part_a()`(LangGraph)로, 6~7단계(전체 화면 교차 분석+영향도 분석→Maven 빌드)는 아직 저장 전인 배치를 `pilot/`의 임시 사본(`_run_stage_6_7_preview()`)에 겹쳐 써서 미리 실행한다 - 실제 `pilot/`은 이 단계에서 전혀 건드리지 않는다. 실제 `pilot/` 폴더와 DB에 반영되는 건(저장) 여전히 사람이 "승인하고 저장" 버튼을 눌러야만 진행되고, 저장 후 6~7단계를 다시 실행하지는 않는다(이미 확인한 미리보기와 동일한 내용이라서). git 커밋/배포는 여전히 사람이 직접 한다.
- 결정론적으로 풀리는 변환(문법 치환, 시그니처 매핑)에 LLM을 쓰지 않는다 — 비용만 쓰고 품질은 안 나온다
- 학습 기반 변환 모델을 새로 훈련하지 않는다 — 병렬 데이터도 없고 규칙성이 높아 불필요
- 완전 자율 탐색형 에이전트(SWE-agent류)를 만들지 않는다 — 1,416회 반복 작업엔 고정된 파이프라인이 자율 탐색보다 낫다
- Nexacro→React 전용 문제에 범용 다국어/프레임워크 전환기를 설계하지 않는다
- DB 접속정보·비밀번호·LLM Gateway API 키 등을 CLAUDE.md/docs/코드에 직접 적거나 커밋하지 않는다 — 채팅에 붙여넣는 것도 피하고 `.env`에 직접 입력하도록 안내한다
- 90% 이상의 공수 절감을 제안서에 약속하지 않는다 — 화면 유형별 실측(@docs/06-mentor-feedback.md 4번) 없이 낙관적 수치를 확정하지 않는다
