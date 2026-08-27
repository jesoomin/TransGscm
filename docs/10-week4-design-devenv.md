# 4주차: 시스템 아키텍처 설계 및 개발 환경 구축

> 이 프로젝트는 범용 대화형 챗봇이 아니라 **결정론적 변환기 + 좁은 영역의 LLM 포팅**으로 구성된 코드 변환 파이프라인이다(@CLAUDE.md 핵심 원칙). 아래 "Agent"는 화면마다 자유롭게 대화하는 하나의 페르소나가 아니라, @docs/06-mentor-feedback.md §B(ReCodeAgent 4-역할)를 따르는 **파이프라인의 역할별 sub-agent**이며, 그중 실제로 이번 세션까지 코드로 존재하고 LLM을 호출하는 것은 **Translator(F BizUnit 로직 포팅) 역할 하나뿐**이다. Analyzer/Planner/Validator는 @docs/03-kickoff-plan.md Phase 1~3(매핑 그래프, 차등 테스트 하네스, 파일럿 확장)이 끝난 뒹 Phase 4에서 구현될 설계 대상이라, 아래에서는 "구현됨" / "설계만(미구현)"을 항목마다 명시한다 — 안 만든 걸 만든 것처럼 쓰지 않는다.

---

## 0. 개발 환경 구축 (이번 세션에서 실제로 검증한 내용)

@docs/03-kickoff-plan.md Phase 0에는 "이 개발 환경엔 Python이 없어 실행 검증 못 했다"는 기록이 남아 있었다. **이번 세션의 컨테이너에는 Python이 있어**, 아래 항목을 실제로 실행해 검증했다(추측 아님).

| 항목 | 결과 |
| --- | --- |
| Python | `python3 --version` → `Python 3.11.15` 확인 |
| 가상환경 | 프로젝트 루트에 `.venv` 생성(`python3 -m venv .venv`) |
| 기존 `requirements.txt` 설치 | `openai`, `python-dotenv`, `streamlit`, `oracledb` 전부 설치 성공(`openai 3.5.0`, `streamlit 1.62.0`, `oracledb 4.0.2`) |
| `agents/`, `chatui/` 문법 검증 | `python -m py_compile agents/*.py chatui/*.py` 전부 통과 |
| `agents/llm_gateway_smoketest.py` 실행 | 스크립트 자체는 정상 실행되고, `.env`가 없으면 `LLMGatewayConfigError`로 명확히 실패하는 것까지 확인. **단, 이 세션엔 실제 `LLM_GATEWAY_API_KEY`가 없어 Azure OpenAI 호환 엔드포인트로의 실제 왕복 호출은 검증하지 못함** — `.env`를 채운 로컬에서 재실행 필요 |
| Oracle DB(`RPLS_ADM`/`xe`) 연결 | 이 세션엔 `.env`가 없어 재검증 불가(2026-08-14 세션에서 `sqlplus`로 검증된 이력만 존재, @docs/03-kickoff-plan.md 참고) |
| Phase 4/6 대비 패키지 설치 검증 | `langgraph 1.2.11`, `fastapi 0.141.1`, `uvicorn[standard] 0.52.4`, `chromadb 1.5.9`, `faiss-cpu 1.15.0` — 설치 및 `import` 성공까지만 확인, 파이프라인에는 아직 연동 안 함 |

`requirements.txt`에 위 5개 패키지를 "Phase 4~6 대비 추가" 섹션으로 나눠 반영했다(기존 4개와 용도가 다르므로 한 블록에 섞지 않음). `.env`는 원칙대로 커밋하지 않았고 `.env.example` 형식도 변경하지 않았다.

**남은 작업(다음 세션 또는 로컬 개발자용)**: `.env`에 실제 `LLM_GATEWAY_API_KEY`와 Oracle 접속정보를 채운 뒤 `python agents/llm_gateway_smoketest.py`와 `sqlplus` 재검증 — 이건 자격증명이 필요해 이번 세션에서 대신할 수 없다.

---

### Agent 페르소나 및 시스템 프롬프트 (Identity)

**현재 구현된 역할: Translator(F 로직 포팅) Agent** — `chatui/app.py`의 "전체 포팅" 버튼이 `agents/llm_gateway.chat()`을 호출할 때 쓰는 프롬프트(`chatui/app.py:658-669`)를 formalize한 것. 지금 코드는 이 내용을 전부 `role: user` 메시지 하나에 넣고 있고 `role: system`을 별도로 쓰지 않는다 — 이번 설계에서 System/User를 분리하는 것을 개선 항목으로 제안한다.

|              |                            |
| ------------ | -------------------------- |
| **항목**       | **정의 내용**                  |
| **Agent 이름** | `translator_agent` (G-SCM Translator Agent) |
| **주요 역할**    | F(Function) BizUnit Java 메서드 1개의 본문을 받아, NEXCORE 프레임워크 의존(`IDataSet`/`IOnlineContext`/`lookupFunctionUnit`/`lookupDataUnit`)만 Spring 방식으로 치환하고 D BizUnit 호출(`du.dXXXX(...)`)을 `store.dXXXX(...)`로 바꿔 Spring Service 메서드로 옮긴다 |
| **핵심 목표**    | 계산·분기·문자열 처리 로직을 한 글자도 새로 설계하지 않고 그대로 보존하면서 프레임워크 의존성만 제거한다(@CLAUDE.md "업무 로직은 포팅, 프레임워크 의존만 치환") |
| **톤앤매너**     | 코드 외 설명·코드펜스·인사말 없이 완성된 메서드 코드 1개만 출력. 확신 없는 부분을 임의로 채우지 않는다 |
| **제약 사항**    | ① SQL/업무 규칙을 새로 설계하지 않는다 ② 원본에 컴파일 에러나 미선언 변수가 있어도 고치지 않고 그대로 옮긴 뒤 `// FIXME(원본 버그): ...`로만 표시한다(삭제·수정 금지) ③ 결정론적으로 풀리는 부분(iBatis 문법, 메서드 시그니처 골격)은 애초에 이 Agent에게 보내지 않는다 — 규칙 기반 변환기(`converters.py`/`skeleton_gen.py`)가 처리 |

**제안 시스템 프롬프트** (설계 — 아직 `agents/llm_gateway.py` 호출부에는 미적용, 현재는 user 메시지 1개로 합쳐져 있음):

```
당신은 G-SCM 차세대 전환 프로젝트의 Translator Agent다.
NEXCORE(BizUnit) F(Function) 계층 Java 메서드를 Spring Service 메서드로 포팅하는
좁은 임무만 수행한다.

반드시 지킬 것:
- 입력 메서드의 계산/분기/문자열 처리 로직을 하나도 빠짐없이 그대로 유지한다.
- IDataSet/IOnlineContext/lookupFunctionUnit/lookupDataUnit 등 NEXCORE 프레임워크
  의존만 제거하고, D BizUnit 호출(du.dXXXX(...))은 store.dXXXX(...)로 바꾼다.
- SQL이나 업무 규칙을 새로 설계하지 않는다. 원본이 이상하게 보여도 임의로 "개선"하지 않는다.
- 원본에 컴파일 에러/미선언 변수가 있어도 고치지 말고 그대로 옮긴 뒤
  `// FIXME(원본 버그): ...` 주석만 남긴다.
- 출력은 `public Map<String, Object> {method}(Map<String, Object> request) { ... }`
  형태의 완성된 메서드 코드 하나뿐이어야 한다. 코드 펜스, 설명, 인사말을 붙이지 않는다.
- 이 임무 밖의 요청(다른 화면 설계, 무관한 질문 등)은 거절하고 그 사실만 짧게 알린다.
```

**Phase 4 설계 대상(미구현) — 나머지 3개 sub-agent**: 아래는 @docs/06-mentor-feedback.md §B ReCodeAgent 구조를 그대로 차용한 역할 정의이며, @docs/03-kickoff-plan.md Phase 1~3이 끝난 뒤 착수한다.

| Agent 이름 | 주요 역할 | 핵심 목표 |
| --- | --- | --- |
| `analyzer_agent` | 화면·nctRid·BizUnit·XSQL 그래프 조회 결과를 읽어 화면 유형(단순조회/CRUD/복합)을 판정 | 탐색 없이 바로 실행 가능한 입력을 Planner에게 넘긴다 |
| `planner_agent` | 대상 fragment, 트랙(Refactor/Reimagine), 예상 산출 파일 목록을 `conversion-plan.json`으로 고정 | 계획 없이 코드 생성으로 바로 넘어가지 않는다(@CLAUDE.md) |
| `validator_agent` | 빌드/정적 검증(`validators.py`) + 차등 테스트 결과를 판정하고 실패 시 재시도 여부를 결정 | 변환기와 분리된 최종 판정자 역할(@docs/06 §D MatchFixAgent) |

---

### 워크플로우 및 오케스트레이션 (Workflow & Logic)

**2.1 처리 로직** (현재 `chatui/app.py`에 실제 구현된 흐름 기준)

* **Step 1 (Input Analysis):** 업로드된 파일을 계층(P/F/D)·종류(java/bizunit/xsql)별로 분류(`chatui/app.py`의 파일 분류 로직)하고, `AS_IS_CONTENT_HASH`로 이전 변환 이력을 조회해 "원본 변경 없음" 여부만 참고 정보로 보여준다(자동 스킵은 하지 않음 — 최종 판단은 사람)
* **Step 2 (Tool Selection):** 결정론적으로 풀리는 부분(iBatis→MyBatis 문법, BizUnit 시그니처→골격, `.BIZUNIT`/getField·putField→Dto)은 전부 규칙 기반 도구(`converters.py`, `skeleton_gen.py`)로 처리하고 LLM을 부르지 않는다. F 메서드 본문처럼 기계적 1:1 치환이 안 되는 부분만 Translator Agent(LLM)로 보낸다 — 이 분기 자체가 @docs/02-architecture.md "결정론적/LLM 경계" 표를 코드로 구현한 것
* **Step 3 (Execution & Response):** 골격 생성 결과 + 포팅 결과를 병합한 뒤 `validators.py`(정적 검증) → `quality_scanner.py`(품질/취약점 스캔) 순서로 자동 재실행하고, PASS/FAIL과 이슈 목록을 화면에 통합해 보여준다. "저장" 버튼을 눌러야만 `pilot/{screen}/`에 쓰고 `CONV_FILE`/`CONV_ISSUE`에 기록한다(자동 커밋 없음)

**2.2 상태 관리**

* 이 시스템은 "대화 턴"이 아니라 **화면(screen_id) 단위 작업 세션**을 관리한다. 현재는 Streamlit `st.session_state`가 사실상의 상태 저장소로, `skeleton_files`(생성된 코드), `validation_results`, `review_findings`, 포팅 완료된 메서드 집합을 화면 하나가 열려 있는 동안 들고 있는다. 브라우저 세션이 끊기면 저장 전 상태는 소실된다(의도된 동작 — 저장 = 사람이 승인한 지점)
* **LangGraph Node/Edge 흐름(Phase 4 설계, 미구현)**:

  ```
  [Analyzer] → [Planner] → [Translator]* → [Validator]
                                ↑______________|
                         (FAIL, retry_count < 3)
  ```
  - `Translator`는 F BizUnit의 메서드 개수만큼 반복되는 subgraph(현재 UI의 "메서드별 순차 포팅"과 동일한 단위)
  - `Validator`가 FAIL을 반환하면 `retry_count`를 늘려 `Translator`로 되돌아가되, @docs/06-mentor-feedback.md §C 권고대로 **재시도 상한 2~3회**를 조건부 엣지에 명시한다 — 무한 루프 방지
  - 제안 State 필드: `screen_id`, `fragments`, `conversion_plan`, `generated_files`, `issues`, `retry_count`

---

### 도구(Tools) 및 함수 명세 (Capability)

"구현" 열이 있는 표는 이 템플릿 원본에는 없지만, CLAUDE.md 원칙(안 만든 걸 만든 것처럼 쓰지 않기)을 지키려면 실제 코드로 존재하는 함수와 아직 설계만 된 함수를 섞어 쓸 수 없어 열을 추가했다.

| 도구명 (Function Name) | 기능 설명 (Description) | 입력 파라미터 (Input Schema) | 출력 데이터 (Output) | 구현 |
| --- | --- | --- | --- | --- |
| `convert_xsql` | iBatis XSQL → MyBatis Mapper.xml 문법 변환(`#var#`→`#{var}`, `<isEqual>`→`<if>` 등) | `xsql_content: str` | `mapper_xml: str`, `issues: list[ConversionIssue]` | ✅ `chatui/converters.py` |
| `generate_skeleton` | P/F/D BizUnit Java 소스에서 호출 관계를 추적해 Controller/Service/Store 골격 생성 | `p_java, f_java, d_java: str` | `dict[filename, code]`, `issues: list` | ✅ `chatui/skeleton_gen.py` |
| `generate_dto` | `.BIZUNIT` 필드가 비어있으면 `getField`/`putField` 실사용값에서 역추출해 Dto 생성 | `bizunit_xml: str`, `java_source: str` | `dto_code: str`, `unresolved_fields: list[str]`(TODO) | ✅ `chatui/skeleton_gen.py` |
| `validate_screen` | 중괄호 균형, 포팅 스텁 잔존, 계층 간 참조(Api→Service→Store→Mapper) 존재 여부, Mapper.xml well-formed 검사 | `files: dict[filename, code]`, `screen_prefix: str` | `list[ValidationResult]`(PASS/FAIL per 파일) | ✅ `chatui/validators.py` |
| `run_review` | `${...}` SQL 인젝션 후보, 문자열 연결 SQL, 원본 버그 보존(FIXME) 집계, 하드코딩 자격증명(BLOCKER) 스캔 | `files: dict[filename, code]` | `list[Issue]`(BLOCKER/WARNING/INFO) | ✅ `chatui/quality_scanner.py` |
| `chat` (Translator 호출) | LLM Gateway 단발 채팅 완성 — F 메서드 포팅에 사용 | `messages: list[dict]`, `model: str` | `str`(포팅된 코드, 코드펜스 방어적 제거 필요) | ✅ `agents/llm_gateway.py` |
| `search_similar_screen` | 화면 유형·트랙이 비슷한 기 승인 화면을 벡터 검색해 few-shot 예시로 반환 | `screen_id: str`, `screen_type: str`, `top_k: int` | `list[{screen_id, code_snippet, similarity}]` | ⛔ 설계만(Phase 6) — 파일럿이 1건뿐이라 코퍼스 없음 |
| `run_differential_test` | 동일 입력을 레거시 nctRid와 신규 REST에 각각 호출해 응답 diff 산출 | `nctrid: str`, `request_fields: dict` | `{match: bool, mismatches: list[{field, legacy, new}]}` | ⛔ 설계만(Phase 1) — 하네스 미구축 |
| `resolve_nctrid_graph` | 화면ID로 nctRid↔P/F/D BizUnit↔XSQL 매핑을 조회 | `screen_id: str` | `{nctrid: [...], p_class, f_class, d_class, xsql_namespace}` | ⛔ 설계만(Phase 1) — 매핑 그래프 미구축 |

---

### 지식 베이스 및 메모리 전략 (Context & Memory)

**4.1 RAG (검색 증강 생성) 전략** — ⛔ 전부 설계 단계(Phase 6), 미구현. `chatui/cross_analysis.py`로 2-화면 픽스처까지는 로직 검증했지만 실제 파일럿이 PLA047 1건뿐이라 "비교 대상 없음"만 나오는 상태(@docs/08-conversion-verification.md).

* **참조 데이터 소스:** `pilot/{screen}/` 하위에 저장되고 리뷰 상태가 "승인"인 화면의 TO-BE 코드만(미승인 코드를 few-shot으로 섞으면 잘못된 패턴이 그대로 재생산됨). 파일럿 20~30건이 끝나면 이게 코퍼스가 된다(@docs/03-kickoff-plan.md Phase 3)
* **청킹(Chunking) 방식:** 화면 통째가 아니라 CLAUDE.md의 5-fragment 원칙을 그대로 따라, F BizUnit은 이미 구현된 `extract_method_bodies()`(메서드 단위 추출) 결과를 청크 단위로 재사용한다 — 새 청킹 로직을 따로 만들지 않는다
* **임베딩 모델:** `text-embedding-3-small` — `agents/llm_gateway.py`에 이미 `DEFAULT_EMBEDDING_MODEL`로 화이트리스트돼 있고, 파일럿 규모(20~30 화면, 수백 메서드)에서 `3-large`를 쓸 만큼의 코퍼스 크기가 아니라 비용 대비 이득이 없음
* **Vector DB:** Chroma 채택(이번 세션에 `chromadb 1.5.9` 설치·임포트 검증). FAISS는 대안으로 남겨둔다 — 화면 유형·트랙(Refactor/Reimagine) 메타데이터로 few-shot 후보를 걸러야 하는데, Chroma는 메타데이터 필터링을 기본 지원해 이 규모에서 별도 인덱스 관리가 필요 없다. `faiss-cpu`도 설치는 해뒀으니 코퍼스가 커져 순수 벡터 검색 성능이 문제가 되면 그때 재검토

**4.2 대화 메모리 (Conversation History)**

* **메모리 유형:** 대화형 챗봇의 "턴"이 아니라 **화면 세션 단위 버퍼** — `st.session_state`가 화면 하나의 전체 작업 상태(생성 파일, 검증 결과, 포팅 완료 메서드 목록)를 들고 있다가, "저장" 시점에만 영구 저장소(디스크 `pilot/`, DB `CONV_FILE`/`CONV_ISSUE`)로 승격된다
* **저장 전략:** 브라우저 세션이 유지되는 동안만 메모리에 존재, 새로고침하면 미저장 상태는 소실(의도된 동작 — 사람 리뷰 없는 자동 커밋 금지 원칙과 일치). 현재 Translator(`chat()`) 호출은 메서드 1개당 완전히 독립된 단발 요청이라 이전 메서드 포팅 결과를 대화 이력으로 넘기지 않는다 — 메서드 간 상호 참조가 있는 화면에서는 컨텍스트 누락 위험이 있어, Phase 4/5 Reflection 루프 설계 시 "같은 화면 내 이전 포팅 결과를 컨텍스트로 넘길지"를 재검토해야 할 미결 항목으로 남긴다

---

### 핵심 에이전트 기술 스택

|                     |                                           |                            |
| ------------------- | ----------------------------------------- | -------------------------- |
| **구분**              | **선정 전략/기술**                              | **선정 사유 (논리적 근거)**         |
| **LLM Model**       | 기본 `gpt-4.1`(`LLM_GATEWAY_DEFAULT_MODEL`), 500줄 넘는 대형 메서드는 `gpt-5`/`gpt-5.4`로 상향 검토 | 사내 LLM Gateway 화이트리스트(`agents/llm_gateway.py` `ALLOWED_MODELS`) 내에서 선택. 결정론적 변환에는 애초에 LLM을 쓰지 않으므로(@CLAUDE.md) 비용 영향이 F 로직 포팅 1건으로 제한됨 |
| **Agent Framework** | LangGraph(Phase 4 설계, 이번 세션에 `langgraph 1.2.11` 설치·임포트 검증) | @CLAUDE.md "GaiA 우선, 한계 확인되면 LangGraph 검토" 원칙에 따라, Analyzer→Planner→Translator→Validator처럼 조건부 재시도(FAIL 시 최대 2~3회 루프백)와 계획 영속화(`conversion-plan.json`)가 필요한 워크플로우에는 세밀한 노드/엣지 제어가 맞다고 판단 |
| **Prompt Strategy** | 현재: Zero-shot 지시형(F 메서드 1개 → 규칙 나열 → 코드 1개 출력). Phase 6부터: Few-shot(승인된 유사 화면 코드 예시 주입) | 결정론적/LLM 경계가 이미 명확히 그어져 있어(@docs/02-architecture.md) CoT/ReAct 같은 탐색형 기법은 의도적으로 배제(@CLAUDE.md "완전 자율 탐색형 에이전트 금지"). Few-shot은 파일럿 코퍼스가 쌓여야 의미가 있어 지금은 zero-shot부터 시작 |
| **Output Parsing**  | 구조화 JSON이 아니라 "코드펜스 없는 완성 메서드 코드 1개" 텍스트 계약 + `_strip_code_fence()` 방어적 파싱, `splice_ported_method()`로 원본 스텁 위치에 문자열 매칭 치환 | 자바 코드를 JSON으로 감싸면 따옴표/개행 이스케이프 문제가 오히려 커짐 — 원문 그대로 받고 후처리로 방어하는 편이 이 도메인엔 더 안전하다고 판단(실제로 `chatui/app.py`에 이미 이 방식으로 구현·검증됨) |
| **Monitoring**      | 현재: Streamlit 진행률바/스피너(사람이 보는 진행 상태) + `CONV_ISSUE`/`CONV_FILE` DB 적재(사실상의 실행 로그). LangSmith/Langfuse 등은 미도입 | 화면 1건·메서드 단위 호출 규모에서는 DB 적재만으로 추적이 충분했음. Phase 4에서 화면 수가 늘어 LLM 호출량이 커지면(화면당 여러 메서드 × 20~30 화면) 토큰 사용량 추적 도구 도입이 필요 — 아직 미결정이라 도구명을 확정하지 않는다 |
