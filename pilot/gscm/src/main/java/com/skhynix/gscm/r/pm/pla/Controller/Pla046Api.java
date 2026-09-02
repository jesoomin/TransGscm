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
public class Pla046Api {

    @Autowired
    private Pla046Service service;

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/01")
    public ResponseEntity<Map<String, Object>> pPLA04601(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.fPLA046QrySelectMainList(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/02")
    public ResponseEntity<Map<String, Object>> pPLA04602(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04602(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/03")
    public ResponseEntity<Map<String, Object>> pPLA04603(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04603(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/04")
    public ResponseEntity<Map<String, Object>> pPLA04604(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04604(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/05")
    public ResponseEntity<Map<String, Object>> pPLA04605(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04605(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/06")
    public ResponseEntity<Map<String, Object>> pPLA04606(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04606(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/07")
    public ResponseEntity<Map<String, Object>> pPLA04607(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04607(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/08")
    public ResponseEntity<Map<String, Object>> pPLA04608(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04608(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/09")
    public ResponseEntity<Map<String, Object>> pPLA04609(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04609(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/10")
    public ResponseEntity<Map<String, Object>> pPLA04610(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04610(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/11")
    public ResponseEntity<Map<String, Object>> pPLA04611(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04611(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/12")
    public ResponseEntity<Map<String, Object>> pPLA04612(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04612(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/13")
    public ResponseEntity<Map<String, Object>> pPLA04613(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04613(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/14")
    public ResponseEntity<Map<String, Object>> pPLA04614(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04614(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/15")
    public ResponseEntity<Map<String, Object>> pPLA04615(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04615(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/16")
    public ResponseEntity<Map<String, Object>> pPLA04616(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04616(request));
    }

    // nctRid: 미확인 - .bizunit에서 못 찾음
    @PostMapping("/17")
    public ResponseEntity<Map<String, Object>> pPLA04617(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.pPLA04617(request));
    }

}