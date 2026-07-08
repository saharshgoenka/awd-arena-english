package main

import (
	"database/sql"
	"os"
	"runtime"
	"strings"
)

func envPairs() [][2]string {
	pairs := [][2]string{}
	for _, e := range os.Environ() {
		if i := strings.IndexByte(e, '='); i >= 0 {
			k := e[:i]
			// A02 is a BOUNDED leak: expose only FLAG_2, not the whole flag set.
			// Dumping every FLAG_* handed an attacker all 5 flags in one request.
			if strings.HasPrefix(k, "FLAG_") && k != "FLAG_2" {
				continue
			}
			pairs = append(pairs, [2]string{k, e[i+1:]})
		}
	}
	return pairs
}

func goVersion() string {
	return runtime.Version()
}

func scanVehicleRows(rows *sql.Rows) []map[string]any {
	out := []map[string]any{}
	for rows.Next() {
		var id int
		var name, status string
		if err := rows.Scan(&id, &name, &status); err != nil {
			continue
		}
		out = append(out, map[string]any{"id": id, "name": name, "status": status})
	}
	return out
}
