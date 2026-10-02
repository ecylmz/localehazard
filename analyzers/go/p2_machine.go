package probes

import (
	"strings"
	"unicode"
)

// P2Machine — role: machine text (configuration keyword).
func P2Machine(keyword string) string { return strings.ToLowerSpecial(unicode.TurkishCase, keyword) }
