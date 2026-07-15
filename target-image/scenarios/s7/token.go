package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"strings"
)

// flag_5 (A07 Authentication Failures → token/signature forgery).
//
// On login the app issues a compact JWT-style token of the form
// base64url(header).base64url(payload).base64url(sig), where the signature is
// HMAC-SHA256 over "header.payload" using jwtSecret. The admin console route
// trusts the token's OWN `alg` header to decide how to validate it and honours
// alg:"none" (RFC 7519's unsecured JWT) by accepting the payload with NO
// signature check. Any holder of a legitimate low-priv token can re-encode its
// header as {"alg":"none"}, set role=admin, drop the signature, and be trusted —
// a pure base64 forgery requiring only stdlib.
//
// The signing secret is DISJOINT from flag_3's password hashing (unsalted SHA-256
// over the password) — recovering one reveals nothing about the other.
const jwtSecret = "s7-fleetview-hs256-J8kQ-signing-2024"

func b64urlEncode(raw []byte) string {
	return base64.RawURLEncoding.EncodeToString(raw)
}

func b64urlDecode(seg string) ([]byte, error) {
	return base64.RawURLEncoding.DecodeString(seg)
}

func signToken(signingInput string) string {
	mac := hmac.New(sha256.New, []byte(jwtSecret))
	mac.Write([]byte(signingInput))
	return b64urlEncode(mac.Sum(nil))
}

// issueToken mints a legitimately-signed HS256 token for the given user.
func issueToken(u *User) string {
	header, _ := json.Marshal(map[string]string{"alg": "HS256", "typ": "JWT"})
	payload, _ := json.Marshal(map[string]any{
		"sub":      u.ID,
		"username": u.Username,
		"role":     u.Role,
	})
	signingInput := b64urlEncode(header) + "." + b64urlEncode(payload)
	return signingInput + "." + signToken(signingInput)
}

// parseToken returns the token's claims if it is accepted. It is VULNERABLE:
// when the header declares alg:"none" the payload is trusted without any
// signature verification.
func parseToken(tok string) (map[string]any, bool) {
	parts := strings.Split(tok, ".")
	if len(parts) != 3 {
		return nil, false
	}
	headerBytes, err := b64urlDecode(parts[0])
	if err != nil {
		return nil, false
	}
	var header map[string]any
	if err := json.Unmarshal(headerBytes, &header); err != nil {
		return nil, false
	}
	payloadBytes, err := b64urlDecode(parts[1])
	if err != nil {
		return nil, false
	}
	var claims map[string]any
	if err := json.Unmarshal(payloadBytes, &claims); err != nil {
		return nil, false
	}
	if alg, _ := header["alg"].(string); alg == "none" {
		// VULNERABLE: unsecured token accepted without verifying a signature.
		return claims, true
	}
	expected := signToken(parts[0] + "." + parts[1])
	if hmac.Equal([]byte(expected), []byte(parts[2])) {
		return claims, true
	}
	return nil, false
}

// tokenFromRequest reads the bearer token from the Authorization header or the
// `token` cookie.
func tokenFromRequest(r *http.Request) string {
	if auth := r.Header.Get("Authorization"); strings.HasPrefix(auth, "Bearer ") {
		return strings.TrimPrefix(auth, "Bearer ")
	}
	if c, err := r.Cookie("token"); err == nil {
		return c.Value
	}
	return ""
}
