"""Recompute the controlled-demonstration aggregates (Section 3 of the paper) from the curated records."""

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
    scenarios = json.loads((root / "scenarios/cases.json").read_text(encoding="utf-8"))

    outcomes = Counter(row["final_outcome"] for row in observations)
    standards_outcomes = Counter(row["standards_oracle_status"] for row in standards)
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
    }


def assert_internal_consistency(root: Path = ROOT) -> None:
    contracts = read_csv(root / "contracts/api_contracts.csv")
    observations = read_csv(root / "data/controlled/controlled_observations.csv")
    scenarios = json.loads((root / "scenarios/cases.json").read_text(encoding="utf-8"))

    assert len({row["observation_id"] for row in observations}) == len(observations)
    assert {row["case_id"] for row in observations} <= {row["id"] for row in scenarios}
    assert all(row["official_source"].startswith("https://") for row in contracts)


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
}


def assert_reported_values(summary: dict[str, object]) -> None:
    surface = summary["study_surface"]
    outcomes = summary["controlled_outcomes"]
    standards = summary["standards_oracle"]
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
    }
    assert actual == EXPECTED, (actual, EXPECTED)
    assert outcomes["all_supported_contract_conformant"] is True


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
        write_csv(args.output / f"controlled_by_{field}.csv", grouped_outcomes(observations, field))
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
