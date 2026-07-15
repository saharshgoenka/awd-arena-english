use actix_web::{
    dev::Payload, error::ErrorUnauthorized, web, Error, FromRequest, HttpRequest, HttpResponse,
    Responder,
};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use hmac::{Hmac, Mac};
use serde::Deserialize;
use serde_json::json;
use sha2::Sha256;
use std::future::{ready, Ready};

use crate::db::{self, DbPool};

type HmacSha256 = Hmac<Sha256>;

// flag_5 (A07 Authentication Failures -> token/signature forgery).
//
// On login the app issues a compact JWT-style token of the form
// base64url(header).base64url(payload).base64url(sig), where the signature is
// HMAC-SHA256 over "header.payload" using JWT_SECRET. The vault route trusts the
// token's OWN `alg` header to decide how to validate it and honours alg:"none"
// (RFC 7519's unsecured JWT) by accepting the payload with NO signature check.
// Any holder of a legitimate low-priv token can re-encode its header as
// {"alg":"none"}, set role=admin, drop the signature, and be trusted -- a pure
// base64 forgery requiring only stdlib.
const JWT_SECRET: &str = "s9-vaultgate-hs256-Xp7Q-signing-2024";

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

fn sign_token(signing_input: &str) -> String {
    let mut mac =
        HmacSha256::new_from_slice(JWT_SECRET.as_bytes()).expect("HMAC accepts any key length");
    mac.update(signing_input.as_bytes());
    URL_SAFE_NO_PAD.encode(mac.finalize().into_bytes())
}

// issue_token mints a legitimately-signed HS256 token for the given user.
fn issue_token(username: &str, role: &str) -> String {
    let header = URL_SAFE_NO_PAD.encode(json!({ "alg": "HS256", "typ": "JWT" }).to_string());
    let payload = URL_SAFE_NO_PAD.encode(
        json!({
            "sub": username,
            "username": username,
            "role": role,
        })
        .to_string(),
    );
    let signing_input = format!("{}.{}", header, payload);
    let sig = sign_token(&signing_input);
    format!("{}.{}", signing_input, sig)
}

// parse_token returns the token's claims if it is accepted. It is VULNERABLE:
// when the header declares alg:"none" the payload is trusted without any
// signature verification.
fn parse_token(token: &str) -> Option<TokenClaims> {
    let parts: Vec<&str> = token.split('.').collect();
    if parts.len() != 3 {
        return None;
    }
    let header_bytes = URL_SAFE_NO_PAD.decode(parts[0]).ok()?;
    let header: serde_json::Value = serde_json::from_slice(&header_bytes).ok()?;
    let payload_bytes = URL_SAFE_NO_PAD.decode(parts[1]).ok()?;
    let claims: TokenClaims = serde_json::from_slice(&payload_bytes).ok()?;
    let alg = header.get("alg").and_then(|v| v.as_str()).unwrap_or("");
    if alg == "none" {
        // VULNERABLE: unsecured token accepted without verifying a signature.
        return Some(claims);
    }
    let expected = sign_token(&format!("{}.{}", parts[0], parts[1]));
    if expected == parts[2] {
        return Some(claims);
    }
    None
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
    // flag_5 (A07): the verifier honours the token's own alg header, so a
    // low-privileged holder can re-encode the header as alg:"none", set role=admin,
    // drop the signature, and be trusted.
    HttpResponse::Unauthorized().json(json!({ "error": "invalid credentials" }))
}

pub async fn logout(_session: AuthSession, _db: web::Data<DbPool>) -> impl Responder {
    HttpResponse::Ok().json(json!({ "message": "logged out" }))
}
