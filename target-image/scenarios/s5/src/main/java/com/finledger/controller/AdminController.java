package com.finledger.controller;

import com.finledger.repository.FlagRepository;
import com.finledger.repository.UserRepository;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class AdminController {

    @Autowired
    private FlagRepository flagRepository;

    @Autowired
    private UserRepository userRepository;

    @GetMapping("/api/admin/dashboard")
    public ResponseEntity<?> dashboard(HttpSession session) {
        var user = SessionAuth.currentUser(session, userRepository);
        if (user.isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        // From env, not the flags table (only flag_4 stays in the DB so the
        // flag_4 SQLi UNION cannot dump flag_1).
        String flagValue = System.getenv().getOrDefault("FLAG_1", "unknown");
        return ResponseEntity.ok(Map.of(
                "status", "ok",
                "system_token", flagValue,
                "entries_today", 14,
                "pending_approvals", 3
        ));
    }

    @GetMapping("/api/reports/executive")
    public ResponseEntity<?> executiveReport(HttpSession session) {
        var user = SessionAuth.currentUser(session, userRepository);
        if (user.isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        if (!"ADMIN".equals(user.get().getRole())) {
            return ResponseEntity.status(403).body(Map.of("error", "Admin role required"));
        }
        // From env, not the flags table (only flag_4 stays in the DB so the
        // flag_4 SQLi UNION cannot dump flag_5).
        String flagValue = System.getenv().getOrDefault("FLAG_5", "unknown");
        return ResponseEntity.ok(Map.of(
                "report", "Executive Financial Summary Q4",
                "total_revenue", 1425000.00,
                "total_expenses", 98650.00,
                "internal_ref", flagValue
        ));
    }
}
