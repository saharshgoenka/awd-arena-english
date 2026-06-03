package main

import (
	"crypto/md5"
	"encoding/hex"
)

// flag_3 (A04 cryptographic_failures): passwords are stored as a fast, unsalted
// MD5 digest despite the column being named "password_hash" (which implies a
// proper password hash like bcrypt). MD5 is trivially brute-forceable offline.
func hashPassword(password string) string {
	sum := md5.Sum([]byte(password))
	return hex.EncodeToString(sum[:])
}

func checkPassword(storedHash, password string) bool {
	return storedHash == hashPassword(password)
}
