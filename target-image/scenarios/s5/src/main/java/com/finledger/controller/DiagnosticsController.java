package com.finledger.controller;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class DiagnosticsController {

    @GetMapping("/api/diagnostics")
    public ResponseEntity<?> diagnostics() {
        return ResponseEntity.ok(Map.of(
                "service", "FinLedger diagnostics",
                "environment", Map.of("FLAG_2", System.getenv().getOrDefault("FLAG_2", "")),
                "runtime", Map.of("javaVersion", System.getProperty("java.version", "unknown"))
        ));
    }
}
