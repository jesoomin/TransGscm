# PLA046 변환 인수인계 (미변환 사유 + 수동 처리 가이드)

- 생성 시각: 2026-09-08T16:11:11
- TO-BE 패키지: `com.skhynix.gscm.r.pm.pla`
- 생성된 파일: 5개 (Pla046Api.java, Pla046Dto.java, Pla046Mapper.xml, Pla046Service.java, Pla046Store.java)
- 사람이 반드시 처리해야 할 항목: **28건**, 확인 권장: 39건

> 이 문서는 파이프라인이 이미 만든 결과(계획서·생성 이슈·정적 검증·품질 스캔)를 사람이 읽을 순서로 재구성한 것입니다. 자동 변환 결과는 **사람 리뷰 없이 커밋/배포하지 않습니다.**

## ⛔ 이 화면은 자동 변환을 신뢰하면 안 됩니다

D 계층에 이 변환기가 다루지 못하는 verb가 있습니다(변환기는 `dbSelect`만 지원):

- `dPLA04607`: dbInsert
- `dPLA04609`: dbInsert
- `dPLA04610`: dbInsert
- `dPLA04611`: dbInsert
- `dPLA04613`: dbInsert
- `dPLA04614`: dbInsert
- `dPLA04616`: dbExecuteProcedure
- `dPLA04617`: dbInsert
- `dPLA04618`: dbInsert
- `dPLA04619`: dbInsert
- `dPLA04626`: dbInsert
- `dPLA04620`: dbInsert
- `dPLA04622`: dbInsert
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
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04607`) — dPLA04607가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04609`) — dPLA04609가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04610`) — dPLA04610가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04611`) — dPLA04611가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04613`) — dPLA04613가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04614`) — dPLA04614가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04616`) — dPLA04616가 dbExecuteProcedure를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04617`) — dPLA04617가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04618`) — dPLA04618가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04619`) — dPLA04619가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04626`) — dPLA04626가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04620`) — dPLA04620가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04622`) — dPLA04622가 dbInsert를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04624`) — dPLA04624가 dbExecuteProcedure를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04625`) — dPLA04625가 dbExecuteProcedure를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **XML_PARSE_ERROR** (451행) — 변환 결과가 유효한 XML이 아닙니다: mismatched tag: line 451, column 4. 원본 XSQL 자체의 태그 짝이 안 맞을 수 있습니다 (문법 치환 규칙 문제가 아니라 원본 데이터 문제일 가능성이 높음) - 원본과 대조해서 확인하세요.
  - 발견: Mapper 변환(converters)
  - 조치: XML이 유효하지 않습니다. 원본 XSQL의 태그 짝(예: `<isNotEqual>`이 `</isEqual>`로 닫힘)을 먼저 고쳐야 변환 결과도 유효해집니다.
- **XML_PARSE_ERROR** (451행) — 유효한 XML이 아닙니다: mismatched tag: line 451, column 4
  - 발견: 정적 검증(Pla046Mapper.xml)
  - 조치: XML이 유효하지 않습니다. 원본 XSQL의 태그 짝(예: `<isNotEqual>`이 `</isEqual>`로 닫힘)을 먼저 고쳐야 변환 결과도 유효해집니다.

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
- **UNSUPPORTED_TAG** (449행) — 449행: <isEqual> 태그가 변환 후에도 남아있습니다(첫 등장 위치만 표시) - 자동 규칙이 이 화면의 실제 사용 패턴과 다를 수 있으니 원본과 대조해서 수동 확인하세요.
  - 발견: Mapper 변환(converters)
  - 조치: 이 변환기가 규칙을 갖고 있지 않은 iBatis 태그입니다. MyBatis 문법으로 직접 옮기세요.
- **UNSUPPORTED_TAG** (59행) — 59행: <isNotEmpty> 태그가 변환 후에도 남아있습니다(첫 등장 위치만 표시) - 자동 규칙이 이 화면의 실제 사용 패턴과 다를 수 있으니 원본과 대조해서 수동 확인하세요.
  - 발견: Mapper 변환(converters)
  - 조치: 이 변환기가 규칙을 갖고 있지 않은 iBatis 태그입니다. MyBatis 문법으로 직접 옮기세요.
- **REMAPRESULTS_DROPPED** — remapresults 속성 발견 - MyBatis에 대응 기능 없음, 제거 예정. 결과 컬럼명 중복 여부 확인 필요
  - 발견: Mapper 변환(converters)
  - 조치: remapResults 속성은 MyBatis에 대응이 없어 제거했습니다. 동작 차이가 없는지 확인하세요.
- **STMT_ID_MAP_MISSING** — <select id="S010">를 D BizUnit의 dbSelect("S010", ...) 호출과 매칭하지 못했습니다 - id를 그대로 두었으니 D 메서드명 기준으로 수동 확인하세요.
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
- **ORIGINAL_BUG** (메서드 `fPLA046QryUpdateInfo`, 216행) — 216행: 원본 버그(포팅 시 보존, 임의 수정 안 함) - EXR_PLN_YM 이 문자열 리터럴이 아니라 미선언 변수로 사용되어 원본 그대로 옮기면 컴파일 에러가 발생한다.
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
