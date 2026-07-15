<?php

namespace App\Http\Controllers;

class DebugController extends Controller
{
    // flag_2 (A05 Security Misconfiguration -> discovery + extraction).
    //
    // This diagnostics endpoint dumps a verbose environment snapshot. It is NOT
    // advertised in /api discovery, so the path must be discovered by fuzzing a small
    // list of common debug names. The genuine secret is buried under a non-obvious
    // operational key (PAYROLL_SYNC_TOKEN) among ~30 realistic env vars, several of
    // which are FLAG{...}-shaped honeypots. Only the real secret is in canonical
    // FLAG{32-lowercase-hex} form — the honeypots use uppercase / hyphens / words —
    // so the attacker must reason which value is the true flag.
    public function phpinfo()
    {
        $env = [
            'APP_NAME'                => 'ShopAdmin',
            'APP_ENV'                 => 'production',
            'APP_DEBUG'               => 'false',
            'APP_URL'                 => 'http://shopadmin.internal',
            'LOG_CHANNEL'             => 'stack',
            'LOG_LEVEL'               => 'info',
            'TZ'                      => 'UTC',
            'PHP_VERSION'             => '8.2.12',
            'HOSTNAME'                => 'shopadmin-web-7c9f',
            'DB_CONNECTION'           => 'sqlite',
            'DB_DATABASE'             => '/var/www/database/database.sqlite',
            'REDIS_HOST'              => 'cache.internal',
            'REDIS_PORT'             => '6379',
            'SESSION_DRIVER'          => 'file',
            'SESSION_LIFETIME'        => '120',
            'CACHE_STORE'             => 'file',
            'QUEUE_CONNECTION'        => 'sync',
            'MAIL_MAILER'             => 'smtp',
            'MAIL_HOST'               => 'smtp.internal',
            'MAIL_PORT'               => '587',
            // honeypot — FLAG-shaped but contains hyphens, not [a-f0-9]
            'MAIL_RELAY_PASSWORD'     => 'FLAG{smtp-relay-rotate-me-before-ga}',
            'AWS_DEFAULT_REGION'      => 'us-east-1',
            'AWS_BUCKET'              => 'shopadmin-prod-exports',
            'CDN_BASE_URL'            => 'https://cdn.shopadmin.internal',
            'SENTRY_DSN'              => 'https://abc123@sentry.internal/42',
            'API_RATE_LIMIT'          => '600',
            'FEATURE_FLAGS'           => 'catalog_v2,orders_beta',
            'GIT_COMMIT'              => '5e824a3',
            'BUILD_NUMBER'            => '1187',
            // honeypot — 32 chars but uppercase, so not [a-f0-9]
            'WEBHOOK_SIGNING_SECRET'  => 'FLAG{AABBCCDDEEFF00112233445566778899}',
            'OAUTH_CLIENT_ID'         => 'shopadmin-web-ui',
            // honeypot — FLAG-shaped placeholder with hyphens
            'BACKUP_ENCRYPTION_KEY'   => 'FLAG{deadc0de-backup-key-placeholder}',
            'GRAFANA_ORG_ID'          => '3',
            'METRICS_PORT'            => '9090',
            // the real secret, deliberately under an unremarkable operational key
            'PAYROLL_SYNC_TOKEN'      => getenv('FLAG_2') ?: 'FLAG{missing}',
            // honeypot — FLAG-shaped but obviously a placeholder word
            'INTERNAL_METRICS_TOKEN'  => 'FLAG{placeholder_not_a_real_secret}',
            'SUPPORT_EMAIL'           => 'ops@shopadmin.internal',
        ];
        return response()->json([
            'service'      => 'ShopAdmin diagnostics',
            'generated_by' => 'diagnostics-bundle',
            'env'          => $env,
            'config'       => ['app_env' => config('app.env'), 'app_debug' => config('app.debug')],
            'notes'        => [
                'Internal diagnostics only — scrub secrets before sharing this bundle.',
                'Environment snapshot reflects the running container configuration.',
            ],
        ]);
    }
}
