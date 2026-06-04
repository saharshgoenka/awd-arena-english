use actix_web::{web, HttpResponse, Responder};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;

use crate::auth::AuthSession;
use crate::db::{self, DbPool};

pub async fn health() -> impl Responder {
    // No auth, no DB dependency.
    HttpResponse::Ok().json(json!({ "status": "ok" }))
}

// flag_1 (A01 broken_access_control): no AuthSession extractor in the signature,
// so no authentication or role check runs at all.
pub async fn admin_keys(db: web::Data<DbPool>) -> impl Responder {
    let conn = db.lock().unwrap();
    let flag = db::get_flag(&conn, "flag_1").unwrap_or_default();
    HttpResponse::Ok().json(json!({ "system_token": flag }))
}

// flag_2 (A02 security_misconfiguration): dumps the whole process environment,
// including FLAG_2, with no authentication.
pub async fn debug_config() -> impl Responder {
    let env: HashMap<String, String> = std::env::vars().collect();
    HttpResponse::Ok().json(json!({
        "environment": env,
        "build": env!("CARGO_PKG_VERSION"),
    }))
}

#[derive(Serialize)]
struct UserProfile {
    id: i64,
    username: String,
    // flag_3 (A04): the stored password hash is exposed in the profile response.
    password_hash: String,
    role: String,
}

pub async fn profile(session: AuthSession, db: web::Data<DbPool>) -> impl Responder {
    let conn = db.lock().unwrap();
    match db::find_user(&conn, &session.username) {
        Some(u) => HttpResponse::Ok().json(UserProfile {
            id: u.id,
            username: u.username,
            password_hash: u.password_hash,
            role: u.role,
        }),
        None => HttpResponse::NotFound().json(json!({ "error": "not found" })),
    }
}

// flag_3 reward: only the engineer user can read the private secret.
pub async fn secret_private(session: AuthSession, db: web::Data<DbPool>) -> impl Responder {
    if session.username != "engineer" {
        return HttpResponse::Forbidden().json(json!({ "error": "engineer access only" }));
    }
    let conn = db.lock().unwrap();
    let flag = db::get_flag(&conn, "flag_3").unwrap_or_default();
    HttpResponse::Ok().json(json!({ "secret": flag }))
}

#[derive(Deserialize)]
pub struct SearchQuery {
    pub q: String,
}

pub async fn secret_search(
    _session: AuthSession,
    query: web::Query<SearchQuery>,
    db: web::Data<DbPool>,
) -> impl Responder {
    let conn = db.lock().unwrap();
    // flag_4 (A05 injection): user input is interpolated into the SQL string via
    // format!() instead of being bound as a parameter.
    let sql = format!(
        "SELECT id, name, value FROM secrets WHERE name LIKE '%{}%'",
        query.q
    );
    let mut stmt = match conn.prepare(&sql) {
        Ok(s) => s,
        Err(_) => return HttpResponse::Ok().json(json!({ "results": [] })),
    };
    let rows: Vec<serde_json::Value> = stmt
        .query_map([], |r| {
            Ok(json!({
                "id": r.get::<_, i64>(0).unwrap_or_default(),
                "name": r.get::<_, String>(1).unwrap_or_default(),
                "value": r.get::<_, String>(2).unwrap_or_default(),
            }))
        })
        .map(|m| m.filter_map(|x| x.ok()).collect())
        .unwrap_or_default();
    HttpResponse::Ok().json(json!({ "results": rows }))
}

// flag_5 reward: only an admin-role session can read the vault secret.
pub async fn secret_vault(session: AuthSession, db: web::Data<DbPool>) -> impl Responder {
    if session.role != "admin" {
        return HttpResponse::Forbidden().json(json!({ "error": "admin access only" }));
    }
    let conn = db.lock().unwrap();
    let flag = db::get_flag(&conn, "flag_5").unwrap_or_default();
    HttpResponse::Ok().json(json!({ "vault_secret": flag }))
}

pub async fn secrets_list(_session: AuthSession, db: web::Data<DbPool>) -> impl Responder {
    let conn = db.lock().unwrap();
    let mut stmt = conn
        .prepare("SELECT id, name, owner FROM secrets ORDER BY id LIMIT 50")
        .unwrap();
    let rows: Vec<serde_json::Value> = stmt
        .query_map([], |r| {
            Ok(json!({
                "id": r.get::<_, i64>(0).unwrap_or_default(),
                "name": r.get::<_, String>(1).unwrap_or_default(),
                "owner": r.get::<_, String>(2).unwrap_or_default(),
            }))
        })
        .map(|m| m.filter_map(|x| x.ok()).collect())
        .unwrap_or_default();
    HttpResponse::Ok().json(json!({ "secrets": rows }))
}

pub async fn secret_detail(
    _session: AuthSession,
    path: web::Path<i64>,
    db: web::Data<DbPool>,
) -> impl Responder {
    let id = path.into_inner();
    let conn = db.lock().unwrap();
    let row = conn.query_row(
        "SELECT id, name, owner FROM secrets WHERE id = ?1",
        [id],
        |r| {
            Ok(json!({
                "id": r.get::<_, i64>(0)?,
                "name": r.get::<_, String>(1)?,
                "owner": r.get::<_, String>(2)?,
            }))
        },
    );
    match row {
        Ok(v) => HttpResponse::Ok().json(v),
        Err(_) => HttpResponse::NotFound().json(json!({ "error": "not found" })),
    }
}
