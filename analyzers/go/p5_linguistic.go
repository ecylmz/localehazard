package probes

import (
	"golang.org/x/text/collate"
	"golang.org/x/text/language"
)

// P5Linguistic — role: linguistic text (names sorted for display to a Turkish user).
func P5Linguistic(names []string) { collate.New(language.Turkish).SortStrings(names) }
