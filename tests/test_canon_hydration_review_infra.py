from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_SCRIPT = REPO_ROOT / "scripts" / "build_canon_hydration_queue.py"
PACKET_SCRIPT = REPO_ROOT / "scripts" / "build_pilot_scene_review_packets.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate_phase1.py"
TEST_TMP_ROOT = REPO_ROOT / ".tmp_source_spine_tests"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(path for path in root.rglob("*") if path.is_file()):
        digest.update(str(file_path.relative_to(root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class CanonHydrationReviewInfraTests(unittest.TestCase):
    def setUp(self) -> None:
        TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp_dir = TEST_TMP_ROOT / self._testMethodName
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

        for name in ["source", "planning", "visual_dev", "prompts", "docs", "schemas"]:
            shutil.copytree(REPO_ROOT / name, self.temp_dir / name)
        (self.temp_dir / "evidence" / "validation_reports").mkdir(parents=True, exist_ok=True)
        (self.temp_dir / "evidence" / "article3").mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_queue_and_packets_are_deterministic_and_validation_safe(self) -> None:
        master_path = self.temp_dir / "source" / "screenplay" / "closing_price.fountain"
        master_hash_before = sha256_file(master_path)
        queue_json = self.temp_dir / "evidence" / "validation_reports" / "canon_hydration_queue.json"
        queue_md = self.temp_dir / "evidence" / "validation_reports" / "canon_hydration_queue.md"
        packet_root = self.temp_dir / "evidence" / "article3" / "pilot_scene_review_packets"

        queue_cmd = [
            sys.executable,
            str(QUEUE_SCRIPT),
            "--root",
            str(self.temp_dir),
            "--report-json",
            "evidence/validation_reports/canon_hydration_queue.json",
            "--report-md",
            "evidence/validation_reports/canon_hydration_queue.md",
        ]
        packet_cmd = [
            sys.executable,
            str(PACKET_SCRIPT),
            "--scenes-root",
            str(self.temp_dir / "planning" / "scenes"),
            "--output-root",
            str(packet_root),
        ]

        subprocess.run(queue_cmd, check=True, cwd=REPO_ROOT)
        subprocess.run(packet_cmd, check=True, cwd=REPO_ROOT)
        first_queue_json_hash = sha256_file(queue_json)
        first_queue_md_hash = sha256_file(queue_md)
        first_packet_hash = hash_tree(packet_root)

        subprocess.run(queue_cmd, check=True, cwd=REPO_ROOT)
        subprocess.run(packet_cmd, check=True, cwd=REPO_ROOT)
        second_queue_json_hash = sha256_file(queue_json)
        second_queue_md_hash = sha256_file(queue_md)
        second_packet_hash = hash_tree(packet_root)

        self.assertEqual(master_hash_before, sha256_file(master_path))
        self.assertEqual(first_queue_json_hash, second_queue_json_hash)
        self.assertEqual(first_queue_md_hash, second_queue_md_hash)
        self.assertEqual(first_packet_hash, second_packet_hash)

        queue_payload = json.loads(queue_json.read_text(encoding="utf-8"))
        self.assertEqual(5, len(queue_payload["queue"]["A"]))
        # Deterministic count updated after PROD-LINE-14D added WD005/WD006 planning wardrobe records.
        self.assertEqual(20, len(queue_payload["queue"]["B"]))
        self.assertEqual(5, len(queue_payload["queue"]["C"]))
        self.assertEqual(115, len(queue_payload["queue"]["D"]))
        self.assertTrue((packet_root / "SC0001.md").exists())

        packet_text = (packet_root / "SC0001.md").read_text(encoding="utf-8")
        self.assertIn("Do not guess beyond source text.", packet_text)
        self.assertIn("## Explicit Human Review Questions", packet_text)

        validate_cmd = [
            sys.executable,
            str(VALIDATE_SCRIPT),
            "--source-dir",
            str(self.temp_dir / "source"),
            "--planning-dir",
            str(self.temp_dir / "planning"),
            "--prompts-dir",
            str(self.temp_dir / "prompts"),
            "--schemas-dir",
            str(self.temp_dir / "schemas"),
            "--evidence-dir",
            str(self.temp_dir / "evidence"),
            "--report-json",
            str(self.temp_dir / "evidence" / "validation_reports" / "phase1_validation_report.json"),
            "--report-md",
            str(self.temp_dir / "evidence" / "validation_reports" / "phase1_validation_report.md"),
        ]
        subprocess.run(validate_cmd, check=True, cwd=REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
