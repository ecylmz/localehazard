package probes

import "strings"

// P3Machine — role: machine text (configuration keyword).
func P3Machine(keyword string) string { return strings.ToLower(keyword) }
