package main

import (
	"crypto/sha256"
	"encoding/hex"
)

// flag_3 (A04 cryptographic_failures): passwords are stored as a fast, unsalted
// SHA-256 digest despite the column being named "password_hash" (which implies a
// proper password hash like bcrypt). SHA-256 is trivially brute-forceable.
func hashPassword(password string) string {
	sum := sha256.Sum256([]byte(password))
	return hex.EncodeToString(sum[:])
}

func checkPassword(storedHash, password string) bool {
	return storedHash == hashPassword(password)
}
