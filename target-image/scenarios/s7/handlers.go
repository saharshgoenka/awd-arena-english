package main

import (
	"encoding/json"
	"net/http"
)

type credentials struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
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
	writeJSON(w, http.StatusOK, map[string]string{"message": "Login successful", "role": user.Role})
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
	// flag_1 (A01): no role check — any authenticated user reaches admin settings.
	flag := flagValue("flag_1")
	writeJSON(w, http.StatusOK, map[string]any{
		"config": map[string]any{"maintenance": false, "system_token": flag},
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
	flag := flagValue("flag_5")
	writeJSON(w, http.StatusOK, map[string]any{
		"total_vehicles": vehicleCount,
		"total_users":    userCount,
		"internal_ref":   flag,
	})
}

func telemetryOverviewHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil || user.Role != "telemetry" {
		writeJSON(w, http.StatusForbidden, map[string]string{"error": "Telemetry access required"})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"collector":   "edge-uplink",
		"region":      "west",
		"service_ref": flagValue("flag_5"),
	})
}

func debugEnvHandler(w http.ResponseWriter, r *http.Request) {
	// flag_2 (A02): a debug endpoint that dumps the full process environment,
	// including FLAG_2, with no authentication. Belongs in development only.
	env := map[string]string{}
	for _, kv := range envPairs() {
		env[kv[0]] = kv[1]
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"go_version":  goVersion(),
		"environment": env,
	})
}

func profileTokenHandler(w http.ResponseWriter, r *http.Request) {
	user := currentUser(r)
	if user == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]string{"error": "Login required"})
		return
	}
	target := user
	if requested := r.URL.Query().Get("username"); requested != "" {
		// flag_3 (A04): any authenticated user can fetch another account's legacy
		// token, leaking the stored password hash needed for offline cracking.
		if other := findUserByUsername(requested); other != nil {
			target = other
		}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"username":     target.Username,
		"legacy_token": target.PasswordHash,
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
	flag := flagValue("flag_3")
	writeJSON(w, http.StatusOK, map[string]any{"message": "Driver vault", "secret": flag})
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
	// flag_4 (A05 injection): the user-controlled query is concatenated straight
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
