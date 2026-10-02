package probes

import (
	"golang.org/x/text/collate"
	"golang.org/x/text/language"
)

// P4Machine — role: machine text (protocol keyword match).
func P4Machine(token, keyword string) bool {
	return collate.New(language.Turkish, collate.IgnoreCase).CompareString(token, keyword) == 0
}
