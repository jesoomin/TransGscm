# PLA045 변환 인수인계 (미변환 사유 + 수동 처리 가이드)

- 생성 시각: 2026-09-05T08:13:40
- TO-BE 패키지: `com.skhynix.gscm.r.pm.pla`
- 생성된 파일: 5개 (Pla045Api.java, Pla045Dto.java, Pla045Mapper.xml, Pla045Service.java, Pla045Store.java)
- 사람이 반드시 처리해야 할 항목: **3건**, 확인 권장: 4건

> 이 문서는 파이프라인이 이미 만든 결과(계획서·생성 이슈·정적 검증·품질 스캔)를 사람이 읽을 순서로 재구성한 것입니다. 자동 변환 결과는 **사람 리뷰 없이 커밋/배포하지 않습니다.**

## ⛔ 이 화면은 자동 변환을 신뢰하면 안 됩니다

D 계층에 이 변환기가 다루지 못하는 verb가 있습니다(변환기는 `dbSelect`만 지원):

- `dPLA04505`: dbExecuteProcedure

→ 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.

## 🔴 반드시 사람이 처리해야 할 것 (BLOCKER)

- **UNSUPPORTED_DB_VERB** (메서드 `dPLA04505`) — dPLA04505가 dbExecuteProcedure를 사용합니다 - 이 변환기는 dbSelect만 지원해서 Store 코드를 selectOne으로 생성했습니다(맞지 않음). 원본을 보고 사람이 직접 고쳐야 하며, Mapper.xml의 해당 statement도 <select>가 아닐 수 있습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 이 변환기는 dbSelect만 다룹니다. Store 메서드가 selectOne으로 생성돼 있으니 원본 verb에 맞는 MyBatis 호출(insert/update/delete)로 직접 바꾸고, Mapper.xml의 해당 statement 태그도 `<select>`가 맞는지 확인하세요.
- **DUPLICATE_STATEMENT_ID** (163행) — 163행: statement id 'dPLA04501'가 중복 정의되어 있습니다(처음 정의: 10행) - MyBatis 로드 시 오류가 납니다.
  - 발견: 정적 검증(Pla045Mapper.xml)
  - 조치: statement id가 중복이라 MyBatis 로드 시 오류가 납니다. 한쪽 id를 바꾸세요.
- **DUPLICATE_STATEMENT_ID** (177행) — 177행: statement id 'dPLA04502'가 중복 정의되어 있습니다(처음 정의: 46행) - MyBatis 로드 시 오류가 납니다.
  - 발견: 정적 검증(Pla045Mapper.xml)
  - 조치: statement id가 중복이라 MyBatis 로드 시 오류가 납니다. 한쪽 id를 바꾸세요.

## 🟡 확인이 필요한 것 (WARNING)

- **REMAPRESULTS_DROPPED** — remapresults 속성 발견 - MyBatis에 대응 기능 없음, 제거 예정. 결과 컬럼명 중복 여부 확인 필요
  - 발견: Mapper 변환(converters)
  - 조치: remapResults 속성은 MyBatis에 대응이 없어 제거했습니다. 동작 차이가 없는지 확인하세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `pPLA04501`) — pPLA04501: fPLA045QrySelectRevisionList에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `PPLA04503`) — PPLA04503: fPLA045QrySelectValidationResult에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.
- **DTO_FIELD_EXTRACT_INCOMPLETE** (메서드 `PPLA04504`) — PPLA04504: fPLA045QryRunProcedure에서 개별 getField 호출을 찾지 못했습니다 (getFieldMap()으로 통째로 넘기는 구조일 수 있음) - 요청 필드를 수동으로 확인하세요.
  - 발견: DTO 생성(skeleton_gen)
  - 조치: 요청/응답 필드를 자동으로 못 뽑아 DTO에 TODO가 남아 있습니다(F가 getFieldMap()으로 통째로 넘기는 구조 등). 원본에서 실제 사용 필드를 확인해 채우세요 - 추측으로 채우지 마세요.

<details><summary>참고 항목 (INFO)</summary>

- **CDATA_SIMPLIFIED** — 특수문자(&/</>)가 없어 불필요했던 CDATA 블록 4개를 일반 텍스트로 정리했습니다. 특수문자가 있어 실제로 필요한 CDATA 1개는 MyBatis가 CDATA를 그대로 지원하므로 그대로 유지했습니다(엔티티 이스케이프로 억지 변환하지 않음).
  - 발견: Mapper 변환(converters)
  - 조치: CDATA 처리를 단순화했습니다. SQL 의미가 바뀌지 않았는지 확인하세요.
- **FETCH_SIZE_DROPPED** — fetchSize 속성은 MyBatis 변환 시 제거했습니다 - 필요하면 <select>에 수동으로 다시 넣으세요.
  - 발견: Mapper 변환(converters)
  - 조치: fetchSize 속성을 제거했습니다. 성능이 중요하면 MyBatis 설정으로 다시 지정하세요.
- **ORIGINAL_BUG** (메서드 `fPLA045QrySelectMainList`, 54행) — 54행: 원본 버그(포팅 시 보존, 임의 수정 안 함) - 원본은 sSUM 변수를 사용하나 선언된 변수는 sSum임.
  - 발견: 품질·취약점 스캔(Pla045Service.java)
  - 조치: 원본에 있던 결함을 고치지 않고 그대로 옮긴 지점입니다(의도된 동작). 업무 규칙을 아는 사람이 고칠지 유지할지 판단해야 합니다.
- **ORIGINAL_BUG** (메서드 `fPLA045QrySelectMainList`, 56행) — 56행: 원본 버그(포팅 시 보존, 임의 수정 안 함) - 원본은 List<Map<String, String>> arrQuaterColMap 를 선언해놓고 HashMap을 대입함(타입 불일치).
  - 발견: 품질·취약점 스캔(Pla045Service.java)
  - 조치: 원본에 있던 결함을 고치지 않고 그대로 옮긴 지점입니다(의도된 동작). 업무 규칙을 아는 사람이 고칠지 유지할지 판단해야 합니다.
- **ORIGINAL_BUG** (메서드 `fPLA045QrySelectMainList`, 58행) — 58행: 원본 버그(포팅 시 보존, 임의 수정 안 함) - 원본은 quaterColList 미선언 상태로 사용함.
  - 발견: 품질·취약점 스캔(Pla045Service.java)
  - 조치: 원본에 있던 결함을 고치지 않고 그대로 옮긴 지점입니다(의도된 동작). 업무 규칙을 아는 사람이 고칠지 유지할지 판단해야 합니다.
- **ORIGINAL_BUG** (메서드 `fPLA045QrySelectMainList`, 62행) — 62행: 원본 버그(포팅 시 보존, 임의 수정 안 함) - 원본은 quaterColList 미선언 상태로 request에 저장함.
  - 발견: 품질·취약점 스캔(Pla045Service.java)
  - 조치: 원본에 있던 결함을 고치지 않고 그대로 옮긴 지점입니다(의도된 동작). 업무 규칙을 아는 사람이 고칠지 유지할지 판단해야 합니다.

</details>

## 자동 변환된 산출물

| 파일 | TO-BE 경로 | 변환 방식 |
|---|---|---|
| Pla045Api.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/Controller/Pla045Api.java` | RULE_BASED |
| Pla045Dto.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/dto/Pla045Dto.java` | RULE_BASED |
| Pla045Service.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/service/Pla045Service.java` | RULE_BASED_SKELETON + LLM_PORTING |
| Pla045Store.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/store/Pla045Store.java` | RULE_BASED |
| Pla045Mapper.xml | `gscm/src/main/resources/mapper/r/pm/pla/Pla045Mapper.xml` | RULE_BASED |

## LLM이 포팅한 메서드 (반드시 사람 리뷰)

생성 코드 첫 줄의 `// AI 변경 요약:` 주석에 무엇을 어떻게 옮겼는지 적혀 있습니다.

- `fPLA045QrySelectRevisionList`
- `fPLA045QrySelectMainList`
- `fPLA045QrySelectValidationResult`
