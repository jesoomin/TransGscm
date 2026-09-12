# PLA048 변환 인수인계 (미변환 사유 + 수동 처리 가이드)

- 생성 시각: 2026-09-12T18:17:52
- TO-BE 패키지: `com.skhynix.gscm.r.pm.pla`
- 생성된 파일: 5개 (Pla048Api.java, Pla048Dto.java, Pla048Mapper.xml, Pla048Service.java, Pla048Store.java)
- 사람이 반드시 처리해야 할 항목: **6건**, 확인 권장: 6건

> 이 문서는 파이프라인이 이미 만든 결과(계획서·생성 이슈·정적 검증·품질 스캔)를 사람이 읽을 순서로 재구성한 것입니다. 자동 변환 결과는 **사람 리뷰 없이 커밋/배포하지 않습니다.**

## 🔴 반드시 사람이 처리해야 할 것 (BLOCKER)

- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04801`) — pPLA04801가 반환하는 결과 메시지 코드(I0016, W0024)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 코드 뼈대 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04802`) — pPLA04802가 반환하는 결과 메시지 코드(I0016, W0024)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 코드 뼈대 생성(skeleton_gen)
- **RESPONSE_MESSAGE_CONVENTION_UNDEFINED** (메서드 `pPLA04803`) — pPLA04803가 반환하는 결과 메시지 코드(I0016)를 담을 TO-BE 응답 규약이 아직 확정되지 않았습니다(docs/09-common-response-convention.md 열린 질문 2번). 규약 없이 임의의 키를 만들지 않았으므로 이 메시지는 현재 TO-BE 응답에 실리지 않습니다 - 사람이 규약을 확정해야 해소됩니다.
  - 발견: 코드 뼈대 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dHistoryQry`) — dHistoryQry: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 코드 뼈대 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04801`) — dPLA04801: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 코드 뼈대 생성(skeleton_gen)
- **STORE_CARDINALITY_MISMATCH** (메서드 `dPLA04802`) — dPLA04802: 원본에서 이 statement 결과를 getRecordSet(...)으로 받아 다건으로 다룹니다(F/P 소스에서 확인). 그런데 Store는 selectOne(단건)으로 생성됐습니다 - 실제로 행이 2개 이상 나오면 런타임에 TooManyResultsException이 납니다. Mapper.xml resultType/Store 반환 타입을 List<Map<String,Object>> + selectList로 바꿀지 사람이 판단하세요(자동 변경 안 함 - 상위 계층 시그니처가 연쇄적으로 바뀝니다).
  - 발견: 코드 뼈대 생성(skeleton_gen)

## 🟡 확인이 필요한 것 (WARNING)

- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04801`) — pPLA04801는 순수 위임이 아닙니다(F 메서드를 2개 호출(fAuthCheck, fPLA048QrySelectMainList); 권한 게이트(AUTH_YN 확인 후 조기 반환); 결과 메시지 코드 I0016, W0024; 레코드셋 선별 반환(MAIN_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 코드 뼈대 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04802`) — pPLA04802는 순수 위임이 아닙니다(결과 메시지 코드 I0016, W0024; 레코드셋 선별 반환(DETAIL_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 코드 뼈대 생성(skeleton_gen)
- **P_ORCHESTRATION_PORT_REQUIRED** (메서드 `pPLA04803`) — pPLA04803는 순수 위임이 아닙니다(결과 메시지 코드 I0016; 레코드셋 선별 반환(HIST_LIST)) - Api를 위임 한 줄로 생성하지 않고 LLM 포팅 대상으로 남겼습니다.
  - 발견: 코드 뼈대 생성(skeleton_gen)
- **REMAPRESULTS_DROPPED** — remapresults 속성 발견 - MyBatis에 대응 기능 없음, 제거 예정. 결과 컬럼명 중복 여부 확인 필요
  - 발견: Mapper 변환(converters)
  - 조치: remapResults 속성은 MyBatis에 대응이 없어 제거했습니다. 동작 차이가 없는지 확인하세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04801`) — pPLA04801: fAuthCheck에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04803`) — pPLA04803: fHistoryQry에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.

<details><summary>참고 항목 (INFO)</summary>

- **CDATA_SIMPLIFIED** — 특수문자(&/</>)가 없어 불필요했던 CDATA 블록 5개를 일반 텍스트로 정리했습니다. 특수문자가 있어 실제로 필요한 CDATA 0개는 MyBatis가 CDATA를 그대로 지원하므로 그대로 유지했습니다(엔티티 이스케이프로 억지 변환하지 않음).
  - 발견: Mapper 변환(converters)
  - 조치: CDATA 처리를 단순화했습니다. SQL 의미가 바뀌지 않았는지 확인하세요.
- **COMMON_STATEMENT_EXTRACTED** — <select id="S901">는 화면 간 공통 SQL로 확정돼 있어 이 Mapper에서 제외했습니다 - 공통 Mapper 한 곳에서 관리합니다(config/common-methods.json).
  - 발견: Mapper 변환(converters)
- **COMMON_STATEMENT_EXTRACTED** — <select id="S902">는 화면 간 공통 SQL로 확정돼 있어 이 Mapper에서 제외했습니다 - 공통 Mapper 한 곳에서 관리합니다(config/common-methods.json).
  - 발견: Mapper 변환(converters)
- **FETCH_SIZE_DROPPED** — fetchSize 속성은 MyBatis 변환 시 제거했습니다 - 필요하면 <select>에 수동으로 다시 넣으세요.
  - 발견: Mapper 변환(converters)
  - 조치: fetchSize 속성을 제거했습니다. 성능이 중요하면 MyBatis 설정으로 다시 지정하세요.

</details>

## 자동 변환된 산출물

| 파일 | TO-BE 경로 | 변환 방식 |
|---|---|---|
| Pla048Api.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/Controller/Pla048Api.java` | RULE_BASED |
| Pla048Dto.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/dto/Pla048Dto.java` | RULE_BASED |
| Pla048Service.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/service/Pla048Service.java` | RULE_BASED_SKELETON + LLM_PORTING |
| Pla048Store.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/store/Pla048Store.java` | RULE_BASED |
| Pla048Mapper.xml | `gscm/src/main/resources/mapper/r/pm/pla/Pla048Mapper.xml` | RULE_BASED |

## LLM이 포팅한 메서드 (반드시 사람 리뷰)

생성 코드 첫 줄의 `// AI 변경 요약:` 주석에 무엇을 어떻게 옮겼는지 적혀 있습니다.

- `fAuthCheck`
