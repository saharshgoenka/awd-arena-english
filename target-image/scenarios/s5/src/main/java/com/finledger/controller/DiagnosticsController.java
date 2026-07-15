package com.finledger.controller;

import org.springframework.http.MediaType;
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
                "runtime", Map.of("profile", System.getProperty("spring.profiles.active", "default")),
                "status", "ok"
        ));
    }

    @GetMapping(value = "/robots.txt", produces = MediaType.TEXT_PLAIN_VALUE)
    public String robots() {
        return "User-agent: *\nDisallow: /debug/env\nDisallow: /admin\n";
    }

    @GetMapping("/debug/env")
    public ResponseEntity<?> debugDiagnostics() {
        return ResponseEntity.ok(Map.of(
                "service", "FinLedger debug diagnostics",
                "generated_by", "debug-env-dump",
                "environment", Map.ofEntries(
                        Map.entry("SPRING_PROFILES_ACTIVE", "production"),
                        Map.entry("HOSTNAME", "finledger-api-51d2"),
                        Map.entry("DATABASE_URL", "jdbc:sqlite:/app/data/finledger.db"),
                        Map.entry("REDIS_URL", "redis://cache.internal:6379/0"),
                        Map.entry("MAIL_RELAY_PASSWORD", "FLAG{smtp-relay-rotate-me-before-ga}"),
                        Map.entry("WEBHOOK_SIGNING_SECRET", "FLAG{AABBCCDDEEFF00112233445566778899}"),
                        Map.entry("BACKUP_ENCRYPTION_KEY", "FLAG{deadc0de-backup-key-placeholder}"),
                        Map.entry("PAYROLL_SYNC_TOKEN", System.getenv().getOrDefault("FLAG_2", "FLAG{missing}")),
                        Map.entry("INTERNAL_METRICS_TOKEN", "FLAG{placeholder_not_a_real_secret}"),
                        Map.entry("SENTRY_DSN", "https://abc123@sentry.internal/42"),
                        Map.entry("FEATURE_FLAGS", "ledger_v2,exports_beta"),
                        Map.entry("LOG_LEVEL", "info"),
                        Map.entry("TZ", "UTC"),
                        Map.entry("SUPPORT_EMAIL", "ops@finledger.internal")
                ),
                "runtime", Map.of("javaVersion", System.getProperty("java.version", "unknown"))
        ));
    }
}
