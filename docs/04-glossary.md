# 용어집

- **Nexacro14**: 투비소프트(Tobesoft)의 클라이언트 UI 플랫폼. G-SCM 프론트엔드에서 사용 중. 화면 정의 파일 확장자는 `.xfdl`.
- **NEXCORE**: SK그룹 표준 Java Spring 기반 엔터프라이즈 애플리케이션 프레임워크. G-SCM 백엔드 프레임워크. 업무 로직을 BizUnit 단위로 개발한다.
- **BizUnit**: NEXCORE에서 업무 로직을 담는 기본 단위 클래스. `BaseBizUnit`을 상속하며, `IDataSet` 요청을 받아 `IDataSet` 응답을 반환한다.
- **PU / FU / DU**: G-SCM에서 BizUnit을 세 계층으로 나눈 프로젝트 컨벤션. P(Presentation, 화면 요청 처리) → F(Function, 비즈니스 로직) → D(Data, 데이터 접근) 순서로 호출된다.
- **XSQL**: iBatis 기반 SQL 매핑 XML 파일. D BizUnit이 참조해 실제 쿼리를 실행한다. MyBatis의 Mapper.xml에 해당.
- **UIAdapter**: Nexacro 클라이언트의 Dataset과 NEXCORE 서버의 `IDataSet`을 직렬화/역직렬화해 연결하는 브릿지 라이브러리.
- **nctRid**: Nexacro 화면에서 트랜잭션을 호출할 때 쓰는 서비스 ID (예: `RPLA04701`). 화면 파일명과 문자열이 일치하지 않으므로, 매핑을 반드시 소스나 문서에서 확인해야 한다.
- **IDataSet / IOnlineContext**: NEXCORE BizUnit 메서드의 표준 파라미터. IDataSet은 요청/응답 데이터, IOnlineContext는 사용자·거래 컨텍스트 정보를 담는다.
- **.BIZUNIT XML**: 각 BizUnit의 입출력 필드/타입을 정의하는 메타데이터 파일로 추정. 실제 스키마는 Phase 0에서 확인 필요.
- **DCOT998류**: 특정 화면에 묶이지 않은 공통/배치성 BizUnit을 가리키는 예시. 이번 변환 범위에서 제외.
- **AG-Grid**: React용 데이터 그리드 라이브러리. 2단계 UI 트랙에서 Nexacro Grid를 대체할 후보 컴포넌트다 — 1단계(서버 전환) 산출물은 아니다.
- **GaiA**: 사내 SKHy LLM 프레임워크. Orchestrator/Multi-Agent 구성을 지원하며, P-MIX Simulation Agent에서 이미 사용 중.

### 1단계(서버 전환) TO-BE 용어
- **`{화면}Api`**: TO-BE의 P BizUnit 대체. `Controller/` 폴더 아래 위치하는 REST 엔드포인트 클래스. nctRid 1개 = 엔드포인트 1개 매핑을 유지한다(범용 CRUD API로 재설계하지 않음). 예: `Pla047Api`.
- **`{화면}Service`**: TO-BE의 F BizUnit 대체. `service/` 폴더. 업무 로직(계산·분기)을 NEXCORE 프레임워크 의존 없이 포팅한 클래스. 예: `Pla047Service`.
- **`{화면}Store`**: TO-BE의 D BizUnit 대체. `store/` 폴더. MyBatis Mapper를 호출하는 데이터 접근 클래스. 예: `Pla047Store`.
- **`{화면}Dto`**: TO-BE의 `.BIZUNIT` 입출력 메타데이터 대체. `dto/` 폴더의 요청/응답 객체.
- **`{화면}Mapper.xml`**: XSQL을 MyBatis 문법으로 변환한 결과물. `resources/mapper/...` 아래 위치.
- **차등 테스트 (Differential Testing)**: 동일 입력을 레거시 nctRid와 신규 REST API에 각각 호출해 응답을 diff로 비교하는 검증 기법. "문법상 변환됨"과 "기능이 맞음"을 구분하기 위한 핵심 전략.
- **Strangler Fig 패턴**: 레거시 시스템을 한 번에 교체하지 않고, 신규 시스템과 당분간 공존시키며 점진적으로 대체하는 전략. 이 프로젝트에서는 신규 REST API가 배포된 뒤에도 기존 nctRid 경로가 한동안 함께 살아있는 상태를 정상으로 취급한다.
- **Translator / Validator 분리**: 코드를 생성하는 변환기(Translator)와 그 결과를 검증하는 검증기(Validator)를 별도 모듈로 두는 설계 원칙. 변환기를 교체해도 검증 자산(테스트, 리포트)이 유지되게 하기 위함.
