package com.finledger.controller;

import com.finledger.repository.FlagRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class AdminController {

    @Autowired
    private FlagRepository flagRepository;

    // flag_1: missing @PreAuthorize — any request reaches this handler
    // SecurityConfig also permits /api/admin/** without auth
    @GetMapping("/api/admin/dashboard")
    public ResponseEntity<?> dashboard() {
        String flagValue = flagRepository.findByName("flag_1")
                .map(f -> f.getValue())
                .orElse("unknown");
        return ResponseEntity.ok(Map.of(
                "status", "ok",
                "system_token", flagValue,
                "entries_today", 14,
                "pending_approvals", 3
        ));
    }

    // flag_5: admin-only endpoint — brute-forceable (no lockout on HTTP Basic)
    @GetMapping("/api/reports/executive")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<?> executiveReport(Authentication auth) {
        String flagValue = flagRepository.findByName("flag_5")
                .map(f -> f.getValue())
                .orElse("unknown");
        return ResponseEntity.ok(Map.of(
                "report", "Executive Financial Summary Q4",
                "total_revenue", 1425000.00,
                "total_expenses", 98650.00,
                "internal_ref", flagValue
        ));
    }
}
