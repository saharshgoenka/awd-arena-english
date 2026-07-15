package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"strings"
	"time"
)

// flag_5 (A07 authentication_failures): session tokens are JWT-style HS256 tokens,
// but the verifier trusts the token's OWN `alg` header and honours alg:"none"
// (RFC 7519's unsecured JWT) by accepting the payload with NO signature check. A
// holder of any low-privilege token can re-encode its header as {"alg":"none"},
// flip role to "admin", drop the signature, and be trusted — a pure base64 forgery
// requiring only stdlib. The signing secret is high-entropy (brute force is not the
// path) and disjoint from the flag_3 keystream material.
// The fix is to reject alg:"none" and require a valid HS256 signature.
const jwtSecret = "s8-gridpulse-hs256-Jq7X-signing-2024"

// Claims is the JWT payload.
type Claims struct {
	Sub      int    `json:"sub"`
	Username string `json:"username"`
	Role     string `json:"role"`
	Exp      int64  `json:"exp"`
}

func b64(b []byte) string {
	return base64.RawURLEncoding.EncodeToString(b)
}

func sign(signingInput string) string {
	mac := hmac.New(sha256.New, []byte(jwtSecret))
	mac.Write([]byte(signingInput))
	return b64(mac.Sum(nil))
}

func signToken(c Claims) string {
	header := b64([]byte(`{"alg":"HS256","typ":"JWT"}`))
	pl, _ := json.Marshal(c)
	signingInput := header + "." + b64(pl)
	return signingInput + "." + sign(signingInput)
}

func verifyToken(token string) (*Claims, error) {
	parts := strings.Split(token, ".")
	if len(parts) != 3 {
		return nil, errors.New("malformed token")
	}
	// Trust the token's own declared algorithm (the vulnerability).
	hraw, err := base64.RawURLEncoding.DecodeString(parts[0])
	if err != nil {
		return nil, err
	}
	var hdr struct {
		Alg string `json:"alg"`
	}
	if err := json.Unmarshal(hraw, &hdr); err != nil {
		return nil, err
	}
	// VULNERABLE: alg:"none" tokens are accepted without verifying any signature.
	if hdr.Alg != "none" {
		signingInput := parts[0] + "." + parts[1]
		if !hmac.Equal([]byte(sign(signingInput)), []byte(parts[2])) {
			return nil, errors.New("bad signature")
		}
	}
	raw, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, err
	}
	var c Claims
	if err := json.Unmarshal(raw, &c); err != nil {
		return nil, err
	}
	if c.Exp != 0 && time.Now().Unix() > c.Exp {
		return nil, errors.New("expired")
	}
	return &c, nil
}
