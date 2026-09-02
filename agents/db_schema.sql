-- G-SCM 전환 작업 추적용 테이블. RPLS_ADM 스키마에 생성.
-- tracking/conversion-verification.csv(사람이 보는 표)와 같은 정보를 다루되,
-- chatui 변환기가 발견한 이슈(문법 오류 등)를 실행할 때마다 자동으로 쌓을 수 있게 한다.
-- CLAUDE.md 원칙: 이건 우리 도구 자체의 메타데이터 테이블이지 G-SCM 업무 스키마가 아니다 -
-- 기존 AS-IS 테이블은 절대 건드리지 않는다.

-- 화면 1개에 대응하는 AS-IS 파일 1개(및 DTO/메시지 같은 파생 산출물)의 변환 상태.
CREATE TABLE CONV_FILE (
    FILE_ID           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    SCREEN_ID         VARCHAR2(30)  NOT NULL,
    AS_IS_LAYER       VARCHAR2(20)  NOT NULL,          -- P(JAVA), P(BIZUNIT), F(JAVA), F(BIZUNIT), D(JAVA), D(BIZUNIT), XSQL, DERIVED
    AS_IS_FILENAME    VARCHAR2(200),
    AS_IS_PATH        VARCHAR2(500),
    TOBE_FILENAME     VARCHAR2(200),
    TOBE_PATH         VARCHAR2(500),
    PARSE_STATUS      VARCHAR2(20)  DEFAULT 'UNKNOWN', -- OK, FAIL, NA, UNKNOWN
    COMPILE_STATUS    VARCHAR2(20)  DEFAULT 'UNKNOWN', -- OK, FAIL, NA, UNKNOWN
    CONVERSION_METHOD VARCHAR2(50),                    -- RULE_BASED, LLM_PORTED, RULE_AND_LLM, MANUAL
    TRACK             VARCHAR2(20)  DEFAULT 'UNDECIDED', -- REFACTOR, REIMAGINE, UNDECIDED
    CONVERSION_STATUS VARCHAR2(20)  DEFAULT 'NOT_STARTED', -- NOT_STARTED, IN_PROGRESS, DONE, BLOCKED
    BUILD_CHECK       VARCHAR2(20)  DEFAULT 'NOT_RUN', -- PASS, FAIL, NOT_RUN, NA
    AS_IS_CONTENT_HASH VARCHAR2(64),                    -- SHA-256(AS-IS 원본 내용) - 재실행 시 스킵 캐싱용
    DIFF_TEST_CHECK   VARCHAR2(20)  DEFAULT 'NOT_RUN', -- PASS, FAIL, NOT_RUN, NA
    HUMAN_EDIT_RATIO  NUMBER(5,2),                      -- % (자동 생성 대비 사람이 수정한 라인 비율), 측정 전엔 NULL
    REVIEW_STATUS     VARCHAR2(20)  DEFAULT 'UNREVIEWED', -- UNREVIEWED, IN_REVIEW, APPROVED
    CREATED_AT        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    UPDATED_AT        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT UQ_CONV_FILE UNIQUE (SCREEN_ID, AS_IS_LAYER, AS_IS_FILENAME)
);

-- 파일(CONV_FILE) 하나 안의 개별 메서드 단위 추적. 화면 하나가 P/F/D 파일 여러 개로 이루어지듯,
-- 파일 하나 안에도 메서드(nctRid별 P/F 메서드, D의 dbSelect 메서드 등)가 여러 개 있다.
-- CONV_FILE : CONV_METHOD = 1:N. chatui/skeleton_gen.py의 SkeletonResult.methods와 1:1 대응.
CREATE TABLE CONV_METHOD (
    METHOD_ID         NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    FILE_ID           NUMBER NOT NULL,
    METHOD_NAME       VARCHAR2(200) NOT NULL,  -- AS-IS 원본 메서드명 (예: fPLA047QrySelectRev)
    METHOD_NAME_TOBE  VARCHAR2(200),           -- TO-BE 변환명 (예: pla04701) - 미정이면 NULL
    BODY_HASH         VARCHAR2(64),            -- SHA-256(공백 정규화한 본문) - 화면 간 중복/유사 로직 탐지용
    CONVERSION_METHOD VARCHAR2(50),            -- RULE_BASED_SKELETON, RULE_BASED_DELEGATION, LLM_PENDING, LLM_PORTED, MANUAL
    MAPPER_STMT_ID    VARCHAR2(100),           -- D 메서드일 때 참조하는 Mapper statement id
    NCTRID            VARCHAR2(50),            -- P 메서드일 때 .bizunit(<method>/<transactionId>)에서 뽑은 nctRid.
                                                -- .bizunit이 없거나 매칭 실패하면 NULL(추측으로 채우지 않음) -
                                                -- agents/nctrid_graph.py가 채운다.
    CREATED_AT        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    UPDATED_AT        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT FK_CONV_METHOD_FILE FOREIGN KEY (FILE_ID) REFERENCES CONV_FILE(FILE_ID),
    CONSTRAINT UQ_CONV_METHOD UNIQUE (FILE_ID, METHOD_NAME)
);

CREATE INDEX IX_CONV_METHOD_FILE ON CONV_METHOD(FILE_ID);
CREATE INDEX IX_CONV_METHOD_HASH ON CONV_METHOD(BODY_HASH);

-- 메서드 간 호출 관계(콜그래프): P->F, F->D 위임 호출을 담는다. "이 XSQL statement/D 메서드를
-- 바꾸면 어떤 Service 메서드까지 영향받는지" 역추적(영향도 분석)하거나, BODY_HASH 중복과 함께
-- "화면 간 동일 로직 재사용" 여부를 보는 데 쓴다. CALLEE가 아직 CONV_METHOD에 없으면(다른 화면
-- 처리 순서상 아직 등록 전 등) CALLEE_METHOD_ID는 NULL, 원본 이름만 CALLEE_NAME_RAW에 남긴다 -
-- 추측으로 연결하지 않는다.
CREATE TABLE CONV_METHOD_CALL (
    CALL_ID           NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    CALLER_METHOD_ID  NUMBER NOT NULL,
    CALLEE_METHOD_ID  NUMBER,
    CALLEE_NAME_RAW   VARCHAR2(200),
    CREATED_AT        TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT FK_CALL_CALLER FOREIGN KEY (CALLER_METHOD_ID) REFERENCES CONV_METHOD(METHOD_ID),
    CONSTRAINT FK_CALL_CALLEE FOREIGN KEY (CALLEE_METHOD_ID) REFERENCES CONV_METHOD(METHOD_ID)
);

CREATE INDEX IX_CALL_CALLER ON CONV_METHOD_CALL(CALLER_METHOD_ID);
CREATE INDEX IX_CALL_CALLEE ON CONV_METHOD_CALL(CALLEE_METHOD_ID);

-- 변환 시도 중 발견된 개별 이슈. 파일 하나에 여러 건 가능(1:N).
-- chatui/converters.py의 ConversionIssue, chatui/skeleton_gen.py의 SkeletonResult.issues와 1:1 대응.
CREATE TABLE CONV_ISSUE (
    ISSUE_ID        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    FILE_ID         NUMBER NOT NULL,
    METHOD_ID       NUMBER,                  -- 이슈가 특정 메서드에 귀속되면 채움(CONV_METHOD FK).
                                              -- XML 파싱 오류처럼 파일 전체에 걸린 이슈는 NULL로 남긴다 -
                                              -- 추측으로 메서드를 지정하지 않는다.
    ISSUE_TYPE      VARCHAR2(40)  NOT NULL,  -- XML_PARSE_ERROR, JAVA_COMPILE_ERROR, TAG_MISMATCH,
                                              -- UNSUPPORTED_TAG, REMAPRESULTS_DROPPED, CDATA_SIMPLIFIED,
                                              -- MISSING_STATEMENT, NCTRID_MAP_EMPTY, DELEGATE_CALL_NOT_FOUND,
                                              -- NO_METHODS_FOUND, MISSING_INPUT_FILE ...
    SEVERITY        VARCHAR2(10)  NOT NULL,  -- BLOCKER, WARNING, INFO
    LINE_NO         NUMBER,
    MESSAGE         VARCHAR2(4000),
    DETECTED_BY     VARCHAR2(100),           -- 'chatui/converters.py', 'chatui/skeleton_gen.py', 'manual review' 등
    DETECTED_AT     TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
    RESOLVED_YN     CHAR(1) DEFAULT 'N' NOT NULL,
    RESOLVED_AT     TIMESTAMP,
    RESOLUTION_NOTE VARCHAR2(4000),
    CONSTRAINT FK_CONV_ISSUE_FILE FOREIGN KEY (FILE_ID) REFERENCES CONV_FILE(FILE_ID),
    CONSTRAINT FK_CONV_ISSUE_METHOD FOREIGN KEY (METHOD_ID) REFERENCES CONV_METHOD(METHOD_ID),
    CONSTRAINT CK_CONV_ISSUE_SEVERITY CHECK (SEVERITY IN ('BLOCKER','WARNING','INFO')),
    CONSTRAINT CK_CONV_ISSUE_RESOLVED CHECK (RESOLVED_YN IN ('Y','N'))
);

CREATE INDEX IX_CONV_ISSUE_FILE ON CONV_ISSUE(FILE_ID);
CREATE INDEX IX_CONV_ISSUE_METHOD ON CONV_ISSUE(METHOD_ID);
CREATE INDEX IX_CONV_FILE_SCREEN ON CONV_FILE(SCREEN_ID);

-- UI_ID(화면) <-> nctRid(트랜잭션) <-> P/F/D 메서드 <-> Mapper statement 평탄화 매핑표.
-- CONV_METHOD/CONV_METHOD_CALL이 정규화된 그래프라면, 이 테이블은 "화면 하나가 실제로 몇 개의
-- 트랜잭션을 갖고 각각 어떤 SQL까지 이어지는지"를 사람이 바로 조회할 수 있게 평탄화한 리포트용
-- 테이블이다(2026-08-28 사용자 확인: UI_ID="U-"+P BizUnit 클래스명(예: U-PPLA047), nctRid는
-- P 메서드 자체(예: pPLA04701)로 봐도 된다는 실사용 확인 - .bizunit의 <transactionId>(예:
-- RPLA04701)가 있으면 그걸 CONFIRMED로 우선하고, 없으면 P 메서드명 자체를 DERIVED로 채운다).
-- 화면 재분석 시 SCREEN_ID 기준으로 DELETE 후 다시 INSERT한다(agents/db.py replace_nctrid_map) -
-- F_METHOD/D_METHOD가 NULL일 수 있어(콜 체인을 못 찾은 경우) UNIQUE 제약 대신 이 방식을 쓴다.
-- PU_ID/FU_ID/DU_ID/XSQL_ID(2026-08-28 사용자 요청 추가): 화면 하나당 P/F/D BizUnit 파일과
-- XSQL 파일은 각각 1개씩이라(CLAUDE.md AS-IS 구조) SCREEN_ID로부터 기계적으로 결정된다
-- (PU_ID="P"+SCREEN_ID, FU_ID="F"+SCREEN_ID, DU_ID=XSQL_ID="D"+SCREEN_ID) - 메서드명 없이도
-- "이 nctRid가 어떤 AS-IS 파일 4종(.java 3개 + .xsql 1개)에 걸쳐있는지"를 파일 단위로 바로
-- 훑어볼 수 있게 별도 컬럼으로 둔다. DU_ID(D BizUnit .java)와 XSQL_ID(D BizUnit .xsql)는 이
-- fixture에서 문자열 값이 같지만(둘 다 "D"+화면ID 컨벤션), 서로 다른 물리 파일이라 컬럼을
-- 분리했다 - 같은 값이 우연이 아니라 원래 그렇다는 뜻이지, 컬럼을 합쳐도 된다는 뜻은 아니다.
CREATE TABLE NCTRID_MAP (
    MAP_ID          NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    UI_ID           VARCHAR2(50)  NOT NULL,  -- 화면ID, 예: U-PPLA047
    SCREEN_ID       VARCHAR2(30)  NOT NULL,  -- 예: PLA047 (CONV_FILE.SCREEN_ID와 동일 키)
    PU_ID           VARCHAR2(50),            -- P BizUnit 파일 id, 예: PPLA047
    FU_ID           VARCHAR2(50),            -- F BizUnit 파일 id, 예: FPLA047 (F 원본이 없으면 NULL)
    DU_ID           VARCHAR2(50),            -- D BizUnit 파일 id, 예: DPLA047 (D 원본이 없으면 NULL)
    XSQL_ID         VARCHAR2(50),            -- XSQL 파일 id, 예: DPLA047 (XSQL 원본이 없으면 NULL)
    NCTRID          VARCHAR2(50)  NOT NULL,  -- 트랜잭션ID
    NCTRID_SOURCE   VARCHAR2(30)  NOT NULL,  -- CONFIRMED_BIZUNIT | DERIVED_FROM_METHOD_NAME
    P_METHOD        VARCHAR2(200) NOT NULL,
    F_METHOD        VARCHAR2(200),           -- P가 호출하는 F 메서드 (못 찾으면 NULL)
    D_METHOD        VARCHAR2(200),           -- F가 호출하는 D 메서드 (못 찾으면 NULL)
    MAPPER_STMT_ID  VARCHAR2(100),           -- D 메서드가 참조하는 Mapper statement id(=TO-BE 기준 D 메서드명)
    CREATED_AT      TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL
);

CREATE INDEX IX_NCTRID_MAP_UI ON NCTRID_MAP(UI_ID);
CREATE INDEX IX_NCTRID_MAP_NCTRID ON NCTRID_MAP(NCTRID);
CREATE INDEX IX_NCTRID_MAP_SCREEN ON NCTRID_MAP(SCREEN_ID);
