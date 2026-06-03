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
  status TEXT NOT NULL
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
	seed()
}

func seed() {
	// Flags come from the environment (FLAG_1..FLAG_5).
	for i := 1; i <= 5; i++ {
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

	// Users. Passwords are weak/guessable in the unpatched build.
	users := []struct{ Username, Password, Role string }{
		{"admin", "gridpulse-admin-2024", "admin"},
		{"operator", "operator789", "operator"},
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

	// Meters (sample telemetry fleet).
	meters := []struct{ Label, Status string }{
		{"Substation North", "online"},
		{"Substation South", "online"},
		{"Feeder Line 12", "degraded"},
		{"Feeder Line 13", "online"},
		{"Rooftop Array A", "online"},
		{"Rooftop Array B", "offline"},
		{"Transformer T-7", "online"},
		{"Transformer T-8", "degraded"},
	}
	var count int
	_ = db.QueryRow("SELECT COUNT(*) FROM meters").Scan(&count)
	if count == 0 {
		for _, m := range meters {
			if _, err := db.Exec("INSERT INTO meters (label, status) VALUES (?, ?)", m.Label, m.Status); err != nil {
				log.Fatalf("seed meter %s: %v", m.Label, err)
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
		return ""
	}
	return v
}
