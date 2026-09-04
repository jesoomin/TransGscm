# PLA049 변환 인수인계 (미변환 사유 + 수동 처리 가이드)

- 생성 시각: 2026-09-05T08:13:40
- TO-BE 패키지: `com.skhynix.gscm.r.pm.pla`
- 생성된 파일: 3개 (Pla049Mapper.xml, Pla049Service.java, Pla049Store.java)
- 사람이 반드시 처리해야 할 항목: **0건**, 확인 권장: 1건

> 이 문서는 파이프라인이 이미 만든 결과(계획서·생성 이슈·정적 검증·품질 스캔)를 사람이 읽을 순서로 재구성한 것입니다. 자동 변환 결과는 **사람 리뷰 없이 커밋/배포하지 않습니다.**

## 🔴 반드시 사람이 처리해야 할 것 (BLOCKER)

없습니다.

## 🟡 확인이 필요한 것 (WARNING)

- **REMAPRESULTS_DROPPED** — remapresults 속성 발견 - MyBatis에 대응 기능 없음, 제거 예정. 결과 컬럼명 중복 여부 확인 필요
  - 발견: Mapper 변환(converters)
  - 조치: remapResults 속성은 MyBatis에 대응이 없어 제거했습니다. 동작 차이가 없는지 확인하세요.

<details><summary>참고 항목 (INFO)</summary>

- **MISSING_INPUT_FILE** — P(Java) 파일이 없어 Api 골격을 생성하지 않았습니다.
  - 발견: 골격 생성(skeleton_gen)
  - 조치: 해당 계층 원본 파일이 없어 산출물을 만들지 않았습니다. 원본 확보 여부를 확인하세요.
- **CDATA_SIMPLIFIED** — 특수문자(&/</>)가 없어 불필요했던 CDATA 블록 6개를 일반 텍스트로 정리했습니다. 특수문자가 있어 실제로 필요한 CDATA 0개는 MyBatis가 CDATA를 그대로 지원하므로 그대로 유지했습니다(엔티티 이스케이프로 억지 변환하지 않음).
  - 발견: Mapper 변환(converters)
  - 조치: CDATA 처리를 단순화했습니다. SQL 의미가 바뀌지 않았는지 확인하세요.
- **FETCH_SIZE_DROPPED** — fetchSize 속성은 MyBatis 변환 시 제거했습니다 - 필요하면 <select>에 수동으로 다시 넣으세요.
  - 발견: Mapper 변환(converters)
  - 조치: fetchSize 속성을 제거했습니다. 성능이 중요하면 MyBatis 설정으로 다시 지정하세요.
- **ORIGINAL_BUG** (메서드 `fAuthCheck`, 52행) — 52행: 원본 버그(포팅 시 보존, 임의 수정 안 함) - 원본은 IRecordSet.getRecordCount() 전제이나, 포팅 후 store 반환 타입 구조가 고정되지 않아 AUTH_LIST 단건/기타 형태일 때 원본과 1:1 대응 구조를 확정할 수 없음
  - 발견: 품질·취약점 스캔(Pla049Service.java)
  - 조치: 원본에 있던 결함을 고치지 않고 그대로 옮긴 지점입니다(의도된 동작). 업무 규칙을 아는 사람이 고칠지 유지할지 판단해야 합니다.

</details>

## 자동 변환된 산출물

| 파일 | TO-BE 경로 | 변환 방식 |
|---|---|---|
| Pla049Service.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/service/Pla049Service.java` | RULE_BASED_SKELETON + LLM_PORTING |
| Pla049Store.java | `gscm/src/main/java/com/skhynix/gscm/r/pm/pla/store/Pla049Store.java` | RULE_BASED |
| Pla049Mapper.xml | `gscm/src/main/resources/mapper/r/pm/pla/Pla049Mapper.xml` | RULE_BASED |

## LLM이 포팅한 메서드 (반드시 사람 리뷰)

생성 코드 첫 줄의 `// AI 변경 요약:` 주석에 무엇을 어떻게 옮겼는지 적혀 있습니다.

- `fAuthCheck`
- `fPLA049QrySelectMainList`
- `fPLA049QrySelectDetail`
