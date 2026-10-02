package probes

import (
	"golang.org/x/text/collate"
	"golang.org/x/text/language"
)

// P5Machine — role: machine text (keys written to a sorted index later searched bytewise).
func P5Machine(keys []string) { collate.New(language.Turkish).SortStrings(keys) }
