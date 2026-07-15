package com.finledger.controller;

import com.finledger.repository.FlagRepository;
import com.finledger.repository.UserRepository;
import jakarta.servlet.http.HttpSession;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.Map;

@RestController
public class LedgerController {

    private static final byte[] EXPORT_KEYSTREAM = buildExportKeystream();

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

    @GetMapping("/api/ledger/entries/{id}")
    public ResponseEntity<?> entry(@PathVariable Long id, HttpSession session) {
        if (SessionAuth.currentUser(session, userRepository).isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                "SELECT id, description, amount, category FROM ledger_entries WHERE id = ?",
                id
        );
        if (rows.isEmpty()) {
            return ResponseEntity.status(404).body(Map.of("error", "Ledger entry not found"));
        }
        return ResponseEntity.ok(Map.of("entry", rows.get(0)));
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
        return ResponseEntity.ok(Map.of(
                "message",
                "Ledger secrets are no longer available in plaintext; use /exports/encrypted?item=vault."
        ));
    }

    @GetMapping("/exports/encrypted")
    public ResponseEntity<?> exportsEncrypted(@RequestParam(defaultValue = "") String item, HttpSession session) {
        if (SessionAuth.currentUser(session, userRepository).isEmpty()) {
            return ResponseEntity.status(401).body(Map.of("error", "Login required"));
        }
        byte[] plaintext;
        if ("vault".equals(item)) {
            plaintext = System.getenv().getOrDefault("FLAG_3", "FLAG{missing}").getBytes(StandardCharsets.UTF_8);
        } else {
            List<Map<String, Object>> rows = jdbcTemplate.queryForList(
                    "SELECT description FROM ledger_entries WHERE id = ?",
                    item
            );
            if (rows.isEmpty()) {
                return ResponseEntity.status(404).body(Map.of("error", "unknown item"));
            }
            plaintext = String.valueOf(rows.get(0).get("description")).getBytes(StandardCharsets.UTF_8);
        }
        if ("vault".equals(item)) {
            return ResponseEntity.ok(Map.of("item", item, "cipher_hex", xorExport(plaintext)));
        }
        // self-contained crib for the reused-keystream recovery
        return ResponseEntity.ok(Map.of(
                "item", item,
                "cipher_hex", xorExport(plaintext),
                "plaintext", new String(plaintext, StandardCharsets.UTF_8)));
    }

    private static byte[] buildExportKeystream() {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest("finledger-export-key-2024".getBytes(StandardCharsets.UTF_8));
            byte[] out = new byte[digest.length * 8];
            for (int i = 0; i < out.length; i++) {
                out[i] = digest[i % digest.length];
            }
            return out;
        } catch (Exception e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }

    private static String xorExport(byte[] plaintext) {
        StringBuilder out = new StringBuilder(plaintext.length * 2);
        for (int i = 0; i < plaintext.length; i++) {
            out.append(String.format("%02x", (plaintext[i] ^ EXPORT_KEYSTREAM[i]) & 0xff));
        }
        return out.toString();
    }
}
