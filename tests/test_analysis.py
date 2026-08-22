from __future__ import annotations

import unittest

from localehazard.analysis import assert_internal_consistency, assert_reported_values, build_summary


class AnalysisTests(unittest.TestCase):
    def test_curated_records_are_consistent(self) -> None:
        assert_internal_consistency()

    def test_reported_aggregate_values(self) -> None:
        assert_reported_values(build_summary())


if __name__ == "__main__":
    unittest.main()
