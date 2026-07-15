package main

import (
	"database/sql"
	"log"
	"os"
	"strconv"

	_ "modernc.org/sqlite"
)

var db *sql.DB

// User mirrors a row in the users table.
type User struct {
	ID           int
	Username     string
	PasswordHash string
	Role         string
}

const schema = `
CREATE TABLE IF NOT EXISTS flags (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  name  TEXT UNIQUE NOT NULL,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meters (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  label  TEXT NOT NULL,
  status TEXT NOT NULL,
  content TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reports (
  id             INTEGER PRIMARY KEY,
  owner          TEXT NOT NULL,
  title          TEXT NOT NULL,
  body           TEXT NOT NULL,
  escalation_ref INTEGER
);
`

func initDB() {
	var err error
	db, err = sql.Open("sqlite", "/app/data/gridpulse.db")
	if err != nil {
		log.Fatalf("open db: %v", err)
	}
	// modernc sqlite + a single file works best with one writer.
	db.SetMaxOpenConns(1)

	if _, err := db.Exec(schema); err != nil {
		log.Fatalf("schema: %v", err)
	}
	_, _ = db.Exec("ALTER TABLE meters ADD COLUMN content TEXT NOT NULL DEFAULT ''")
	seed()
}

func seed() {
	// Only flag_4 (the SQLi-reachable flag) is stored in the DB; the others are
	// served from env by their handlers so one UNION injection can't dump every
	// flag at once. flagValue() falls back to env for the non-DB flags.
	for i := 4; i <= 4; i++ {
		name := "flag_" + strconv.Itoa(i)
		value := os.Getenv("FLAG_" + strconv.Itoa(i))
		if value == "" {
			value = "FLAG{00000000000000000000000000000000}"
		}
		if _, err := db.Exec(
			`INSERT INTO flags (name, value) VALUES (?, ?)
			 ON CONFLICT(name) DO UPDATE SET value=excluded.value`,
			name, value,
		); err != nil {
			log.Fatalf("seed flag %s: %v", name, err)
		}
	}

	// Users. Viewer is the intended low-priv foothold. Operator uses a weak MD5
	// password that is meant to be cracked only after its hash is leaked.
	users := []struct{ Username, Password, Role string }{
		{"admin", "S8Admin-Control-2024!", "admin"},
		{"operator", "operator789", "operator"},
		{"lineoperator", "meter2024", "operator"},
		{"viewer", "view123", "viewer"},
	}
	for _, u := range users {
		if _, err := db.Exec(
			`INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)
			 ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, role=excluded.role`,
			u.Username, hashPassword(u.Password), u.Role,
		); err != nil {
			log.Fatalf("seed user %s: %v", u.Username, err)
		}
	}

	// Meters (sample telemetry fleet). The content field gives a normal
	// plaintext source for the reused-keystream export oracle.
	meters := []struct{ Label, Status, Content string }{
		{"Substation North", "online", "Substation North meter reports nominal voltage, steady frequency, and routine feeder telemetry for known plaintext recovery."},
		{"Substation South", "online", "Substation South meter reports nominal inverter load and no active outage alarms during the test window."},
		{"Feeder Line 12", "degraded", "Feeder Line 12 reports a degraded phase balance but stable telemetry ingestion for grid operations."},
		{"Feeder Line 13", "online", "Feeder Line 13 reports online status with normal dispatchable reserve and stable collector sync."},
		{"Rooftop Array A", "online", "Rooftop Array A reports production within forecast and healthy collector heartbeat."},
		{"Rooftop Array B", "offline", "Rooftop Array B reports offline maintenance state with no emergency escalation required."},
		{"Transformer T-7", "online", "Transformer T-7 reports normal thermal envelope and clean telemetry upload."},
		{"Transformer T-8", "degraded", "Transformer T-8 reports degraded cooling loop telemetry and pending operator review."},
	}
	var count int
	_ = db.QueryRow("SELECT COUNT(*) FROM meters").Scan(&count)
	if count == 0 {
		for _, m := range meters {
			if _, err := db.Exec("INSERT INTO meters (label, status, content) VALUES (?, ?, ?)", m.Label, m.Status, m.Content); err != nil {
				log.Fatalf("seed meter %s: %v", m.Label, err)
			}
		}
	}

	reports := []struct {
		ID          int
		Owner       string
		Title       string
		Body        string
		Ref         int
	}{
		{1, "viewer", "Meter access review", "Routine viewer report. Follow the escalation_ref for the privileged grid control review.", 4},
		{2, "operator", "Operator shift handoff", "Operator handoff notes for feeder maintenance and status checks.", 0},
		{3, "lineoperator", "Line operations note", "Line operations field note for transformer and feeder telemetry.", 0},
		{4, "admin", "Escalation: grid control token", "Restricted grid control review. system_token=__FLAG_1__", 0},
	}
	var reportCount int
	_ = db.QueryRow("SELECT COUNT(*) FROM reports").Scan(&reportCount)
	if reportCount == 0 {
		for _, rp := range reports {
			var ref any
			if rp.Ref > 0 {
				ref = rp.Ref
			}
			if _, err := db.Exec(
				"INSERT INTO reports (id, owner, title, body, escalation_ref) VALUES (?, ?, ?, ?, ?)",
				rp.ID, rp.Owner, rp.Title, rp.Body, ref,
			); err != nil {
				log.Fatalf("seed report %d: %v", rp.ID, err)
			}
		}
	}
}

func findUserByUsername(username string) *User {
	row := db.QueryRow("SELECT id, username, password_hash, role FROM users WHERE username = ?", username)
	u := &User{}
	if err := row.Scan(&u.ID, &u.Username, &u.PasswordHash, &u.Role); err != nil {
		return nil
	}
	return u
}

func findUserByID(id int) *User {
	row := db.QueryRow("SELECT id, username, password_hash, role FROM users WHERE id = ?", id)
	u := &User{}
	if err := row.Scan(&u.ID, &u.Username, &u.PasswordHash, &u.Role); err != nil {
		return nil
	}
	return u
}

func flagValue(name string) string {
	var v string
	if err := db.QueryRow("SELECT value FROM flags WHERE name = ?", name).Scan(&v); err != nil {
		// Only flag_4 is in the DB; the rest come from env (FLAG_1..FLAG_5)
		// so the flag_4 SQLi cannot dump them.
		if len(name) > 4 {
			return os.Getenv("FLAG" + name[4:])
		}
		return ""
	}
	return v
}
