package main

import (
	"database/sql"
	"os"
)

func scanMeterRows(rows *sql.Rows) []map[string]any {
	out := []map[string]any{}
	for rows.Next() {
		var id int
		var label, status string
		if err := rows.Scan(&id, &label, &status); err != nil {
			continue
		}
		out = append(out, map[string]any{"id": id, "label": label, "status": status})
	}
	return out
}

func reportBody(body string) string {
	return stringsReplace(body, "__FLAG_1__", os.Getenv("FLAG_1"))
}

func stringsReplace(s, old, new string) string {
	for {
		i := indexOf(s, old)
		if i < 0 {
			return s
		}
		s = s[:i] + new + s[i+len(old):]
	}
}

func indexOf(s, sub string) int {
	for i := 0; i+len(sub) <= len(s); i++ {
		if s[i:i+len(sub)] == sub {
			return i
		}
	}
	return -1
}
