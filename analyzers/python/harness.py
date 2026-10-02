import locale, sys
sys.path.insert(0, "python")
locale.setlocale(locale.LC_ALL, "tr_TR.UTF-8")
import p3_machine, p3_linguistic, p5_machine, p5_linguistic
def o(p, r, ok): print(f"python\t{p}\t{r}\t{'CORRECT' if ok else 'CDM'}")
o("P3","machine", p3_machine.config_key("TITLE")=="title"); o("P3","linguistic", p3_linguistic.display_lower("IŞIK")=="ışık")
k=["cam","çay","dağ","Zeta","alpha","İzmir","ırmak","ilk"]
o("P5","machine", p5_machine.sort_index_keys(k)==sorted(k)); o("P5","linguistic", p5_linguistic.sort_for_display(["dağ","çay","cam"])==["cam","çay","dağ"])
