package com.finledger.controller;

import com.finledger.repository.FlagRepository;
import com.finledger.repository.UserRepository;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
public class LedgerController {

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private FlagRepository flagRepository;

    @Autowired
    private UserRepository userRepository;

    @GetMapping("/api/ledger/entries")
    public ResponseEntity<?> entries(HttpSession session) {
        if (SessionAuth.currentUser(session, userRepository).isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id, description, amount, category FROM ledger_entries ORDER BY id"
        );
        return ResponseEntity.ok(Map.of("entries", rows));
    }

    @GetMapping("/api/ledger/search")
    public ResponseEntity<?> search(@RequestParam(defaultValue = "") String q, HttpSession session) {
        if (SessionAuth.currentUser(session, userRepository).isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        String sql = "SELECT id, description, amount FROM ledger_entries WHERE description LIKE '%" + q + "%'";
        List<Map<String, Object>> results = jdbcTemplate.queryForList(sql);
        return ResponseEntity.ok(Map.of("results", results));
    }

    @GetMapping("/api/ledger/secret")
    public ResponseEntity<?> ledgerSecret(HttpSession session) {
        var user = SessionAuth.currentUser(session, userRepository);
        if (user.isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        if (!"analyst".equals(user.get().getUsername())) {
            return ResponseEntity.status(403).body(Map.of("error", "Access restricted to analyst account"));
        }
        // From env, not the flags table (only flag_4 stays in the DB so the
        // flag_4 SQLi UNION cannot dump flag_3).
        String flagValue = System.getenv().getOrDefault("FLAG_3", "unknown");
        return ResponseEntity.ok(Map.of("secret", flagValue));
    }
}
