from __future__ import annotations

import base64
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PythonAdapterSmokeTest(unittest.TestCase):
    def test_root_lowercase_smoke(self) -> None:
        encoded = base64.b64encode("FILE".encode()).decode()
        process = subprocess.run(
            [sys.executable, str(ROOT / "adapters/python_adapter.py"), "unicode_default", "lower", "root", encoded],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        result = json.loads(process.stdout)
        self.assertEqual(base64.b64decode(result["value_b64"]).decode(), "file")


if __name__ == "__main__":
    unittest.main()
