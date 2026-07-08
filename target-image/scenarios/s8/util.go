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

// publishEnvVar registers an expvar named "environment" so it shows up in the
// /debug/vars dump. flag_2 (A02): this leaks the process environment, but
// envPairs() bounds it so only FLAG_2 (not the other flags) is exposed.
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
