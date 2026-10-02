# RQ3 codebook — validation of the deterministic diff classifier

Frozen 2026-10-01 before the validation sample was drawn. Coders see, for each item: repository name, commit subject and message, the classifier's matched removed/added line pairs (if any), and up to 120 lines of the commit patch around changed text operations. Coders do not see the other coder's labels, the classifier's derived message features, or any aggregate result.

## Q1 GENUINE — does the commit change locale- or culture-dependent text-processing behaviour?

- `YES`: at least one changed line alters which locale, culture, collation, case-mapping table, comparison semantics, character classification, or process-locale setting a text operation uses (in either direction).
- `NO`: the matched change does not alter such behaviour (e.g. a refactoring that preserves the call, a translation/resource-file change, a formatting-only change of numbers or dates, a performance change between semantically equivalent calls, vendored or generated code merely moved).
- `UNCLEAR`: the evidence shown is insufficient.

Number and date formatting/parsing changes (e.g. `String.format(Locale.ROOT, ...)`, `ToString(CultureInfo.InvariantCulture)` on numbers) are `NO` for this study's scope.

## Q2 ROLE — role of the text whose processing changed (only if Q1 = YES)

- `MACHINE`: text that a program, protocol, or file format interprets: identifiers, keys, enum or constant names, protocol/HTTP header tokens, keywords, configuration keys, file names/paths/extensions, MIME types, SQL/HTML/XML/JSON names, command-line options, language tags, hexadecimal or encoded values, hostnames, e-mail local parts used as identifiers.
- `LINGUISTIC`: human-language text shown to, searched by, or sorted for people (names, titles, messages, user content).
- `MIXED`: the commit changes both roles.
- `UNCLEAR`: role cannot be determined from the evidence.

## Q3 TRIGGER — what prompted the change (only if Q1 = YES)

- `OBSERVED_FAILURE`: the message, linked issue reference, or added test indicates an actual malfunction (bug report, failing test, crash, wrong output, a named locale symptom such as Turkish dotless i).
- `TOOL_DRIVEN`: the message names a static analyzer, linter, IDE inspection, or automated refactoring recipe as the reason.
- `PREVENTIVE`: proactive hardening or cleanup without a reported failure or tool.
- `UNCLEAR`.

If a message names both a failure and a tool, code `OBSERVED_FAILURE`.

## Q4 MECHANISM — closest frozen scenario family (only if Q1 = YES)

- `F1` linguistic tailoring required (locale-aware mapping/comparison needed for human text);
- `F2` machine/canonical mapping (case mapping of machine text must be locale-neutral);
- `F3` comparison semantics (equality/ordering/case-insensitive comparison semantics chosen for a domain);
- `F4` normalization interaction;
- `F5` native/process-locale contamination (C library or process locale, environment variables such as `LC_ALL`);
- `F6` collation/provider persistence (sort order or collation persisted in indexes, files, or databases, or expected to be stable across environments);
- `OTHER` (locale-dependent behaviour outside F1–F6);
- choose the single best family; if both F2 and F3 apply (e.g. lower-casing two strings to compare them), choose `F3`.

## Reporting

Agreement is reported as raw agreement and Cohen's kappa on the independent labels, before adjudication. Q2–Q4 agreement is computed on items both coders labelled Q1 = `YES`. Classifier precision is the adjudicated share of classifier-included items with Q1 = `YES`.
