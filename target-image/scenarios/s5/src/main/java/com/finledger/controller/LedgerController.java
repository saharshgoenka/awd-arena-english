package com.finledger.controller;

import com.finledger.repository.FlagRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.Authentication;
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

    // GET /api/ledger/entries — list all ledger entries
    @GetMapping("/api/ledger/entries")
    public ResponseEntity<?> entries(Authentication auth) {
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id, description, amount, category FROM ledger_entries ORDER BY id"
        );
        return ResponseEntity.ok(Map.of("entries", rows));
    }

    // flag_4: SQL injection via string concatenation in JdbcTemplate
    @GetMapping("/api/ledger/search")
    public ResponseEntity<?> search(@RequestParam(defaultValue = "") String q, Authentication auth) {
        String sql = "SELECT id, description, amount FROM ledger_entries WHERE description LIKE '%" + q + "%'";
        List<Map<String, Object>> results = jdbcTemplate.queryForList(sql);
        return ResponseEntity.ok(Map.of("results", results));
    }

    // flag_3 target: analyst-only endpoint
    @GetMapping("/api/ledger/secret")
    public ResponseEntity<?> ledgerSecret(Authentication auth) {
        if (!auth.getName().equals("analyst")) {
            return ResponseEntity.status(403).body(Map.of("error", "Access restricted to analyst account"));
        }
        String flagValue = flagRepository.findByName("flag_3")
                .map(f -> f.getValue())
                .orElse("unknown");
        return ResponseEntity.ok(Map.of("secret", flagValue));
    }
}
