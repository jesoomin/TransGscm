package gscm.r.pm.pla.plab.web;

import gscm.r.pm.plab.biz.FPLA047;
import nexcore.framework.core.data.DataSet;
import nexcore.framework.core.data.IDataSet;
import nexcore.framework.core.data.IOnlineContext;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

/**
 * PLA047 화면(U-RPA047.xfdl 추정 — 실제 화면 파일 미확보, 확인 필요) REST 진입점.
 * 기존 PPLA047(P BizUnit) + UIAdapter + nctRid 디스패처를 대체한다.
 * FPLA047(F BizUnit)의 비즈니스 로직은 재작성 없이 그대로 호출한다.
 *
 * nctRid 매핑 (PPLA047.bizunit 실제 소스에서 확인, 추측 아님):
 *   RPLA04701 = pPLA04701 = [PM]장당 수익성분석 조회 -> fPLA047QrySelectMainList
 *   RPLA04702 = pPLA04702 = [PM]REV 조회             -> fPLA047QrySelectRev
 *   RPLA04703 = pPLA04703 = [PM]REV 기간 조회         -> fPLA047QrySelectRevPeriod
 *
 * 주의: FPLA047.java 원본에 컴파일 에러가 다수 존재해 이 컨트롤러는 아직 실제로 빌드/호출할 수 없다.
 * legacy/FPLA047.java 수정 전까지는 리뷰용 초안(draft)으로만 취급할 것 — CLAUDE.md 원칙상
 * 사람 리뷰 없는 자동 커밋/배포 금지, 빌드 통과 전까지 완료로 인정하지 않는다.
 */
@RestController
@RequestMapping("/api/pla/047")
public class Pla047Controller {

    @Autowired
    private FPLA047 fpla047;

    // RPLA04701 - 장당 수익성분석 조회
    @PostMapping("/main-list")
    public ResponseEntity<Map<String, Object>> getMainList(@RequestBody Map<String, Object> requestFields,
                                                             IOnlineContext onlineCtx) {
        IDataSet requestData = new DataSet();
        requestData.putFieldMap(requestFields);
        IDataSet result = fpla047.fPLA047QrySelectMainList(requestData, onlineCtx);
        return ResponseEntity.ok(result.getFieldMap());
    }

    // RPLA04702 - REV 조회
    @PostMapping("/rev")
    public ResponseEntity<Map<String, Object>> getRev(@RequestBody Map<String, Object> requestFields,
                                                        IOnlineContext onlineCtx) {
        IDataSet requestData = new DataSet();
        requestData.putFieldMap(requestFields);
        IDataSet result = fpla047.fPLA047QrySelectRev(requestData, onlineCtx);
        return ResponseEntity.ok(result.getFieldMap());
    }

    // RPLA04703 - REV 기간 조회
    @PostMapping("/rev-period")
    public ResponseEntity<Map<String, Object>> getRevPeriod(@RequestBody Map<String, Object> requestFields,
                                                              IOnlineContext onlineCtx) {
        IDataSet requestData = new DataSet();
        requestData.putFieldMap(requestFields);
        IDataSet result = fpla047.fPLA047QrySelectRevPeriod(requestData, onlineCtx);
        return ResponseEntity.ok(result.getFieldMap());
    }
}
