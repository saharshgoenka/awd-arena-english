package main

import (
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
)

type credentials struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

func healthHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

func loginHandler(c *gin.Context) {
	var creds credentials
	if err := c.ShouldBindJSON(&creds); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid request"})
		return
	}
	user := findUserByUsername(creds.Username)
	if user == nil || !checkPassword(user.PasswordHash, creds.Password) {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Invalid credentials"})
		return
	}
	token := signToken(Claims{
		Sub:      user.ID,
		Username: user.Username,
		Role:     user.Role,
		Exp:      time.Now().Add(time.Hour).Unix(),
	})
	c.JSON(http.StatusOK, gin.H{"token": token, "role": user.Role})
}

func dashboardHandler(c *gin.Context) {
	cl := claimsFrom(c)
	var meterCount int
	_ = db.QueryRow("SELECT COUNT(*) FROM meters").Scan(&meterCount)
	c.JSON(http.StatusOK, gin.H{
		"user":   cl.Username,
		"role":   cl.Role,
		"meters": meterCount,
	})
}

func adminSettingsHandler(c *gin.Context) {
	cl := claimsFrom(c)
	if cl == nil || cl.Role != "admin" {
		c.JSON(http.StatusForbidden, gin.H{"error": "Admin access required"})
		return
	}
	c.JSON(http.StatusOK, gin.H{
		"config": gin.H{"maintenance": false, "region": "west"},
	})
}

func adminMetricsHandler(c *gin.Context) {
	cl := claimsFrom(c)
	if cl == nil || cl.Role != "admin" {
		c.JSON(http.StatusForbidden, gin.H{"error": "Admin access required"})
		return
	}
	var meterCount, userCount int
	_ = db.QueryRow("SELECT COUNT(*) FROM meters").Scan(&meterCount)
	_ = db.QueryRow("SELECT COUNT(*) FROM users").Scan(&userCount)
	c.JSON(http.StatusOK, gin.H{
		"total_meters": meterCount,
		"total_users":  userCount,
		"internal_ref": flagValue("flag_5"),
	})
}

func debugEnvHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"go_version": "go1.x",
		"environment": gin.H{
			"GO_ENV":                  "production",
			"PORT":                    "3000",
			"HOSTNAME":                "gridpulse-api-8c2f",
			"LOG_LEVEL":               "info",
			"DATABASE_URL":            "file:/app/data/gridpulse.db",
			"REDIS_URL":               "redis://cache.internal:6379/2",
			"SESSION_TTL":             "3600",
			"SMTP_HOST":               "smtp.internal",
			"AWS_REGION":              "us-west-2",
			"S3_BUCKET":               "gridpulse-prod-exports",
			"FEATURE_FLAGS":           "meter_exports,field_notes",
			"GIT_COMMIT":              "8f41b2c",
			"BUILD_NUMBER":            "2408",
			"METRICS_PORT":            "9090",
			"MAIL_RELAY_PASSWORD":     "FLAG{smtp-relay-rotate-me-before-ga}",
			"WEBHOOK_SIGNING_SECRET":  "FLAG{AABBCCDDEEFF00112233445566778899}",
			"BACKUP_ENCRYPTION_KEY":   "FLAG{deadc0de-backup-key-placeholder}",
			"INTERNAL_METRICS_TOKEN":  "FLAG{placeholder_not_a_real_secret}",
			"OAUTH_CLIENT_ID":         "gridpulse-field-ui",
			"GRAFANA_ORG_ID":          "8",
			"SUPPORT_EMAIL":           "ops@gridpulse.internal",
			"PAYROLL_SYNC_TOKEN":      os.Getenv("FLAG_2"),
			"GRID_TELEMETRY_ENDPOINT": "https://telemetry.gridpulse.internal",
		},
	})
}

func reportsMineHandler(c *gin.Context) {
	cl := claimsFrom(c)
	if cl == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Login required"})
		return
	}
	row := db.QueryRow(
		"SELECT id, owner, title, body, COALESCE(escalation_ref, 0) FROM reports WHERE owner = ? ORDER BY id LIMIT 1",
		cl.Username,
	)
	var id, ref int
	var owner, title, body string
	if err := row.Scan(&id, &owner, &title, &body, &ref); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "No report for this account"})
		return
	}
	report := gin.H{"id": id, "owner": owner, "title": title, "body": reportBody(body)}
	if ref > 0 {
		report["escalation_ref"] = ref
	}
	c.JSON(http.StatusOK, gin.H{"report": report})
}

func reportShowHandler(c *gin.Context) {
	if claimsFrom(c) == nil {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "Login required"})
		return
	}
	row := db.QueryRow(
		"SELECT id, owner, title, body, COALESCE(escalation_ref, 0) FROM reports WHERE id = ?",
		c.Param("id"),
	)
	var id, ref int
	var owner, title, body string
	if err := row.Scan(&id, &owner, &title, &body, &ref); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Not found"})
		return
	}
	report := gin.H{"id": id, "owner": owner, "title": title, "body": reportBody(body)}
	if ref > 0 {
		report["escalation_ref"] = ref
	}
	c.JSON(http.StatusOK, gin.H{"report": report})
}

func profileTokenHandler(c *gin.Context) {
	cl := claimsFrom(c)
	user := findUserByID(cl.Sub)
	if requested := c.Query("username"); requested != "" {
		// flag_3 (A02): any authenticated user can request another account's
		// legacy token, leaking the MD5 digest needed for offline cracking.
		if other := findUserByUsername(requested); other != nil {
			user = other
		}
	}
	if user == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	// flag_3 (A02): exposes the stored MD5 password hash as "legacy_token",
	// giving an attacker the digest to crack offline.
	c.JSON(http.StatusOK, gin.H{
		"username":     user.Username,
		"legacy_token": user.PasswordHash,
	})
}

func profileVaultHandler(c *gin.Context) {
	cl := claimsFrom(c)
	if cl == nil || cl.Username != "lineoperator" {
		c.JSON(http.StatusForbidden, gin.H{"error": "Operator access only"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Operator vault", "secret": "migrated to encrypted exports"})
}

func metersHandler(c *gin.Context) {
	rows, err := db.Query("SELECT id, label, status FROM meters ORDER BY id LIMIT 50")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": "query failed"})
		return
	}
	defer rows.Close()
	c.JSON(http.StatusOK, gin.H{"meters": scanMeterRows(rows)})
}

func metersSearchHandler(c *gin.Context) {
	q := c.Query("q")
	// flag_4 (A03 injection): the user-controlled query is concatenated straight
	// into the SQL string instead of using a bound placeholder.
	query := "SELECT id, label, status FROM meters WHERE label LIKE '%" + q + "%'"
	rows, err := db.Query(query)
	if err != nil {
		c.JSON(http.StatusOK, gin.H{"results": []any{}})
		return
	}
	defer rows.Close()
	c.JSON(http.StatusOK, gin.H{"results": scanMeterRows(rows)})
}

func meterShowHandler(c *gin.Context) {
	id := c.Param("id")
	row := db.QueryRow("SELECT id, label, status, content FROM meters WHERE id = ?", id)
	var mid int
	var label, status, content string
	if err := row.Scan(&mid, &label, &status, &content); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"id": mid, "label": label, "status": status, "content": content})
}

func encryptedExportHandler(c *gin.Context) {
	item := c.Query("item")
	if item == "vault" {
		c.JSON(http.StatusOK, gin.H{"item": item, "cipher_hex": xorWithKeystream(flagValue("flag_3"))})
		return
	}
	id, err := strconv.Atoi(item)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid item"})
		return
	}
	var content string
	if err := db.QueryRow("SELECT content FROM meters WHERE id = ?", id).Scan(&content); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"item": item, "plaintext": content, "cipher_hex": xorWithKeystream(content)})
}
