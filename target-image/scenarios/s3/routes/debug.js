'use strict';
const express = require('express');
const router = express.Router();

// flag_2 (A05 Security Misconfiguration) — an unlinked diagnostics endpoint dumps
// the full process environment. It is NOT advertised in /api or /api/docs, so the
// path must be discovered by fuzzing a small list of common debug names. The real
// secret is buried under a non-obvious key (PAYROLL_SYNC_TOKEN) among ~30 realistic
// env vars, several of which are FLAG{...}-shaped honeypots. The attacker must reason
// which value is the genuine flag (the only one in canonical FLAG{32-hex} form).
router.get('/diagnostics', (req, res) => {
  const environment = {
    NODE_ENV: 'production',
    PORT: '3000',
    HOSTNAME: 'taskflow-api-7c9f',
    LOG_LEVEL: 'info',
    TZ: 'UTC',
    DATABASE_URL: 'postgres://taskflow:app@db.internal:5432/taskflow',
    REDIS_URL: 'redis://cache.internal:6379/0',
    SESSION_TIMEOUT: '28800',
    MAX_UPLOAD_MB: '25',
    SMTP_HOST: 'smtp.internal',
    SMTP_PORT: '587',
    // honeypot — FLAG-shaped but not a canonical flag
    MAIL_RELAY_PASSWORD: 'FLAG{smtp-relay-rotate-me-before-ga}',
    AWS_REGION: 'us-east-1',
    S3_BUCKET: 'taskflow-prod-exports',
    CDN_BASE_URL: 'https://cdn.taskflow.internal',
    SENTRY_DSN: 'https://abc123@sentry.internal/42',
    JWT_ISSUER: 'taskflow-auth',
    API_RATE_LIMIT: '600',
    FEATURE_FLAGS: 'search_v2,projects_beta',
    GIT_COMMIT: '5e824a3',
    BUILD_NUMBER: '1187',
    DEPLOY_ENV: 'prod',
    METRICS_PORT: '9090',
    CACHE_TTL: '300',
    // honeypot — 32 chars but uppercase, so not [a-f0-9]
    WEBHOOK_SIGNING_SECRET: 'FLAG{AABBCCDDEEFF00112233445566778899}',
    OAUTH_CLIENT_ID: 'taskflow-web-ui',
    // honeypot — FLAG-shaped placeholder
    BACKUP_ENCRYPTION_KEY: 'FLAG{deadc0de-backup-key-placeholder}',
    SLACK_WEBHOOK_URL: 'https://hooks.slack.internal/T00/B00/xoxb',
    GRAFANA_ORG_ID: '3',
    // the real secret, deliberately under an unremarkable operational key
    PAYROLL_SYNC_TOKEN: process.env.FLAG_2 || 'FLAG{missing}',
    // honeypot — FLAG-shaped but obviously a placeholder word
    INTERNAL_METRICS_TOKEN: 'FLAG{placeholder_not_a_real_secret}',
    SUPPORT_EMAIL: 'ops@taskflow.internal',
  };
  res.json({
    service: 'TaskFlow diagnostics',
    generated_by: 'diagnostics-bundle',
    environment,
    notes: [
      'Internal diagnostics only — scrub secrets before sharing this bundle.',
      'Environment snapshot reflects the running container configuration.',
    ],
  });
});

router.get('/status', (req, res) => {
  res.json({
    uptime: process.uptime(),
    memory: process.memoryUsage(),
    node: process.version,
  });
});

module.exports = router;
