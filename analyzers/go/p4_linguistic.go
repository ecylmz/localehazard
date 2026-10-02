package probes

import (
	"golang.org/x/text/collate"
	"golang.org/x/text/language"
)

// P4Linguistic — role: linguistic text (user search term against a Turkish name).
func P4Linguistic(query, name string) bool {
	return collate.New(language.Turkish, collate.IgnoreCase).CompareString(query, name) == 0
}
