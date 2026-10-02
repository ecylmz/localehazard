package probes

import ("fmt"; "sort"; "testing"; "reflect")

func o(p, r string, ok bool) { s := "CDM"; if ok { s = "CORRECT" }; fmt.Printf("go\t%s\t%s\t%s\n", p, r, s) }

func TestHarness(t *testing.T) {
	o("P2", "machine", P2Machine("TITLE") == "title"); o("P2", "linguistic", P2Linguistic("IŞIK") == "ışık")
	o("P3", "machine", P3Machine("TITLE") == "title"); o("P3", "linguistic", P3Linguistic("IŞIK") == "ışık")
	o("P4", "machine", P4Machine("FILE", "file")); o("P4", "linguistic", P4Linguistic("IŞIK", "ışık") && !P4Linguistic("ISIK", "ışık"))
	k := []string{"cam", "çay", "dağ", "Zeta", "alpha", "İzmir", "ırmak", "ilk"}; bw := append([]string{}, k...); sort.Strings(bw)
	k1 := append([]string{}, k...); P5Machine(k1); o("P5", "machine", reflect.DeepEqual(k1, bw))
	k2 := []string{"dağ", "çay", "cam"}; P5Linguistic(k2); o("P5", "linguistic", reflect.DeepEqual(k2, []string{"cam", "çay", "dağ"}))
}
