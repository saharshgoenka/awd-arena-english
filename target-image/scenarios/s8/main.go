package main

import (
	"log"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
)

// ── Auth middleware (JWT bearer tokens) ──────────────────────────────────────

func bearerToken(c *gin.Context) string {
	h := c.GetHeader("Authorization")
	if strings.HasPrefix(h, "Bearer ") {
		return strings.TrimPrefix(h, "Bearer ")
	}
	return ""
}

func authMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		claims, err := verifyToken(bearerToken(c))
		if err != nil {
			c.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "Login required"})
			return
		}
		c.Set("claims", claims)
		c.Next()
	}
}

func claimsFrom(c *gin.Context) *Claims {
	v, ok := c.Get("claims")
	if !ok {
		return nil
	}
	cl, _ := v.(*Claims)
	return cl
}

// ── Bootstrap ────────────────────────────────────────────────────────────────

func main() {
	initDB()

	gin.SetMode(gin.ReleaseMode)
	r := gin.New()
	r.Use(gin.Recovery())

	r.GET("/", homeHandler)
	r.GET("/about", aboutHandler)
	r.GET("/status", statusHandler)
	r.GET("/help", helpHandler)
	r.GET("/api", apiDiscoveryHandler)
	r.GET("/health", healthHandler)
	r.POST("/login", loginHandler)

	r.GET("/robots.txt", func(c *gin.Context) {
		c.Data(http.StatusOK, "text/plain; charset=utf-8", []byte("User-agent: *\nDisallow: /debug/env\nDisallow: /admin\n"))
	})
	r.GET("/debug/env", debugEnvHandler)

	// Authenticated routes. A valid JWT is required by authMiddleware.
	auth := r.Group("/")
	auth.Use(authMiddleware())
	auth.GET("/dashboard", dashboardHandler)
	auth.GET("/admin/settings", adminSettingsHandler)
	auth.GET("/admin/metrics", adminMetricsHandler)
	auth.GET("/reports/mine", reportsMineHandler)
	auth.GET("/reports/:id", reportShowHandler)
	auth.GET("/profile/token", profileTokenHandler)
	auth.GET("/profile/vault", profileVaultHandler)
	auth.GET("/exports/encrypted", encryptedExportHandler)
	auth.GET("/meters", metersHandler)
	auth.GET("/meters/search", metersSearchHandler)
	auth.GET("/meter/:id", meterShowHandler)

	addr := ":3000"
	log.Printf("GridPulse listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, r))
}
