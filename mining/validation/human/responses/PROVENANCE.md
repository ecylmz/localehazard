# Provenance of D1 / D2 exports (checked 2026-10-31)

These are NOT human labels and must not be reported as human coding.
D1 = OpenAI Codex CLI, gpt-6.1-sol, reasoning high; D2 = Anthropic Claude Opus 5.5, reasoning high (stated by the author, 2026-10-31). The author confirmed that neither re-coder had access to the original labels or to the validation/ files.
- Coder pages were sent at 2026-10-30 19:58Z; D2 exported all 391 items complete at 20:13Z, D1 at 20:26Z (one timestamp for every row in each file, i.e. bulk-imported, not coded item by item in the page).
- Every D1 note starts with "Yapay zekâ değerlendirmesi" (AI assessment); D2 notes cite `gh` lookups.
- `agreement_D1_D2.json` / `disagreements_D1_D2.csv`: output of `../analyze_human.py` on these files. The "human_human" and "*_vs_llm" keys are script names only: read them as model–model agreement.
