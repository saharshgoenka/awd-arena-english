package main

import (
	"net/http"
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
	// flag_1 (A01): this handler is registered without auth middleware, so no
	// identity or role is ever checked — anyone can read the admin config.
	c.JSON(http.StatusOK, gin.H{
		"config": gin.H{"maintenance": false, "system_token": flagValue("flag_1")},
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

func profileTokenHandler(c *gin.Context) {
	cl := claimsFrom(c)
	user := findUserByID(cl.Sub)
	if user == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}
	// flag_3 (A04): exposes the stored MD5 password hash as "legacy_token",
	// giving an attacker the digest to crack offline.
	c.JSON(http.StatusOK, gin.H{
		"username":     user.Username,
		"legacy_token": user.PasswordHash,
	})
}

func profileVaultHandler(c *gin.Context) {
	cl := claimsFrom(c)
	if cl == nil || cl.Username != "operator" {
		c.JSON(http.StatusForbidden, gin.H{"error": "Operator access only"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"message": "Operator vault", "secret": flagValue("flag_3")})
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
	// flag_4 (A05 injection): the user-controlled query is concatenated straight
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
	row := db.QueryRow("SELECT id, label, status FROM meters WHERE id = ?", id)
	var mid int
	var label, status string
	if err := row.Scan(&mid, &label, &status); err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Not found"})
		return
	}
	c.JSON(http.StatusOK, gin.H{"id": mid, "label": label, "status": status})
}
