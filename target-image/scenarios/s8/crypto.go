package main

import (
	"crypto/rand"
	"crypto/md5"
	"crypto/sha256"
	"encoding/hex"
)

// flag_3 (A02 cryptographic_failures): passwords are stored as a fast, unsalted
// MD5 digest despite the column being named "password_hash" (which implies a
// proper password hash like bcrypt). MD5 is trivially brute-forceable offline.
func hashPassword(password string) string {
	sum := md5.Sum([]byte(password))
	return hex.EncodeToString(sum[:])
}

func checkPassword(storedHash, password string) bool {
	return storedHash == hashPassword(password)
}

var exportKeystream = repeatedSHA256("gridpulse-export-key-2024", 512)

func repeatedSHA256(seed string, size int) []byte {
	out := make([]byte, 0, size)
	block := sha256.Sum256([]byte(seed))
	for len(out) < size {
		out = append(out, block[:]...)
	}
	return out[:size]
}

func xorWithKeystream(plaintext string) string {
	raw := []byte(plaintext)
	out := make([]byte, len(raw))
	for i, b := range raw {
		out[i] = b ^ exportKeystream[i%len(exportKeystream)]
	}
	return hex.EncodeToString(out)
}

func randomHex(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}
