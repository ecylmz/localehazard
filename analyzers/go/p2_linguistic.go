package probes

import (
	"strings"
	"unicode"
)

// P2Linguistic — role: linguistic text (Turkish user text).
func P2Linguistic(userText string) string {
	return strings.ToLowerSpecial(unicode.TurkishCase, userText)
}
