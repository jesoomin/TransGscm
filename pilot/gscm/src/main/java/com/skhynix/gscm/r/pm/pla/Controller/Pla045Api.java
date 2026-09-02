package com.skhynix.gscm.r.pm.pla.Controller;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

// TODO: 원본 P BizUnit의 화면 검증 로직 유무를 다시 한번 확인할 것(PLA047은 순수 위임이었음, 다른 화면은 표본 확대 전)
@RestController
@RequestMapping("/api/pm/pla")
public class Pla045Api {

    @Autowired
    private Pla045Service service;

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/01")
    public ResponseEntity<Map<String, Object>> pPLA04501(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04501(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/02")
    public ResponseEntity<Map<String, Object>> PPLA04502(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.PPLA04502(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/03")
    public ResponseEntity<Map<String, Object>> PPLA04503(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.PPLA04503(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/04")
    public ResponseEntity<Map<String, Object>> PPLA04504(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.PPLA04504(request));
    }

}