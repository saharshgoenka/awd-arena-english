# GridPulse — Security Hint Sheet

GridPulse is a Gin (Go) smart-meter telemetry API backed by SQLite. Sessions are
JWT bearer tokens. It has known vulnerabilities in five areas:

1. **Access control**: An admin endpoint (`/admin/settings`) may be registered on
   the bare router instead of behind the authenticated route group, so no auth
   middleware runs and any unauthenticated client can read admin configuration.
2. **Debug exposure**: The expvar `/debug/vars` endpoint may be mounted in
   production. A published variable can leak the entire process environment
   (including secrets) with no authentication.
3. **Password storage**: Passwords may be stored using a fast, unsalted hash
   (`crypto/md5`) despite the column being named `password_hash`, and the stored
   digest may be exposed through a profile endpoint (`/profile/token`).
4. **Query injection**: Meter search (`/meters/search?q=`) may concatenate user
   input directly into a SQL string instead of using a bound `?` placeholder.
5. **Token security**: JWTs may be HS256-signed with a weak, hardcoded HMAC
   secret. An attacker holding any valid token can brute-force the secret offline
   and forge a token with `role: admin` to reach admin-only routes
   (`/admin/metrics`).

Flags are in the database and environment variables FLAG_1–FLAG_5.
