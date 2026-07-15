package com.finledger.controller;

import com.finledger.repository.FlagRepository;
import com.finledger.repository.UserRepository;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@RestController
public class AdminController {

    @Autowired
    private FlagRepository flagRepository;

    @Autowired
    private UserRepository userRepository;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @GetMapping("/api/admin/dashboard")
    public ResponseEntity<?> dashboard(HttpSession session) {
        var user = SessionAuth.currentUser(session, userRepository);
        if (user.isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        return ResponseEntity.ok(Map.of(
                "status", "ok",
                "entries_today", 14,
                "pending_approvals", 3
        ));
    }

    @GetMapping("/api/reports/mine")
    public ResponseEntity<?> myReport(HttpSession session) {
        var user = SessionAuth.currentUser(session, userRepository);
        if (user.isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id, owner, title, body, escalation_ref FROM access_reports WHERE owner = ? ORDER BY id LIMIT 1",
                user.get().getUsername()
        );
        if (rows.isEmpty()) {
            return ResponseEntity.status(404).body(Map.of("error", "No report for this account"));
        }
        return ResponseEntity.ok(Map.of("report", serializeReport(rows.get(0))));
    }

    @GetMapping("/api/reports/{id}")
    public ResponseEntity<?> reportById(@PathVariable Long id, HttpSession session) {
        if (SessionAuth.currentUser(session, userRepository).isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id, owner, title, body, escalation_ref FROM access_reports WHERE id = ?",
                id
        );
        if (rows.isEmpty()) {
            return ResponseEntity.status(404).body(Map.of("error", "Report not found"));
        }
        // MISSING per-object authorization: should verify owner == current user.
        return ResponseEntity.ok(Map.of("report", serializeReport(rows.get(0))));
    }

    @GetMapping("/api/reports/executive")
    public ResponseEntity<?> executiveReport(HttpServletRequest request) {
        TokenUtil.Claims claims = TokenUtil.verify(readCookie(request, "fin_access"));
        if (claims == null) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        if (!"ADMIN".equals(claims.role())) {
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

    private Map<String, Object> serializeReport(Map<String, Object> row) {
        String body = String.valueOf(row.get("body"))
                .replace("__FLAG_1__", System.getenv().getOrDefault("FLAG_1", "unknown"));
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("id", row.get("id"));
        report.put("owner", row.get("owner"));
        report.put("title", row.get("title"));
        report.put("body", body);
        report.put("escalation_ref", row.get("escalation_ref"));
        return report;
    }

    private String readCookie(HttpServletRequest request, String name) {
        Cookie[] cookies = request.getCookies();
        if (cookies == null) {
            return "";
        }
        for (Cookie cookie : cookies) {
            if (name.equals(cookie.getName())) {
                return cookie.getValue();
            }
        }
        return "";
    }
}
