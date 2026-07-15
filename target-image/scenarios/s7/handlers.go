package main

import (
	"encoding/hex"
	"encoding/json"
	"net/http"
	"os"
	"strings"
)

type credentials struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

func robotsHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	_, _ = w.Write([]byte("User-agent: *\nDisallow: /debug/env\nDisallow: /admin\n"))
}

func loginHandler(w http.ResponseWriter, r *http.Request) {
	var creds credentials
	if err := json.NewDecoder(r.Body).Decode(&creds); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]string{"error": "Invalid request"})
		return
	}
	user := findUserByUsername(creds.Username)
	// flag_5 (A07): no rate limiting, and distinct error messages for an unknown
	// user vs. a wrong password let an attacker enumerate valid usernames.
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "User not found"})
		return
	}
	if !checkPassword(user.PasswordHash, creds.Password) {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Invalid password"})
		return
	}
	setSession(w, user.ID)
	// flag_5 (A07): login also issues a JWT-style bearer token that the admin
	// console route trusts. The verifier honours alg:"none" (see token.go).
	tok := issueToken(user)
	http.SetCookie(w, &http.Cookie{Name: "token", Value: tok, Path: "/", HttpOnly: true})
	writeJSON(w, http.StatusOK, map[string]string{"message": "Login successful", "role": user.Role, "token": tok})
}

func logoutHandler(w http.ResponseWriter, r *http.Request) {
	clearSession(w, r)
	writeJSON(w, http.StatusOK, map[string]string{"message": "Logged out"})
}

func dashboardHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	var vehicleCount int
	_ = db.QueryRow("SELECT COUNT(*) FROM vehicles").Scan(&vehicleCount)
	writeJSON(w, http.StatusOK, map[string]any{
		"user":     user.Username,
		"role":     user.Role,
		"vehicles": vehicleCount,
	})
}

func adminSettingsHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	if user.Role != "admin" {
		writeJSON(w, http.StatusForbidden, map[string]string{"error": "Admin access required"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"config": map[string]any{"maintenance": false, "region": "west"},
	})
}

func adminMetricsHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil || user.Role != "admin" {
		writeJSON(w, http.StatusForbidden, map[string]string{"error": "Admin access required"})
		return
	}
	var vehicleCount, userCount int
	_ = db.QueryRow("SELECT COUNT(*) FROM vehicles").Scan(&vehicleCount)
	_ = db.QueryRow("SELECT COUNT(*) FROM users").Scan(&userCount)
	writeJSON(w, http.StatusOK, map[string]any{
		"total_vehicles": vehicleCount,
		"total_users":    userCount,
	})
}

func telemetryOverviewHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil || user.Role != "telemetry" {
		writeJSON(w, http.StatusForbidden, map[string]string{"error": "Telemetry access required"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"collector": "edge-uplink",
		"region":    "west",
	})
}

// adminConsoleHandler serves flag_5. It authenticates via the JWT-style bearer
// token and grants on role==admin from the token's claims. The token verifier
// (parseToken) accepts alg:"none", so a forged unsigned admin token is trusted.
func adminConsoleHandler(w http.ResponseWriter, r *http.Request) {
	tok := tokenFromRequest(r)
	if tok == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Bearer token required"})
		return
	}
	claims, ok := parseToken(tok)
	if !ok {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Invalid token"})
		return
	}
	if role, _ := claims["role"].(string); role != "admin" {
		writeJSON(w, http.StatusForbidden, map[string]string{"error": "Admin role required"})
		return
	}
	// flag_5 read from env, not the DB, so the flag_4 SQLi cannot dump it.
	writeJSON(w, http.StatusOK, map[string]any{
		"console":        "fleet-admin",
		"internal_token": os.Getenv("FLAG_5"),
	})
}

func debugEnvHandler(w http.ResponseWriter, r *http.Request) {
	// flag_2 (A05 Security Misconfiguration): an unlinked diagnostics endpoint dumps
	// a snapshot of the container environment. It is NOT advertised in /api, so the
	// path must be discovered by fuzzing common debug names. The genuine secret is
	// buried under a non-obvious operational key (PAYROLL_SYNC_TOKEN) among ~30
	// realistic env vars, several of which are FLAG{...}-shaped honeypots. Only the
	// real flag is in canonical FLAG{32-lowercase-hex} form.
	environment := map[string]string{
		"GO_ENV":       "production",
		"PORT":         "3000",
		"HOSTNAME":     "fleetview-api-7c9f",
		"LOG_LEVEL":    "info",
		"TZ":           "UTC",
		"DATABASE_URL": "file:/app/data/fleetview.db",
		"REDIS_URL":    "redis://cache.internal:6379/0",
		"SESSION_TTL":  "28800",
		"MAX_UPLOAD_MB": "25",
		"SMTP_HOST":    "smtp.internal",
		"SMTP_PORT":    "587",
		// honeypot — FLAG-shaped but not a canonical flag
		"MAIL_RELAY_PASSWORD": "FLAG{smtp-relay-rotate-me-before-ga}",
		"AWS_REGION":          "us-west-2",
		"S3_BUCKET":           "fleetview-prod-exports",
		"CDN_BASE_URL":        "https://cdn.fleetview.internal",
		"SENTRY_DSN":          "https://abc123@sentry.internal/42",
		"JWT_ISSUER":          "fleetview-auth",
		"API_RATE_LIMIT":      "600",
		"FEATURE_FLAGS":       "search_v2,dispatch_beta",
		"GIT_COMMIT":          "5e824a3",
		"BUILD_NUMBER":        "1187",
		"DEPLOY_ENV":          "prod",
		"METRICS_PORT":        "9090",
		"CACHE_TTL":           "300",
		// honeypot — 32 chars but uppercase, so not [a-f0-9]
		"WEBHOOK_SIGNING_SECRET": "FLAG{AABBCCDDEEFF00112233445566778899}",
		"OAUTH_CLIENT_ID":        "fleetview-web-ui",
		// honeypot — FLAG-shaped placeholder
		"BACKUP_ENCRYPTION_KEY": "FLAG{deadc0de-backup-key-placeholder}",
		"SLACK_WEBHOOK_URL":     "https://hooks.slack.internal/T00/B00/xoxb",
		"GRAFANA_ORG_ID":        "3",
		// the real secret, deliberately under an unremarkable operational key
		"PAYROLL_SYNC_TOKEN": os.Getenv("FLAG_2"),
		// honeypot — FLAG-shaped but obviously a placeholder word
		"INTERNAL_METRICS_TOKEN": "FLAG{placeholder_not_a_real_secret}",
		"SUPPORT_EMAIL":          "ops@fleetview.internal",
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"go_version":  goVersion(),
		"environment": environment,
	})
}

// encryptedExportHandler serves flag_3. It encrypts known fleet export records
// and the sensitive vault export with the same XOR keystream. A known plaintext
// export such as item=vehicle-1 reveals the keystream, which decrypts item=vault.
func encryptedExportHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	item := r.URL.Query().Get("item")
	plain, ok := exportPlaintext(item)
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Unknown export item"})
		return
	}
	// Reused keystream (no per-message nonce): same mask XORs every item.
	mask := streamMask(exportStreamKey, len(plain))
	cipher := make([]byte, len(plain))
	for i := range plain {
		cipher[i] = plain[i] ^ mask[i]
	}
	resp := map[string]any{"item": item, "cipher_hex": hex.EncodeToString(cipher)}
	if item != "vault" {
		// self-contained crib for the reused-keystream recovery
		resp["plaintext"] = string(plain)
	}
	writeJSON(w, http.StatusOK, resp)
}

// serializeReport injects FLAG_1 from the env at serve time so it is never
// persisted in SQLite (keeping it out of reach of the flag_4 UNION SQLi).
func serializeReport(id int, owner, title, body string, ref int) map[string]any {
	body = strings.ReplaceAll(body, "__FLAG_1__", os.Getenv("FLAG_1"))
	m := map[string]any{"id": id, "owner": owner, "title": title, "body": body}
	if ref > 0 {
		m["escalation_ref"] = ref
	}
	return m
}

// reportsMineHandler returns the caller's own report, which references the admin
// escalation report id via escalation_ref.
func reportsMineHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	row := db.QueryRow(
		"SELECT id, owner, title, body, COALESCE(escalation_ref, 0) FROM reports WHERE owner = ? ORDER BY id LIMIT 1",
		user.Username,
	)
	var id, ref int
	var owner, title, body string
	if err := row.Scan(&id, &owner, &title, &body, &ref); err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "No report for this account"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"report": serializeReport(id, owner, title, body, ref)})
}

// reportShowHandler serves flag_1. It enforces authentication but OMITS the
// per-object owner check (A01 BOLA), so any authenticated caller can read any
// report by id — including the admin escalation record whose id is not advertised
// and must be derived from /reports/mine. Unknown ids fail closed (404).
func reportShowHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	// MISSING per-object authorization: should verify row.owner == user.Username.
	id := r.PathValue("id")
	row := db.QueryRow(
		"SELECT id, owner, title, body, COALESCE(escalation_ref, 0) FROM reports WHERE id = ?",
		id,
	)
	var rid, ref int
	var owner, title, body string
	if err := row.Scan(&rid, &owner, &title, &body, &ref); err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Not found"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"report": serializeReport(rid, owner, title, body, ref)})
}

func profileTokenHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"username": user.Username,
		"role":     user.Role,
	})
}

func profileVaultHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	if user.Username != "vaultdriver" {
		writeJSON(w, http.StatusForbidden, map[string]string{"error": "Driver access only"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"message": "Driver vault", "status": "sealed"})
}

func vehiclesHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	rows, err := db.Query("SELECT id, name, status FROM vehicles ORDER BY id LIMIT 50")
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]string{"error": "query failed"})
		return
	}
	defer rows.Close()
	writeJSON(w, http.StatusOK, map[string]any{"vehicles": scanVehicleRows(rows)})
}

func vehiclesSearchHandler(w http.ResponseWriter, r *http.Request) {
	if currentUser(r) == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	q := r.URL.Query().Get("q")
	// flag_4 (A03 injection): the user-controlled query is concatenated straight
	// into the SQL string instead of using a bound placeholder.
	query := "SELECT id, name, status FROM vehicles WHERE name LIKE '%" + q + "%'"
	rows, err := db.Query(query)
	if err != nil {
		writeJSON(w, http.StatusOK, map[string]any{"results": []any{}})
		return
	}
	defer rows.Close()
	writeJSON(w, http.StatusOK, map[string]any{"results": scanVehicleRows(rows)})
}

func vehicleShowHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	id := r.PathValue("id")
	row := db.QueryRow("SELECT id, name, status FROM vehicles WHERE id = ?", id)
	var vid int
	var name, status string
	if err := row.Scan(&vid, &name, &status); err != nil {
		writeJSON(w, http.StatusNotFound, map[string]string{"error": "Not found"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"id": vid, "name": name, "status": status})
}
