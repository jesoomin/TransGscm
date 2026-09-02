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
public class Pla047Api {

    @Autowired
    private Pla047Service service;

    // nctRid: RPLA04701
    @PostMapping("/rpla04701")
    public ResponseEntity<Map<String, Object>> pPLA04701(@RequestBody Map<String, Object> request) {
        return ResponseEntity.ok(service.fPLA047QrySelectMainList(request));
    }

    // nctRid: RPLA04702
    @PostMapping("/rpla04702")
    public ResponseEntity<List<Pla04701Dto>> pPLA04702(@RequestBody Pla04701Dto dto) {
        return ResponseEntity.ok(service.pla04701(dto));
    }

    // nctRid: RPLA04703
    @PostMapping("/rpla04703")
    public ResponseEntity<List<Pla04706Dto>> pPLA04703(@RequestBody Pla04706Dto dto) {
        return ResponseEntity.ok(service.pla04706(dto));
    }

}