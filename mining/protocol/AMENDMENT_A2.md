# Scientific amendment A2 — evidence expansion

**Decision date:** 2026-10-01
**Decision owner:** Research Lead (autonomous, recorded per Empiria lifecycle rules)
**Status of prior evidence:** the LocaleHazardBench controlled matrix (298 planned / 289 supported observations), the standards layer (141 validations), and their freeze manifests remain frozen and are reused unchanged.

## Motivation (recorded before any new outcome-bearing data were collected)

Feedback on an earlier version of the study named four weaknesses: (i) limited novelty because the core anti-pattern is known, (ii) a researcher-constructed non-probability matrix, (iii) an independent defect corpus of only 14 defects, and (iv) scenario family F6 tested collation portability in memory without database persistence.

A re-audit of the frozen confirmatory retrieval found that the 14-defect corpus was a retrieval artefact rather than a property of the phenomenon: every GitHub query retrieved only the first 30 items sorted by ascending creation date (legacy imported trackers dated 1919-2015), while reported totals were 300-5,043 for well-formed queries, and three queries were malformed and matched 12-34 million issues. The issue corpus therefore cannot support a defensible corpus-level answer and is retired from the confirmatory evidence of the revised study (it remains available in the git history of this repository).

## Amended research questions

- **RQ1 (controlled construct evidence; frozen data):** When contract-conforming text operations are applied to explicit text roles, where do they violate application-domain invariants? Reuses the frozen matrix.
- **RQ2 (real DBMS persistence; new experiment):** Does a change in the collation provider's data invalidate persisted structures in a real DBMS, and do the DBMS's own safeguards detect it? Replaces the in-memory-only interpretation of F6 with an executed PostgreSQL experiment.
- **RQ3 (repository mining; new data):** How do developers repair contract-domain mismatches in practice — in which ecosystems, operations, and text roles, and with which triggers and regression tests?
- **RQ4 (detector evaluation; new experiment):** Which mismatch mechanisms do mainstream static analyzers flag, and do they distinguish text roles?

## Frozen design rules for RQ3 (set before retrieval)

1. Source: GitHub commit search API (`/search/commits`), commit-message search. Query families and slicing are in `protocol/mining_queries.json`; retrieval is bounded and its incompleteness is reported, not engineered away.
2. Unit of analysis: a unique commit lineage. Duplicates are removed by SHA; fork copies are dropped when a non-fork copy exists; cherry-picks/backports are collapsed by a normalized patch fingerprint.
3. Inclusion is decided by a deterministic diff classifier (`src/classify_diffs.py`), not by commit-message keywords: a commit is a *locale-pinning repair* when at least one removed line contains a locale-sensitive text operation and a paired added line in the same hunk replaces it with an explicit locale-neutral, ordinal, invariant, or ASCII-only counterpart. Number/date formatting edits are recorded but out of scope.
4. Message-derived features (Turkic trigger, failure vocabulary, analyzer vocabulary, issue reference) and file-derived features (ecosystem, test-file change) are deterministic regular expressions frozen in the classifier.
5. Classifier precision and text-role/trigger labels are estimated on a seeded random sample coded by two independent coders using `protocol/CODEBOOK_RQ3.md`; agreement is reported before adjudication.
6. No query, rule, or threshold is changed after classifier outputs are inspected; any later change is logged as POST_HOC in `protocol/DEVIATIONS.md`.

## Frozen design rules for RQ2

PostgreSQL is built from official source. A database cluster is initialised with glibc collation data compiled from the glibc 2.27 locale sources (pre-ISO-14651 update) and indexed; the same cluster is then restarted with locale data compiled from the host glibc (2.43) sources, emulating an operating-system upgrade without dump/restore. Outcomes: `amcheck` verdicts, index-scan versus sequential-scan result differences, uniqueness violations, and PostgreSQL's collation-version warnings. An ICU-provider and a `C`-collation control are run under the same protocol.

## Frozen design rules for RQ4

Detectors are executed, not inferred from documentation, on a probe suite derived one-to-one from the frozen F1-F7 semantic cases (`detectors/probes`). Each probe exists in a machine-text and a linguistic-text variant with identical API calls, so a detector that ignores text role must give identical verdicts to both.

## Consequence

The revised manuscript is a new submission. The frozen matrix becomes construct-demonstration evidence; prevalence-like claims are drawn only from the mined corpus and are bounded by its retrieval frame.


> Numbering note: this amendment uses the internal numbering (RQ1 controlled, RQ2 DBMS, RQ3 mining, RQ4 analyzers). In the paper the controlled study is a construct demonstration and the RQs are RQ1 mining, RQ2 analyzers, RQ3 DBMS.
