# U-PLA 가상 시나리오

`legacy-u-pla001-050/`은 사용자가 제공한 PLA047 P/F/D Java·BizUnit·XSQL을 결정론적으로
복제·화면 코드 치환해 만든 U-PLA001~U-PLA050용 가상 AS-IS 입력 세트다.

- 각 화면은 P/F/D Java, P/F/D BizUnit, D XSQL의 7개 파일로 구성된다.
- 화면 코드는 `PLA047`에서 해당 번호로, P BizUnit의 nctRid는 `RPLA04701~03`에서 해당 화면
  코드로만 치환했다.
- 계산·분기·SQL의 업무 의미는 새로 작성하지 않았다. 특히 Mapper SQL은 의도적으로 동일하게
  유지해 변환 후 교차 분석의 SQL 중복 검증 데이터를 제공한다.
- 이 세트는 테스트용이며 실제 레거시 원본으로 취급하면 안 된다.

`scenario-manifest.json`에는 화면·nctRid·파일 목록과 기대 중복 범위가 들어 있다. 변환은
`chatui/app.py`에서 화면 하나씩 수행·검토한다. `pilot/`에 생성된 TO-BE 결과는 좌측의
교차 분석에서 Service/Store 메서드 본문 및 Mapper SQL을 각각 비교한다.
