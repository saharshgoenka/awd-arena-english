//go:build tools

// This file is excluded from normal builds. It exists so `go mod tidy` keeps
// golang.org/x/crypto in the module graph: the unpatched app does not import
// bcrypt, but the defender's flag_3 patch (crypto.go) switches to it, and the
// in-container rebuild must succeed offline.
package main

import _ "golang.org/x/crypto/bcrypt"
