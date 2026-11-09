# Round-4 human coding (stratified subset and locale-test validation)

Status (2026-11-09): page built, no human label collected yet. Design fixed before any human label
(`protocol/DEVIATIONS.md`, 2026-11-09).

## Files

- `for_coders/degerlendirici_1.html`, `for_coders/degerlendirici_2.html`: the two files to hand out, one per coder
  (coder name fixed to H1 / H2). Each opens offline in a browser, stores answers in that browser, and exports
  `human_coding_H1_<date>.csv` / `human_coding_H2_<date>.csv`.
- `human_coding_r4.html`: the same page with a free coder-name field (spare copy).
- `key_r4.csv`: maps the blinded IDs to the original items, with stratum and stratum size. Do not give it to the
  coders. Coders must not open `validation/`, `validation/ling/` or `validation/human/responses/`, which hold the
  model labels.
- `build_coding_page_r4.py`: rebuilds the page and the key (seed 20261109, template `../human/template.html`).
- `set3_sample.csv`, `set3_items.jsonl`: the Set-3 sample and what the coders see (written by
  `src/r4_loctest_indicators.py`).
- `analyze_human_r4.py H1.csv H2.csv [reconciled.csv]`: agreement before reconciliation, the list of disagreements
  (`disagreements_r4.csv`), and, with reconciled labels, the stratum-weighted estimates (`results/r4_human.json`).

## Design

Per coder, 260 items:

| Set | Items | Stratum | Questions |
|---|---|---|---|
| 1 | 15 | all validation-sample changes that pin linguistic or mixed text by the model labels (census) | Q1-Q5 |
| 2 | 40 | all opposite-direction lineages coded LOCALE_AWARE on machine or mixed text by the model labels (census) | change, role, Q5 |
| 1, 2 | 105 | random from the remaining 336 items of Sets 1 and 2 | as above |
| 3 | 100 | 50 lineages with a locale-test line, 40 with a test-file change and none, 10 without a test-file change | Q6 |

Q5 asks whether the new behaviour suits how the text is used (the application requirement), not only its role.
Q6 asks whether the commit adds or changes a test that sets, asserts or exercises the locale behaviour of the
repaired operation.

## Procedure

1. Each coder codes alone and does not discuss items with the other coder until both export their CSV.
   Expected effort: about 3 hours per coder.
2. Run `python3 validation/human_r4/analyze_human_r4.py H1.csv H2.csv` and record the agreement (before
   reconciliation) with `run-record.py`.
3. The two coders reconcile the items in `disagreements_r4.csv` by discussion and export a reconciled CSV.
4. Run the script again with the reconciled CSV as the third argument, through `run-record.py`.

## Kodlayıcılar için kısa not (Türkçe)

Size verilen HTML dosyasını tarayıcıda açın. Önce "Kodlama kılavuzu" bölümünü okuyun. Üç set var: Set 1 ve Set 2,
önceki turdaki sorularla aynı. Set 3 yalnızca Q6'yı soruyor: commit, onarılan işlemin locale davranışını sınayan bir
test ekliyor mu? Cevaplar tarayıcıda saklanır. Yine de arada bir "CSV dışa aktar" ile yedek alın. Bitirince CSV
dosyasını gönderin. Diğer kodlayıcıyla, ikiniz de bitirene kadar öğeler hakkında konuşmayın.
