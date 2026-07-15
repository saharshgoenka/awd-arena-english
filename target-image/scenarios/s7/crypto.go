package main

import (
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"encoding/hex"
	"os"
	"strconv"
)

// flag_3 (A02 cryptographic_failures): passwords are stored as a fast, unsalted
// SHA-256 digest despite the column being named "password_hash" (which implies a
// proper password hash like bcrypt). SHA-256 is trivially brute-forceable.
func hashPassword(password string) string {
	sum := sha256.Sum256([]byte(password))
	return hex.EncodeToString(sum[:])
}

func checkPassword(storedHash, password string) bool {
	return storedHash == hashPassword(password)
}

const exportStreamKey = "fleetview-s7-static-export-stream"

func exportPlaintext(item string) ([]byte, bool) {
	switch item {
	case "1", "vehicle-1":
		b, _ := json.Marshal(map[string]any{"id": 1, "name": "Truck Alpha", "status": "active"})
		return b, true
	case "report-1":
		b, _ := json.Marshal(map[string]any{
			"id":    1,
			"owner": "dispatcher",
			"title": "West yard shift summary",
			"body":  "Routine dispatch notes for the west yard. Flagged incident tracked in the linked escalation report.",
		})
		return b, true
	case "vault":
		b, _ := json.Marshal(map[string]any{"vault": "driver-safety", "secret": os.Getenv("FLAG_3")})
		return b, true
	default:
		return nil, false
	}
}

func streamMask(seed string, n int) []byte {
	out := make([]byte, 0, n)
	counter := 0
	for len(out) < n {
		block := sha256.Sum256([]byte(seed + ":" + strconv.Itoa(counter)))
		out = append(out, block[:]...)
		counter++
	}
	return out[:n]
}

func vulnerableExportCiphertext(item string) (string, bool) {
	plain, ok := exportPlaintext(item)
	if !ok {
		return "", false
	}
	mask := streamMask(exportStreamKey, len(plain))
	cipher := make([]byte, len(plain))
	for i := range plain {
		cipher[i] = plain[i] ^ mask[i]
	}
	return base64.RawURLEncoding.EncodeToString(cipher), true
}
