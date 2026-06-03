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
CREATE TABLE IF NOT EXISTS vehicles (
  id     INTEGER PRIMARY KEY AUTOINCREMENT,
  name   TEXT NOT NULL,
  status TEXT NOT NULL
);
`

func initDB() {
	var err error
	db, err = sql.Open("sqlite", "/app/data/fleetview.db")
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
		{"admin", "fleetadmin2024", "admin"},
		{"dispatcher", "dispatch456", "dispatcher"},
		{"driver", "fleet123", "driver"},
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

	// Vehicles (sample fleet data).
	vehicles := []struct{ Name, Status string }{
		{"Truck Alpha", "active"},
		{"Truck Bravo", "active"},
		{"Van Charlie", "maintenance"},
		{"Van Delta", "active"},
		{"Truck Echo", "idle"},
		{"Forklift Foxtrot", "active"},
		{"Van Golf", "maintenance"},
		{"Truck Hotel", "active"},
	}
	var count int
	_ = db.QueryRow("SELECT COUNT(*) FROM vehicles").Scan(&count)
	if count == 0 {
		for _, v := range vehicles {
			if _, err := db.Exec("INSERT INTO vehicles (name, status) VALUES (?, ?)", v.Name, v.Status); err != nil {
				log.Fatalf("seed vehicle %s: %v", v.Name, err)
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
