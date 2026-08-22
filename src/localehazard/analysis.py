"""Recompute the paper's aggregate values from the curated source records."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SIGNATURE_FIELDS = (
    "backend_family",
    "api_class",
    "operation",
    "locale_requested",
    "expected_application",
    "actual_escaped",
    "actual_relation",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def agreement(labels: list[dict[str, str]], part: str, field: str) -> dict[str, object]:
    rows = [row for row in labels if row["task_part"] == part and row["label_field"] == field]
    agreements = sum(row["primary_label"] == row["second_label"] for row in rows)
    return {
        "agreements": agreements,
        "total": len(rows),
        "percent": round(100 * agreements / len(rows), 1),
    }


def grouped_outcomes(observations: list[dict[str, str]], field: str) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for value in sorted({row[field] for row in observations}):
        rows = [row for row in observations if row[field] == value]
        outcomes = Counter(row["final_outcome"] for row in rows)
        eligible = outcomes["application_correct"] + outcomes["cdm_hazard"]
        result.append(
            {
                field: value,
                "observations": len(rows),
                "eligible": eligible,
                "application_correct": outcomes["application_correct"],
                "cdm_hazards": outcomes["cdm_hazard"],
                "unsupported": outcomes["unsupported"],
                "constructed_proportion": round(outcomes["cdm_hazard"] / eligible, 6) if eligible else "",
            }
        )
    return result


def unique_signatures(observations: list[dict[str, str]]) -> list[dict[str, object]]:
    counts = Counter(
        tuple(row[field] for field in SIGNATURE_FIELDS)
        for row in observations
        if row["final_outcome"] == "cdm_hazard"
    )
    return [dict(zip(SIGNATURE_FIELDS, key)) | {"row_count": count} for key, count in sorted(counts.items())]


def build_summary(root: Path = ROOT) -> dict[str, object]:
    contracts = read_csv(root / "contracts/api_contracts.csv")
    observations = read_csv(root / "data/controlled/controlled_observations.csv")
    standards = read_csv(root / "data/controlled/standards_validation.csv")
    screening = read_csv(root / "data/defects/screening.csv")
    retained = read_csv(root / "data/defects/retained.csv")
    labels = read_csv(root / "data/defects/adjudicated_final_labels.csv")
    family_correspondence = read_csv(root / "data/defects/family_correspondence.csv")
    scenarios = json.loads((root / "scenarios/cases.json").read_text(encoding="utf-8"))

    outcomes = Counter(row["final_outcome"] for row in observations)
    standards_outcomes = Counter(row["standards_oracle_status"] for row in standards)
    mechanism_counts = Counter(row["mechanism_family"] for row in retained)
    issue_rows = [
        row for row in labels
        if row["task_part"] == "C_correspondence" and row["label_field"] == "correspondence"
    ]
    issue_correspondence = Counter(row["final_label"] for row in issue_rows)
    family_counts = Counter(row["correspondence"] for row in family_correspondence)
    signatures = unique_signatures(observations)

    supported = outcomes["application_correct"] + outcomes["cdm_hazard"]
    return {
        "study_surface": {
            "ecosystems": len({row["ecosystem"] for row in contracts}),
            "api_contract_records": len(contracts),
            "controlled_cases": len(scenarios),
            "controlled_observations": len(observations),
        },
        "controlled_outcomes": {
            "application_correct": outcomes["application_correct"],
            "cdm_hazard": outcomes["cdm_hazard"],
            "unsupported": outcomes["unsupported"],
            "supported_contract_resolved": supported,
            "all_supported_contract_conformant": all(
                row["api_contract_status"] == "conformant"
                for row in observations
                if row["final_outcome"] != "unsupported"
            ),
            "constructed_cdm_proportion": round(outcomes["cdm_hazard"] / supported, 4),
            "unique_failure_signatures": len(signatures),
        },
        "standards_oracle": {
            "validations": len(standards),
            "applicable_conformant": standards_outcomes["conformant"],
            "not_applicable": standards_outcomes["not_applicable"],
        },
        "defect_corpus": {
            "screened_candidates": len(screening),
            "retained_defects": len(retained),
            "excluded_candidates": len(screening) - len(retained),
            "mechanism_families": len(mechanism_counts),
            "mechanism_counts": dict(sorted(mechanism_counts.items())),
        },
        "coding_agreement": {
            "screening": agreement(labels, "A_screening", "screening_decision"),
            "mechanism": agreement(labels, "B_mechanism", "mechanism_family"),
            "correspondence": agreement(labels, "C_correspondence", "correspondence"),
        },
        "independent_correspondence": {
            "families": len(family_correspondence),
            "direct_families": family_counts["direct"],
            "direct_plus_partial_families": family_counts["direct"] + family_counts["partial"],
            "issues": len(issue_rows),
            "direct_issues": issue_correspondence["direct"],
            "direct_plus_partial_issues": issue_correspondence["direct"] + issue_correspondence["partial"],
        },
        "family_classification_sensitivity": {
            "primary_5_families": {"families": 5, "direct": 2, "direct_plus_partial": 4},
            "merge_managed_and_native_ambient_locale": {"families": 4, "direct": 1, "direct_plus_partial": 3},
            "split_backend_mapping_from_collation": {"families": 6, "direct": 2, "direct_plus_partial": 4},
        },
    }


def assert_internal_consistency(root: Path = ROOT) -> None:
    contracts = read_csv(root / "contracts/api_contracts.csv")
    observations = read_csv(root / "data/controlled/controlled_observations.csv")
    screening = read_csv(root / "data/defects/screening.csv")
    retained = read_csv(root / "data/defects/retained.csv")
    labels = read_csv(root / "data/defects/adjudicated_final_labels.csv")
    scenarios = json.loads((root / "scenarios/cases.json").read_text(encoding="utf-8"))
    query_config = json.loads((root / "data/defects/search_queries.json").read_text(encoding="utf-8"))

    assert len({row["observation_id"] for row in observations}) == len(observations)
    assert {row["case_id"] for row in observations} <= {row["id"] for row in scenarios}
    assert all(row["official_source"].startswith("https://") for row in contracts)
    assert all(row["screen_decision"] == "include" for row in retained)
    assert {row["source_url"] for row in retained} == {
        row["source_url"] for row in screening if row["screen_decision"] == "include"
    }
    configured_query_ids = {
        row["id"]
        for section in ("queries", "repair_queries", "tracker_queries")
        for row in query_config[section]
    }
    observed_query_ids = {
        query_id
        for row in screening
        for query_id in row["discovery_queries"].split(";")
        if query_id
    }
    assert observed_query_ids <= configured_query_ids
    retained_urls = {row["source_url"] for row in retained}
    for part in ("B_mechanism", "C_correspondence"):
        assert {
            row["source_url"] for row in labels if row["task_part"] == part
        } == retained_urls


EXPECTED = {
    "ecosystems": 9,
    "api_contract_records": 42,
    "controlled_cases": 21,
    "controlled_observations": 298,
    "application_correct": 183,
    "cdm_hazard": 106,
    "unsupported": 9,
    "supported_contract_resolved": 289,
    "unique_failure_signatures": 67,
    "standards_validations": 141,
    "standards_conformant": 113,
    "standards_not_applicable": 28,
    "screened_candidates": 218,
    "retained_defects": 14,
    "mechanism_families": 5,
    "direct_families": 2,
    "direct_plus_partial_families": 4,
    "direct_issues": 9,
    "direct_plus_partial_issues": 13,
}


def assert_reported_values(summary: dict[str, object]) -> None:
    surface = summary["study_surface"]
    outcomes = summary["controlled_outcomes"]
    standards = summary["standards_oracle"]
    defects = summary["defect_corpus"]
    correspondence = summary["independent_correspondence"]
    actual = {
        "ecosystems": surface["ecosystems"],
        "api_contract_records": surface["api_contract_records"],
        "controlled_cases": surface["controlled_cases"],
        "controlled_observations": surface["controlled_observations"],
        "application_correct": outcomes["application_correct"],
        "cdm_hazard": outcomes["cdm_hazard"],
        "unsupported": outcomes["unsupported"],
        "supported_contract_resolved": outcomes["supported_contract_resolved"],
        "unique_failure_signatures": outcomes["unique_failure_signatures"],
        "standards_validations": standards["validations"],
        "standards_conformant": standards["applicable_conformant"],
        "standards_not_applicable": standards["not_applicable"],
        "screened_candidates": defects["screened_candidates"],
        "retained_defects": defects["retained_defects"],
        "mechanism_families": defects["mechanism_families"],
        "direct_families": correspondence["direct_families"],
        "direct_plus_partial_families": correspondence["direct_plus_partial_families"],
        "direct_issues": correspondence["direct_issues"],
        "direct_plus_partial_issues": correspondence["direct_plus_partial_issues"],
    }
    assert actual == EXPECTED, (actual, EXPECTED)
    assert outcomes["all_supported_contract_conformant"] is True
    assert summary["coding_agreement"] == {
        "screening": {"agreements": 37, "total": 43, "percent": 86.0},
        "mechanism": {"agreements": 13, "total": 14, "percent": 92.9},
        "correspondence": {"agreements": 12, "total": 14, "percent": 85.7},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "out/analysis")
    parser.add_argument("--check", action="store_true", help="fail if source records diverge from reported values")
    args = parser.parse_args(argv)

    assert_internal_consistency(ROOT)
    summary = build_summary(ROOT)
    if args.check:
        assert_reported_values(summary)

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    observations = read_csv(ROOT / "data/controlled/controlled_observations.csv")
    write_csv(args.output / "unique_failure_signatures.csv", unique_signatures(observations))
    for field in ("scenario_family", "ecosystem", "api_class", "backend_family", "text_domain"):
        write_csv(args.output / f"rq2_by_{field}.csv", grouped_outcomes(observations, field))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
