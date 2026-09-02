package com.skhynix.gscm.r.pm.pla.Controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import com.skhynix.gscm.r.pm.pla.dto.*;
import java.util.List;
import java.util.Map;

// TODO: 원본 P BizUnit의 화면 검증 로직 유무를 다시 한번 확인할 것(PLA047은 순수 위임이었음, 다른 화면은 표본 확대 전)
@RestController
@RequestMapping("/api/pm/pla")
public class Pla011Api {

    @Autowired
    private Pla011Service service;

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/01")
    public ResponseEntity<Map<String, Object>> pPLA01101(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.fAuthCheck(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/02")
    public ResponseEntity<Map<String, Object>> pPLA01102(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.fPLA011QrySelectDetail(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/03")
    public ResponseEntity<List<HistoryqryDto>> pPLA01103(@RequestBody HistoryqryDto dto) {
        return ResponseEntity.ok(service.historyqry(dto));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/04")
    public ResponseEntity<List<ExceldownqryDto>> pPLA01104(@RequestBody ExceldownqryDto dto) {
        return ResponseEntity.ok(service.exceldownqry(dto));
    }

}