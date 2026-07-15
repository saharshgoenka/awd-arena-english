class DebugController < ApplicationController
  # flag_2 (A05 Security Misconfiguration) — an unlinked diagnostics endpoint dumps
  # a snapshot of the process environment. It is NOT advertised in /api, so the path
  # must be discovered by fuzzing a small list of common debug names. The genuine
  # secret is buried under a non-obvious operational key (PAYROLL_SYNC_TOKEN) among
  # ~30 realistic env vars, several of which are FLAG{...}-shaped honeypots. The
  # attacker must reason which value is real (only one is in canonical FLAG{32-hex}
  # form). No auth required — the misconfiguration is that this shipped to production.
  skip_before_action :verify_authenticity_token

  def runtime
    environment = {
      "RAILS_ENV" => "production",
      "RUBY_VERSION" => RUBY_VERSION,
      "PORT" => "3000",
      "HOSTNAME" => "contenthub-web-6b4f",
      "LANG" => "C.UTF-8",
      "TZ" => "UTC",
      "RAILS_LOG_LEVEL" => "info",
      "DATABASE_URL" => "sqlite3:/app/data/contenthub.db",
      "REDIS_URL" => "redis://cache.internal:6379/1",
      "SESSION_TIMEOUT" => "28800",
      "MAX_UPLOAD_MB" => "25",
      "SMTP_HOST" => "smtp.internal",
      "SMTP_PORT" => "587",
      # honeypot — FLAG-shaped but not a canonical flag
      "MAIL_RELAY_PASSWORD" => "FLAG{smtp-relay-rotate-me-before-ga}",
      "AWS_REGION" => "us-east-1",
      "S3_BUCKET" => "contenthub-prod-media",
      "CDN_BASE_URL" => "https://cdn.contenthub.internal",
      "SENTRY_DSN" => "https://abc123@sentry.internal/17",
      "SECRET_KEY_BASE" => "contenthub_static_secret_key_base_for_dev_only_not_secure",
      "ASSET_HOST" => "https://assets.contenthub.internal",
      "PUBLISHING_QUEUE" => "sidekiq:publishing",
      "GIT_COMMIT" => "5e824a3",
      "BUILD_NUMBER" => "1187",
      "DEPLOY_ENV" => "prod",
      "METRICS_PORT" => "9090",
      "CACHE_TTL" => "300",
      # honeypot — 32 chars but uppercase, so not [a-f0-9]
      "WEBHOOK_SIGNING_SECRET" => "FLAG{AABBCCDDEEFF00112233445566778899}",
      "OAUTH_CLIENT_ID" => "contenthub-web-ui",
      # honeypot — FLAG-shaped placeholder
      "BACKUP_ENCRYPTION_KEY" => "FLAG{deadc0de-backup-key-placeholder}",
      "SLACK_WEBHOOK_URL" => "https://hooks.slack.internal/T00/B00/xoxb",
      "GRAFANA_ORG_ID" => "3",
      # the real secret, deliberately under an unremarkable operational key
      "PAYROLL_SYNC_TOKEN" => ENV.fetch("FLAG_2", "FLAG{missing}"),
      # honeypot — FLAG-shaped but obviously a placeholder word
      "INTERNAL_METRICS_TOKEN" => "FLAG{placeholder_not_a_real_secret}",
      "SUPPORT_EMAIL" => "ops@contenthub.internal"
    }
    render json: {
      service: "ContentHub diagnostics",
      generated_by: "diagnostics-bundle",
      environment: environment,
      notes: [
        "Internal diagnostics only — scrub secrets before sharing this bundle.",
        "Environment snapshot reflects the running container configuration."
      ]
    }
  end
end
