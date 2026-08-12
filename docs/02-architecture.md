# 아키텍처 분석: NEXCORE(AS-IS) → React(TO-BE)

## AS-IS: NEXCORE 구조
NEXCORE는 SK그룹 표준 Java Spring 기반 애플리케이션 프레임워크로, 업무 로직을 BizUnit 단위로 개발한다. G-SCM에서는 화면 하나당 P(Presentation)/F(Function)/D(Data) 3개 BizUnit과 XSQL(iBatis SQL 매핑) 세트로 구성되어 있다.

요청 흐름은 이렇다.
- Nexacro 화면이 Dataset을 구성해 트랜잭션을 호출한다 (예: `nctRid = RPLA04701`)
- UIAdapter가 Nexacro의 Dataset을 서버의 IDataSet 객체로 직렬화해 전달한다
- nctRid 하나로 들어온 요청이 공통 디스패처를 거쳐 P → F → D BizUnit 순서로 호출된다
- D BizUnit이 `insert("클래스명.메서드명", paramMap, ctx)` 형태로 XSQL(iBatis) SQL을 실행한다
- 응답은 다시 IDataSet으로 감싸져 UIAdapter를 통해 Nexacro Dataset으로 돌아간다

## 핵심 인사이트: 재사용 vs 신규개발
**바꿔야 할 건 로직이 아니라 통신 계층이다.** F/D BizUnit의 비즈니스 로직과 SQL은 Nexacro와 무관하다. Nexacro에 실제로 종속된 부분은 UIAdapter의 Dataset 직렬화 방식과, nctRid로 라우팅하는 P 계층뿐이다.

- **교체 대상 (신규 개발)**
  - Nexacro 화면 → React + AG-Grid
  - UIAdapter + nctRid 디스패처 + P BizUnit → REST Controller
- **재사용 대상 (거의 그대로)**
  - F BizUnit → 비즈니스 로직 그대로
  - D BizUnit + XSQL → 그대로 두고 SQL 문법만 MyBatis로 변환
- **변경 없음**
  - DB 스키마

화면당 실제 신규 개발 비중은 Controller/DTO/화면 등 20~30% 수준으로 추정한다. 나머지 70~80%는 검증된 기존 코드를 재활용한다.

## TO-BE 제안 아키텍처

**1. REST Controller 신설 (P 계층 + UIAdapter 대체)**
nctRid 하나로 모든 요청을 받던 단일 디스패처 방식을 버리고, 화면·기능 단위로 명시적인 REST 엔드포인트를 설계한다. 예: U-RPA047 화면이라면 `GET /api/pla/047/list`, `POST /api/pla/047/save` 식으로 nctRid(RPLA04701, RPLA04702 등) 단위를 엔드포인트로 풀어낸다. Controller는 얇게 유지하고, 실제 처리는 기존 F BizUnit을 그대로 호출한다.

**2. IDataSet ↔ DTO/JSON 변환 계층**
NEXCORE의 `.BIZUNIT` XML이 각 BizUnit의 입출력 필드/타입을 메타데이터로 정의하고 있을 가능성이 높다. 이 파일을 파싱해 Java DTO와 TypeScript 인터페이스를 자동 생성한다. 사람이 스펙을 손으로 다시 정의할 필요가 없어지는 지점이라, Agent가 가장 크게 기여할 수 있는 부분이다.

**3. AG-Grid에 맞춘 API 설계**
데이터가 큰 그리드 화면은 전체를 한 번에 내려주는 방식 대신, AG-Grid의 서버사이드 row model(페이지·정렬·필터 파라미터)에 맞춘 API로 설계한다. Nexacro Dataset을 통째로 넘기던 습관을 그대로 REST에 옮기면 그리드가 큰 화면에서 성능 문제가 그대로 재현된다.

**4. 인증/컨텍스트**
BizUnit이 받던 `IOnlineContext`(사용자·거래 정보)는 Spring Security + 토큰 기반 인증으로 대체하고, 인터셉터에서 요청 스코프 컨텍스트 객체를 채워 F/D BizUnit에 그대로 넘겨준다.

**5. 배치성 프로그램은 건드리지 않는다**
`DCOT998`류처럼 화면에 안 묶인 공통·배치 BizUnit은 이번 전환 범위에서 제외한다. UI가 없으니 React 전환과 무관하고, 건드리면 리스크만 커진다.

## 선결 확인 필요 사항 (Phase 0에서 반드시 확보)
- UIAdapter의 실제 서블릿/URL 패턴 및 nctRid 라우팅 코드
- `.BIZUNIT` XML의 실제 스키마 (필드/타입 정의 포맷)
- P BizUnit이 순수 진입점 역할만 하는지, 화면별 검증 로직이 섞여있는지 (섞여 있으면 Controller 흡수 난이도 상승)
- 소스코드 외부 LLM 전송에 대한 사내 보안 정책
