package probes

import "strings"

// P3Linguistic — role: linguistic text (Turkish user text).
func P3Linguistic(userText string) string { return strings.ToLower(userText) }
