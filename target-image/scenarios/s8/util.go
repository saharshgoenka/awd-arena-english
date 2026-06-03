package main

import (
	"database/sql"
	"expvar"
	"os"
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

// publishEnvVar registers an expvar named "environment" so it shows up in the
// /debug/vars dump. flag_2 (A02): this leaks the whole process environment,
// FLAG_2 included.
func publishEnvVar() {
	expvar.Publish("environment", expvar.Func(func() any {
		m := map[string]string{}
		for _, kv := range envPairs() {
			m[kv[0]] = kv[1]
		}
		return m
	}))
}

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
