package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"log"
	"net"
	"net/http"
	"sync"
)

// ── Session store (in-memory cookie sessions) ────────────────────────────────

var (
	sessions   = map[string]int{}
	sessionsMu sync.RWMutex
)

func newSessionID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

func setSession(w http.ResponseWriter, userID int) {
	sid := newSessionID()
	sessionsMu.Lock()
	sessions[sid] = userID
	sessionsMu.Unlock()
	http.SetCookie(w, &http.Cookie{Name: "session_id", Value: sid, Path: "/", HttpOnly: true})
}

func clearSession(w http.ResponseWriter, r *http.Request) {
	c, err := r.Cookie("session_id")
	if err != nil {
		return
	}
	sessionsMu.Lock()
	delete(sessions, c.Value)
	sessionsMu.Unlock()
	http.SetCookie(w, &http.Cookie{Name: "session_id", Value: "", Path: "/", MaxAge: -1})
}

func currentUser(r *http.Request) *User {
	c, err := r.Cookie("session_id")
	if err != nil {
		return nil
	}
	sessionsMu.RLock()
	uid, ok := sessions[c.Value]
	sessionsMu.RUnlock()
	if !ok {
		return nil
	}
	return findUserByID(uid)
}

// ── Login failure tracking (used by the hardened login path) ─────────────────

var (
	loginFailMu sync.Mutex
	loginFails  = map[string]int{}
)

func clientIP(r *http.Request) string {
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

func loginAttemptsExceeded(ip string) bool {
	loginFailMu.Lock()
	defer loginFailMu.Unlock()
	return loginFails[ip] >= 10
}

func recordLoginFailure(ip string) {
	loginFailMu.Lock()
	loginFails[ip]++
	loginFailMu.Unlock()
}

func clearLoginFailures(ip string) {
	loginFailMu.Lock()
	delete(loginFails, ip)
	loginFailMu.Unlock()
}

// ── JSON helper ──────────────────────────────────────────────────────────────

func writeJSON(w http.ResponseWriter, status int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(body)
}

// ── Bootstrap ────────────────────────────────────────────────────────────────

func main() {
	initDB()

	mux := http.NewServeMux()
	mux.HandleFunc("GET /", homeHandler)
	mux.HandleFunc("GET /about", aboutHandler)
	mux.HandleFunc("GET /status", statusHandler)
	mux.HandleFunc("GET /help", helpHandler)
	mux.HandleFunc("GET /api", apiDiscoveryHandler)
	mux.HandleFunc("GET /health", healthHandler)
	mux.HandleFunc("GET /robots.txt", robotsHandler)
	mux.HandleFunc("POST /login", loginHandler)
	mux.HandleFunc("POST /logout", logoutHandler)
	mux.HandleFunc("GET /dashboard", dashboardHandler)
	mux.HandleFunc("GET /admin/settings", adminSettingsHandler)
	mux.HandleFunc("GET /admin/metrics", adminMetricsHandler)
	mux.HandleFunc("GET /admin/console", adminConsoleHandler)
	mux.HandleFunc("GET /telemetry/overview", telemetryOverviewHandler)
	mux.HandleFunc("GET /reports/mine", reportsMineHandler)
	mux.HandleFunc("GET /reports/{id}", reportShowHandler)
	mux.HandleFunc("GET /debug/env", debugEnvHandler)
	mux.HandleFunc("GET /exports/encrypted", encryptedExportHandler)
	mux.HandleFunc("GET /profile/token", profileTokenHandler)
	mux.HandleFunc("GET /profile/vault", profileVaultHandler)
	mux.HandleFunc("GET /vehicles", vehiclesHandler)
	mux.HandleFunc("GET /vehicles/search", vehiclesSearchHandler)
	mux.HandleFunc("GET /vehicles/{id}", vehicleShowHandler)

	addr := ":3000"
	log.Printf("FleetView listening on %s", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}
