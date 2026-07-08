use actix_web::{
    dev::Payload, error::ErrorUnauthorized, web, Error, FromRequest, HttpRequest, HttpResponse,
    Responder,
};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use serde::Deserialize;
use serde_json::json;
use std::future::{ready, Ready};

use crate::db::{self, DbPool};

// AuthSession is an Actix extractor: a handler is only authenticated if it
// declares an `AuthSession` parameter. Handlers that omit it run no auth check.
pub struct AuthSession {
    pub username: String,
    pub role: String,
}

#[derive(Deserialize)]
struct TokenClaims {
    username: String,
    role: String,
}

fn issue_token(username: &str, role: &str) -> String {
    URL_SAFE_NO_PAD.encode(
        json!({
            "username": username,
            "role": role,
        })
        .to_string(),
    )
}

fn parse_token(token: &str) -> Option<TokenClaims> {
    let raw = URL_SAFE_NO_PAD.decode(token).ok()?;
    serde_json::from_slice(&raw).ok()
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
        match token.and_then(|tok| parse_token(&tok)) {
            Some(claims) => ready(Ok(AuthSession {
                username: claims.username,
                role: claims.role,
            })),
            None => ready(Err(ErrorUnauthorized("invalid or missing token"))),
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
            let token = issue_token(&user.username, &user.role);
            return HttpResponse::Ok().json(json!({ "token": token, "role": user.role }));
        }
    }
    // flag_5 (A07): bearer tokens are unsigned self-describing JSON blobs, so a
    // low-privileged token can be edited offline and replayed with a stronger role.
    HttpResponse::Unauthorized().json(json!({ "error": "invalid credentials" }))
}

pub async fn logout(_session: AuthSession, _db: web::Data<DbPool>) -> impl Responder {
    HttpResponse::Ok().json(json!({ "message": "logged out" }))
}
