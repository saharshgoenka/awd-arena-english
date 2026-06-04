use actix_web::{
    dev::Payload, error::ErrorUnauthorized, web, Error, FromRequest, HttpRequest, HttpResponse,
    Responder,
};
use serde::Deserialize;
use serde_json::json;
use std::future::{ready, Ready};

use crate::db::{self, DbPool};

// AuthSession is an Actix extractor: a handler is only authenticated if it
// declares an `AuthSession` parameter. Handlers that omit it run no auth check.
pub struct AuthSession {
    #[allow(dead_code)]
    pub username: String,
    pub role: String,
    pub token: String,
}

impl FromRequest for AuthSession {
    type Error = Error;
    type Future = Ready<Result<Self, Error>>;

    fn from_request(req: &HttpRequest, _payload: &mut Payload) -> Self::Future {
        let token = req
            .headers()
            .get("Authorization")
            .and_then(|h| h.to_str().ok())
            .and_then(|s| s.strip_prefix("Bearer "))
            .map(|s| s.to_string());
        let pool = req.app_data::<web::Data<DbPool>>().cloned();
        match (token, pool) {
            (Some(tok), Some(pool)) => {
                let conn = pool.lock().unwrap();
                match db::lookup_session(&conn, &tok) {
                    Some((username, role)) => ready(Ok(AuthSession {
                        username,
                        role,
                        token: tok,
                    })),
                    None => ready(Err(ErrorUnauthorized("invalid or missing token"))),
                }
            }
            _ => ready(Err(ErrorUnauthorized("invalid or missing token"))),
        }
    }
}

#[derive(Deserialize)]
pub struct LoginReq {
    pub username: String,
    pub password: String,
}

pub async fn login(db: web::Data<DbPool>, body: web::Json<LoginReq>) -> impl Responder {
    let conn = db.lock().unwrap();
    if let Some(user) = db::find_user(&conn, &body.username) {
        if db::check_password(&user.password_hash, &body.password) {
            let token = uuid::Uuid::new_v4().to_string();
            db::create_session(&conn, &token, &user.username, &user.role);
            return HttpResponse::Ok().json(json!({ "token": token, "role": user.role }));
        }
    }
    // flag_5 (A07 authentication_failures): no rate limiting on this endpoint,
    // so weak credentials are brute-forceable.
    HttpResponse::Unauthorized().json(json!({ "error": "invalid credentials" }))
}

pub async fn logout(session: AuthSession, db: web::Data<DbPool>) -> impl Responder {
    let conn = db.lock().unwrap();
    db::delete_session(&conn, &session.token);
    HttpResponse::Ok().json(json!({ "message": "logged out" }))
}
