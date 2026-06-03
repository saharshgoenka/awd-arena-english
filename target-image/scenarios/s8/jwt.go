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

// flag_5 (A07 authentication_failures): session tokens are HS256 JWTs signed
// with a weak, hardcoded secret. An attacker who obtains any valid token (e.g.
// by logging in with a low-privilege account) can brute-force this secret
// offline, then forge a token with role="admin" to reach admin-only routes.
// The fix is a high-entropy secret loaded from a secret store, not a constant.
const jwtSecret = "gridpulse"

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
	signingInput := parts[0] + "." + parts[1]
	if !hmac.Equal([]byte(sign(signingInput)), []byte(parts[2])) {
		return nil, errors.New("bad signature")
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
