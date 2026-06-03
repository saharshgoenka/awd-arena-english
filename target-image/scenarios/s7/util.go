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
			pairs = append(pairs, [2]string{e[:i], e[i+1:]})
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
