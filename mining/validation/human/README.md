# Blinded re-coding page (round 3)

**Status (2026-10-31):** no human coding was collected. The page was completed by two language-model coders (D1 = OpenAI Codex gpt-6.1-sol, high; D2 = Anthropic Claude Opus 5.5, high); exports and provenance in `responses/`, analysis in `src/r3_recoding.py`. The page remains available for human re-coding.

- `for_coders/degerlendirici_1.html`, `for_coders/degerlendirici_2.html` — the files to hand out, one per coder; identical items and order, coder name fixed to D1 / D2 (exports `human_coding_D1_<date>.csv`, `human_coding_D2_<date>.csv`).
- `human_coding.html` — same page with a free coder-name field (spare copy).
- `key.csv` — maps blinded IDs (A###, B###) to the original sample IDs and SHAs. **Do not give it to the coders.**
- `build_coding_page.py` + `template.html` — regenerate the page (seed 20261030).
- `analyze_human.py coder1.csv coder2.csv` — human–human and human–LLM agreement (`agreement.json`) and the items to reconcile (`disagreements.csv`).

Design (fixed 2026-10-30, before any human label):
- Set 1: all 210 validation items (150 included + 60 excluded), message + patch excerpt only, so excluded items are not recognizable by missing classifier matches. Questions Q1–Q4 of `protocol/CODEBOOK_RQ3.md` plus Q5 FIT (FIT / MISFIT / NEUTRAL / CANNOT_TELL): does the new behaviour suit how the text is used, considering Turkish, Azerbaijani, or Lithuanian users.
- Set 2: all 181 opposite-direction lineages, with matched edit lines: change type, role, Q5.
- Two human coders code independently; agreement is computed before reconciliation; disagreements are reconciled by discussion between the two humans. Human labels replace the LLM labels for the paper's role-fit, trigger, precision, and recall figures; human–LLM agreement is reported.
- Coders should not consult `validation/` files of the replication package, which contain the LLM labels by SHA.
