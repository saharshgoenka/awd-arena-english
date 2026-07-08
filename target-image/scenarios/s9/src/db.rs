use rusqlite::{params, Connection};
use std::sync::{Arc, Mutex};

pub type DbPool = Arc<Mutex<Connection>>;

#[derive(Clone)]
pub struct User {
    pub id: i64,
    pub username: String,
    pub password_hash: String,
    pub role: String,
}

// flag_3 (A04 cryptographic_failures): MD5 is a fast, unsalted checksum, not a
// password hash, despite the column being named password_hash.
pub fn hash_password(password: &str) -> String {
    format!("{:x}", md5::compute(password))
}

pub fn check_password(stored: &str, password: &str) -> bool {
    stored == hash_password(password)
}

const SCHEMA: &str = "
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS secrets (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    value TEXT NOT NULL,
    owner TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS flags (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL
);
";

pub fn init_db() -> DbPool {
    let conn = Connection::open("/app/data/vaultgate.db").expect("open db");
    conn.execute_batch(SCHEMA).expect("create schema");
    let pool = Arc::new(Mutex::new(conn));
    seed(&pool);
    pool
}

fn seed(pool: &DbPool) {
    let conn = pool.lock().unwrap();

    // Only flag_4 (the SQLi-reachable flag) is stored in the DB; the others are
    // served from env by their handlers so one UNION injection can't dump every
    // flag at once. get_flag() falls back to env for the non-DB flags.
    for i in 4..=4 {
        let name = format!("flag_{}", i);
        let value = std::env::var(format!("FLAG_{}", i))
            .unwrap_or_else(|_| "FLAG{00000000000000000000000000000000}".to_string());
        conn.execute(
            "INSERT INTO flags (name, value) VALUES (?1, ?2)
             ON CONFLICT(name) DO UPDATE SET value = excluded.value",
            params![name, value],
        )
        .unwrap();
    }

    // Users. Readonly is the intended foothold. Engineer uses a weak MD5-backed
    // password that should be recovered only after its hash is leaked.
    let users = [
        ("admin", "S9Admin-Vault-Core!", "admin"),
        ("engineer", "password123", "engineer"),
        ("vaulteng", "engshift7", "engineer"),
        ("readonly", "readonly789", "readonly"),
    ];
    for (username, password, role) in users {
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?1, ?2, ?3)
             ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash, role = excluded.role",
            params![username, hash_password(password), role],
        )
        .unwrap();
    }

    // Secrets (nominal data). Only seed once.
    let count: i64 = conn
        .query_row("SELECT COUNT(*) FROM secrets", [], |r| r.get(0))
        .unwrap_or(0);
    if count == 0 {
        let secrets = [
            ("stripe-prod", "sk_live_x9f2a7c1", "engineer"),
            ("datadog-api", "dd_8h3k0p2m", "engineer"),
            ("github-deploy", "ghp_q4w7e1r9", "admin"),
            ("smtp-relay", "smtp_5t6y7u8i", "admin"),
            ("s3-backups", "akia_2z3x4c5v", "engineer"),
            ("pagerduty", "pd_9o8i7u6y", "readonly"),
        ];
        for (name, value, owner) in secrets {
            conn.execute(
                "INSERT INTO secrets (name, value, owner) VALUES (?1, ?2, ?3)",
                params![name, value, owner],
            )
            .unwrap();
        }
    }
}

pub fn find_user(conn: &Connection, username: &str) -> Option<User> {
    conn.query_row(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?1",
        params![username],
        |r| {
            Ok(User {
                id: r.get(0)?,
                username: r.get(1)?,
                password_hash: r.get(2)?,
                role: r.get(3)?,
            })
        },
    )
    .ok()
}

pub fn create_session(conn: &Connection, token: &str, username: &str, role: &str) {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs() as i64)
        .unwrap_or(0);
    let _ = conn.execute(
        "INSERT INTO sessions (token, username, role, created_at) VALUES (?1, ?2, ?3, ?4)",
        params![token, username, role, now],
    );
}

pub fn lookup_session(conn: &Connection, token: &str) -> Option<(String, String)> {
    conn.query_row(
        "SELECT username, role FROM sessions WHERE token = ?1",
        params![token],
        |r| Ok((r.get(0)?, r.get(1)?)),
    )
    .ok()
}

pub fn delete_session(conn: &Connection, token: &str) {
    let _ = conn.execute("DELETE FROM sessions WHERE token = ?1", params![token]);
}

pub fn get_flag(conn: &Connection, name: &str) -> Option<String> {
    conn.query_row(
        "SELECT value FROM flags WHERE name = ?1",
        params![name],
        |r| r.get(0),
    )
    .ok()
    // Only flag_4 is in the DB; the rest come from env so the flag_4 SQLi
    // cannot dump them.
    .or_else(|| std::env::var(name.to_uppercase()).ok())
}
