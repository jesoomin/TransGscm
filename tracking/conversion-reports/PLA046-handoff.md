# PLA046 변환 인수인계 (미변환 사유 + 수동 처리 가이드)

- 생성 시각: 2026-09-11T04:43:54
- TO-BE 패키지: `com.skhynix.gscm.r.pm.pla`
- 생성된 파일: 5개 (Pla046Api.java, Pla046Dto.java, Pla046Mapper.xml, Pla046Service.java, Pla046Store.java)
- 사람이 반드시 처리해야 할 항목: **24건**, 확인 권장: 42건

> 이 문서는 파이프라인이 이미 만든 결과(계획서·생성 이슈·정적 검증·품질 스캔)를 사람이 읽을 순서로 재구성한 것입니다. 자동 변환 결과는 **사람 리뷰 없이 커밋/배포하지 않습니다.**

## ⛔ 이 화면은 자동 변환을 신뢰하면 안 됩니다

D 계층에 이 변환기가 다루지 못하는 verb가 있습니다(변환기는 `dbSelect`만 지원):

- `dPLA04616`: dbExecuteProcedure
- `dPLA04624`: dbExecuteProcedure
- `dPLA04625`: dbExecuteProcedure

→ 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.

## 🔴 반드시 사람이 처리해야 할 것 (BLOCKER)

- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04601`) — pPLA04601가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04602`) — pPLA04602가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04603`) — pPLA04603가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04604`) — pPLA04604가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04605`) — pPLA04605가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04607`) — pPLA04607가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04609`) — pPLA04609가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04610`) — pPLA04610가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04612`) — pPLA04612가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04613`) — pPLA04613가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04616`) — pPLA04616가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 골격 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04601`) — dPLA04601: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04602`) — dPLA04602: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04603`) — dPLA04603: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04604`) — dPLA04604: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04605`) — dPLA04605: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04606`) — dPLA04606: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04608`) — dPLA04608: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04612`) — dPLA04612: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04615`) — dPLA04615: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04616`) — dPLA04616가 dbExecuteProcedure를 사용하는데 XSQL이 없어 statement 종류를 확정하지 못했습니다 - 조회(selectOne)로 생성했으니 원본을 보고 확인하세요. XSQL을 함께 넣으면 자동으로 맞춰집니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04623`) — dPLA04623: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 골격 생성(skeleton_gen)
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04624`) — dPLA04624가 dbExecuteProcedure를 사용하는데 XSQL이 없어 statement 종류를 확정하지 못했습니다 - 조회(selectOne)로 생성했으니 원본을 보고 확인하세요. XSQL을 함께 넣으면 자동으로 맞춰집니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04625`) — dPLA04625가 dbExecuteProcedure를 사용하는데 XSQL이 없어 statement 종류를 확정하지 못했습니다 - 조회(selectOne)로 생성했으니 원본을 보고 확인하세요. XSQL을 함께 넣으면 자동으로 맞춰집니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.

## 🟡 확인이 필요한 것 (WARNING)

- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04601`) — pPLA04601는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(MAIN_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04602`) — pPLA04602는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(EXR_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04603`) — pPLA04603는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(YLD_PLN_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04604`) — pPLA04604는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(REV_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04605`) — pPLA04605는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(REV_LIST, REV_LIST_A, REV_LIST_B)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04606`) — pPLA04606는 순수 위임이 아닙니다(레코드셋 선별 반환(MAIN_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04607`) — pPLA04607는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(MEMO_INFO)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04609`) — pPLA04609는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(MAIN_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04610`) — pPLA04610는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(MAIN_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04612`) — pPLA04612는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(PLN_REV_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04613`) — pPLA04613는 순수 위임이 아닙니다(결과 메시지 코드 I0016) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04614`) — pPLA04614는 순수 위임이 아닙니다(F 메서드를 2개 호출(fPLA046QryUpdateRlsYn, fPLA046QryPlnRevReleasedCheck); 레코드셋 선별 반환(MAIN_LIST, PLN_REV_RELEASED_LIST); 분기 로직) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04616`) — pPLA04616는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(MAX_WEEK)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04617`) — pPLA04617는 순수 위임이 아닙니다(레코드셋 선별 반환(MAIN_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 골격 생성(skeleton_gen)
- **ORIGINAL_XML_ATTR_QUOTE_FIXED** (902행) — 902행: 원본 XSQL의 <insert id="I005...> 속성에 닫는 따옴표가 빠져 있어(원본 결함) 자동으로 채워 넣었습니다 - 값 자체는 바꾸지 않았습니다. 의도한 값이 맞는지 원본과 대조해 확인하세요.
  - 발견: Mapper 변환(converters)
- **ORIGINAL_XML_ATTR_QUOTE_FIXED** (933행) — 933행: 원본 XSQL의 <insert id="I006...> 속성에 닫는 따옴표가 빠져 있어(원본 결함) 자동으로 채워 넣었습니다 - 값 자체는 바꾸지 않았습니다. 의도한 값이 맞는지 원본과 대조해 확인하세요.
  - 발견: Mapper 변환(converters)
- **ORIGINAL_XML_ATTR_QUOTE_FIXED** (1032행) — 1032행: 원본 XSQL의 <insert id="I007...> 속성에 닫는 따옴표가 빠져 있어(원본 결함) 자동으로 채워 넣었습니다 - 값 자체는 바꾸지 않았습니다. 의도한 값이 맞는지 원본과 대조해 확인하세요.
  - 발견: Mapper 변환(converters)
- **REMAPRESULTS_DROPPED** — remapresults 속성 발견 - MyBatis에 대응 기능 없음, 제거 예정. 결과 컬럼명 중복 여부 확인 필요
  - 발견: Mapper 변환(converters)
  - 조치: remapResults 속성은 MyBatis에 대응이 없어 제거했습니다. 동작 차이가 없는지 확인하세요.
- **STMT_ID_MAP_MISSING** — <select id="S099">를 D 메서드명으로 자동 매핑하지 못했습니다 - dPLA04625가 이 statement를 실제로 부르지만, 그 메서드의 **첫 번째** 호출이 아니라서(메서드 하나가 문을 2개 이상 순서대로/조건부로 실행) 자동 매핑 대상에서 빠졌습니다. id를 그대로 두었으니 dPLA04625 안에서 이 문을 어떻게 반환값에 반영할지 수동으로 판단하세요.
  - 발견: Mapper 변환(converters)
  - 조치: statement id를 D 메서드명으로 바꾸지 못했습니다. Store가 참조하는 id와 Mapper.xml id를 직접 맞추세요.
- **STMT_ID_MAP_MISSING** — <select id="S010">를 D BizUnit의 dbSelect("S010", ...) 호출과 매칭하지 못했습니다 - id를 그대로 두었으니 D 메서드명 기준으로 수동 확인하세요.
  - 발견: Mapper 변환(converters)
  - 조치: statement id를 D 메서드명으로 바꾸지 못했습니다. Store가 참조하는 id와 Mapper.xml id를 직접 맞추세요.
- **STMT_ID_MAP_MISSING** — <update id="U003">를 D 메서드명으로 자동 매핑하지 못했습니다 - dPLA04614가 이 statement를 실제로 부르지만, 그 메서드의 **첫 번째** 호출이 아니라서(메서드 하나가 문을 2개 이상 순서대로/조건부로 실행) 자동 매핑 대상에서 빠졌습니다. id를 그대로 두었으니 dPLA04614 안에서 이 문을 어떻게 반영할지 수동으로 판단하세요.
  - 발견: Mapper 변환(converters)
  - 조치: statement id를 D 메서드명으로 바꾸지 못했습니다. Store가 참조하는 id와 Mapper.xml id를 직접 맞추세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04601`) — pPLA04601: fPLA046QrySelectMainList에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04602`) — pPLA04602: fPLA046QrySelectExrList에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04603`) — pPLA04603: fPLA046QrySelectCopyPlanRevision에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04604`) — pPLA04604: fPLA046erpMbcRpVerRevisionList에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04605`) — pPLA04605: fPLA046QrySelectYieldRevisionList에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04607`) — pPLA04607: fPLA046QrySelectMemo에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04608`) — pPLA04608: fPLA046QryUpdateMemo에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04608`) — pPLA04608: pPLA04608에서 putRecordset 호출을 찾지 못했습니다 - 응답 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04609`) — pPLA04609: fPLA046QryBatchRun에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04610`) — pPLA04610: fPLA046QrySelectDetailCreateInfo에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04611`) — pPLA04611: pPLA04611에서 putRecordset 호출을 찾지 못했습니다 - 응답 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04612`) — pPLA04612: fPLA046QrySelectSomVersion에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04613`) — pPLA04613: pPLA04613에서 putRecordset 호출을 찾지 못했습니다 - 응답 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04614`) — pPLA04614: fPLA046QryUpdateRlsYn에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04615`) — pPLA04615: fPLA046QryUpdateFinalConfirm에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04615`) — pPLA04615: pPLA04615에서 putRecordset 호출을 찾지 못했습니다 - 응답 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04616`) — pPLA04616: fPLA046QrySelectrecentlyWeek에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04617`) — pPLA04617: fPLA046QryCreateReportBatchRun에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04617`) — pPLA04617: pPLA04617에서 putRecordset 호출을 찾지 못했습니다 - 응답 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **SQL_INJECTION_RISK** (781행) — ${BP_EXR}가 2곳(781, 794행)에서 발견됨: 조건절(WHERE/AND/OR/LIKE)에서 값이 SQL 텍스트에 직접 섞입니다 - 외부 입력 경로를 타면 실제 인젝션으로 이어질 수 있습니다. 가능하면 #{BP_EXR}(파라미터 바인딩)로 바꿀 수 있는지 우선 검토하세요.
  - 발견: 품질·취약점 스캔(Pla046Mapper.xml)
  - 조치: `${...}`가 조건절에 쓰였습니다. 값이 외부 입력에서 오면 인젝션 위험이니 가능하면 `#{...}`로 바꿀 수 있는지 검토하세요.
- **SQL_INJECTION_RISK** (787행) — ${TGT_YM}가 2곳(787, 797행)에서 발견됨: 조건절(WHERE/AND/OR/LIKE)에서 값이 SQL 텍스트에 직접 섞입니다 - 외부 입력 경로를 타면 실제 인젝션으로 이어질 수 있습니다. 가능하면 #{TGT_YM}(파라미터 바인딩)로 바꿀 수 있는지 우선 검토하세요.
  - 발견: 품질·취약점 스캔(Pla046Mapper.xml)
  - 조치: `${...}`가 조건절에 쓰였습니다. 값이 외부 입력에서 오면 인젝션 위험이니 가능하면 `#{...}`로 바꿀 수 있는지 검토하세요.

<details><summary>참고 항목 (INFO)</summary>

- **CDATA_SIMPLIFIED** — 특수문자(&/</>)가 없어 불필요했던 CDATA 블록 46개를 일반 텍스트로 정리했습니다. 특수문자가 있어 실제로 필요한 CDATA 2개는 MyBatis가 CDATA를 그대로 지원하므로 그대로 유지했습니다(엔티티 이스케이프로 억지 변환하지 않음).
  - 발견: Mapper 변환(converters)
  - 조치: CDATA 처리를 단순화했습니다. SQL 의미가 바뀌지 않았는지 확인하세요.
- **FETCH_SIZE_DROPPED** — fetchSize 속성은 MyBatis 변환 시 제거했습니다 - 필요하면 <select>에 수동으로 다시 넣으세요.
  - 발견: Mapper 변환(converters)
  - 조치: fetchSize 속성을 제거했습니다. 성능이 중요하면 MyBatis 설정으로 다시 지정하세요.
- **SQL_INJECTION_RISK** (818행) — ${RSL_CNT}가 1곳(818행)에서 발견됨: ORDER BY/컬럼·테이블명 동적 치환으로 보여 상대적으로 위험도가 낮게 분류했습니다 - 값의 출처가 코드 상수/고정 목록이 아니라 외부 입력이라면 여전히 검토가 필요합니다.
  - 발견: 품질·취약점 스캔(Pla046Mapper.xml)
  - 조치: `${...}`가 조건절에 쓰였습니다. 값이 외부 입력에서 오면 인젝션 위험이니 가능하면 `#{...}`로 바꿀 수 있는지 검토하세요.
- **ORIGINAL_BUG** (메서드 `fPLA046QryUpdateInfo`, 233행) — 233행: 원본 버그(포팅 시 보존, 임의 수정 안 함) - EXR_PLN_YM가 문자열 리터럴이 아니라 미선언 변수로 사용됨
  - 발견: 품질·취약점 스캔(Pla046Service.java)
  - 조치: 원본에 있던 결함을 고치지 않고 그대로 옮긴 지점입니다(의도된 동작). 업무 규칙을 아는 사람이 고칠지 유지할지 판단해야 합니다.

</details>

## 자동 변환된 산출물

| 파일 | TO-BE 경로 | 변환 방식 |
|---|---|---|
| Pla046Api.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/Controller/Pla046Api.java` | RULE_BASED |
| Pla046Dto.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/dto/Pla046Dto.java` | RULE_BASED |
| Pla046Service.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/service/Pla046Service.java` | RULE_BASED_SKELETON + LLM_PORTING |
| Pla046Store.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/store/Pla046Store.java` | RULE_BASED |
| Pla046Mapper.xml | `gscm/src/main/resources/mapper/r/pm/pla/Pla046Mapper.xml` | RULE_BASED |

## LLM이 포팅한 메서드 (반드시 사람 리뷰)

생성 코드 첫 줄의 `// AI 변경 요약:` 주석에 무엇을 어떻게 옮겼는지 적혀 있습니다.

- `fPLA046QryInsertMainList`
- `fPLA046QryUpdateMemo`
- `fPLA046QryBatchRun`
- `fPLA046QryUpdateInfo`
- `fPLA046QryCallProc`
- `fPLA046QryUpdateRlsYn`
- `fPLA046QryPlnRevReleasedCheck`
- `fPLA046QryUpdateFinalConfirm`
- `fPLA046QryCreateReportBatchRun`
